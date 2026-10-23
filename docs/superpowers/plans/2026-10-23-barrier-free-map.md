# 무장애 관광지 지도 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** KorWithService2(JSON)로 무장애 관광정보를 검색해 카카오맵에 표시하고, 목록에서 고른 장소의 무장애 상세정보를 보여주는 Streamlit 앱을 만든다.

**Architecture:** Streamlit 비의존 API 클라이언트(`tour_api.py`), 설정 로더(`config.py`), 카카오맵 HTML 생성기(`kakao_map.py`)를 각각 단위 테스트하고, `app.py`가 이들을 조합한다. 지도는 `components.html`로 렌더하며 선택은 `st.dataframe` 행 선택으로 받는다.

**Tech Stack:** Python 3.10+, streamlit>=1.35, requests, python-dotenv, pytest, Kakao Maps JS SDK

**Spec:** `docs/superpowers/specs/2026-10-23-barrier-free-map-design.md`

## Global Constraints

- 서비스 URL 기본값: `https://apis.data.go.kr/B551011/KorWithService2`
- 공통 파라미터: `serviceKey`, `MobileOS=ETC`, `MobileApp=BarrierFreeMap`, `_type=json`
- 설정 키 이름: `OPENAI_API_KEY`(data.go.kr 서비스키), `OPENAI_END_POINT`, `KAKAO_JS_KEY` — 조회 순서 `st.secrets` → 환경변수/`.env`
- 서비스키는 `urllib.parse.unquote` 1회 후 `requests` params로 전달
- 검색: `numOfRows=100`, `pageNo=1`, `arrange=C`; 요청 timeout 15초
- 캐시 TTL: `area_codes` 24h, `search` 1h, `barrier_free` 24h
- 관광타입: 12 관광지, 14 문화시설, 15 행사/공연/축제, 28 레포츠, 32 숙박, 38 쇼핑, 39 음식점
- 한도 초과 메시지: "오늘 API 호출 한도를 초과했습니다"
- 빈 지도 중심: 서울시청 (37.5666, 126.9784); 선택 시 레벨 4
- 커밋: 사용자 규칙에 따라 `[유형] 제목` 한글 형식, **사용자 승인 후** 커밋 (commit-with-design-notes 스킬 사용)

## Review Focus

1. 장소 제목·주소에 `"`, `'`, `</script>`, `<img onerror>` 등이 들어있음 → 지도 HTML이 깨지거나 스크립트가 실행되면 안 됨 (Task 3 테스트)
2. JSON도 XML 오류도 아닌 응답(HTTP 500 HTML 페이지, 빈 본문) 또는 타임아웃 → 앱이 죽지 않고 `TourApiError`로 안내 (Task 2 테스트)
3. 시도 "전체" 상태에서 시군구 값이 남아 있음 → `sigunguCode`가 `areaCode` 없이 전송되면 안 됨 (Task 2 테스트)
4. 새 검색 후 이전 선택 행 인덱스가 새 결과 범위를 벗어남 → 선택 초기화, IndexError 없음 (Task 4 AppTest)
5. 키워드에 공백만 입력 → 키워드 없음으로 취급해 `areaBasedList2` 호출 (Task 2 테스트)

---

## File Structure

| 파일 | 책임 |
|---|---|
| `config.py` | `get_setting(name, default)` — secrets → env 조회 |
| `tour_api.py` | `TourApi`, `TourApiError`, 응답 정규화 |
| `kakao_map.py` | `render_map_html(places, js_key, selected_id)` |
| `labels.py` | 관광타입 코드, 무장애 필드 그룹/한글 라벨 상수 |
| `app.py` | Streamlit UI 조합 |
| `tests/test_config.py`, `tests/test_tour_api.py`, `tests/test_kakao_map.py`, `tests/test_app.py` | 테스트 |
| `requirements.txt`, `.streamlit/secrets.toml.example`, `.gitignore`(수정) | 실행/배포 설정 |

테스트 실행 위치는 프로젝트 루트. `tests/conftest.py`에서 `sys.path`에 루트를 넣는다.

---

### Task 1: 프로젝트 설정 + `config.py`

**Files:**
- Create: `requirements.txt`, `.streamlit/secrets.toml.example`, `config.py`, `tests/conftest.py`, `tests/test_config.py`
- Modify: `.gitignore` (끝에 `.streamlit/secrets.toml` 추가)

