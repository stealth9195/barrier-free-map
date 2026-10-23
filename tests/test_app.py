from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def place(cid, title=None):
    return {"contentid": cid, "title": title or f"장소{cid}", "addr1": "서울", "contenttypeid": "12",
            "firstimage2": "", "mapx": 126.9, "mapy": 37.5}


class FakeApi:
    search_calls = []
    titles = {}

    def __init__(self, *args, **kwargs):
        pass

    def area_codes(self, area_code=None):
        return [] if area_code else [{"code": "1", "name": "서울"}]

    def search(self, **kwargs):
        FakeApi.search_calls.append(kwargs)
        n = 3 if len(FakeApi.search_calls) == 1 else 1
        return [place(str(i), FakeApi.titles.get(str(i))) for i in range(1, n + 1)], n

    def barrier_free(self, content_id):
        return {"parking": "있음"}


@pytest.fixture(autouse=True)
def clear_caches():
    st.cache_data.clear()
    st.cache_resource.clear()
    FakeApi.search_calls = []
    FakeApi.titles = {}


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr("config.get_setting", lambda n, d=None: d or "dummy")
    monkeypatch.setattr("tour_api.TourApi", FakeApi)
    return AppTest.from_file(APP, default_timeout=30)


def pick(at, cid):
    next(b for b in at.button if b.key == f"pick_{cid}").click().run()


def test_missing_keys_shows_error(monkeypatch):
    monkeypatch.setattr("config.get_setting", lambda n, d=None: d)
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert any("OPENAI_API_KEY" in e.value for e in at.error)


def test_first_screen_searches_without_button(app):
    at = app.run()
    assert not at.exception
    assert len(FakeApi.search_calls) == 1
    assert len(at.session_state["results"][0]) == 3
    assert not at.sidebar.children


def test_pick_card_then_new_keyword_resets_selection(app):
    at = app.run()
    pick(at, "3")
    assert at.session_state["selected_id"] == "3"

    at.text_input(key="keyword").input("다른 검색").run()
    assert not at.exception
    assert FakeApi.search_calls[-1]["keyword"] == "다른 검색"
    assert len(at.session_state["results"][0]) == 1
    assert at.session_state["selected_id"] is None


def test_content_type_pill_filters_search(app):
    at = app.run()
    at.button_group(key="ctype").set_value("39").run()
    assert FakeApi.search_calls[-1]["content_type_id"] == "39"


def test_area_from_settings_used_in_search(app):
    at = app.run()
    at.session_state["area"] = "1"
    at.run()
    assert FakeApi.search_calls[-1]["area_code"] == "1"


def test_selected_place_shows_barrier_info(app):
    at = app.run()
    pick(at, "2")
    text = " ".join(m.value for m in at.markdown)
    assert "장소2" in text and "주차" in text and "있음" in text


def test_card_escapes_html_in_title(app):
    FakeApi.titles = {"1": "<img src=x onerror=alert(1)>"}
    at = app.run()
    text = " ".join(m.value for m in at.markdown)
    assert "<img src=x" not in text and "&lt;img src=x" in text


def test_api_error_shows_message(monkeypatch):
    import tour_api

    class Broken(FakeApi):
        def area_codes(self, area_code=None):
            raise tour_api.TourApiError(tour_api.QUOTA_EXCEEDED)

        def search(self, **kwargs):
            raise tour_api.TourApiError(tour_api.QUOTA_EXCEEDED)

    monkeypatch.setattr("config.get_setting", lambda n, d=None: d or "dummy")
    monkeypatch.setattr("tour_api.TourApi", Broken)
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert any("오늘 API 호출 한도를 초과했습니다" in e.value for e in at.error)


def test_top100_notice_only_when_over_100(app, monkeypatch):
    monkeypatch.setattr(FakeApi, "search", lambda self, **kw: ([place("1")], 99))
    at = app.run()
    assert not any("상위 100건" in c.value for c in at.caption)


def test_top100_notice_when_over_100(app, monkeypatch):
    monkeypatch.setattr(FakeApi, "search", lambda self, **kw: ([place("1")], 250))
    at = app.run()
    assert any("상위 100건" in c.value for c in at.caption)
