import json,re,time,urllib.request,urllib.error,urllib.robotparser
from pathlib import Path
from datetime import datetime,timezone
BASE='https://shanashel.com'
RAW=Path(__file__).parent/'raw'; RAW.mkdir(exist_ok=True)
robot=urllib.robotparser.RobotFileParser();robot.parse((RAW/'shanashel-robots.txt').read_text().splitlines())
def extract(html,key):
 chunks=[]
 for m in re.finditer(r'self\.__next_f\.push\((\[1,.*?\])\)</script>',html):
  try:chunks.append(json.loads(m.group(1))[1])
  except ValueError:pass
 flight=''.join(chunks);needle='"'+key+'":';p=flight.find(needle)
 if p<0:return None
 return json.JSONDecoder().raw_decode(flight[p+len(needle):])[0]
def fetch(page):
 url=BASE+'/properties/sell-land'+('?page='+str(page) if page>1 else '')
 if not robot.can_fetch('ChatGPT-User',url):raise ValueError('robots denied '+url)
 p=RAW/f'shanashel-page-{page}.html'
 
 if not p.exists():
  req=urllib.request.Request(url,headers={'User-Agent':'IraqLandResearch/1.0 (public listing price research)'})
  with urllib.request.urlopen(req,timeout=40) as r:p.write_bytes(r.read())
 return p.read_text()
allrows={};stats=[]
for page in range(1,301):
 try:
  html=fetch(page);props=extract(html,'initialProperties') or [];labels=extract(html,'propertyLabelsMap') or {}
  added=0
  for p in props:
   lab=labels.get(str(p['id']),{});currency={'دينار عراقي':'IQD','دولار أمريكي':'USD'}.get(lab.get('currency'),'OTHER')
   if p['id'] in allrows:continue
   # Persist factual pricing fields only. Do not copy seller contacts, prose or images.
   raw_area=p.get('area');unit=p.get('area_measurement_unit');sqm=p.get('area_sqm') if unit==1 else None
   row={'id':'sh-'+str(p['id']),'sourceName':'شناشيل','sourceUrl':BASE+'/property/'+str(p['id']),'sourceType':'listing','province':{'الديوانية':'القادسية','اربيل':'أربيل'}.get(lab.get('province'),lab.get('province','غير محدد')),'district':lab.get('city','غير محدد'),'use':lab.get('category','غير محدد'),'currency':currency,'price':p.get('price_total'),'area':sqm,'rawArea':raw_area,'areaUnit':'م²' if unit==1 else 'غير محسومة','date':str(p.get('create_date',''))[:10],'observedAt':datetime.now(timezone.utc).date().isoformat(),'title':'غير محدد','street':'غير محدد','kind':'عرض','review':[]}
   if isinstance(p.get('location_lat'),(int,float)) and isinstance(p.get('location_lng'),(int,float)) and 29<=p['location_lat']<=38 and 38<=p['location_lng']<=49:
    row.update(latitude=p['location_lat'],longitude=p['location_lng'],locationAccuracy='advertiser_approximate')
   if unit!=1:row['review'].append('وحدة المساحة تحتاج مراجعة؛ مستبعد من الحساب')
   if p.get('price_check') not in (None,'ok'):row['review'].append('المصدر أشار إلى سعر يحتاج مراجعة')
   if currency=='OTHER':row['review'].append('العملة غير محسومة')
   if sqm and row['price'] and currency=='IQD' and not 10000<=row['price']/sqm<=50000000:row['review'].append('سعر المتر خارج نطاق فحص أولي واسع؛ راجع الإعلان')
   allrows[p['id']]=row;added+=1
  stats.append({'page':page,'rows':len(props),'added':added});print(page,len(props),added,flush=True)
  Path(__file__).with_name('listings.json').write_text(json.dumps(list(allrows.values()),ensure_ascii=False,indent=2))
  if not props or not added:break
  if not re.search(r'rel="next"',html):break
  time.sleep(.25)
 except Exception as e:
  print('STOP',page,str(e),flush=True);stats.append({'page':page,'error':str(e)});break
(RAW/'collection-log.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2))
