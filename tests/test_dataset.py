import json

from dataset import filter_places, load_dataset

PLACES = [
    {"contentid": "1", "title": "경복궁", "addr1": "종로구 사직로", "contenttypeid": "12", "sigungucode": "23",
     "barrier": {"parking": "장애인 주차장", "elevator": "있음", "route": "경사로 있음"}},
    {"contentid": "2", "title": "남산타워", "addr1": "용산구", "contenttypeid": "12", "sigungucode": "21",
     "barrier": {"parking": "있음"}},
    {"contentid": "3", "title": "한식당", "addr1": "종로구", "contenttypeid": "39", "sigungucode": "23",
     "barrier": {}},
]


def ids(ps):
    return [p["contentid"] for p in ps]


def test_no_filters_returns_all():
    assert ids(filter_places(PLACES)) == ["1", "2", "3"]


def test_facilities_are_and():
    assert ids(filter_places(PLACES, facilities=["parking"])) == ["1", "2"]
    assert ids(filter_places(PLACES, facilities=["parking", "elevator"])) == ["1"]


def test_content_type_and_sigungu():
    assert ids(filter_places(PLACES, content_type="39")) == ["3"]
    assert ids(filter_places(PLACES, sigungu="23")) == ["1", "3"]


def test_keyword_matches_title_addr_and_barrier_text():
    assert ids(filter_places(PLACES, keyword="남산")) == ["2"]
    assert ids(filter_places(PLACES, keyword="경사로")) == ["1"]
    assert ids(filter_places(PLACES, keyword="  ")) == ["1", "2", "3"]


def test_combined_filters():
    assert ids(filter_places(PLACES, sigungu="23", content_type="12", facilities=["route"], keyword="경복")) == ["1"]


def test_load_dataset(tmp_path):
    f = tmp_path / "d.json"
    f.write_text(json.dumps({"places": PLACES}, ensure_ascii=False), encoding="utf-8")
    assert len(load_dataset(str(f))["places"]) == 3
