
import pytest
from unittest.mock import patch, mock_open
from packaging.version import Version
import snap_constraints as constraints

@patch("snap_constraints.open", new_callable=mock_open)
@patch("snap_constraints.print")
def test_no_numpy_found(mock_print, mock_file):
    # Simulate numpy not being installed
    with patch("builtins.__import__", side_effect=ImportError):
        constraints.main()

    mock_print.assert_any_call("No system numpy found, skipping constraints.")
    mock_file().write.assert_called_once_with("")

@patch("snap_constraints.open", new_callable=mock_open)
@patch("snap_constraints.print")
def test_system_numpy_too_old(mock_print, mock_file):
    # Simulate numpy being installed with an old version
    with patch("builtins.__import__", return_value=type("MockNumpy", (), {"__version__": "1.25.0"})):
        constraints.main()

    mock_print.assert_any_call("System numpy version: 1.25.0")
    mock_print.assert_any_call("No constraint added for numpy version: 1.25.0")
    mock_file().write.assert_called_once_with("")

@patch("snap_constraints.open", new_callable=mock_open)
@patch("snap_constraints.print")
def test_system_numpy_meets_minimum_version(mock_print, mock_file):
    # Simulate numpy being installed with a version that meets the minimum
    with patch("builtins.__import__", return_value=type("MockNumpy", (), {"__version__": "1.26.4"})):
        constraints.main()

    mock_print.assert_any_call("System numpy version: 1.26.4")
    mock_print.assert_any_call("Constraint added for numpy version: 1.26.4")
    mock_file().write.assert_called_once_with("numpy==1.26.4\n")

@patch("snap_constraints.open", new_callable=mock_open)
@patch("snap_constraints.print")
def test_system_numpy_exceeds_minimum_version(mock_print, mock_file):
    # Simulate numpy being installed with a version newer than the minimum
    with patch("builtins.__import__", return_value=type("MockNumpy", (), {"__version__": "1.30.0"})):
        constraints.main()

    mock_print.assert_any_call("System numpy version: 1.30.0")
    mock_print.assert_any_call("Constraint added for numpy version: 1.30.0")
    mock_file().write.assert_called_once_with("numpy==1.30.0\n")

