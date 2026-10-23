"""무장애 여행 API(KorWithService2)로 지역별 관광정보 + 무장애 상세정보를 받아 CSV 한 파일로 저장한다.
사용법: python fetch_tour_csv.py [areaCode=1] [출력경로=data/seoul_barrier_free.csv] [contentTypeId(생략=전체)]
"""
import sys,re,csv,json,time,urllib.request,urllib.parse,concurrent.futures as cf
sys.stdout.reconfigure(encoding='utf-8')
env=dict(l.strip().partition('=')[::2] for l in open('.env',encoding='utf-8') if '=' in l)
KEY=urllib.parse.unquote(env['OPENAI_API_KEY'])
BASE=(env.get('OPENAI_END_POINT') or 'https://apis.data.go.kr/B551011/KorWithService2').rstrip('/')+'/'
TYPES={'12':'관광지','14':'문화시설','15':'행사/공연/축제','28':'레포츠','32':'숙박','38':'쇼핑','39':'음식점'}
# 무장애 상세 열 → 한글명 (매뉴얼 v4.3 기준)
DETAIL={
 'parking':'주차','publictransport':'대중교통','route':'접근로','ticketoffice':'매표소','promotion':'홍보물',
 'wheelchair':'휠체어','exit':'출입통로','elevator':'엘리베이터','restroom':'화장실','auditorium':'관람석',
 'room':'객실','handicapetc':'지체장애 기타상세',
 'braileblock':'점자블록','helpdog':'보조견 동반','guidehuman':'안내요원','audioguide':'오디오 가이드',
 'bigprint':'큰 활자 홍보물','brailepromotion':'점자 홍보물 및 점자표지판','guidesystem':'유도 안내 설비',
 'blindhandicapetc':'시각장애 기타상세',
 'signguide':'수화 안내','videoguide':'자막 비디오 가이드','hearingroom':'객실(청각)','hearinghandicapetc':'청각장애 기타상세',
 'stroller':'유모차','lactationroom':'수유실','babysparechair':'유아용 보조의자','infantsfamilyetc':'영유아가족 기타상세',
}

def call(op,**p):
    q=urllib.parse.urlencode(dict(serviceKey=KEY,MobileOS='ETC',MobileApp='BarrierFreeMap',_type='json',**p))
    for i in range(5):
        try:
            r=urllib.request.urlopen(BASE+op+'?'+q,timeout=30).read().decode()
            body=json.loads(r)['response']['body']
            items=body['items']['item'] if body.get('items') else []
            return body,(items if isinstance(items,list) else [items])
        except json.JSONDecodeError: raise RuntimeError(r[:300])  # 포털 오류는 XML로 옴
        except Exception:
            if i==4: raise
            time.sleep(1.5*(i+1))

def all_items(op,**p):
    out=[];page=1
    while True:
        body,items=call(op,numOfRows=1000,pageNo=page,**p)
        out+=items
        if len(out)>=body['totalCount'] or not items: return out
        page+=1

def clean(s): return re.sub(r'\s*<br\s*/?>\s*',' / ',s or '').strip()  # 상세정보 안의 <br/> 태그 제거

def ymd(t): return f'{t[:4]}-{t[4:6]}-{t[6:8]}' if t and len(t)>=8 else ''

if __name__=='__main__':
    area=sys.argv[1] if len(sys.argv)>1 else '1'
    path=sys.argv[2] if len(sys.argv)>2 else 'data/seoul_barrier_free.csv'
    p={'areaCode':area,'arrange':'C'}
    if len(sys.argv)>3: p['contentTypeId']=sys.argv[3]
    cls={c['lclsSystm3Cd']:c for c in all_items('lclsSystmCode2',lclsSystmListYn='Y')}
    ldong={(d['lDongRegnCd'],d['lDongSignguCd']):d for d in all_items('ldongCode2',lDongListYn='Y')}
    rows=all_items('areaBasedList2',**p)
    with cf.ThreadPoolExecutor(3) as ex:
        details=list(ex.map(lambda r:(call('detailWithTour2',contentId=r['contentid'])[1] or [{}])[0],rows))
    out=[]
    for r,d in zip(rows,details):
        c=cls.get(r.get('lclsSystm3'),{}); g=ldong.get((r.get('lDongRegnCd'),r.get('lDongSignguCd')),{})
        row={
         '콘텐츠ID':r['contentid'],'이름':r['title'],
         '관광타입':TYPES.get(r['contenttypeid'],r['contenttypeid']),
         '대분류':c.get('lclsSystm1Nm',''),'중분류':c.get('lclsSystm2Nm',''),'소분류':c.get('lclsSystm3Nm',''),
         '시도':g.get('lDongRegnNm',''),'시군구':g.get('lDongSignguNm',''),
         '주소':r.get('addr1',''),'상세주소':r.get('addr2',''),'우편번호':r.get('zipcode',''),'전화번호':r.get('tel',''),
         '경도':r.get('mapx',''),'위도':r.get('mapy',''),
         '대표이미지':r.get('firstimage',''),'대표이미지(썸네일)':r.get('firstimage2',''),
         '등록일':ymd(r.get('createdtime')),'수정일':ymd(r.get('modifiedtime')),
        }
        row.update({v:clean(d.get(k)) for k,v in DETAIL.items()})
        out.append(row)
    import os; os.makedirs(os.path.dirname(path) or '.',exist_ok=True)
    with open(path,'w',encoding='utf-8-sig',newline='') as f:  # utf-8-sig: 엑셀에서 한글 안 깨지게
        w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
    print(len(out),'rows ->',path)
