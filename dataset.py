"""미리 수집한 무장애 관광 데이터셋 로딩과 필터링 (Streamlit 비의존)."""
import json


def load_dataset(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def filter_places(places, *, sigungu=None, content_type=None, facilities=(), keyword=""):
    keyword = (keyword or "").strip().lower()
    result = []
    for p in places:
        barrier = p.get("barrier") or {}
        if sigungu and p.get("sigungucode") != sigungu:
            continue
        if content_type and p.get("contenttypeid") != content_type:
            continue
        if any(f not in barrier for f in facilities):
            continue
        if keyword:
            text = " ".join([p.get("title", ""), p.get("addr1", ""), *barrier.values()]).lower()
            if keyword not in text:
                continue
        result.append(p)
    return result
