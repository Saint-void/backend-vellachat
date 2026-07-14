from importlib import reload
from pathlib import Path

import pytest


def test_settings_loads_backend_dotenv_when_cwd_is_elsewhere(tmp_path, monkeypatch):
    import app.core.config as config

    for key in [
        "DATABASE_URL",
        "DIRECT_DATABASE_URL",
        "SUPABASE_URL",
        "SUPABASE_PUBLISHABLE_KEY",
    ]:
        monkeypatch.delenv(key, raising=False)

    monkeypatch.chdir(tmp_path)

    reloaded = reload(config)

    assert reloaded.settings.DATABASE_URL.startswith("postgresql")
    assert reloaded.settings.SUPABASE_URL.startswith("https://")
    assert reloaded.settings.SUPABASE_PUBLISHABLE_KEY.startswith("sb_publishable")