**Interfaces:**
- Produces: `config.get_setting(name: str, default: str | None = None) -> str | None`

- [ ] **Step 1: 설정 파일 작성**
  - `requirements.txt`: `streamlit>=1.35`, `requests`, `python-dotenv` (pytest 제외)
  - `.streamlit/secrets.toml.example`: spec 8장 3번의 TOML 3줄 그대로
  - `tests/conftest.py`: 프로젝트 루트를 `sys.path`에 삽입
  - 설치: `pip install -r requirements.txt pytest`

- [ ] **Step 2: 실패하는 테스트 작성** (`tests/test_config.py`)

```python
def test_secrets_take_priority(monkeypatch):
    monkeypatch.setenv("KAKAO_JS_KEY", "from-env")
    monkeypatch.setattr(config, "_read_secret", lambda name: "from-secrets")
    assert config.get_setting("KAKAO_JS_KEY") == "from-secrets"

def test_env_fallback_when_secret_missing(monkeypatch):
    monkeypatch.setenv("KAKAO_JS_KEY", "from-env")
    monkeypatch.setattr(config, "_read_secret", lambda name: None)
    assert config.get_setting("KAKAO_JS_KEY") == "from-env"

def test_default_when_nothing(monkeypatch):
    monkeypatch.delenv("NOPE_KEY", raising=False)
    monkeypatch.setattr(config, "_read_secret", lambda name: None)
    assert config.get_setting("NOPE_KEY", "dflt") == "dflt"

def test_empty_string_treated_as_missing(monkeypatch):
    monkeypatch.setenv("KAKAO_JS_KEY", "")
    monkeypatch.setattr(config, "_read_secret", lambda name: None)
    assert config.get_setting("KAKAO_JS_KEY", "dflt") == "dflt"
```

- [ ] **Step 3: 실행해 실패 확인** — `pytest tests/test_config.py -v` → FAIL (`config` 없음)

- [ ] **Step 4: `config.py` 구현**
  - 모듈 import 시 `dotenv.load_dotenv()` 1회 (기존 env 덮어쓰지 않음)
  - `_read_secret(name) -> str | None`: `st.secrets.get(name)`을 `try/except Exception`으로 감싸 secrets.toml이 없을 때 `None`
  - `get_setting`: secret → `os.environ.get` → default 순, 빈 문자열은 없음 취급

- [ ] **Step 5: 통과 확인** — `pytest tests/test_config.py -v` → 4 passed

- [ ] **Step 6: 커밋 (승인 후)** — `[설정] 프로젝트 의존성과 설정 로더 추가`

---

### Task 2: `tour_api.py` — API 클라이언트

**Files:**
- Create: `tour_api.py`, `tests/test_tour_api.py`

**Interfaces:**
- Consumes: 없음 (Streamlit/config 비의존)
- Produces:
  - `class TourApiError(Exception)`
  - `TourApi(service_key: str, base_url: str = DEFAULT_BASE_URL, session=None)` — `session`은 `.get(url, params=..., timeout=...)`가 `.text`, `.status_code`를 가진 응답을 반환하는 객체(기본 `requests.Session()`)
  - `area_codes(area_code: str | None = None) -> list[dict]` — `[{"code": "1", "name": "서울"}]`
  - `search(area_code=None, sigungu_code=None, content_type_id=None, keyword=None) -> tuple[list[dict], int]` — item dict는 API 원본 필드 유지 + `mapx`/`mapy`는 float
  - `barrier_free(content_id: str) -> dict[str, str]`
  - `DEFAULT_BASE_URL`, `QUOTA_EXCEEDED = "LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR"`

- [ ] **Step 1: 실패하는 테스트 작성** — `FakeSession(text, status=200)`이 호출된 `(url, params)`를 `calls`에 기록. `ok(items)` 헬퍼는 `{"response":{"header":{"resultCode":"0000","resultMsg":"OK"},"body":{"items":items,"totalCount":N}}}` JSON 문자열 생성.

