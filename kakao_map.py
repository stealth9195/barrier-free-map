"""카카오맵 JavaScript SDK로 장소 마커를 그리는 HTML 생성."""
import json
import re

CITY_HALL = (37.5666, 126.9784)
ACCENT = "#2563EB"

_PIN_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="42" viewBox="0 0 32 42">'
    '<path d="M16 41s14-13.2 14-25A14 14 0 0 0 2 16c0 11.8 14 25 14 25z" fill="COLOR" stroke="#fff" stroke-width="2"/>'
    '<circle cx="16" cy="16" r="5.5" fill="#fff"/></svg>'
)

_TEMPLATE = """
<style>
  html, body { margin: 0; height: 100%; font-family: "Noto Sans KR", system-ui, sans-serif; }
  #map { width: 100%; height: 100%; border-radius: 16px; overflow: hidden; }
  .iw { padding: 12px 14px; width: 220px; box-sizing: border-box; color: #0F172A; }
  .iw b { display: block; font-size: 14px; font-weight: 700; margin-bottom: 2px; }
  .iw .addr { font-size: 12px; color: #475569; line-height: 1.4; }
  .iw img { width: 100%; height: 96px; object-fit: cover; border-radius: 8px; margin-top: 8px; }
  .iw .tags { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
  .iw .tag { font-size: 11px; color: #1D4ED8; background: #EFF6FF; border-radius: 6px; padding: 2px 6px; }
</style>
<div id="map"></div>
<script src="https://dapi.kakao.com/v2/maps/sdk.js?appkey=__KEY__&autoload=false"></script>
<script>
const places = __PLACES__;
const selectedId = __SELECTED__;
const selectedTags = __TAGS__;
const pin = __PIN__;
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}
kakao.maps.load(function () {
  const map = new kakao.maps.Map(document.getElementById("map"), {
    center: new kakao.maps.LatLng(__LAT__, __LNG__), level: 7
  });
  const normal = new kakao.maps.MarkerImage(pin.normal, new kakao.maps.Size(28, 37),
    { offset: new kakao.maps.Point(14, 37) });
  const big = new kakao.maps.MarkerImage(pin.selected, new kakao.maps.Size(40, 52),
    { offset: new kakao.maps.Point(20, 52) });
  const bounds = new kakao.maps.LatLngBounds();
  let opened = null;
  places.forEach(function (p) {
    const pos = new kakao.maps.LatLng(p.mapy, p.mapx);
    const isSel = p.contentid === selectedId;
    const marker = new kakao.maps.Marker({
      map: map, position: pos, title: p.title, image: isSel ? big : normal, zIndex: isSel ? 10 : 1
    });
    const img = p.firstimage2 ? '<img src="' + esc(p.firstimage2) + '" alt="">' : "";
    const tags = isSel && selectedTags.length
      ? '<div class="tags">' + selectedTags.map(t => '<span class="tag">' + esc(t) + '</span>').join("") + '</div>'
      : "";
    const info = new kakao.maps.InfoWindow({
      content: '<div class="iw"><b>' + esc(p.title) + '</b><div class="addr">' + esc(p.addr1) + '</div>'
        + img + tags + '</div>'
    });
    kakao.maps.event.addListener(marker, "click", function () {
      if (opened) opened.close();
      if (opened === info) { opened = null; return; }
      info.open(map, marker); opened = info;
    });
    bounds.extend(pos);
    if (isSel) {
      map.setLevel(4); map.setCenter(pos);
      map.panBy(0, -140);  // 인포윈도우가 위로 잘리지 않게 핀을 아래쪽으로 내린다
      info.open(map, marker); opened = info;
    }
  });
  if (places.length && !places.some(p => p.contentid === selectedId)) map.setBounds(bounds);
});
</script>
"""


def _js(value):
    # "</script>" 같은 문자열이 스크립트 블록을 끊지 못하도록 "<" 를 이스케이프한다.
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


def _pin_uri(color):
    return "data:image/svg+xml;charset=utf-8," + _PIN_SVG.replace("COLOR", color).replace("#", "%23")


def render_map_html(places, js_key, selected_id=None, selected_tags=None):
    data = [{k: p.get(k) for k in ("contentid", "title", "addr1", "firstimage2", "mapx", "mapy")}
            for p in places]
    values = {
        "__KEY__": js_key,
        "__PLACES__": _js(data),
        "__SELECTED__": _js(selected_id),
        "__TAGS__": _js(list(selected_tags or [])),
        "__PIN__": _js({"normal": _pin_uri(ACCENT), "selected": _pin_uri("#1D4ED8")}),
        "__LAT__": str(CITY_HALL[0]),
        "__LNG__": str(CITY_HALL[1]),
    }
    # 한 번에 치환해야 장소 데이터 안의 "__SELECTED__" 같은 글자가 다시 치환되지 않는다.
    return re.sub("|".join(values), lambda m: values[m.group(0)], _TEMPLATE)
