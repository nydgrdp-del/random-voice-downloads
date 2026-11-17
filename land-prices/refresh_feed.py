"""Refresh public market facts. Writes a candidate; publishing is a separate authenticated step."""
import argparse,base64,gzip,hashlib,json,subprocess,sys,tempfile,urllib.request
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent
FEED='https://raw.githubusercontent.com/nydgrdp-del/random-voice-downloads/main/land-prices/latest.json'
ALIASES={'الانبار':'الأنبار','اربيل':'أربيل','الديوانية':'القادسية','بصرة':'البصرة'}
def download(url):
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'IraqLandResearch/1.0'}),timeout=60) as r:return r.read()
def pack(data):
 raw=json.dumps(data,ensure_ascii=False,separators=(',',':')).encode();body=gzip.compress(raw,mtime=0)
 return {'format':'iraq-land-feed-v1','encoding':'gzip-base64','updatedAt':data.get('lastRefreshAt',data['collectedAt']),'records':len(data['rows']),'sha256':hashlib.sha256(body).hexdigest(),'payload':base64.b64encode(body).decode()}
def unpack(blob):
 obj=json.loads(blob)
 if obj.get('format')=='iraq-land-feed-v1':
  raw=base64.b64decode(obj['payload']);assert hashlib.sha256(raw).hexdigest()==obj['sha256'];obj=json.loads(gzip.decompress(raw))
 assert obj['version']==2 and isinstance(obj['rows'],list) and len(obj['rows'])>0
 return obj
def merge(old,incoming,stamp):
 out={r['id']:r for r in old}
 for r in incoming:
  r['province']=ALIASES.get(r['province'],r['province']);r.setdefault('priceBasis','total')
  if not isinstance(r.get('price'),(float,int)) or not 0<r['price']<=1e15:continue
  r['availability']='seen';prev=out.get(r['id'])
  if prev:
   history=prev.get('priceHistory',[])
   if (prev.get('price'),prev.get('currency'),prev.get('priceBasis'))!=(r.get('price'),r.get('currency'),r.get('priceBasis')):
    history=(history+[{'price':prev['price'],'currency':prev['currency'],'priceBasis':prev.get('priceBasis','total'),'observedAt':prev.get('observedAt')}])[-12:];r['priceChangedAt']=stamp
   elif prev.get('priceChangedAt'):r['priceChangedAt']=prev['priceChangedAt']
   if history:r['priceHistory']=history
  out[r['id']]=r
 return list(out.values())
def run(base,output):
 now=datetime.now(timezone.utc).isoformat();data=unpack(Path(base).read_bytes()) if base else unpack(download(FEED));reports=[]
 with tempfile.TemporaryDirectory(prefix='iraq-land-refresh-') as work:
  root=Path(work);raw=root/'raw';raw.mkdir()
  for slug,name,robot in [('shanashel','listings','https://shanashel.com/robots.txt'),('aiqarat','aiqarat','https://aiqarat.com/robots.txt')]:
   try:
    (raw/('shanashel-robots.txt' if slug=='shanashel' else 'aiqarat-robots.html')).write_bytes(download(robot))
    script=HERE/('collect_'+slug+'.py');(root/script.name).write_bytes(script.read_bytes())
    result=subprocess.run([sys.executable,str(root/script.name)],cwd=root,capture_output=True,text=True,timeout=3000)
    if result.returncode:raise RuntimeError(result.stderr[-400:])
    incoming=json.loads((root/(name+'.json')).read_text())
    if not incoming:raise RuntimeError('No parsed records; keep previous source data')
    # Keep old rows absent from a scan: absence alone is not evidence of a sold property.
    data['rows']=merge(data['rows'],incoming,now)
    report={'source':slug,'status':'updated','recordsSeen':len(incoming),'checkedAt':now}
    log=raw/('collection-log.json' if slug=='shanashel' else 'aiqarat-log.json')
    if log.exists():report['scanLog']=json.loads(log.read_text())
    reports.append(report)
   except Exception as e:reports.append({'source':slug,'status':'failed','checkedAt':now,'error':str(e)[:400]})
  # Government tables are historical tax references. Do not auto-relabel new PDFs as current market prices.
  try:
   official='https://tax.mof.gov.iq/wp-content/uploads/2024/02/%D9%86%D9%82%D9%84-%D9%85%D9%84%D9%83%D9%8A%D8%A9.rar'
   digest=hashlib.sha256(download(official)).hexdigest();prior=data.get('officialArchiveSHA256')
   data['officialArchiveSHA256']=digest;reports.append({'source':'official','status':'checked','checkedAt':now,'changed':bool(prior and prior!=digest),'reviewRequired':bool(prior and prior!=digest)})
  except Exception as e:reports.append({'source':'official','status':'failed','error':str(e)[:400]})
 data['sourceChecks']=reports;data['lastAttemptAt']=now
 if any(x['status']=='updated' for x in reports):data['lastRefreshAt']=now
 data['refreshIntervalDays']=15
 out=Path(output);out.write_text(json.dumps(pack(data),ensure_ascii=False,separators=(',',':')))
 (out.parent/'refresh-report.json').write_text(json.dumps({'rows':len(data['rows']),'sources':reports},ensure_ascii=False,indent=2))
 print(json.dumps({'candidate':str(out),'rows':len(data['rows']),'sources':[{k:v for k,v in r.items() if k!='scanLog'}for r in reports]},ensure_ascii=False))
 return any(x['status']=='updated' for x in reports)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--base');parser.add_argument('--output',default='latest-candidate.json');args=parser.parse_args()
 if not run(args.base,args.output):sys.exit(2)
