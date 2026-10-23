from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def place(cid):
    return {"contentid": cid, "title": f"장소{cid}", "addr1": "서울", "contenttypeid": "12",
            "firstimage2": "", "mapx": 126.9, "mapy": 37.5}


class FakeApi:
    search_calls = 0

    def __init__(self, *args, **kwargs):
        pass

    def area_codes(self, area_code=None):
        return [] if area_code else [{"code": "1", "name": "서울"}]

    def search(self, **kwargs):
        FakeApi.search_calls += 1
        n = 3 if FakeApi.search_calls == 1 else 1
        return [place(str(i)) for i in range(1, n + 1)], n

    def barrier_free(self, content_id):
        return {"parking": "있음"}


@pytest.fixture(autouse=True)
def clear_caches():
    st.cache_data.clear()
    st.cache_resource.clear()
    FakeApi.search_calls = 0


def test_missing_keys_shows_error(monkeypatch):
    monkeypatch.setattr("config.get_setting", lambda n, d=None: d)
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert any("OPENAI_API_KEY" in e.value for e in at.error)


def test_new_search_resets_selection(monkeypatch):
    monkeypatch.setattr("config.get_setting", lambda n, d=None: d or "dummy")
    monkeypatch.setattr("tour_api.TourApi", FakeApi)
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.button[0].click().run()
    assert len(at.session_state["results"][0]) == 3

    at.session_state["selected_id"] = "3"
    at.text_input[0].input("다른 검색")
    at.button[0].click().run()
    assert not at.exception
    assert len(at.session_state["results"][0]) == 1
    assert at.session_state["selected_id"] is None


def test_selected_place_shows_barrier_info(monkeypatch):
    monkeypatch.setattr("config.get_setting", lambda n, d=None: d or "dummy")
    monkeypatch.setattr("tour_api.TourApi", FakeApi)
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.button[0].click().run()
    at.session_state["selected_id"] = "2"
    at.run()
    text = " ".join(m.value for m in at.markdown)
    assert "장소2" in text and "주차" in text and "있음" in text


def test_api_error_shows_message(monkeypatch):
    import tour_api

    class Broken(FakeApi):
        def area_codes(self, area_code=None):
            raise tour_api.TourApiError(tour_api.QUOTA_EXCEEDED)

    monkeypatch.setattr("config.get_setting", lambda n, d=None: d or "dummy")
    monkeypatch.setattr("tour_api.TourApi", Broken)
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert any("오늘 API 호출 한도를 초과했습니다" in e.value for e in at.error)
