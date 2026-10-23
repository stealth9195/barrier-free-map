# 무장애 관광지 지도 (Streamlit) 설계

작성일: 2026-10-23

## 1. 목적

장애인·어르신·영유아 동반 여행자가 지역별 무장애 관광정보를 지도에서 찾아보고, 장소별 무장애 편의시설(휠체어, 화장실, 점자블록, 수유실 등)을 확인할 수 있는 Streamlit 앱을 만든다. 로컬 실행과 Streamlit Community Cloud 배포를 모두 지원한다.

**성공 기준**
- `streamlit run app.py` 실행 → 사이드바에서 "서울 / 종로구 / 관광지" 검색 → 카카오맵에 결과 마커 표시
- 결과 목록에서 한 곳을 선택 → 지도가 해당 위치로 이동하고, 우측 패널에 무장애 상세정보가 그룹별로 표시
- 키워드("박물관" 등) 입력 시 키워드 검색 결과로 동일하게 동작
- Streamlit Community Cloud에 배포한 URL에서도 동일하게 동작 (Secrets로 키 주입)

## 2. 범위

**포함**
- 한국관광공사 국문 무장애여행 서비스 `KorWithService2` (JSON 응답, `_type=json`)
  - `areaCode2` 지역/시군구 코드
  - `areaBasedList2` 지역기반 목록
  - `searchKeyword2` 키워드 검색
  - `detailWithTour2` 무장애 상세정보
- 카카오맵 JavaScript SDK로 지도 표시
- 로컬(`.env`) / 배포(`st.secrets`) 양쪽 설정 로딩

**제외 (YAGNI)**
- 기존 장애인편의시설 데이터(`data/`, `fetch_list.py`, `fetch_detail.py`)와의 결합
- 마커 클릭 → 파이썬 연동(양방향 커스텀 컴포넌트)
- 위치기반(`locationBasedList2`) 검색, 이미지 갤러리, 소개/반복정보
- 페이지네이션 (검색당 최대 100건, 초과 시 안내 문구만 표시)

## 3. 외부 의존성과 제약

| 항목 | 내용 |
|---|---|
| 서비스 URL | `https://apis.data.go.kr/B551011/KorWithService2` |
| 공통 요청 파라미터 | `serviceKey`, `MobileOS=ETC`, `MobileApp=BarrierFreeMap`, `_type=json` |
| 트래픽 한도 | 개발계정 일 1,000건 (배포 시 모든 방문자 공유) |
| 오류 응답 | 인증·한도 등 포털 오류는 `_type=json`이어도 XML(`OpenAPI_ServiceResponse`)로 반환 |
| 좌표 | 응답 `mapx`(경도), `mapy`(위도), WGS84 |
| 관광타입 | 12 관광지, 14 문화시설, 15 행사/공연/축제, 28 레포츠, 32 숙박, 38 쇼핑, 39 음식점 |
| 카카오맵 | 카카오 개발자 콘솔 > 플랫폼 > Web 도메인에 `http://localhost:8501` 및 배포 URL 등록 필요 |

## 4. 설정 로딩

키 이름은 기존 `.env`를 그대로 따른다.

| 키 | 용도 |
|---|---|
| `OPENAI_API_KEY` | data.go.kr 서비스키 (이름과 달리 공공데이터포털 키) |
| `OPENAI_END_POINT` | `https://apis.data.go.kr/B551011/KorWithService2` |
| `KAKAO_JS_KEY` | 카카오맵 JavaScript 키 |

조회 순서: `st.secrets[키]` → 환경변수/`.env`(python-dotenv). `st.secrets`가 없거나(로컬에 `secrets.toml` 없음) 키가 없으면 다음 단계로 넘어간다. 서비스키가 URL 인코딩된 형태로 저장된 경우를 대비해 `urllib.parse.unquote`로 한 번 디코딩한 뒤 `requests`의 params로 전달한다(이중 인코딩 방지, 기존 `fetch_list.py`와 동일한 방식).

`OPENAI_END_POINT`가 없으면 위 서비스 URL을 기본값으로 쓴다. 서비스키나 카카오 키가 없으면 앱은 `st.error`로 어떤 키가 필요한지 안내하고 `st.stop()`한다.

