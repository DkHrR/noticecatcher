import sys


def test_serve_engine_not_imported_until_make_app():
    sys.modules.pop("engine", None)
    if "serve" in sys.modules:
        del sys.modules["serve"]

    import serve

    assert "engine" not in sys.modules, "engine must not be imported when serve is imported"

    app = serve.make_app()
    assert app is not None
    assert "engine" in sys.modules, "engine should be loaded after make_app() is called"
