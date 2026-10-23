"""설정 로딩: st.secrets(배포) → 환경변수/.env(로컬) 순서로 조회한다."""
import os

from dotenv import load_dotenv

load_dotenv()


def _read_secret(name):
    try:
        import streamlit as st

        return st.secrets.get(name)
    except Exception:
        # secrets.toml 이 없으면 st.secrets 접근 자체가 예외를 던진다.
        return None


def get_setting(name, default=None):
    for value in (_read_secret(name), os.environ.get(name)):
        if value:
            return value
    return default
