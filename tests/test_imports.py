"""Tests for morphic.imports module."""

from unittest.mock import patch

import pytest

from morphic.imports import optional_dependency


class TestOptionalDependency:
    """Tests for optional_dependency context manager."""

    def test_successful_import_ignore_mode(self):
        """Test successful import with ignore mode."""
        with optional_dependency("sys", error="ignore") as ctx:
            import sys

            result = sys.version

        assert result is not None
        assert ctx is None

    def test_successful_import_warn_mode(self):
        """Test successful import with warn mode."""
        with optional_dependency("sys", error="warn") as ctx:
            import sys

            result = sys.version

        assert result is not None
        assert ctx is None

    def test_successful_import_raise_mode(self):
        """Test successful import with raise mode."""
        with optional_dependency("sys", error="raise") as ctx:
            import sys

            result = sys.version

        assert result is not None
        assert ctx is None

    def test_missing_dependency_ignore_mode(self):
        """Test missing dependency with ignore mode (should pass silently)."""
        executed = False
        with optional_dependency("nonexistent_module_12345", error="ignore"):
            import nonexistent_module_12345
            executed = True  # This line should not execute

        assert executed is False

    @patch("builtins.print")
    def test_missing_dependency_warn_mode(self, mock_print):
        """Test missing dependency with warn mode (should print warning)."""
        executed = False
        with optional_dependency("nonexistent_module_12345", error="warn"):
            import nonexistent_module_12345
            executed = True  # This line should not execute

        assert executed is False
        mock_print.assert_called_once()
        args, _ = mock_print.call_args
        assert "Warning:" in args[0]
        assert "nonexistent_module_12345" in args[0]

    def test_missing_dependency_raise_mode(self):
        """Test missing dependency with raise mode (should raise ImportError)."""
        with pytest.raises((ImportError, ModuleNotFoundError)):
            with optional_dependency("nonexistent_module_12345", error="raise"):
                import nonexistent_module_12345
                pass

    def test_multiple_dependencies_success(self):
        """Test multiple dependencies that all exist."""
        with optional_dependency("sys", "os", error="ignore") as ctx:
            import os
            import sys

            result = sys.version + os.name

        assert result is not None
        assert ctx is None

    def test_multiple_dependencies_one_missing_ignore(self):
        """Test multiple dependencies where one is missing, ignore mode."""
        executed = False
        with optional_dependency("sys", "nonexistent_module_12345", error="ignore"):
            import sys

            import nonexistent_module_12345
            executed = True

        assert executed is False

    @patch("builtins.print")
    def test_multiple_dependencies_one_missing_warn(self, mock_print):
        """Test multiple dependencies where one is missing, warn mode."""
        executed = False
        with optional_dependency("sys", "nonexistent_module_12345", error="warn"):
            import sys
            print("sys imported")
            import nonexistent_module_12345
            executed = True

        assert executed is False
        mock_print.assert_called_once()

    def test_multiple_dependencies_one_missing_raise(self):
        """Test multiple dependencies where one is missing, raise mode."""
        with pytest.raises((ImportError, ModuleNotFoundError)):
            with optional_dependency("sys", "nonexistent_module_12345", error="raise"):
                import sys

                import nonexistent_module_12345
                pass

    def test_non_optional_dependency_missing_should_raise(self):
        """Test that missing non-optional dependencies still raise errors."""
        with pytest.raises((ImportError, ModuleNotFoundError)):
            with optional_dependency("nonexistent_optional", error="ignore"):
                # This doesn't exist and isn't in names, it should be raised:
                import nonexistent_should_raise

    def test_warn_every_time_false_default(self):
        """Test that warnings are not repeated by default."""
        with patch("builtins.print") as mock_print:
            # First warning
            __WARNED_OPTIONAL_MODULES = set()
            with optional_dependency(
                "nonexistent_module_12345", 
                error="warn", 
                __WARNED_OPTIONAL_MODULES=__WARNED_OPTIONAL_MODULES,
            ):
                import nonexistent_module_12345

            # Second attempt - should not warn again
            with optional_dependency(
                "nonexistent_module_12345", 
                error="warn", 
                __WARNED_OPTIONAL_MODULES=__WARNED_OPTIONAL_MODULES,
            ):
                import nonexistent_module_12345

        # Should only be called once
        assert mock_print.call_count == 1

    def test_warn_every_time_true(self):
        """Test that warnings are repeated when warn_every_time=True."""
        with patch("builtins.print") as mock_print:
            # First warning
            with optional_dependency("nonexistent_module_54321", error="warn", warn_every_time=True):
                import nonexistent_module_54321
                pass

            # Second attempt - should warn again
            with optional_dependency("nonexistent_module_54321", error="warn", warn_every_time=True):
                import nonexistent_module_54321
                pass

        # Should be called twice
        assert mock_print.call_count == 2

    def test_invalid_error_parameter(self):
        """Test that invalid error parameter raises assertion error."""
        with pytest.raises(AssertionError):
            with optional_dependency("sys", error="invalid"):
                import sys
                pass

    def test_context_manager_returns_none(self):
        """Test that context manager yields None."""
        with optional_dependency("sys", error="ignore") as ctx:
            assert ctx is None

    def test_nested_optional_dependencies(self):
        """Test nested optional_dependency contexts."""
        result = None
        with optional_dependency("sys", error="ignore"):
            with optional_dependency("os", error="ignore"):
                import os
                import sys
                result = "both imported"

        assert result == "both imported"

    def test_code_after_context_always_executes(self):
        """Test that code after the context manager always executes."""
        executed_after = False

        # Case 1: Successful import
        with optional_dependency("sys", error="ignore"):
            import sys
            pass

        executed_after = True
        assert executed_after is True

        # Case 2: Failed import
        executed_after = False
        with optional_dependency("nonexistent_module_12345", error="ignore"):
            import nonexistent_module_12345
            pass

        executed_after = True
        assert executed_after is True

    @patch("builtins.print")
    def test_warning_message_format(self, mock_print):
        """Test the format of warning messages."""
        with optional_dependency("test_missing_module", error="warn"):
            import test_missing_module
            pass

        mock_print.assert_called_once()
        args, _ = mock_print.call_args
        warning_msg = args[0]

        assert "Warning:" in warning_msg
        assert "Missing optional dependency" in warning_msg
        assert "test_missing_module" in warning_msg
        assert "pip or conda" in warning_msg

    def test_private_warned_modules_parameter(self):
        """Test that the private __WARNED_OPTIONAL_MODULES parameter works."""
        # This is testing implementation details, but it's part of the interface
        warned_set = set()

        with patch("builtins.print") as mock_print:
            with optional_dependency("test_module_1", error="warn", __WARNED_OPTIONAL_MODULES=warned_set):
                import test_module_1
                pass

            # Should warn once
            assert mock_print.call_count == 1
            assert "test_module_1" in warned_set

            # Should not warn again with same set
            with optional_dependency("test_module_1", error="warn", __WARNED_OPTIONAL_MODULES=warned_set):
                import test_module_1
                pass

            # Still should be called only once
            assert mock_print.call_count == 1

    def test_original_error_preserved_for_non_optional_deps(self):
        """Test that the original error is preserved when it's not an optional dependency."""
        original_error = ImportError("specific_error_message")

        with patch("builtins.__import__", side_effect=original_error):
            with pytest.raises(ImportError, match="specific_error_message"):
                with optional_dependency("other_module", error="ignore"):
                    import other_module
                    pass  # Not in the optional list


