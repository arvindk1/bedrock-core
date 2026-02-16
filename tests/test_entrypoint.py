import sys
import os
import importlib
import asyncio
from unittest.mock import MagicMock

# Add agent directory to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

# Save original modules to restore later
_original_modules = {}


def _run_async(coro):
    """Helper to run async functions in sync tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def setup_module():
    """Mock heavy dependencies before importing app."""
    for mod_name in ("strands", "strands.tools", "strands.models", "bedrock_agentcore", "bedrock_agentcore.runtime", "dotenv",
                     "options_scanner", "orchestrator", "risk_engine"):
        _original_modules[mod_name] = sys.modules.get(mod_name)

    mock_strands = MagicMock()
    mock_strands.Agent = MagicMock
    sys.modules["strands"] = mock_strands

    mock_strands_tools = MagicMock()
    mock_strands_tools.tool = lambda f: f
    sys.modules["strands.tools"] = mock_strands_tools

    sys.modules["strands.models"] = MagicMock()
    sys.modules["bedrock_agentcore"] = MagicMock()
    sys.modules["bedrock_agentcore.runtime"] = MagicMock()
    sys.modules["dotenv"] = MagicMock()

    # Mock agent submodules
    sys.modules["options_scanner"] = MagicMock()
    sys.modules["orchestrator"] = MagicMock()
    sys.modules["risk_engine"] = MagicMock()

    import agent.tools as tools
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
    import agent.app as app_module

    mock_agentcore_app = MagicMock()
    mock_agentcore_app.return_value.entrypoint = lambda f: f
    sys.modules["bedrock_agentcore.runtime"].BedrockAgentCoreApp = mock_agentcore_app

    mock_agent_cls = MagicMock()
    if agent_side_effect:
        mock_agent_instance = MagicMock(side_effect=agent_side_effect)
        mock_agent_cls.return_value = mock_agent_instance
    else:
        mock_response = MagicMock()
        mock_response.message = {"content": "test output"}
        mock_agent_cls.return_value.return_value = mock_response
    sys.modules["strands"].Agent = mock_agent_cls

    importlib.reload(app_module)
    return app_module.invoke


class TestEntrypointValidation:
    def test_none_payload_returns_error(self):
        main = _reload_app()
        result = _run_async(main(None))
        assert result["status"] == "error"
        assert "Invalid payload" in result["output"]

    def test_non_dict_payload_returns_error(self):
        main = _reload_app()
        result = _run_async(main("not a dict"))
        assert result["status"] == "error"

    def test_empty_prompt_returns_error(self):
        main = _reload_app()
        result = _run_async(main({"prompt": "   "}))
        assert result["status"] == "error"
        assert "Empty prompt" in result["output"]

    def test_none_prompt_returns_error(self):
        main = _reload_app()
        result = _run_async(main({"prompt": None}))
        assert result["status"] == "error"
        assert "Empty prompt" in result["output"]

    def test_missing_prompt_key_returns_error(self):
        main = _reload_app()
        result = _run_async(main({"other_key": "value"}))
        assert result["status"] == "error"
        assert "Empty prompt" in result["output"]

    def test_valid_prompt_returns_success(self):
        main = _reload_app()
        result = _run_async(main({"prompt": "hello"}))
        assert result["status"] == "success"
        assert result["output"] == "test output"

    def test_agent_exception_returns_error(self):
        main = _reload_app(agent_side_effect=RuntimeError("bedrock timeout"))
        result = _run_async(main({"prompt": "hello"}))
        assert result["status"] == "error"
        assert "RuntimeError" in result["output"]
