def test_package_importable():
    import x4_companion
    assert x4_companion.__version__ == "0.1.0"
