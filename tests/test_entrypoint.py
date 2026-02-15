from unittest.mock import patch, MagicMock


def _make_entrypoint():
    """Import and return the entrypoint function, mocking heavy dependencies."""
    with patch("app.BedrockAgentCoreApp"), \
         patch("app.BedrockModel"), \
         patch("app.Agent") as mock_agent_cls:
        # Set up agent mock so agent(prompt) returns an object with .text
        mock_response = MagicMock()
        mock_response.text = "mock response"
        mock_agent_cls.return_value.return_value = mock_response

        import importlib
        import app as app_module
        importlib.reload(app_module)
        return app_module.main, mock_agent_cls


class TestEntrypointValidation:
    def test_none_payload_returns_error(self):
        with patch("app.BedrockAgentCoreApp") as mock_app, \
             patch("app.BedrockModel"), \
             patch("app.Agent"):
            mock_app.return_value.entrypoint = lambda f: f
            import importlib
            import app as app_module
            importlib.reload(app_module)

            result = app_module.main(None)
            assert result["status"] == "error"
            assert "Invalid payload" in result["output"]

    def test_empty_string_payload_returns_error(self):
        with patch("app.BedrockAgentCoreApp") as mock_app, \
             patch("app.BedrockModel"), \
             patch("app.Agent"):
            mock_app.return_value.entrypoint = lambda f: f
            import importlib
            import app as app_module
            importlib.reload(app_module)

            result = app_module.main("not a dict")
            assert result["status"] == "error"

    def test_empty_prompt_returns_error(self):
        with patch("app.BedrockAgentCoreApp") as mock_app, \
             patch("app.BedrockModel"), \
             patch("app.Agent"):
            mock_app.return_value.entrypoint = lambda f: f
            import importlib
            import app as app_module
            importlib.reload(app_module)

            result = app_module.main({"prompt": "   "})
            assert result["status"] == "error"
            assert "Empty prompt" in result["output"]

    def test_valid_prompt_returns_success(self):
        with patch("app.BedrockAgentCoreApp") as mock_app, \
             patch("app.BedrockModel"), \
             patch("app.Agent") as mock_agent_cls:
            mock_app.return_value.entrypoint = lambda f: f
            mock_response = MagicMock()
            mock_response.text = "test output"
            mock_agent_cls.return_value.return_value = mock_response

            import importlib
            import app as app_module
            importlib.reload(app_module)

            result = app_module.main({"prompt": "hello"})
            assert result["status"] == "success"
            assert result["output"] == "test output"

    def test_agent_exception_returns_error(self):
        with patch("app.BedrockAgentCoreApp") as mock_app, \
             patch("app.BedrockModel"), \
             patch("app.Agent") as mock_agent_cls:
            mock_app.return_value.entrypoint = lambda f: f
            mock_agent_cls.return_value.side_effect = RuntimeError("bedrock timeout")

            import importlib
            import app as app_module
            importlib.reload(app_module)

            result = app_module.main({"prompt": "hello"})
            assert result["status"] == "error"
            assert "RuntimeError" in result["output"]
