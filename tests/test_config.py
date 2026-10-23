import config


def test_secrets_take_priority(monkeypatch):
    monkeypatch.setenv("KAKAO_JS_KEY", "from-env")
    monkeypatch.setattr(config, "_read_secret", lambda name: "from-secrets")
    assert config.get_setting("KAKAO_JS_KEY") == "from-secrets"


def test_env_fallback_when_secret_missing(monkeypatch):
    monkeypatch.setenv("KAKAO_JS_KEY", "from-env")
    monkeypatch.setattr(config, "_read_secret", lambda name: None)
    assert config.get_setting("KAKAO_JS_KEY") == "from-env"


def test_default_when_nothing(monkeypatch):
    monkeypatch.delenv("NOPE_KEY", raising=False)
    monkeypatch.setattr(config, "_read_secret", lambda name: None)
    assert config.get_setting("NOPE_KEY", "dflt") == "dflt"


def test_empty_string_treated_as_missing(monkeypatch):
    monkeypatch.setenv("KAKAO_JS_KEY", "")
    monkeypatch.setattr(config, "_read_secret", lambda name: None)
    assert config.get_setting("KAKAO_JS_KEY", "dflt") == "dflt"
