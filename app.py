"""Trip For All — 미리 수집한 무장애 관광 데이터셋 + 카카오맵."""
from html import escape

import streamlit as st

import config
from dataset import filter_places, load_dataset
from kakao_map import render_map_html
from labels import BARRIER_GROUPS, CONTENT_TYPES, FACILITY_CHIPS

st.set_page_config(page_title="Trip For All", layout="wide", initial_sidebar_state="collapsed")

STYLE = """
<style>
.stApp { background: #F5F6F8; }
.block-container { padding-top: 2.2rem; max-width: 1400px; }
h1 { font-size: 1.5rem !important; font-weight: 700 !important; letter-spacing: -0.02em; }
.st-key-sheet { background: #FFFFFF; border-radius: 24px 24px 16px 16px; padding: 10px 16px 16px;
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.06); }
.st-key-sheet::before { content: ""; display: block; width: 40px; height: 4px; border-radius: 2px;
  background: #D1D5DB; margin: 0 auto 6px; }
.st-key-keyword div[data-baseweb="input"], .st-key-keyword div[data-baseweb="base-input"] {
  border-radius: 999px; background: #F1F3F5; border-color: transparent; }
.st-key-keyword input { background: transparent; font-size: 15px; }
[class*="st-key-card-"] { background: #FFFFFF; border: 1px solid #E5E7EB !important; border-radius: 16px !important;
  transition: border-color 150ms ease; }
[class*="st-key-card-"]:hover { border-color: #93C5FD !important; }
[class*="st-key-card-selected"] { border: 2px solid #2563EB !important; }
.card { display: flex; gap: 12px; align-items: flex-start; }
.card-body { flex: 1; min-width: 0; }
.card-title { font-size: 16px; font-weight: 700; color: #0F172A; line-height: 1.35; }
.card-addr { font-size: 13px; color: #475569; margin: 4px 0 10px; overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap; }
.tag { display: inline-block; font-size: 12px; color: #334155; background: #F1F5F9; border-radius: 6px;
  padding: 3px 8px; margin: 0 4px 4px 0; }
.tag.blue { color: #1D4ED8; background: #EFF6FF; }
.thumb { width: 76px; height: 76px; border-radius: 12px; flex: none; background: #F1F5F9 center / cover no-repeat; }
.region { font-size: 13px; color: #475569; }
.detail-title { font-size: 20px; font-weight: 700; color: #0F172A; margin-bottom: 2px; }
.detail-meta { font-size: 13px; color: #475569; line-height: 1.6; }
.st-key-detail img { max-height: 200px; object-fit: cover; border-radius: 12px; }
.info-row { font-size: 14px; color: #0F172A; line-height: 1.55; padding: 6px 0; border-top: 1px solid #F1F5F9; }
.info-row span { display: inline-block; min-width: 92px; color: #475569; }
.st-key-facilities button[data-variant="pills"] { border-radius: 999px !important; background: #FFFFFF !important;
  border: 1px solid #D1D5DB !important; min-height: 36px; padding: 0 14px !important; }
.st-key-facilities button[aria-checked="true"], .st-key-facilities button[aria-pressed="true"] { background: #1F2937 !important; border-color: #1F2937 !important; }
.st-key-facilities button[aria-checked="true"] p, .st-key-facilities button[aria-pressed="true"] p { color: #FFFFFF !important; }
[class*="st-key-dlg_"] button[data-variant="pills"] { border-radius: 8px !important; background: #FFFFFF !important;
  border: 1px solid #D1D5DB !important; min-height: 40px; }
[class*="st-key-dlg_"] button[aria-checked="true"] { border: 1.5px solid #2563EB !important; }
[class*="st-key-dlg_"] button[aria-checked="true"] p { color: #2563EB !important; font-weight: 700; }
.st-key-ctype div[data-baseweb="select"] > div { border-radius: 999px; }
.st-key-open_settings button { border-radius: 999px; width: 44px; height: 44px; padding: 0;
  background: #FFFFFF; border: 1px solid #D1D5DB; }
@media (max-width: 640px) {
  .block-container { padding: 1.2rem 0.75rem 2rem; }
  .stMain iframe, .stMain .stElementContainer:has(> iframe) { height: 380px !important; flex: 0 0 380px !important; }
  .st-key-maphint { display: none; }
  .st-key-sheet { margin-top: -48px; position: relative; z-index: 2; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>
"""
st.html(STYLE)

