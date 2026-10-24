from pathlib import Path
import engine


def test_fallback_api_key_and_model(monkeypatch):
    monkeypatch.setenv("API_KEY", "fallback-fake-key-12345")
    monkeypatch.setenv("MODEL", "custom-model-test")

    orig_exists = Path.exists
    monkeypatch.setattr(Path, "exists", lambda self: False if self.name == ".env" else orig_exists(self))

    # With bypass_prefix_check=True, it should return the env var fallback
    key_bypassed = engine.load_api_key(bypass_prefix_check=True)
    assert key_bypassed == "fallback-fake-key-12345"

    # With bypass_prefix_check=False, since fallback value does not start with expected prefix, it returns ""
    key_normal = engine.load_api_key(bypass_prefix_check=False)
    assert key_normal == ""

    # Model name should fallback to the env var MODEL
    model = engine.get_model_name()
    assert model == "custom-model-test"
