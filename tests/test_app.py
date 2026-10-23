import json
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def place(cid, title=None, ctype="12", sigungu="23", barrier=None):
    return {"contentid": cid, "title": title or f"장소{cid}", "addr1": "서울", "tel": "",
            "contenttypeid": ctype, "sigungucode": sigungu, "firstimage": "", "firstimage2": "",
            "mapx": 126.9, "mapy": 37.5, "barrier": barrier or {}}


PLACES = [
    place("1", barrier={"parking": "있음", "elevator": "있음"}),
    place("2", barrier={"parking": "있음", "route": "경사로 설치"}),
    place("3", ctype="39", sigungu="21"),
]


def write_dataset(tmp_path, places=PLACES):
    f = tmp_path / "seoul.json"
    f.write_text(json.dumps({"area_name": "서울", "built_at": "2026-10-23",
                             "sigungu": [{"code": "23", "name": "종로구"}, {"code": "21", "name": "용산구"}],
                             "places": places}, ensure_ascii=False), encoding="utf-8")
    return str(f)


@pytest.fixture(autouse=True)
def clear_caches():
    st.cache_data.clear()
    st.cache_resource.clear()


@pytest.fixture
def app(monkeypatch, tmp_path):
    path = write_dataset(tmp_path)
    settings = {"KAKAO_JS_KEY": "dummy", "DATASET_PATH": path}
    monkeypatch.setattr("config.get_setting", lambda n, d=None: settings.get(n, d))
    return AppTest.from_file(APP, default_timeout=30)


def shown(at):
    return [p["contentid"] for p in at.session_state["results"]]


def pick(at, cid):
    next(b for b in at.button if b.key == f"pick_{cid}").click().run()


def test_missing_kakao_key_shows_error(monkeypatch):
    monkeypatch.setattr("config.get_setting", lambda n, d=None: d)
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert any("KAKAO_JS_KEY" in e.value for e in at.error)


def test_runs_without_service_key(app):
    at = app.run()
    assert not at.exception and not at.error
    assert shown(at) == ["1", "2", "3"]


def test_title_is_trip_for_all(app):
    at = app.run()
    assert at.title[0].value == "Trip For All"


def test_missing_dataset_shows_hint(monkeypatch):
    settings = {"KAKAO_JS_KEY": "dummy", "DATASET_PATH": "nope/none.json"}
    monkeypatch.setattr("config.get_setting", lambda n, d=None: settings.get(n, d))
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert any("build_dataset.py" in e.value for e in at.error)


def test_facility_chips_are_and_and_toggle_off(app):
    at = app.run()
    at.button_group(key="facilities").set_value(["parking"]).run()
    assert shown(at) == ["1", "2"]
    at.button_group(key="facilities").set_value(["parking", "elevator"]).run()
    assert shown(at) == ["1"]
    at.button_group(key="facilities").set_value([]).run()
    assert shown(at) == ["1", "2", "3"]


def test_content_type_dropdown(app):
    at = app.run()
    at.selectbox(key="ctype").set_value("39").run()
    assert shown(at) == ["3"]


def test_keyword_searches_facility_text(app):
    at = app.run()
    at.text_input(key="keyword").input("경사로").run()
    assert shown(at) == ["2"]


def test_sigungu_from_settings(app):
    at = app.run()
    at.session_state["sigungu"] = "21"
    at.run()
    assert shown(at) == ["3"]


def test_filter_change_resets_selection(app):
    at = app.run()
    pick(at, "1")
    assert at.session_state["selected_id"] == "1"
    at.text_input(key="keyword").input("장소2").run()
    assert at.session_state["selected_id"] is None


def test_selected_place_shows_barrier_info(app):
    at = app.run()
    pick(at, "1")
    text = " ".join(m.value for m in at.markdown)
    assert "장소1" in text and "주차" in text and "엘리베이터" in text


def test_card_shows_facility_tags(app):
    at = app.run()
    text = " ".join(m.value for m in at.markdown)
    assert "경사로" not in text  # 태그는 라벨(접근로)로 표시
    assert "접근로" in text


def test_card_escapes_html_in_title(monkeypatch, tmp_path):
    path = write_dataset(tmp_path, [place("1", title="<img src=x onerror=alert(1)>")])
    settings = {"KAKAO_JS_KEY": "dummy", "DATASET_PATH": path}
    monkeypatch.setattr("config.get_setting", lambda n, d=None: settings.get(n, d))
    at = AppTest.from_file(APP, default_timeout=30).run()
    text = " ".join(m.value for m in at.markdown)
    assert "<img src=x" not in text and "&lt;img src=x" in text


def test_no_results_message(app):
    at = app.run()
    at.text_input(key="keyword").input("없는장소이름").run()
    assert any("조건에 맞는 장소가 없어요" in c.value for c in at.caption)