## 5. 구조

```
app.py              # Streamlit UI
tour_api.py         # KorWithService2 클라이언트 (Streamlit 비의존)
config.py           # 설정 로딩 (st.secrets → .env)
kakao_map.py        # 카카오맵 HTML 생성 함수
requirements.txt
tests/test_tour_api.py
.streamlit/secrets.toml.example
```

`requirements.txt`: `streamlit>=1.35`(dataframe 행 선택 지원), `requests`, `python-dotenv`. 개발용 `pytest`는 requirements에 넣지 않는다.

### 5.1 `tour_api.py`

```python
class TourApiError(Exception): ...

class TourApi:
    def __init__(self, service_key: str, base_url: str, session=None): ...
    def area_codes(self, area_code: str | None = None) -> list[dict]  # [{code, name}]
    def search(self, area_code=None, sigungu_code=None,
               content_type_id=None, keyword=None) -> tuple[list[dict], int]  # (items, totalCount)
    def barrier_free(self, content_id: str) -> dict  # 비어있지 않은 필드만
```

- `_get(operation, **params)`: 공통 파라미터를 붙여 GET (timeout 15초). `None` 값 파라미터는 제외.
  - 응답 본문이 `<`로 시작하면 XML 오류로 보고 `returnAuthMsg`/`errMsg`를 추출해 `TourApiError`.
  - JSON의 `response.header.resultCode`가 `"0000"`이 아니면 `TourApiError(resultMsg)`.
  - `response.body.items`가 `""`(0건)이면 빈 리스트, `items.item`이 dict(1건)면 리스트로 감싼다.
  - `requests` 예외는 `TourApiError("네트워크 오류: …")`로 감싼다.
- `search`: `keyword`가 있으면 `searchKeyword2`(`keyword` + 지역/타입 필터), 없으면 `areaBasedList2`. 공통으로 `numOfRows=100`, `pageNo=1`, `arrange=C`(수정일순). `mapx`/`mapy`가 비어 있거나 0인 항목은 제외하고, 좌표를 float로 변환한다.
- `barrier_free`: `detailWithTour2?contentId=…`의 첫 item에서 `contentid`를 제외한 값 중 공백이 아닌 필드만 반환.

### 5.2 `config.py`

`get_setting(name: str, default: str | None = None) -> str | None` — 4장의 조회 순서 구현.

### 5.3 `kakao_map.py`

`render_map_html(places: list[dict], js_key: str, selected_id: str | None) -> str`
- `//dapi.kakao.com/v2/maps/sdk.js?appkey=…&autoload=false` 로드 후 `kakao.maps.load` 콜백에서 지도 생성.
- 장소마다 마커 + 인포윈도우(제목, 주소, 썸네일 `firstimage2`가 있으면 표시). 마커 클릭 시 인포윈도우 토글.
- `selected_id`가 있으면 해당 좌표 중심, 레벨 4로 확대하고 인포윈도우를 연 상태로 표시. 없으면 `LatLngBounds`로 전체 마커가 보이게 맞춤.
- 장소 데이터는 `json.dumps`로 삽입하고, HTML 특수문자는 인포윈도우 생성 시 JS에서 이스케이프한다.
- 결과 0건이면 서울시청 중심의 빈 지도.

### 5.4 `app.py`

- 페이지: `st.set_page_config(layout="wide", page_title="무장애 관광지 지도")`
- **사이드바**: 시도 selectbox(전체 포함) → 시군구 selectbox(시도 선택 시만) → 관광타입 selectbox(전체 + 7종) → 키워드 text_input → "검색" 버튼.
  - 검색 결과는 `st.session_state["results"]`에 저장해 재실행 시 유지.
