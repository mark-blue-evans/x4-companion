from x4_companion.config import load_config

def test_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv("MINIMAX_API_KEY", "mm-test")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "dg-test")
    cfg = load_config(tmp_path / "missing.toml")
    assert cfg.hotkey.key == "home"
    assert cfg.brain.model == "MiniMax-M2.7"
    assert cfg.brain.history_turns == 12
    assert cfg.overlay.opacity == 0.85
    assert cfg.secrets.minimax_api_key == "mm-test"
    assert cfg.secrets.deepgram_api_key == "dg-test"

def test_overrides_from_toml(tmp_path, monkeypatch):
    monkeypatch.setenv("MINIMAX_API_KEY", "")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "")
    p = tmp_path / "c.toml"
    p.write_text(
        '[hotkey]\nkey = "f8"\n'
        '[brain]\nhistory_turns = 12\n'
        '[overlay]\nposition = "top-left"\n'
    )
    cfg = load_config(p)
    assert cfg.hotkey.key == "f8"
    assert cfg.brain.history_turns == 12
    assert cfg.overlay.position == "top-left"
    assert cfg.brain.model == "MiniMax-M2.7"