class TestOptionalDependencyUsageScenarios:
    """Test real-world usage scenarios for optional_dependency."""

    def test_pandas_sklearn_scenario_success(self):
        """Test a scenario similar to the docstring example with existing modules."""
        with optional_dependency("sys", "os", error="ignore"):
            import os
            import sys

            class TestCalculator:
                def __init__(self):
                    self.sys_version = sys.version
                    self.os_name = os.name

                def get_info(self):
                    return f"{self.sys_version[:10]}_{self.os_name}"

            calc = TestCalculator()
            result = calc.get_info()

        assert result is not None
        assert "_" in result

    def test_graceful_degradation_pattern(self):
        """Test graceful degradation when optional dependencies are missing."""
        features_available = []

        # Try to import an existing module
        with optional_dependency("json", error="ignore"):
            import json
            features_available.append("json_support")

        # Try to import a non-existing module
        with optional_dependency("nonexistent_advanced_feature", error="ignore"):
            import nonexistent_advanced_feature
            features_available.append("advanced_feature")

        # The first feature should be available, the second should not
        assert "json_support" in features_available
        assert "advanced_feature" not in features_available
        assert len(features_available) == 1

    def test_conditional_class_definition(self):
        """Test conditionally defining classes based on optional dependencies."""
        defined_classes = []

        # This should work
        with optional_dependency("collections", error="ignore"):
            import collections
            from collections import defaultdict

            class CollectionUtils:
                @staticmethod
                def make_default_dict():
                    return defaultdict(list)

            defined_classes.append("CollectionUtils")

        # This should not work
        with optional_dependency("nonexistent_ml_lib", error="ignore"):
            import nonexistent_ml_lib
            from nonexistent_ml_lib import SomeMLModel

            class MLUtils:
                @staticmethod
                def create_model():
                    return SomeMLModel()

            defined_classes.append("MLUtils")

        assert "CollectionUtils" in defined_classes
        assert "MLUtils" not in defined_classes

        # Verify the class was actually defined and works
        if "CollectionUtils" in defined_classes:
            utils = CollectionUtils()
            dd = utils.make_default_dict()
            assert isinstance(dd, defaultdict)

    @patch("builtins.print")
    def test_development_vs_production_behavior(self, mock_print):
        """Test different behaviors for development vs production."""
        # Development mode: warn about missing dependencies
        with optional_dependency("dev_only_dependency", error="warn"):
            import dev_only_dependency
            pass

        # Should have printed a warning
        assert mock_print.call_count == 1

        # Production mode: silently ignore missing dependencies
        mock_print.reset_mock()
        with optional_dependency("optional_production_feature", error="ignore"):
            import optional_production_feature
            pass

        # Should not have printed anything
        assert mock_print.call_count == 0

    def test_feature_flags_pattern(self):
        """Test using optional dependencies as feature flags."""
        features = {
            "basic": True,  # Always available
            "advanced_math": False,
            "data_processing": False,
            "visualization": False,
        }

        # Try to enable features based on available dependencies
        with optional_dependency("math", error="ignore"):
            import math
            features["advanced_math"] = True

        with optional_dependency("json", error="ignore"):  # Use existing module
            import json
            features["data_processing"] = True

        with optional_dependency("nonexistent_viz_lib", error="ignore"):
            import nonexistent_viz_lib
            features["visualization"] = True

        # Check which features are enabled
        assert features["basic"] is True
        assert features["advanced_math"] is True
        assert features["data_processing"] is True
        assert features["visualization"] is False
