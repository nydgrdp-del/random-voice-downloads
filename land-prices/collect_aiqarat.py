from datetime import datetime, timezone
import urllib.request,urllib.robotparser,concurrent.futures,time,re,json,hashlib
from pathlib import Path
from lxml import html
ROOT=Path(__file__).parent;RAW=ROOT/'raw'
robot=urllib.robotparser.RobotFileParser();robot.parse((RAW/'aiqarat-robots.html').read_text().splitlines())
def text(el,xp):return ' '.join(' '.join(el.xpath(xp)).split())
def number(s):
 s=s.translate(str.maketrans('٠١٢٣٤٥٦٧٨٩','0123456789'));m=re.search(r'\d[\d,.]*',s);return float(m.group().replace(',','')) if m else None
def page(i):
 p=RAW/f'aiqarat-page-{i}.html';u='https://aiqarat.com/status/for-sale/'+(f'page/{i}/' if i>1 else '')
 if not robot.can_fetch('ChatGPT-User',u):return []
 if not p.exists():
  with urllib.request.urlopen(u,timeout=45) as r:p.write_bytes(r.read())
 doc=html.fromstring(p.read_text());rows=[]
 for el in doc.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," item-wrap ")]'):
  typ=text(el,'.//*[contains(@class,"h-type")]//text()');name=text(el,'.//*[contains(@class,"item-title")]//a/text()')
  if not re.search('أرض|ارض|أراضي|اراضي|مزرعة',typ):continue
  # Exclude buildings advertised as plots.
  if re.search('دار|بيت|بناية|عمارة|مشيد',name):continue
  ps=text(el,'.//*[contains(concat(" ",@class," ")," price ")]/text()');v=number(ps)
  if not v or v<1000:continue
  currency='USD' if '$' in ps or 'USD' in ps else 'IQD' if 'IQD' in ps or 'دينار' in ps else 'OTHER'
  basis='sqm' if 'للمتر' in text(el,'.//*[contains(@class,"price-postfix")]//text()') or re.search('للمتر|سعر المتر',name) else 'total'
  loc=text(el,'.//address//text()').split(',');province=loc[-1].strip();district=', '.join(loc[:-1]).strip() or 'غير محدد'
  area=number(text(el,'.//*[contains(@class,"h-area")]//*[contains(@class,"hz-figure")][1]/text()'))
  url=el.xpath('.//*[contains(@class,"item-title")]//a/@href')[0]
  rows.append({'id':'aq-'+hashlib.sha256(url.encode()).hexdigest()[:16],'sourceName':'عقارات العراق','sourceUrl':url,'sourceType':'listing','province':province,'district':district,'use':'زراعي' if 'زراع' in typ else 'تجاري' if 'تجاري' in typ else 'سكني' if 'سكن' in typ else 'غير محدد','currency':currency,'price':v,'priceBasis':basis,'area':area,'rawArea':area,'areaUnit':'م²','date':None,'observedAt':datetime.now(timezone.utc).date().isoformat(),'title':'غير محدد','street':'غير محدد','kind':'عرض','review':['تاريخ نشر الإعلان غير متاح في صفحة النتائج؛ تاريخ الرصد لا يثبت حداثة السعر']})
 time.sleep(.4);print(i,len(rows),flush=True);return rows
allrows={};errors=[]
first=urllib.request.urlopen('https://aiqarat.com/status/for-sale/',timeout=45).read()
(RAW/'aiqarat-page-1.html').write_bytes(first)
last=max([1]+[int(x) for x in re.findall(r'/status/for-sale/page/(\d+)/',first.decode())]);last=min(last,300)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 futures={pool.submit(page,i):i for i in range(1,last+1)}
 for f in concurrent.futures.as_completed(futures):
  try:
   for r in f.result():allrows[r['id']]=r
   (ROOT/'aiqarat.json').write_text(json.dumps(list(allrows.values()),ensure_ascii=False,indent=2))
  except Exception as e:errors.append({'page':futures[f],'error':str(e)});print('ERROR',futures[f],str(e),flush=True)
print('TOTAL',len(allrows))

(RAW/'aiqarat-log.json').write_text(json.dumps({'errors':errors,'pages':last}))