```python
def test_search_parses_items_and_floats_coords():
    api = TourApi("k", session=FakeSession(ok({"item": [
        {"contentid": "1", "title": "A", "mapx": "126.9", "mapy": "37.5"},
        {"contentid": "2", "title": "B", "mapx": "", "mapy": ""},
        {"contentid": "3", "title": "C", "mapx": "0", "mapy": "0"}]}, total=3)))
    items, total = api.search(area_code="1")
    assert [i["contentid"] for i in items] == ["1"]
    assert items[0]["mapx"] == 126.9 and items[0]["mapy"] == 37.5
    assert total == 3

def test_single_item_dict_wrapped():      # items.item 이 dict → 길이 1
def test_empty_items_string():            # items == "" → ([], 0)

def test_xml_error_raises():
    xml = "<OpenAPI_ServiceResponse><cmmMsgHeader><errMsg>SERVICE ERROR</errMsg><returnAuthMsg>SERVICE_KEY_IS_NOT_REGISTERED_ERROR</returnAuthMsg></cmmMsgHeader></OpenAPI_ServiceResponse>"
    with pytest.raises(TourApiError, match="SERVICE_KEY_IS_NOT_REGISTERED_ERROR"):
        TourApi("k", session=FakeSession(xml)).search()

def test_result_code_not_ok_raises():     # resultCode "10", resultMsg "INVALID" → match "INVALID"
def test_non_json_body_raises():          # FakeSession("<html>500</html>", status=500) 및 "" → TourApiError
def test_network_error_wrapped():         # session.get이 requests.Timeout 발생 → TourApiError("네트워크 오류...")

def test_keyword_uses_search_keyword():
    s = FakeSession(ok(""))
    TourApi("k", session=s).search(keyword="박물관", area_code="1")
    url, params = s.calls[0]
    assert url.endswith("/searchKeyword2") and params["keyword"] == "박물관"

def test_no_keyword_uses_area_based():
    s = FakeSession(ok(""))
    TourApi("k", session=s).search(area_code="1", keyword="   ")
    url, params = s.calls[0]
    assert url.endswith("/areaBasedList2") and "keyword" not in params

def test_common_params_and_none_dropped():
    s = FakeSession(ok(""))
    TourApi("a%2Bb", session=s).search(content_type_id="12")
    _, p = s.calls[0]
    assert p["serviceKey"] == "a+b" and p["_type"] == "json"
    assert p["MobileOS"] == "ETC" and p["MobileApp"] == "BarrierFreeMap"
    assert p["numOfRows"] == 100 and p["arrange"] == "C"
    assert "areaCode" not in p

def test_sigungu_dropped_without_area():
    s = FakeSession(ok(""))
    TourApi("k", session=s).search(sigungu_code="23")
    assert "sigunguCode" not in s.calls[0][1]

def test_area_codes_maps_fields():        # item {"code":"1","name":"서울","rnum":1} → [{"code":"1","name":"서울"}], area_code 주면 params["areaCode"]

def test_barrier_free_drops_empty_and_contentid():
    s = FakeSession(ok({"item": [{"contentid": "9", "parking": "있음", "route": "", "elevator": "  "}]}))
    assert TourApi("k", session=s).barrier_free("9") == {"parking": "있음"}
    assert s.calls[0][1]["contentId"] == "9"
```

- [ ] **Step 2: 실패 확인** — `pytest tests/test_tour_api.py -v` → FAIL (import 오류)

- [ ] **Step 3: `tour_api.py` 구현**
  - `_get(operation, **params) -> tuple[list[dict], int]`: 공통 파라미터 병합, `None`/빈 문자열 값 제거, `GET {base_url}/{operation}` (timeout 15). `requests.RequestException` → `TourApiError(f"네트워크 오류: {e}")`. 본문 `lstrip()`이 `<`로 시작하면 정규식으로 `returnAuthMsg` (없으면 `errMsg`, 그것도 없으면 `"알 수 없는 오류 (HTTP {status})"`) 추출해 raise. 그 외 `json.loads` 실패 → `TourApiError(f"응답 해석 실패 (HTTP {status})")`. resultCode ≠ `"0000"` → raise resultMsg. items 정규화 후 `(list, int(totalCount or 0))`.
  - `search`: `keyword.strip()`이 비면 None 취급; `area_code`가 없으면 `sigungu_code` 무시.

- [ ] **Step 4: 통과 확인** — `pytest tests/test_tour_api.py -v` → 전부 PASS

- [ ] **Step 5: 커밋 (승인 후)** — `[기능] KorWithService2 API 클라이언트 추가`