KAKAO_JS_KEY = config.get_setting("KAKAO_JS_KEY")
DATASET_PATH = config.get_setting("DATASET_PATH", "dataset/seoul.json")

if not KAKAO_JS_KEY:
    st.error("설정이 필요합니다: KAKAO_JS_KEY — 로컬은 .env, 배포는 Streamlit Secrets에 입력하세요.")
    st.stop()

GROUP_ICONS = {"지체장애": ":material/accessible:", "시각장애": ":material/visibility:",
               "청각장애": ":material/hearing:", "영유아가족": ":material/child_friendly:"}
CHIP_LABELS = dict(FACILITY_CHIPS)


@st.cache_data(show_spinner=False)
def get_dataset(path):
    return load_dataset(path)


def select(content_id):
    st.session_state.selected_id = content_id


try:
    data = get_dataset(DATASET_PATH)
except FileNotFoundError:
    st.error(f"데이터 파일({DATASET_PATH})이 없습니다. 먼저 `python build_dataset.py` 를 실행하세요.")
    st.stop()

sigungus = {s["code"]: s["name"] for s in data.get("sigungu", [])}
area_name = data.get("area_name", "")

for name, default in (("sigungu", None), ("selected_id", None), ("last_query", None), ("results", [])):
    st.session_state.setdefault(name, default)


@st.dialog("세부 설정")
def settings_dialog():
    st.markdown(f"**{area_name} 시군구** · 선택하지 않으면 전체")
    sigungu = st.pills("시군구", list(sigungus), format_func=sigungus.get, default=st.session_state.sigungu,
                       key="dlg_sigungu", label_visibility="collapsed")
    if st.button("저장", type="primary", width="stretch"):
        st.session_state.sigungu = sigungu
        st.rerun()


st.title("Trip For All")
st.caption(f"{area_name} 무장애 관광 지도 · 데이터 기준일 {data.get('built_at', '-')} · 출처: 한국관광공사 무장애여행 정보")

map_col, panel_col = st.columns([3, 2], gap="medium")

with panel_col:
    sheet = st.container(key="sheet")

with sheet:
    # 열(columns)은 휴대폰 폭에서 세로로 쌓이므로 가로 컨테이너로 검색창과 버튼을 한 줄에 둔다.
    with st.container(horizontal=True, vertical_alignment="center", gap="small"):
        keyword = st.text_input("장소 검색", key="keyword", placeholder="장소나 편의시설로 검색해 보세요 (예: 경사로)",
                                icon=":material/search:", label_visibility="collapsed")
        if st.button("", icon=":material/tune:", key="open_settings", help="세부 설정 (시군구)"):
            settings_dialog()
    ctype = st.selectbox("관광타입", [None, *CONTENT_TYPES], key="ctype", label_visibility="collapsed",
                         format_func=lambda c: CONTENT_TYPES.get(c, "관광타입 전체"))
    facilities = st.pills("편의시설", list(CHIP_LABELS), format_func=CHIP_LABELS.get, key="facilities",
                          selection_mode="multi", label_visibility="collapsed") or []

    sigungu = st.session_state.sigungu
    query = (sigungu, ctype, tuple(facilities), (keyword or "").strip())
    if query != st.session_state.last_query:
        st.session_state.selected_id = None
        st.session_state.last_query = query
    places = filter_places(data["places"], sigungu=sigungu, content_type=ctype,
                           facilities=facilities, keyword=keyword)
    st.session_state.results = places

