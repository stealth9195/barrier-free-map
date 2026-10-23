"""지역 무장애 관광정보 + 장소별 편의시설 정보를 미리 받아 앱용 JSON 으로 저장한다.

사용법: python build_dataset.py [areaCode=1] [출력=dataset/seoul.json]
앱은 이 파일만 읽으므로, 실행 중에는 data.go.kr 을 호출하지 않는다.
"""
import concurrent.futures as cf
import datetime
import json
import os
import re
import sys
import time

from tour_api import TourApiError

FIELDS = ("contentid", "title", "addr1", "tel", "contenttypeid", "sigungucode", "firstimage", "firstimage2")


def _clean(value):
    return re.sub(r"\s*<br\s*/?>\s*", " / ", str(value or "")).strip()


def _https(url):
    return "https://" + url[len("http://"):] if url.startswith("http://") else url


def _detail(api, content_id, retries):
    for attempt in range(retries):
        try:
            return {k: _clean(v) for k, v in api.barrier_free(content_id).items() if _clean(v)}
        except TourApiError:
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
    return None


def build(api, area_code, page_size=1000, built_at=None, retries=3):
    area_name = next((a["name"] for a in api.area_codes() if a["code"] == area_code), area_code)
    rows, page = [], 1
    while True:
        items, total = api.area_based_page(area_code, page, rows=page_size)
        rows += items
        if not items or len(rows) >= total:
            break
        page += 1

    places = []
    for r in rows:
        try:
            x, y = float(r.get("mapx") or 0), float(r.get("mapy") or 0)
        except ValueError:
            continue
        if x and y:
            place = {k: str(r.get(k) or "") for k in FIELDS}
            place["firstimage"], place["firstimage2"] = _https(place["firstimage"]), _https(place["firstimage2"])
            places.append({**place, "mapx": x, "mapy": y})

    with cf.ThreadPoolExecutor(3) as ex:
        details = list(ex.map(lambda p: _detail(api, p["contentid"], retries), places))
    for place, detail in zip(places, details):
        place["barrier"] = detail or {}

    return {
        "area_code": area_code,
        "area_name": area_name,
        "built_at": built_at or datetime.date.today().isoformat(),
        "sigungu": api.area_codes(area_code),
        "failed": sum(d is None for d in details),
        "places": places,
    }


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    from config import get_setting
    from tour_api import DEFAULT_BASE_URL, TourApi

    area = sys.argv[1] if len(sys.argv) > 1 else "1"
    path = sys.argv[2] if len(sys.argv) > 2 else "dataset/seoul.json"
    api = TourApi(get_setting("OPENAI_API_KEY"), get_setting("OPENAI_END_POINT", DEFAULT_BASE_URL))
    data = build(api, area)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{data['area_name']} {len(data['places'])}곳 -> {path} (상세 실패 {data['failed']}곳)")
