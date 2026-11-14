import os
import nasa_access

def test_no_secrets_in_diagnostics(monkeypatch):
    monkeypatch.setenv("EARTHDATA_TOKEN", "very-secret-edl-token")
    monkeypatch.setenv("EARTHDATA_USERNAME", "private-user")
    monkeypatch.setenv("EARTHDATA_PASSWORD", "very-secret-password")
    config = nasa_access.configuration()
    assert config["earthdata_bearer_configured"]
    assert config["appeears_auth_configured"]
    for secret in ("very-secret-edl-token", "private-user", "very-secret-password"):
        assert secret not in str(config)

def test_edl_token_alone_does_not_authorize_appeears(monkeypatch):
    monkeypatch.setenv("EARTHDATA_TOKEN", "edl-token")
    monkeypatch.delenv("EARTHDATA_USERNAME", raising=False)
    monkeypatch.delenv("EARTHDATA_PASSWORD", raising=False)
    monkeypatch.delenv("APPEEARS_TOKEN", raising=False)
    assert nasa_access.configuration()["appeears_auth_method"] == "missing"
