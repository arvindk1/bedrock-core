import sys
import importlib
from unittest.mock import MagicMock

# Save original modules to restore later
_original_modules = {}


def setup_module():
    """Mock heavy dependencies before importing app."""
    for mod_name in ("strands_agents", "strands_agents.models", "bedrock_agentcore", "dotenv"):
        _original_modules[mod_name] = sys.modules.get(mod_name)

    mock_strands = MagicMock()
    mock_strands.tool = lambda f: f
    sys.modules["strands_agents"] = mock_strands
    sys.modules["strands_agents.models"] = MagicMock()
    sys.modules["bedrock_agentcore"] = MagicMock()
    sys.modules["dotenv"] = MagicMock()

    import delete.tools as tools
    importlib.reload(tools)


def teardown_module():
    """Restore original modules."""
    for mod_name, original in _original_modules.items():
        if original is None:
            sys.modules.pop(mod_name, None)
        else:
            sys.modules[mod_name] = original


def _reload_app(agent_side_effect=None):
    """Reload app module with a fresh mock agent, return the entrypoint function."""
    import delete.app as app_module

    mock_agentcore_app = MagicMock()
    mock_agentcore_app.return_value.entrypoint = lambda f: f
    sys.modules["bedrock_agentcore"].BedrockAgentCoreApp = mock_agentcore_app

    mock_agent_cls = MagicMock()
    if agent_side_effect:
        mock_agent_cls.return_value.side_effect = agent_side_effect
    else:
        mock_response = MagicMock()
        mock_response.text = "test output"
        mock_agent_cls.return_value.return_value = mock_response
    sys.modules["strands_agents"].Agent = mock_agent_cls

    importlib.reload(app_module)
    return app_module.main


class TestEntrypointValidation:
    def test_none_payload_returns_error(self):
        main = _reload_app()
        result = main(None)
        assert result["status"] == "error"
        assert "Invalid payload" in result["output"]

    def test_non_dict_payload_returns_error(self):
        main = _reload_app()
        result = main("not a dict")
        assert result["status"] == "error"

    def test_empty_prompt_returns_error(self):
        main = _reload_app()
        result = main({"prompt": "   "})
        assert result["status"] == "error"
        assert "Empty prompt" in result["output"]

    def test_none_prompt_returns_error(self):
        main = _reload_app()
        result = main({"prompt": None})
        assert result["status"] == "error"
        assert "Empty prompt" in result["output"]

    def test_missing_prompt_key_returns_error(self):
        main = _reload_app()
        result = main({"other_key": "value"})
        assert result["status"] == "error"
        assert "Empty prompt" in result["output"]

    def test_valid_prompt_returns_success(self):
        main = _reload_app()
        result = main({"prompt": "hello"})
        assert result["status"] == "success"
        assert result["output"] == "test output"

    def test_agent_exception_returns_error(self):
        main = _reload_app(agent_side_effect=RuntimeError("bedrock timeout"))
        result = main({"prompt": "hello"})
        assert result["status"] == "error"
        assert "RuntimeError" in result["output"]
