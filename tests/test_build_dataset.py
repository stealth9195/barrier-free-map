from build_dataset import build
from tour_api import TourApiError


class FakeApi:
    def __init__(self, rows, details, fail=()):
        self.rows, self.details, self.fail = rows, details, set(fail)
        self.pages = []

    def area_codes(self, area_code=None):
        if area_code:
            return [{"code": "23", "name": "종로구"}]
        return [{"code": "1", "name": "서울"}]

    def area_based_page(self, area_code, page, rows=1000):
        self.pages.append(page)
        chunk = self.rows[(page - 1) * 2: page * 2]
        return chunk, len(self.rows)

    def barrier_free(self, content_id):
        if content_id in self.fail:
            raise TourApiError("timeout")
        return self.details.get(content_id, {})


def row(cid, x="126.9", y="37.5", img="http://tong.visitkorea.or.kr/a.jpg"):
    return {"contentid": cid, "title": f"장소{cid}", "addr1": "서울", "tel": "", "contenttypeid": "12",
            "sigungucode": "23", "firstimage": img, "firstimage2": img, "mapx": x, "mapy": y}


def test_build_pages_until_total_and_cleans():
    api = FakeApi([row("1"), row("2"), row("3", x="0", y="0")],
                  {"1": {"parking": "있음<br>2면", "route": "경사로<br />있음"}})
    data = build(api, "1", page_size=2, built_at="2026-10-23")
    assert api.pages == [1, 2]
    assert data["area_name"] == "서울" and data["built_at"] == "2026-10-23"
    assert data["sigungu"] == [{"code": "23", "name": "종로구"}]
    ids = [p["contentid"] for p in data["places"]]
    assert ids == ["1", "2"]
    p1 = data["places"][0]
    assert p1["barrier"] == {"parking": "있음 / 2면", "route": "경사로 / 있음"}
    assert p1["mapx"] == 126.9 and p1["firstimage"].startswith("https://")
    assert data["failed"] == 0


def test_build_failed_detail_becomes_empty_barrier():
    api = FakeApi([row("1")], {}, fail={"1"})
    data = build(api, "1", page_size=2, built_at="x", retries=1)
    assert data["places"][0]["barrier"] == {} and data["failed"] == 1
