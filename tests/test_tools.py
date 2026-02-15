from unittest.mock import patch


def test_get_weather_returns_string():
    with patch("tools.tool", lambda f: f):
        # Re-import to get the raw function without decorator side effects
        import importlib
        import tools
        importlib.reload(tools)
        result = tools.get_weather("Columbus")
        assert isinstance(result, str)
        assert "Columbus" in result


def test_get_crypto_price_returns_string():
    with patch("tools.tool", lambda f: f):
        import importlib
        import tools
        importlib.reload(tools)
        result = tools.get_crypto_price("BTC")
        assert isinstance(result, str)
        assert "BTC" in result
