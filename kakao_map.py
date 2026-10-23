"""카카오맵 JavaScript SDK로 장소 마커를 그리는 HTML 생성."""
import json
import re

CITY_HALL = (37.5666, 126.9784)

_TEMPLATE = """
<div id="map" style="width:100%;height:580px;border-radius:8px"></div>
<script src="https://dapi.kakao.com/v2/maps/sdk.js?appkey=__KEY__&autoload=false"></script>
<script>
const places = __PLACES__;
const selectedId = __SELECTED__;
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}
kakao.maps.load(function () {
  const map = new kakao.maps.Map(document.getElementById("map"), {
    center: new kakao.maps.LatLng(__LAT__, __LNG__), level: 7
  });
  const bounds = new kakao.maps.LatLngBounds();
  let opened = null;
  places.forEach(function (p) {
    const pos = new kakao.maps.LatLng(p.mapy, p.mapx);
    const marker = new kakao.maps.Marker({ map: map, position: pos, title: p.title });
    const img = p.firstimage2
      ? '<img src="' + esc(p.firstimage2) + '" style="width:120px;display:block;margin-top:4px">' : "";
    const info = new kakao.maps.InfoWindow({
      content: '<div style="padding:6px 8px;font-size:12px;max-width:220px">'
        + '<b>' + esc(p.title) + '</b><br>' + esc(p.addr1) + img + '</div>'
    });
    kakao.maps.event.addListener(marker, "click", function () {
      if (opened) opened.close();
      if (opened === info) { opened = null; return; }
      info.open(map, marker); opened = info;
    });
    bounds.extend(pos);
    if (p.contentid === selectedId) {
      map.setCenter(pos); map.setLevel(4);
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


def render_map_html(places, js_key, selected_id=None):
    data = [{k: p.get(k) for k in ("contentid", "title", "addr1", "firstimage2", "mapx", "mapy")}
            for p in places]
    values = {
        "__KEY__": js_key,
        "__PLACES__": _js(data),
        "__SELECTED__": _js(selected_id),
        "__LAT__": str(CITY_HALL[0]),
        "__LNG__": str(CITY_HALL[1]),
    }
    # 한 번에 치환해야 장소 데이터 안의 "__SELECTED__" 같은 글자가 다시 치환되지 않는다.
    return re.sub("|".join(values), lambda m: values[m.group(0)], _TEMPLATE)
