import sys,json,re,time,os,urllib.request,urllib.parse,concurrent.futures as cf
sys.stdout.reconfigure(encoding='utf-8')
from fetch_list import KEY
BASE='http://apis.data.go.kr/B554287/DisabledPersonConvenientFacility/getFacInfoOpenApiJpEvalInfoList'
EXCLUDE={'다세대주택','아파트','연립주택','아파트 부대복리시설','기숙사','대피소','생활숙박시설'}
def detail(row):
    q=urllib.parse.urlencode({'serviceKey':KEY,'wfcltId':row['wfcltId']})
    for i in range(6):
        try:
            r=urllib.request.urlopen(BASE+'?'+q,timeout=30).read().decode()
            m=re.search(r'<evalInfo>(.*?)</evalInfo>',r,re.S)
            return [x.strip() for x in m.group(1).split(',') if x.strip()] if m else []
        except Exception: time.sleep(1.5*(i+1))
    return None
if __name__=='__main__':
    rows=[r for r in json.load(open(sys.argv[1],encoding='utf-8')) if r['faclTyCd'] not in EXCLUDE]
    prev={}
    if os.path.exists(sys.argv[2]):
        prev={r['wfcltId']:r['evalList'] for r in json.load(open(sys.argv[2],encoding='utf-8')) if r.get('evalList') is not None}
    todo=[r for r in rows if r['wfcltId'] not in prev]
    with cf.ThreadPoolExecutor(2) as ex: got=list(ex.map(detail,todo))
    prev.update({r['wfcltId']:e for r,e in zip(todo,got) if e is not None})
    for r in rows: r['evalList']=prev.get(r['wfcltId'])
    ev=[r['evalList'] for r in rows]
    json.dump(rows,open(sys.argv[2],'w',encoding='utf-8'),ensure_ascii=False)
    print(len(rows),'failed',sum(e is None for e in ev),'>=3:',sum(bool(e) and len(e)>=3 for e in ev))