---

### Task 3: `labels.py` + `kakao_map.py`

**Files:**
- Create: `labels.py`, `kakao_map.py`, `tests/test_kakao_map.py`

**Interfaces:**
- Produces:
  - `labels.CONTENT_TYPES: dict[str, str]` — `{"12": "관광지", ..., "39": "음식점"}` (Global Constraints 7종, 순서 유지)
  - `labels.BARRIER_GROUPS: list[tuple[str, list[tuple[str, str]]]]` — `[("지체장애", [("parking", "주차"), ...]), ("시각장애", ...), ("청각장애", ...), ("영유아가족", ...)]`; 필드 순서·그룹은 spec 5.4 목록, 라벨은 매뉴얼 항목명(주차, 대중교통, 접근로, 매표소, 홍보물, 휠체어, 출입통로, 엘리베이터, 화장실, 관람석, 객실, 지체장애 기타 상세, 점자블록, 보조견 동반, 안내요원, 오디오 가이드, 큰 활자 홍보물, 점자 홍보물 및 점자표지판, 유도 안내 설비, 시각장애 기타상세, 수화 안내, 자막 비디오 가이드 및 영상 자막 안내, 객실, 청각장애 기타상세, 유모차, 수유실, 유아용 보조의자, 영유아가족 기타상세)
  - `kakao_map.render_map_html(places: list[dict], js_key: str, selected_id: str | None = None) -> str` — places는 `TourApi.search` item(`contentid`, `title`, `addr1`, `firstimage2`, `mapx`, `mapy` 사용)

- [ ] **Step 1: 실패하는 테스트 작성**

```python
P = [{"contentid": "1", "title": "경복궁", "addr1": "서울 종로구", "firstimage2": "", "mapx": 126.97, "mapy": 37.57}]

def test_includes_sdk_with_key():
    h = render_map_html(P, "JSKEY")
    assert "dapi.kakao.com/v2/maps/sdk.js?appkey=JSKEY&autoload=false" in h

def test_places_embedded_as_json():
    assert '"경복궁"' in render_map_html(P, "K")   # ensure_ascii=False

def test_script_breakout_escaped():
    evil = [{**P[0], "title": "</script><script>alert(1)</script>"}]
    h = render_map_html(evil, "K")
    assert "</script><script>alert(1)" not in h

def test_selected_sets_center_and_level():
    h = render_map_html(P, "K", selected_id="1")
    assert '"1"' in h and "setLevel(4)" in h

def test_empty_places_centers_city_hall():
    h = render_map_html([], "K")
    assert "37.5666" in h and "126.9784" in h

def test_barrier_groups_cover_all_fields():
    keys = [k for _, fs in BARRIER_GROUPS for k, _ in fs]
    assert len(keys) == 28 and len(set(keys)) == 28
```

- [ ] **Step 2: 실패 확인** — `pytest tests/test_kakao_map.py -v` → FAIL

- [ ] **Step 3: 구현**
  - 데이터 삽입: `json.dumps(places, ensure_ascii=False).replace("<", "\\u003c")`로 `</script>` 차단
  - JS: `kakao.maps.load` 안에서 지도 생성, 장소별 마커 + `InfoWindow`, 인포윈도우 내용은 `esc()`(`& < > " '` 치환) 거친 문자열로 구성; 썸네일이 있으면 `<img>` 추가
  - `selected_id`가 있으면 해당 장소 `setCenter` + `map.setLevel(4)` + 인포윈도우 열기, 없고 places가 있으면 `LatLngBounds` + `setBounds`
  - 컨테이너 `<div id="map" style="width:100%;height:580px">`

- [ ] **Step 4: 통과 확인** — `pytest tests/test_kakao_map.py -v` → PASS

- [ ] **Step 5: 커밋 (승인 후)** — `[기능] 카카오맵 렌더링과 라벨 상수 추가`

---

### Task 4: `app.py` — Streamlit UI

**Files:**
- Create: `app.py`, `tests/test_app.py`

**Interfaces:**
- Consumes: `config.get_setting`, `TourApi`/`TourApiError`/`QUOTA_EXCEEDED`/`DEFAULT_BASE_URL`, `render_map_html`, `CONTENT_TYPES`, `BARRIER_GROUPS`
- Produces: 실행 가능한 `app.py`

