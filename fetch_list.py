import sys,urllib.request,urllib.parse,re,json,collections
sys.stdout.reconfigure(encoding='utf-8')
def load_key():
    for l in open('.env',encoding='utf-8'):
        k,_,v=l.strip().partition('=')
        if k=='OPENAI_API_KEY' and v: return urllib.parse.unquote(v)
KEY=load_key()
BASE='http://apis.data.go.kr/B554287/DisabledPersonConvenientFacility/getDisConvFaclList'
def fetch(sido,cgg=None):
    out=[];page=1
    while True:
        p={'serviceKey':KEY,'pageNo':page,'numOfRows':1000,'siDoNm':sido}
        if cgg:p['cggNm']=cgg
        r=urllib.request.urlopen(BASE+'?'+urllib.parse.urlencode(p),timeout=60).read().decode()
        rows=re.findall(r'<servList>(.*?)</servList>',r,re.S)
        for x in rows:
            out.append({k:v for k,v in re.findall(r'<(\w+)>(.*?)</\1>',x,re.S)})
        if len(rows)<1000:break
        page+=1
    return out
if __name__=='__main__':
    rows=fetch(sys.argv[1], sys.argv[2] if len(sys.argv)>2 else None)
    json.dump(rows,open(sys.argv[3],'w',encoding='utf-8'),ensure_ascii=False)
    print(len(rows))
    print(collections.Counter(r.get('faclTyCd') for r in rows).most_common(12))
    print('open:',sum(r.get('salStaDivCd')=='Y' for r in rows),'coord0:',sum(r.get('faclLat')in('0',None) for r in rows))
    print(collections.Counter(r.get('lcMnad','').split()[1] if len(r.get('lcMnad','').split())>1 else '?' for r in rows).most_common(30))
