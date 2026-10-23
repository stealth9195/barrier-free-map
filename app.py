"""무장애 관광지 지도 — KorWithService2 + 카카오맵."""
import streamlit as st

import config
import tour_api
from kakao_map import render_map_html
from labels import BARRIER_GROUPS, CONTENT_TYPES
from selection import selected_from_rows

st.set_page_config(page_title="무장애 관광지 지도", layout="wide")
st.title("무장애 관광지 지도")

SERVICE_KEY = config.get_setting("OPENAI_API_KEY")
BASE_URL = config.get_setting("OPENAI_END_POINT", tour_api.DEFAULT_BASE_URL)
KAKAO_JS_KEY = config.get_setting("KAKAO_JS_KEY")

missing = [name for name, value in (("OPENAI_API_KEY", SERVICE_KEY), ("KAKAO_JS_KEY", KAKAO_JS_KEY))
           if not value]
if missing:
    st.error(f"설정이 필요합니다: {', '.join(missing)} — 로컬은 .env, 배포는 Streamlit Secrets에 입력하세요.")
    st.stop()


@st.cache_resource
def get_api():
    return tour_api.TourApi(SERVICE_KEY, BASE_URL)


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def load_areas(area_code=None):
    return get_api().area_codes(area_code)


@st.cache_data(ttl=3600, show_spinner="검색 중...")
def run_search(area_code, sigungu_code, content_type_id, keyword):
    return get_api().search(area_code=area_code, sigungu_code=sigungu_code,
                            content_type_id=content_type_id, keyword=keyword)


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def load_barrier(content_id):
    return get_api().barrier_free(content_id)


def show_error(e):
    if tour_api.QUOTA_EXCEEDED in str(e):
        st.error("오늘 API 호출 한도를 초과했습니다")
    else:
        st.error(f"API 오류: {e}")


st.session_state.setdefault("results", ([], 0))
st.session_state.setdefault("selected_id", None)
st.session_state.setdefault("search_no", 0)

try:
    with st.sidebar:
        st.header("검색 조건")
        areas = {a["code"]: a["name"] for a in load_areas()}
        area = st.selectbox("시도", [None, *areas], format_func=lambda c: areas.get(c, "전체"))
        sigungu = None
        if area:
            sigungus = {a["code"]: a["name"] for a in load_areas(area)}
            sigungu = st.selectbox("시군구", [None, *sigungus], format_func=lambda c: sigungus.get(c, "전체"))
        ctype = st.selectbox("관광타입", [None, *CONTENT_TYPES], format_func=lambda c: CONTENT_TYPES.get(c, "전체"))
        keyword = st.text_input("키워드 (선택)")
        if st.button("검색", type="primary", use_container_width=True):
            st.session_state.results = run_search(area, sigungu, ctype, keyword.strip())
            st.session_state.selected_id = None
            st.session_state.search_no += 1
except tour_api.TourApiError as e:
    show_error(e)

places, total = st.session_state.results
map_col, side_col = st.columns([3, 2])

with side_col:
    st.markdown(f"**검색 결과 {len(places)}건**")
    if total > len(places):
        st.info("상위 100건만 표시합니다")
    if places:
        rows = [{"이름": p.get("title", ""), "주소": p.get("addr1", ""),
                 "타입": CONTENT_TYPES.get(str(p.get("contenttypeid")), "")} for p in places]
        table_key = f"table_{st.session_state.search_no}"

        def on_pick():
            # 선택이 바뀔 때만 호출되므로 선택 해제 시 상세 패널도 닫힌다.
            picked = st.session_state[table_key].selection.rows
            st.session_state.selected_id = selected_from_rows(picked, places)

        st.dataframe(rows, hide_index=True, on_select=on_pick, selection_mode="single-row",
                     key=table_key, height=260)

    selected = next((p for p in places if p["contentid"] == st.session_state.selected_id), None)
    if selected:
        st.divider()
        st.markdown(f"### {selected.get('title', '')}")
        if selected.get("firstimage2"):
            st.image(selected["firstimage2"], width=200)
        st.markdown(f"주소: {selected.get('addr1', '')}  \n전화: {selected.get('tel') or '-'}")
        try:
            info = load_barrier(selected["contentid"])
            sections = []
            for group, fields in BARRIER_GROUPS:
                lines = [f"- **{label}**: {info[key]}" for key, label in fields if info.get(key)]
                if lines:
                    sections.append(f"#### {group}\n" + "\n".join(lines))
            st.markdown("\n\n".join(sections) or "등록된 무장애 정보가 없습니다")
        except tour_api.TourApiError as e:
            show_error(e)

with map_col:
    st.iframe(render_map_html(places, KAKAO_JS_KEY, st.session_state.selected_id), height=600)
    st.caption("지도가 보이지 않으면 카카오 개발자 콘솔 > 플랫폼 > Web 사이트 도메인에 현재 주소를 등록하세요.")