- [ ] **Step 1: 실패하는 테스트 작성** (`streamlit.testing.v1.AppTest`)

```python
def test_missing_keys_shows_error(monkeypatch):
    monkeypatch.setattr("config.get_setting", lambda n, d=None: d)
    at = AppTest.from_file("app.py").run()
    assert any("OPENAI_API_KEY" in e.value for e in at.error)

def test_new_search_resets_selection(monkeypatch):
    # get_setting → 더미 키, TourApi를 FakeApi로 교체:
    #   area_codes → [{"code":"1","name":"서울"}]
    #   search → 첫 호출 3건, 두 번째 호출 1건
    # 1) 검색 실행 → session_state["selected_id"]="3" 설정
    # 2) 다시 검색 → at.session_state["selected_id"] is None, at.exception 비어 있음
```

`app.py`는 `TourApi`를 `st.cache_resource` 함수 `get_api()`로 만들므로, 테스트는 `monkeypatch.setattr("tour_api.TourApi", FakeApi)` 후 `AppTest`를 실행한다 (`app.py`는 `import tour_api`, `import config` 후 `tour_api.TourApi(...)`, `config.get_setting(...)`처럼 모듈 속성으로 참조해야 monkeypatch가 먹는다).

- [ ] **Step 2: 실패 확인** — `pytest tests/test_app.py -v` → FAIL

- [ ] **Step 3: `app.py` 구현** — spec 5.4 그대로
  - 키 확인: 서비스키·`KAKAO_JS_KEY` 중 없는 이름을 `st.error`로 나열 후 `st.stop()`
  - 캐시 함수: `load_areas(area_code)`, `run_search(area, sigungu, ctype, keyword)`, `load_barrier(content_id)` — TTL은 Global Constraints
  - 사이드바: 시도(“전체” 포함) → 시군구(시도 선택 시) → 관광타입(“전체” + `CONTENT_TYPES`) → 키워드 → `st.button("검색")`
  - 검색 시 `session_state["results"]=(items,total)`, `session_state["selected_id"]=None`
  - `st.dataframe(..., key="table", on_select="rerun", selection_mode="single-row", hide_index=True)` — 선택 행 인덱스가 현재 결과 범위 안일 때만 `selected_id` 갱신
  - 상세: 썸네일, 주소, 전화, `BARRIER_GROUPS` 순으로 값 있는 그룹만 `st.markdown` 목록; 전부 없으면 "등록된 무장애 정보가 없습니다"
  - total>100 → `st.info("상위 100건만 표시합니다")`; 지도 아래 `st.caption`으로 카카오 Web 도메인 등록 안내
  - `TourApiError`: 메시지에 `QUOTA_EXCEEDED` 포함 시 "오늘 API 호출 한도를 초과했습니다", 아니면 원문을 `st.error`

- [ ] **Step 4: 통과 확인** — `pytest -v` → 전체 PASS

- [ ] **Step 5: 커밋 (승인 후)** — `[기능] 무장애 관광지 지도 Streamlit 화면 추가`

---

### Task 5: 실제 API·브라우저 검증

**Files:** 없음 (문제 발견 시 해당 Task 파일 수정)

- [ ] **Step 1: 실제 키로 API 스모크** — `python -c "from config import get_setting; from tour_api import TourApi; a=TourApi(get_setting('OPENAI_API_KEY')); print(a.area_codes()[:3]); i,t=a.search(area_code='1', content_type_id='12'); print(t, i[0]['title']); print(a.barrier_free(i[0]['contentid']))"` → 시도 목록, totalCount>0, 상세 dict 출력. 실패 시 응답 원문을 확인해 Task 2 파싱 수정(테스트 먼저 추가).
- [ ] **Step 2: 앱 실행** — `streamlit run app.py` → 브라우저 `http://localhost:8501`
- [ ] **Step 3: 성공 기준 시나리오** — 서울/종로구/관광지 검색 → 마커 표시, 행 선택 → 지도 이동 + 상세 그룹 표시, 키워드 "박물관" 검색 동작. 카카오 도메인 미등록으로 지도가 비면 사용자에게 콘솔 등록 요청.
- [ ] **Step 4: 결과 보고** — 확인한 항목과 확인 못 한 항목(배포 환경 해외 IP 응답 등)을 사용자에게 보고. 배포 자체는 사용자가 진행.