- **캐시**: `area_codes` 24시간, `search` 1시간, `barrier_free` 24시간 `st.cache_data(ttl=…)`. API 객체는 `st.cache_resource`.
- **본문**: `st.columns([3, 2])`
  - 왼쪽: `components.html(render_map_html(...), height=600)`
  - 오른쪽 위: 결과 표(`st.dataframe`, 컬럼 제목/주소/타입, `on_select="rerun"`, `selection_mode="single-row"`). totalCount가 100을 넘으면 "상위 100건만 표시" 안내.
  - 오른쪽 아래: 선택 장소 상세 — 썸네일, 주소, 전화, 그리고 무장애 정보를 4개 그룹으로 표시. 데이터가 없는 그룹은 생략, 전부 없으면 "등록된 무장애 정보가 없습니다".
    - 지체장애: parking, publictransport, route, ticketoffice, promotion, wheelchair, exit, elevator, restroom, auditorium, room, handicapetc
    - 시각장애: braileblock, helpdog, guidehuman, audioguide, bigprint, brailepromotion, guidesystem, blindhandicapetc
    - 청각장애: signguide, videoguide, hearingroom, hearinghandicapetc
    - 영유아가족: stroller, lactationroom, babysparechair, infantsfamilyetc
  - 필드명은 한글 라벨로 매핑(매뉴얼 항목명 기준).
- **오류 처리**: `TourApiError`는 `st.error(메시지)`로 표시하고 나머지 화면은 유지. 한도 초과(`LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR`)는 "오늘 API 호출 한도를 초과했습니다" 문구로 변환.

## 6. 데이터 흐름

1. 앱 시작 → 설정 로딩 → `area_codes()`(캐시)로 시도 목록
2. 시도 선택 → `area_codes(area)`(캐시)로 시군구 목록
3. 검색 → `search(...)`(캐시) → session_state 저장 → 지도 + 목록 렌더
4. 목록 행 선택 → `barrier_free(contentid)`(캐시) → 상세 패널, 지도는 선택 위치로 재렌더

API 호출은 선택한 장소에 대해서만 상세를 조회하므로, 검색 1회 + 선택 n회로 한도를 아낀다.

## 7. 테스트

- `tests/test_tour_api.py` (pytest, 가짜 session 주입으로 네트워크 없음)
  - 정상 JSON 다건 → 리스트 + 좌표 float 변환, 좌표 없는 항목 제외
  - 1건 응답(`item`이 dict) → 길이 1 리스트
  - 0건 응답(`items: ""`) → 빈 리스트
  - XML 오류 응답 → `TourApiError`에 `SERVICE_KEY_IS_NOT_REGISTERED_ERROR` 포함
  - `keyword` 유무에 따라 호출 오퍼레이션이 `searchKeyword2`/`areaBasedList2`로 바뀜
  - `barrier_free`가 빈 필드와 `contentid`를 제외
- `config.get_setting`: secrets 우선, 환경변수 fallback
- 수동 확인: 실제 키로 `streamlit run app.py` → 성공 기준 시나리오 수행

## 8. 배포 (Streamlit Community Cloud)

1. GitHub 저장소에 push (공개/비공개 모두 가능). 앱에 불필요한 docx 매뉴얼과 `data/`는 커밋에서 제외 권장.
2. share.streamlit.io → New app → 저장소/브랜치, Main file `app.py` 지정.
3. Advanced settings > Secrets에 `.streamlit/secrets.toml.example` 형식으로 입력:
   ```toml
   OPENAI_API_KEY = "data.go.kr 서비스키"
   OPENAI_END_POINT = "https://apis.data.go.kr/B551011/KorWithService2"
   KAKAO_JS_KEY = "카카오 JavaScript 키"
   ```
4. 카카오 개발자 콘솔 Web 도메인에 `https://<앱이름>.streamlit.app` 추가.
5. 배포 후 첫 검색으로 data.go.kr이 해외(미국) IP에서 정상 응답하는지 확인. 차단되면 국내 리전 서버 배포로 전환.
6. `.gitignore`에 `.streamlit/secrets.toml` 추가 (example 파일은 커밋).

## 9. 위험과 대응

| 위험 | 대응 |
|---|---|
| 일 1,000건 한도 공유 소진 | `st.cache_data`, 상세는 선택 시만 조회, 필요 시 운영계정 신청 |
| data.go.kr 해외 IP 응답 불가 | 배포 직후 확인, 국내 서버로 전환 |
| 카카오 도메인 미등록 시 빈 지도 | 지도 아래 `st.caption`으로 도메인 등록 필요 안내 |
| 서비스키 인코딩 혼동 | 디코딩 후 params 전달로 통일 |
