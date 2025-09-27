"""Tests for morphic.structs module."""

from unittest.mock import Mock, patch

import pytest

from morphic.structs import (
    all_are_false,
    all_are_none,
    all_are_not_none,
    all_are_true,
    any_are_none,
    any_are_not_none,
    as_list,
    as_set,
    as_tuple,
    default,
    is_empty_list,
    is_empty_list_like,
    is_list_like,
    is_list_or_set_like,
    is_not_empty_list,
    is_not_empty_list_like,
    is_null,
    is_scalar,
    is_set_like,
    keep_values,
    multiple_are_none,
    multiple_are_not_none,
    none_count,
    not_impl,
    not_none_count,
    only_item,
    only_key,
    only_value,
    remove_nulls,
    remove_values,
    set_intersection,
    set_union,
)


class TestIsScalar:
    """Tests for is_scalar function."""

    def test_pandas_method_with_pandas_available(self):
        """Test pandas method when pandas is available."""
        with patch("morphic.structs.optional_dependency") as mock_dep:
            mock_dep.return_value.__enter__ = Mock(return_value=None)
            mock_dep.return_value.__exit__ = Mock(return_value=None)

            with patch("pandas.api.types.is_scalar", return_value=True) as mock_pd_scalar:
                result = is_scalar(42, method="pandas")
                assert result is True
                mock_pd_scalar.assert_called_once_with(42)

    def test_pandas_method_fallback(self):
        """Test pandas method fallback when pandas not available."""
        # Test basic Python scalars
        assert is_scalar(42, method="pandas") is True
        assert is_scalar(3.14, method="pandas") is True
        assert is_scalar("hello", method="pandas") is True
        assert is_scalar(True, method="pandas") is True
        assert is_scalar(None, method="pandas") is True
        assert is_scalar(b"bytes", method="pandas") is True
        assert is_scalar(1 + 2j, method="pandas") is True

        # Test non-scalars
        assert is_scalar([1, 2, 3], method="pandas") is False
        assert is_scalar({"a": 1}, method="pandas") is False
        assert is_scalar({1, 2, 3}, method="pandas") is False

    def test_numpy_method_with_numpy_available(self):
        """Test numpy method when numpy is available."""
        with patch("morphic.structs.optional_dependency") as mock_dep:
            mock_dep.return_value.__enter__ = Mock(return_value=None)
            mock_dep.return_value.__exit__ = Mock(return_value=None)

            with patch("numpy.isscalar", return_value=True) as mock_np_scalar:
                result = is_scalar(42, method="numpy")
                assert result is True
                mock_np_scalar.assert_called_once_with(42)

    def test_numpy_method_fallback(self):
        """Test numpy method fallback when numpy not available."""
        # Test basic Python scalars
        assert is_scalar(42, method="numpy") is True
        assert is_scalar(3.14, method="numpy") is True
        assert is_scalar("hello", method="numpy") is True
        assert is_scalar(True, method="numpy") is True
        assert is_scalar(None, method="numpy") is True

        # Test non-scalars
        assert is_scalar([1, 2, 3], method="numpy") is False
        assert is_scalar({"a": 1}, method="numpy") is False

    def test_invalid_method(self):
        """Test invalid method raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match='Unsupported method: "invalid"'):
            is_scalar(42, method="invalid")


class TestIsNull:
    """Tests for is_null function."""

    def test_scalar_with_pandas_available(self):
        """Test is_null with scalars when pandas is available."""
        with patch("morphic.structs.optional_dependency") as mock_dep:
            mock_dep.return_value.__enter__ = Mock(return_value=None)
            mock_dep.return_value.__exit__ = Mock(return_value=None)

            with patch("pandas.isnull", return_value=True) as mock_pd_isnull:
                result = is_null(None)
                assert result is True
                mock_pd_isnull.assert_called_once_with(None)

    def test_scalar_fallback(self):
        """Test is_null fallback for scalars."""
        assert is_null(None) is True
        assert is_null(42) is False
        assert is_null("") is False
        assert is_null(0) is False

    def test_non_scalar(self):
        """Test is_null with non-scalars."""
        assert is_null([]) is False
        assert is_null([None]) is False
        assert is_null({}) is False
        assert is_null(set()) is False

        # None is always null regardless of scalar status
        assert is_null(None) is True


class TestDefault:
    """Tests for default function."""

    def test_first_non_null(self):
        """Test returns first non-null value."""
        assert default(None, None, 42, 10) == 42

    def test_all_null(self):
        """Test returns None when all values are null."""
        assert default(None, None, None) is None

    def test_empty_args(self):
        """Test with no arguments."""
        assert default() is None

    def test_first_is_non_null(self):
        """Test when first argument is non-null."""
        assert default(42, None, 10) == 42

    def test_with_falsy_values(self):
        """Test with falsy but non-null values."""
        assert default(None, 0, 42) == 0
        assert default(None, "", 42) == ""
        assert default(None, [], 42) == []
        assert default(None, False, 42) is False

    def test_complex_data_types(self):
        """Test with complex data types."""
        obj = {"key": "value"}
        assert default(None, None, obj) == obj

        lst = [1, 2, 3]
        assert default(None, None, lst) == lst


class TestNoneUtilities:
    """Tests for None checking utilities."""

    def test_any_are_none(self):
        """Test any_are_none function."""
        assert any_are_none(None) is True
        assert any_are_none(None, 1, 2) is True
        assert any_are_none(1, None, 2) is True
        assert any_are_none(1, 2, None) is True
        assert any_are_none(1, 2, 3) is False
        assert any_are_none() is False

    def test_all_are_not_none(self):
        """Test all_are_not_none function."""
        assert all_are_not_none(1, 2, 3) is True
        assert all_are_not_none(1) is True
        assert all_are_not_none() is True
        assert all_are_not_none(None, 1, 2) is False
        assert all_are_not_none(1, None, 2) is False
        assert all_are_not_none(None) is False

    def test_all_are_none(self):
        """Test all_are_none function."""
        assert all_are_none(None, None, None) is True
        assert all_are_none(None) is True
        assert all_are_none() is True
        assert all_are_none(None, None, 1) is False
        assert all_are_none(1, None, None) is False
        assert all_are_none(1, 2, 3) is False

    def test_any_are_not_none(self):
        """Test any_are_not_none function."""
        assert any_are_not_none(1, 2, 3) is True
        assert any_are_not_none(None, None, 1) is True
        assert any_are_not_none(1, None, None) is True
        assert any_are_not_none(None, None, None) is False
        assert any_are_not_none(None) is False
        assert any_are_not_none() is False

    def test_none_count(self):
        """Test none_count function."""
        assert none_count() == 0
        assert none_count(None) == 1
        assert none_count(1, 2, 3) == 0
        assert none_count(None, 1, None) == 2
        assert none_count(None, None, None) == 3

    def test_not_none_count(self):
        """Test not_none_count function."""
        assert not_none_count() == 0
        assert not_none_count(None) == 0
        assert not_none_count(1, 2, 3) == 3
        assert not_none_count(None, 1, None) == 1
        assert not_none_count(1, None, 2) == 2

    def test_multiple_are_none(self):
        """Test multiple_are_none function."""
        assert multiple_are_none(None, None) is True
        assert multiple_are_none(None, None, None) is True
        assert multiple_are_none(None, 1, None) is True
        assert multiple_are_none(None, 1, 2) is False
        assert multiple_are_none(1, 2, 3) is False
        assert multiple_are_none(None) is False
        assert multiple_are_none() is False

    def test_multiple_are_not_none(self):
        """Test multiple_are_not_none function."""
        assert multiple_are_not_none(1, 2) is True
        assert multiple_are_not_none(1, 2, 3) is True
        assert multiple_are_not_none(1, None, 2) is True
        assert multiple_are_not_none(1, None, None) is False
        assert multiple_are_not_none(None, None, None) is False
        assert multiple_are_not_none(1) is False
        assert multiple_are_not_none() is False


class TestBooleanUtilities:
    """Tests for boolean checking utilities."""

    def test_all_are_true(self):
        """Test all_are_true function."""
        assert all_are_true(True, True, True) is True
        assert all_are_true(True) is True
        assert all_are_true() is True
        assert all_are_true(True, False, True) is False
        assert all_are_true(False, False, False) is False

        # Test with truthy/falsy values
        assert all_are_true(1, "hello", [1]) is True
        assert all_are_true(1, "", [1]) is False
        assert all_are_true(0, 1, 2) is False

    def test_all_are_false(self):
        """Test all_are_false function."""
        assert all_are_false(False, False, False) is True
        assert all_are_false(False) is True
        assert all_are_false() is True
        assert all_are_false(False, True, False) is False
        assert all_are_false(True, True, True) is False

        # Test with truthy/falsy values
        assert all_are_false(0, "", []) is True
        assert all_are_false(0, "", 1) is False
        assert all_are_false(1, 2, 3) is False


class TestNotImpl:
    """Tests for not_impl function."""

    def test_basic_not_implemented(self):
        """Test basic NotImplementedError generation."""
        result = not_impl("param", "value")
        assert isinstance(result, NotImplementedError)
        assert "param" in str(result)
        assert "value" in str(result)

    def test_with_supported_values(self):
        """Test NotImplementedError with supported values list."""
        supported = ["a", "b", "c"]
        result = not_impl("mode", "d", supported=supported)
        assert isinstance(result, NotImplementedError)
        assert "mode" in str(result)
        assert str(supported) in str(result)

    def test_with_long_param_value(self):
        """Test with very long parameter value."""
        long_value = "x" * 150
        result = not_impl("param", long_value)
        error_msg = str(result)
        assert "param" in error_msg
        # Should include newline due to length
        assert "\n" in error_msg

    def test_invalid_param_name(self):
        """Test with non-string parameter name."""
        with pytest.raises(ValueError, match="First value `param_name` must be a string"):
            not_impl(123, "value")

    def test_different_supported_types(self):
        """Test with different types for supported parameter."""
        # Test with set
        result = not_impl("param", "value", supported={1, 2, 3})
        assert isinstance(result, NotImplementedError)

        # Test with tuple
        result = not_impl("param", "value", supported=(1, 2, 3))
        assert isinstance(result, NotImplementedError)

        # Test with single value
        result = not_impl("param", "value", supported="single")
        assert isinstance(result, NotImplementedError)


class TestCollectionConversion:
    """Tests for collection conversion utilities."""

    def test_as_list(self):
        """Test as_list function."""
        assert as_list([1, 2, 3]) == [1, 2, 3]
        assert as_list((1, 2, 3)) == [1, 2, 3]
        assert as_list({1, 2, 3}) == [1, 2, 3]
        assert as_list(42) == [42]
        assert as_list("hello") == ["hello"]
        assert as_list(None) == [None]

    def test_as_tuple(self):
        """Test as_tuple function."""
        assert as_tuple([1, 2, 3]) == (1, 2, 3)
        assert as_tuple((1, 2, 3)) == (1, 2, 3)
        assert as_tuple({1, 2, 3}) == (1, 2, 3)
        assert as_tuple(42) == (42,)
        assert as_tuple("hello") == ("hello",)
        assert as_tuple(None) == (None,)

    def test_as_set(self):
        """Test as_set function."""
        assert as_set([1, 2, 3]) == {1, 2, 3}
        assert as_set((1, 2, 3)) == {1, 2, 3}
        assert as_set({1, 2, 3}) == {1, 2, 3}
        assert as_set(42) == {42}
        assert as_set("hello") == {"hello"}
        assert as_set(None) == {None}

        # Test with duplicates
        assert as_set([1, 1, 2, 2, 3]) == {1, 2, 3}


class TestTypeChecking:
    """Tests for type checking utilities."""

    def test_is_list_like(self):
        """Test is_list_like function."""
        assert is_list_like([1, 2, 3]) is True
        assert is_list_like((1, 2, 3)) is True
        assert is_list_like({1, 2, 3}) is False
        assert is_list_like("string") is False
        assert is_list_like(42) is False

    def test_is_set_like(self):
        """Test is_set_like function."""
        assert is_set_like({1, 2, 3}) is True
        assert is_set_like(frozenset([1, 2, 3])) is True
        assert is_set_like([1, 2, 3]) is False
        assert is_set_like((1, 2, 3)) is False
        assert is_set_like("string") is False

    def test_is_list_or_set_like(self):
        """Test is_list_or_set_like function."""
        assert is_list_or_set_like([1, 2, 3]) is True
        assert is_list_or_set_like((1, 2, 3)) is True
        assert is_list_or_set_like({1, 2, 3}) is True
        assert is_list_or_set_like(frozenset([1, 2, 3])) is True
        assert is_list_or_set_like("string") is False
        assert is_list_or_set_like(42) is False

    def test_is_not_empty_list_like(self):
        """Test is_not_empty_list_like function."""
        assert is_not_empty_list_like([1, 2, 3]) is True
        assert is_not_empty_list_like((1, 2, 3)) is True
        assert is_not_empty_list_like([]) is False
        assert is_not_empty_list_like(()) is False
        assert is_not_empty_list_like({1, 2, 3}) is False  # Sets are not list-like

    def test_is_empty_list_like(self):
        """Test is_empty_list_like function."""
        assert is_empty_list_like([]) is True
        assert is_empty_list_like(()) is True
        assert is_empty_list_like([1, 2, 3]) is False
        assert is_empty_list_like((1, 2, 3)) is False
        assert is_empty_list_like({}) is False  # Sets are not list-like

    def test_is_not_empty_list(self):
        """Test is_not_empty_list function."""
        assert is_not_empty_list([1, 2, 3]) is True
        assert is_not_empty_list([]) is False
        assert is_not_empty_list((1, 2, 3)) is False  # Tuple is not a list
        assert is_not_empty_list("string") is False

    def test_is_empty_list(self):
        """Test is_empty_list function."""
        assert is_empty_list([]) is True
        assert is_empty_list([1, 2, 3]) is False
        assert is_empty_list(()) is False  # Tuple is not a list
        assert is_empty_list("string") is False


class TestSetOperations:
    """Tests for set operation utilities."""

    def test_set_union(self):
        """Test set_union function."""
        result = set_union({1, 2}, {2, 3}, [3, 4])
        assert result == {1, 2, 3, 4}

        # Test with empty sets
        result = set_union(set(), {1, 2})
        assert result == {1, 2}

        # Test with single set
        result = set_union({1, 2, 3})
        assert result == {1, 2, 3}

        # Test with no arguments
        result = set_union()
        assert result == set()

    def test_set_intersection(self):
        """Test set_intersection function."""
        result = set_intersection({1, 2, 3}, {2, 3, 4}, [2, 4, 5])
        assert result == {2}

        # Test with no common elements
        result = set_intersection({1, 2}, {3, 4})
        assert result == set()

        # Test with single set
        result = set_intersection({1, 2, 3})
        assert result == {1, 2, 3}

        # Test with no arguments
        result = set_intersection()
        assert result == set()

        # Test with lists and tuples
        result = set_intersection([1, 2, 3], (2, 3, 4))
        assert result == {2, 3}


class TestCollectionFiltering:
    """Tests for collection filtering utilities."""

    def test_keep_values_list(self):
        """Test keep_values with lists."""
        result = keep_values([1, 2, 3, 4, 5], [2, 4])
        assert result == [2, 4]

        result = keep_values([1, 2, 3, 2, 4], 2)
        assert result == [2, 2]

    def test_keep_values_tuple(self):
        """Test keep_values with tuples."""
        result = keep_values((1, 2, 3, 4, 5), [2, 4])
        assert result == (2, 4)

    def test_keep_values_set(self):
        """Test keep_values with sets."""
        result = keep_values({1, 2, 3, 4, 5}, [2, 4])
        assert result == {2, 4}

    def test_keep_values_dict(self):
        """Test keep_values with dictionaries."""
        result = keep_values({"a": 1, "b": 2, "c": 3}, [1, 3])
        assert result == {"a": 1, "c": 3}

    def test_keep_values_unsupported_type(self):
        """Test keep_values with unsupported type."""
        with pytest.raises(NotImplementedError):
            keep_values("string", ["s"])

    def test_remove_values_list(self):
        """Test remove_values with lists."""
        result = remove_values([1, 2, 3, 4, 5], [2, 4])
        assert result == [1, 3, 5]

    def test_remove_values_tuple(self):
        """Test remove_values with tuples."""
        result = remove_values((1, 2, 3, 4, 5), [2, 4])
        assert result == (1, 3, 5)

    def test_remove_values_set(self):
        """Test remove_values with sets."""
        result = remove_values({1, 2, 3, 4, 5}, [2, 4])
        assert result == {1, 3, 5}

    def test_remove_values_dict(self):
        """Test remove_values with dictionaries."""
        result = remove_values({"a": 1, "b": 2, "c": 3}, [1, 3])
        assert result == {"b": 2}

    def test_remove_nulls_list(self):
        """Test remove_nulls with lists."""
        result = remove_nulls([1, None, 2, None, 3])
        assert result == [1, 2, 3]

    def test_remove_nulls_tuple(self):
        """Test remove_nulls with tuples."""
        result = remove_nulls((1, None, 2, None, 3))
        assert result == (1, 2, 3)

    def test_remove_nulls_set(self):
        """Test remove_nulls with sets."""
        result = remove_nulls({1, None, 2, 3})
        assert result == {1, 2, 3}

    def test_remove_nulls_dict(self):
        """Test remove_nulls with dictionaries."""
        result = remove_nulls({"a": 1, "b": None, "c": 3})
        assert result == {"a": 1, "c": 3}


class TestSingleItemExtraction:
    """Tests for single item extraction utilities."""

    def test_only_item_single_item_list(self):
        """Test only_item with single-item list."""
        assert only_item([42]) == 42

    def test_only_item_single_item_tuple(self):
        """Test only_item with single-item tuple."""
        assert only_item((42,)) == 42

    def test_only_item_single_item_set(self):
        """Test only_item with single-item set."""
        assert only_item({42}) == 42

    def test_only_item_single_item_dict(self):
        """Test only_item with single-item dict."""
        result = only_item({"key": "value"})
        assert result == ("key", "value")

    def test_only_item_multiple_items_raise_error(self):
        """Test only_item with multiple items (should raise error)."""
        with pytest.raises(ValueError, match="Expected input .* to have only one item"):
            only_item([1, 2, 3])

    def test_only_item_multiple_items_no_raise(self):
        """Test only_item with multiple items (no error)."""
        result = only_item([1, 2, 3], raise_error=False)
        assert result == [1, 2, 3]

    def test_only_item_empty_collection(self):
        """Test only_item with empty collection."""
        with pytest.raises(ValueError, match="Expected input .* to have only one item"):
            only_item([])

    def test_only_item_non_collection(self):
        """Test only_item with non-collection."""
        assert only_item(42) == 42
        assert only_item("string") == "string"

    def test_only_key_single_key(self):
        """Test only_key with single key."""
        assert only_key({"key": "value"}) == "key"

    def test_only_key_multiple_keys(self):
        """Test only_key with multiple keys."""
        with pytest.raises(ValueError, match="Expected input .* to have only one item"):
            only_key({"key1": "value1", "key2": "value2"})

    def test_only_key_non_dict(self):
        """Test only_key with non-dict."""
        assert only_key("string") == "string"

    def test_only_value_single_value(self):
        """Test only_value with single value."""
        assert only_value({"key": "value"}) == "value"

    def test_only_value_multiple_values(self):
        """Test only_value with multiple values."""
        with pytest.raises(ValueError, match="Expected input .* to have only one item"):
            only_value({"key1": "value1", "key2": "value2"})

    def test_only_value_non_dict(self):
        """Test only_value with non-dict."""
        assert only_value("string") == "string"


class TestIntegrationScenarios:
    """Integration tests combining multiple utilities."""

    def test_data_processing_pipeline(self):
        """Test a data processing pipeline using multiple utilities."""
        # Start with raw data
        raw_data = [1, None, 2, None, 3, 4, 5]

        # Remove nulls
        clean_data = remove_nulls(raw_data)
        assert clean_data == [1, 2, 3, 4, 5]

        # Keep only certain values
        filtered_data = keep_values(clean_data, [2, 4])
        assert filtered_data == [2, 4]

        # Convert to set and back
        as_set_data = as_set(filtered_data)
        as_tuple_data = as_tuple(as_set_data)
        assert as_tuple_data == (2, 4)

        # Extract single item if possible
        if len(as_tuple_data) == 1:
            single_item = only_item(as_tuple_data)
        else:
            single_item = as_tuple_data

        assert single_item == (2, 4)

    def test_configuration_validation(self):
        """Test configuration validation scenario."""
        config = {
            "database_url": None,
            "redis_url": "redis://localhost",
            "debug": True,
            "workers": None,
        }

        # Remove null configurations
        valid_config = remove_nulls(config)
        assert "database_url" not in valid_config
        assert "workers" not in valid_config
        assert valid_config["redis_url"] == "redis://localhost"

        # Check if all required settings are present
        required_settings = ["redis_url", "debug"]
        available_settings = set(valid_config.keys())
        has_all_required = set_intersection(available_settings, required_settings) == set(required_settings)
        assert has_all_required is True

    def test_feature_flag_management(self):
        """Test feature flag management scenario."""
        features = {
            "feature_a": True,
            "feature_b": False,
            "feature_c": None,  # Not configured
            "feature_d": True,
        }

        # Get enabled features (remove None and False)
        configured_features = remove_nulls(features)  # Remove None values
        enabled_features = keep_values(configured_features, True)  # Keep only True values
        feature_names = list(enabled_features.keys())

        assert set(feature_names) == {"feature_a", "feature_d"}

        # Check if any features are enabled
        has_enabled_features = any_are_not_none(*enabled_features.values())
        assert has_enabled_features is True

        # Check if all features are enabled
        all_enabled = all_are_true(*enabled_features.values())
        assert all_enabled is True

    def test_error_handling_scenario(self):
        """Test error handling scenario using not_impl."""
        supported_modes = ["read", "write", "append"]

        def process_file(mode: str):
            if mode not in supported_modes:
                raise not_impl("mode", mode, supported=supported_modes)
            return f"Processing in {mode} mode"

        # Valid mode
        result = process_file("read")
        assert result == "Processing in read mode"

        # Invalid mode
        with pytest.raises(NotImplementedError) as exc_info:
            process_file("delete")

        error_msg = str(exc_info.value)
        assert "mode" in error_msg
        assert "delete" in error_msg
        assert str(supported_modes) in error_msg

    def test_data_structure_normalization(self):
        """Test normalizing different data structures to a common format."""
        # Various input formats
        inputs = [
            [1, 2, 3],  # List
            (4, 5, 6),  # Tuple
            {7, 8, 9},  # Set
            10,  # Single item
        ]

        normalized = []
        for inp in inputs:
            # Normalize everything to a sorted list
            if is_list_or_set_like(inp):
                normalized.extend(as_list(inp))
            else:
                normalized.extend(as_list(inp))

        # Sort to make comparison easier (since sets don't preserve order)
        normalized.sort()
        assert normalized == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        # Get unique values
        unique_values = as_set(normalized)
        assert len(unique_values) == 10

        # Check if we have multiple non-null values
        assert multiple_are_not_none(*normalized) is True
