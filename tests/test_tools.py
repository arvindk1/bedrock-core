import os
import sys
from unittest.mock import MagicMock, patch

# Mock strands before importing tools
mock_strands = MagicMock()
mock_strands.tools.tool = lambda f: f  # @tool decorator is a passthrough
sys.modules["strands"] = mock_strands
sys.modules["strands.tools"] = mock_strands.tools

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

import importlib
import tools


def setup_module():
    importlib.reload(tools)


@patch("tools.find_cheapest_options", return_value="Current Price: $150.00\n...")
def test_scan_options_returns_result(mock_find):
    result = tools.scan_options("AAPL", "2026-03-01", "2026-06-01", 5)
    assert "Current Price" in result
    mock_find.assert_called_once_with("AAPL", "2026-03-01", "2026-06-01", 5)


@patch("tools.find_cheapest_options", side_effect=ValueError("No options available"))
def test_scan_options_value_error(mock_find):
    result = tools.scan_options("BAD", "2026-03-01", "2026-06-01")
    assert "Error:" in result
    assert "No options available" in result


@patch("tools.find_cheapest_options", side_effect=RuntimeError("network failure"))
def test_scan_options_generic_error(mock_find):
    result = tools.scan_options("AAPL", "2026-03-01", "2026-06-01")
    assert "Error scanning options" in result
    # Should NOT leak exception details
    assert "network failure" not in result
    assert "RuntimeError" not in result
