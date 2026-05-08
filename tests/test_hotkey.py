from x4_companion.hotkey import Hotkey

def test_hotkey_fires_once_per_press():
    downs, ups = [], []
    hk = Hotkey("home", lambda: downs.append(1), lambda: ups.append(1))
    hk._handle_down()
    hk._handle_down()
    hk._handle_up()
    hk._handle_up()
    assert downs == [1]
    assert ups == [1]

def test_hotkey_handles_multiple_press_release_cycles():
    downs, ups = [], []
    hk = Hotkey("home", lambda: downs.append(1), lambda: ups.append(1))
    for _ in range(3):
        hk._handle_down(); hk._handle_up()
    assert downs == [1, 1, 1]
    assert ups == [1, 1, 1]