selected = next((p for p in places if p["contentid"] == st.session_state.selected_id), None)
info = selected["barrier"] if selected else {}

with sheet:
    region = " · ".join(n for n in (area_name, sigungus.get(sigungu)) if n)
    st.markdown(f'<div class="region">{escape(region)}</div>', unsafe_allow_html=True)

    if selected:
        with st.container(border=True, key="detail"):
            head, close = st.columns([10, 1], vertical_alignment="top")
            head.markdown(f'<div class="detail-title">{escape(selected.get("title", ""))}</div>'
                          f'<div class="detail-meta">{escape(selected.get("addr1", ""))}<br>'
                          f'전화 {escape(selected.get("tel") or "-")}</div>', unsafe_allow_html=True)
            close.button("", icon=":material/close:", key="close_detail", type="tertiary",
                         help="선택 해제", on_click=select, args=(None,))
            if selected.get("firstimage"):
                st.image(selected["firstimage"], width="stretch")
            shown = False
            for group, fields in BARRIER_GROUPS:
                rows = [(label, info[key]) for key, label in fields if info.get(key)]
                if rows:
                    shown = True
                    st.markdown(f"{GROUP_ICONS[group]} **{group}**")
                    st.markdown("".join(f'<div class="info-row"><span>{escape(label)}</span>{escape(value)}</div>'
                                        for label, value in rows), unsafe_allow_html=True)
            if not shown:
                st.markdown("등록된 무장애 정보가 없습니다")

    st.markdown(f"**검색 결과 {len(places)}곳**")
    if not places:
        st.caption("조건에 맞는 장소가 없어요. 편의시설 칩을 줄이거나 검색어를 바꿔 보세요.")

    with st.container(height=560 if places else "content", border=False, key="list"):
        for p in places:
            cid = p["contentid"]
            is_sel = cid == st.session_state.selected_id
            with st.container(border=True, key=f"card-selected-{cid}" if is_sel else f"card-{cid}"):
                # 원본 서버에 없는 이미지가 많아 배경 이미지로 넣는다. 실패하면 회색 칸만 보인다.
                thumb = (f'<div class="thumb" style="background-image:url(&quot;{escape(p["firstimage2"])}&quot;)"></div>'
                         if p.get("firstimage2") else '<div class="thumb"></div>')
                ctype_name = CONTENT_TYPES.get(str(p.get("contenttypeid")), "")
                # 켜 둔 칩에 해당하는 편의시설을 앞에 두고 파란색으로 강조한다.
                keys = sorted((k for k in CHIP_LABELS if k in p["barrier"]), key=lambda k: k not in facilities)
                tags = "".join(f'<span class="tag{" blue" if k in facilities else ""}">{escape(CHIP_LABELS[k])}</span>'
                               for k in keys[:4])
                if len(keys) > 4:
                    tags += f'<span class="tag">+{len(keys) - 4}</span>'
                st.markdown(
                    f'<div class="card"><div class="card-body">'
                    f'<div class="card-title">{escape(p.get("title", ""))}</div>'
                    f'<div class="card-addr">{escape(p.get("addr1", ""))}</div>'
                    f'<span class="tag">{escape(ctype_name)}</span>{tags}</div>{thumb}</div>',
                    unsafe_allow_html=True)
                st.button("선택됨" if is_sel else "자세히 보기", key=f"pick_{cid}", type="tertiary",
                          icon=":material/check:" if is_sel else ":material/chevron_right:",
                          on_click=select, args=(cid,))

tags = [label for _, fields in BARRIER_GROUPS for key, label in fields if info.get(key)][:4]
with map_col:
    st.iframe(render_map_html(places, KAKAO_JS_KEY, st.session_state.selected_id, tags), height=620)
    with st.container(key="maphint"):
        st.caption("지도가 보이지 않으면 카카오 개발자 콘솔 > 플랫폼 > Web 사이트 도메인에 현재 주소를 등록하세요.")
