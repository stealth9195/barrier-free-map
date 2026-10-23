import json

import pytest
import requests

from tour_api import TourApi, TourApiError


class FakeResponse:
    def __init__(self, text, status_code):
        self.text = text
        self.status_code = status_code


class FakeSession:
    def __init__(self, text="", status=200, exc=None):
        self.text, self.status, self.exc = text, status, exc
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        if self.exc:
            raise self.exc
        return FakeResponse(self.text, self.status)


def ok(items, total=0, code="0000", msg="OK"):
    return json.dumps({"response": {
        "header": {"resultCode": code, "resultMsg": msg},
        "body": {"items": items, "totalCount": total},
    }}, ensure_ascii=False)


def test_search_parses_items_and_floats_coords():
    api = TourApi("k", session=FakeSession(ok({"item": [
        {"contentid": "1", "title": "A", "mapx": "126.9", "mapy": "37.5"},
        {"contentid": "2", "title": "B", "mapx": "", "mapy": ""},
        {"contentid": "3", "title": "C", "mapx": "0", "mapy": "0"}]}, total=3)))
    items, total = api.search(area_code="1")
    assert [i["contentid"] for i in items] == ["1"]
    assert items[0]["mapx"] == 126.9 and items[0]["mapy"] == 37.5
    assert total == 3


def test_single_item_dict_wrapped():
    api = TourApi("k", session=FakeSession(ok(
        {"item": {"contentid": "1", "title": "A", "mapx": "127", "mapy": "37"}}, total=1)))
    items, total = api.search()
    assert len(items) == 1 and total == 1


def test_empty_items_string():
    assert TourApi("k", session=FakeSession(ok(""))).search() == ([], 0)


def test_xml_error_raises():
    xml = ("<OpenAPI_ServiceResponse><cmmMsgHeader><errMsg>SERVICE ERROR</errMsg>"
           "<returnAuthMsg>SERVICE_KEY_IS_NOT_REGISTERED_ERROR</returnAuthMsg>"
           "</cmmMsgHeader></OpenAPI_ServiceResponse>")
    with pytest.raises(TourApiError, match="SERVICE_KEY_IS_NOT_REGISTERED_ERROR"):
        TourApi("k", session=FakeSession(xml)).search()


def test_result_code_not_ok_raises():
    with pytest.raises(TourApiError, match="INVALID"):
        TourApi("k", session=FakeSession(ok("", code="10", msg="INVALID"))).search()


@pytest.mark.parametrize("body", ["Internal Server Error", ""])
def test_non_json_body_raises(body):
    with pytest.raises(TourApiError, match="500"):
        TourApi("k", session=FakeSession(body, status=500)).search()


def test_html_error_page_raises():
    with pytest.raises(TourApiError):
        TourApi("k", session=FakeSession("<html>500</html>", status=500)).search()


def test_network_error_wrapped():
    with pytest.raises(TourApiError, match="네트워크 오류"):
        TourApi("k", session=FakeSession(exc=requests.Timeout("slow"))).search()


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


def test_area_codes_maps_fields():
    s = FakeSession(ok({"item": [{"code": "1", "name": "서울", "rnum": 1}]}, total=1))
    assert TourApi("k", session=s).area_codes("1") == [{"code": "1", "name": "서울"}]
    url, params = s.calls[0]
    assert url.endswith("/areaCode2") and params["areaCode"] == "1"


def test_barrier_free_drops_empty_and_contentid():
    s = FakeSession(ok({"item": [{"contentid": "9", "parking": "있음", "route": "", "elevator": "  "}]}))
    assert TourApi("k", session=s).barrier_free("9") == {"parking": "있음"}
    assert s.calls[0][1]["contentId"] == "9"


def test_network_error_hides_service_key():
    exc = requests.ConnectionError("Max retries exceeded with url: /areaCode2?serviceKey=SECRETKEY")
    with pytest.raises(TourApiError) as info:
        TourApi("SECRETKEY", session=FakeSession(exc=exc)).area_codes()
    assert "SECRETKEY" not in str(info.value)


def test_image_urls_upgraded_to_https():
    api = TourApi("k", session=FakeSession(ok({"item": [{
        "contentid": "1", "mapx": "127", "mapy": "37",
        "firstimage": "http://tong.visitkorea.or.kr/a.jpg",
        "firstimage2": "http://tong.visitkorea.or.kr/b.jpg"}]}, total=1)))
    item = api.search()[0][0]
    assert item["firstimage"] == "https://tong.visitkorea.or.kr/a.jpg"
    assert item["firstimage2"] == "https://tong.visitkorea.or.kr/b.jpg"
