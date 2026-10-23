from kakao_map import render_map_html
from labels import BARRIER_GROUPS, CONTENT_TYPES

P = [{"contentid": "1", "title": "경복궁", "addr1": "서울 종로구", "firstimage2": "",
      "mapx": 126.97, "mapy": 37.57}]


def test_includes_sdk_with_key():
    h = render_map_html(P, "JSKEY")
    assert "dapi.kakao.com/v2/maps/sdk.js?appkey=JSKEY&autoload=false" in h


def test_places_embedded_as_json():
    assert '"경복궁"' in render_map_html(P, "K")


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
    assert [g for g, _ in BARRIER_GROUPS] == ["지체장애", "시각장애", "청각장애", "영유아가족"]


def test_content_types():
    assert list(CONTENT_TYPES) == ["12", "14", "15", "28", "32", "38", "39"]
    assert CONTENT_TYPES["39"] == "음식점"


def test_placeholder_text_in_data_is_not_substituted():
    tricky = [{**P[0], "title": "a__SELECTED__b", "addr1": "__KEY__"}]
    h = render_map_html(tricky, "K", selected_id="1")
    assert '"a__SELECTED__b"' in h and '"__KEY__"' in h


def test_custom_marker_image_used():
    assert "MarkerImage" in render_map_html(P, "K")


def test_selected_tags_shown_in_infowindow():
    h = render_map_html(P, "K", selected_id="1", selected_tags=["경사로", "화장실"])
    assert '"경사로"' in h and '"화장실"' in h
