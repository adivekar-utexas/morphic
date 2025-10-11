"""Tests for morphic.structs module."""

from unittest.mock import Mock, patch

import pytest

from morphic.structs import (
    AttrDict,
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
    map_collection,
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


class TestAttrDict:
    """Tests for AttrDict class."""

    def test_initialization_empty(self):
        """Test empty AttrDict initialization."""
        ad = AttrDict()
        assert len(ad) == 0
        assert ad.to_dict() == {}

    def test_initialization_with_dict(self):
        """Test AttrDict initialization with dictionary."""
        ad = AttrDict({"a": 1, "b": 2})
        assert len(ad) == 2
        assert ad["a"] == 1
        assert ad["b"] == 2

    def test_initialization_with_kwargs(self):
        """Test AttrDict initialization with keyword arguments."""
        ad = AttrDict(x=10, y=20)
        assert len(ad) == 2
        assert ad["x"] == 10
        assert ad["y"] == 20

    def test_initialization_mixed(self):
        """Test AttrDict initialization with both dict and kwargs."""
        ad = AttrDict({"a": 1}, b=2, c=3)
        assert len(ad) == 3
        assert ad["a"] == 1
        assert ad["b"] == 2
        assert ad["c"] == 3

    def test_initialization_with_none(self):
        """Test AttrDict initialization with None."""
        ad = AttrDict(None)
        assert len(ad) == 0
        assert ad.to_dict() == {}

    def test_attribute_read(self):
        """Test reading values via attribute access."""
        ad = AttrDict({"a": 1, "b": 2})
        assert ad.a == 1
        assert ad.b == 2

    def test_attribute_write(self):
        """Test writing values via attribute access."""
        ad = AttrDict()
        ad.a = 1
        ad.b = 2
        assert ad["a"] == 1
        assert ad["b"] == 2
        assert len(ad) == 2

    def test_item_read(self):
        """Test reading values via item access."""
        ad = AttrDict(x=10, y=20)
        assert ad["x"] == 10
        assert ad["y"] == 20

    def test_item_write(self):
        """Test writing values via item access."""
        ad = AttrDict()
        ad["a"] = 1
        ad["b"] = 2
        assert ad.a == 1
        assert ad.b == 2
        assert len(ad) == 2

    def test_bidirectional_access(self):
        """Test bidirectional access between attributes and items."""
        ad = AttrDict()

        # Set via attribute, read via item
        ad.attr_key = "attr_value"
        assert ad["attr_key"] == "attr_value"

        # Set via item, read via attribute
        ad["item_key"] = "item_value"
        assert ad.item_key == "item_value"

    def test_attribute_deletion(self):
        """Test deletion via attribute access."""
        ad = AttrDict({"a": 1, "b": 2})
        del ad.a
        assert "a" not in ad
        assert len(ad) == 1
        with pytest.raises(AttributeError):
            _ = ad.a

    def test_item_deletion(self):
        """Test deletion via item access."""
        ad = AttrDict({"a": 1, "b": 2})
        del ad["a"]
        assert "a" not in ad
        assert len(ad) == 1
        with pytest.raises(KeyError):
            _ = ad["a"]

    def test_delete_nonexistent_attribute(self):
        """Test deleting non-existent attribute raises AttributeError."""
        ad = AttrDict({"a": 1})
        with pytest.raises(AttributeError):
            del ad.nonexistent

    def test_delete_nonexistent_item(self):
        """Test deleting non-existent item raises KeyError."""
        ad = AttrDict({"a": 1})
        with pytest.raises(KeyError):
            del ad["nonexistent"]

    def test_getattr_nonexistent(self):
        """Test accessing non-existent attribute raises AttributeError."""
        ad = AttrDict({"a": 1})
        with pytest.raises(AttributeError):
            _ = ad.nonexistent

    def test_getitem_nonexistent(self):
        """Test accessing non-existent item raises KeyError."""
        ad = AttrDict({"a": 1})
        with pytest.raises(KeyError):
            _ = ad["nonexistent"]

    def test_private_attributes(self):
        """Test that private attributes (starting with _) are not accessible via dict operations."""
        ad = AttrDict({"a": 1})

        # Try to set a key starting with '_' via dict access
        ad["_private"] = "internal"

        # This key should be in the dictionary
        assert "_private" in ad
        assert ad["_private"] == "internal"

        # Can also access via attribute
        assert ad._private == "internal"

        # Both 'a' and '_private' should be in the dict
        assert len(ad) == 2

        # Note: Due to __slots__, we cannot add arbitrary private attributes
        # that aren't stored in the dict (e.g., ad._something = value will fail)

    def test_iteration(self):
        """Test iteration over AttrDict."""
        ad = AttrDict({"a": 1, "b": 2, "c": 3})
        keys = list(ad)
        assert set(keys) == {"a", "b", "c"}

    def test_keys_method(self):
        """Test keys() method."""
        ad = AttrDict({"a": 1, "b": 2})
        keys = list(ad.keys())
        assert set(keys) == {"a", "b"}

    def test_values_method(self):
        """Test values() method."""
        ad = AttrDict({"a": 1, "b": 2})
        values = list(ad.values())
        assert set(values) == {1, 2}

    def test_items_method(self):
        """Test items() method."""
        ad = AttrDict({"a": 1, "b": 2})
        items = list(ad.items())
        assert set(items) == {("a", 1), ("b", 2)}

    def test_len(self):
        """Test len() function."""
        ad = AttrDict()
        assert len(ad) == 0

        ad["a"] = 1
        assert len(ad) == 1

        ad.b = 2
        ad.c = 3
        assert len(ad) == 3

    def test_contains(self):
        """Test 'in' operator."""
        ad = AttrDict({"a": 1, "b": 2})
        assert "a" in ad
        assert "b" in ad
        assert "c" not in ad

    def test_get_method(self):
        """Test get() method with default values."""
        ad = AttrDict({"a": 1})
        assert ad.get("a") == 1
        assert ad.get("b") is None
        assert ad.get("b", "default") == "default"

    def test_update_method(self):
        """Test update() method."""
        ad = AttrDict({"a": 1})
        ad.update({"b": 2, "c": 3})
        assert len(ad) == 3
        assert ad.a == 1
        assert ad.b == 2
        assert ad.c == 3

    def test_update_with_kwargs(self):
        """Test update() method with keyword arguments."""
        ad = AttrDict({"a": 1})
        ad.update(b=2, c=3)
        assert len(ad) == 3
        assert ad["b"] == 2
        assert ad["c"] == 3

    def test_pop_method(self):
        """Test pop() method."""
        ad = AttrDict({"a": 1, "b": 2})
        value = ad.pop("a")
        assert value == 1
        assert "a" not in ad
        assert len(ad) == 1

    def test_pop_with_default(self):
        """Test pop() method with default value."""
        ad = AttrDict({"a": 1})
        value = ad.pop("nonexistent", "default")
        assert value == "default"
        assert len(ad) == 1

    def test_popitem_method(self):
        """Test popitem() method."""
        ad = AttrDict({"a": 1})
        key, value = ad.popitem()
        assert key == "a"
        assert value == 1
        assert len(ad) == 0

    def test_clear_method(self):
        """Test clear() method."""
        ad = AttrDict({"a": 1, "b": 2, "c": 3})
        ad.clear()
        assert len(ad) == 0
        assert ad.to_dict() == {}

    def test_setdefault_method(self):
        """Test setdefault() method."""
        ad = AttrDict({"a": 1})

        # Key exists
        value = ad.setdefault("a", 99)
        assert value == 1
        assert ad.a == 1

        # Key doesn't exist
        value = ad.setdefault("b", 2)
        assert value == 2
        assert ad.b == 2

    def test_to_dict(self):
        """Test to_dict() method returns a regular dictionary."""
        ad = AttrDict({"a": 1, "b": 2, "c": 3})
        d = ad.to_dict()
        assert isinstance(d, dict)
        assert not isinstance(d, AttrDict)
        assert d == {"a": 1, "b": 2, "c": 3}

    def test_to_dict_copy(self):
        """Test that to_dict() returns a copy, not a reference."""
        ad = AttrDict({"a": 1})
        d = ad.to_dict()
        d["b"] = 2
        assert "b" not in ad
        assert len(ad) == 1

    def test_repr(self):
        """Test __repr__ method."""
        ad = AttrDict({"a": 1, "b": 2})
        repr_str = repr(ad)
        assert "AttrDict" in repr_str
        assert "'a'" in repr_str or '"a"' in repr_str
        assert "1" in repr_str

    def test_equality(self):
        """Test equality comparison with dictionaries."""
        ad = AttrDict({"a": 1, "b": 2})
        assert ad == {"a": 1, "b": 2}
        assert ad != {"a": 1, "b": 3}
        assert ad != {"a": 1}

    def test_different_data_types(self):
        """Test storing different data types."""
        ad = AttrDict()
        ad.string_val = "hello"
        ad.int_val = 42
        ad.float_val = 3.14
        ad.list_val = [1, 2, 3]
        ad.dict_val = {"nested": "dict"}
        ad.none_val = None
        ad.bool_val = True

        assert ad.string_val == "hello"
        assert ad.int_val == 42
        assert ad.float_val == 3.14
        assert ad.list_val == [1, 2, 3]
        assert ad.dict_val == {"nested": "dict"}
        assert ad.none_val is None
        assert ad.bool_val is True

    def test_nested_attrdict(self):
        """Test nesting AttrDict objects."""
        inner = AttrDict({"x": 1, "y": 2})
        outer = AttrDict({"inner": inner, "z": 3})

        assert outer.inner.x == 1
        assert outer["inner"]["y"] == 2
        assert outer.z == 3

    def test_overwrite_existing_value(self):
        """Test overwriting existing values."""
        ad = AttrDict({"a": 1})
        ad.a = 2
        assert ad.a == 2
        assert ad["a"] == 2

        ad["a"] = 3
        assert ad.a == 3
        assert ad["a"] == 3

    def test_update_existing_value_with_update(self):
        """Test updating existing values with update() method."""
        ad = AttrDict({"a": 1, "b": 2})
        ad.update({"a": 10, "c": 3})
        assert ad.a == 10
        assert ad.b == 2
        assert ad.c == 3

    def test_copy_like_behavior(self):
        """Test creating a copy of AttrDict."""
        ad = AttrDict({"a": 1, "b": [1, 2, 3]})

        # Create a new AttrDict from the existing one
        copied = AttrDict(ad.to_dict())

        # Modify the original
        ad.a = 2
        ad.c = 3

        # Copy should not be affected for simple values
        assert copied.a == 1
        assert "c" not in copied

        # Note: Since we used to_dict(), nested mutable objects are shared
        # This is standard shallow copy behavior
        ad.b.append(4)
        assert copied.b == [1, 2, 3, 4]

    def test_boolean_context(self):
        """Test AttrDict in boolean context."""
        ad_empty = AttrDict()
        ad_filled = AttrDict({"a": 1})

        # Empty AttrDict should be falsy (standard dict behavior)
        assert not ad_empty
        assert bool(ad_empty) is False

        # Non-empty AttrDict should be truthy
        assert ad_filled
        assert bool(ad_filled) is True

    def test_special_key_names(self):
        """Test handling of special key names that could conflict with methods."""
        ad = AttrDict()

        # These should work as they don't start with '_'
        ad.keys_data = "data"
        ad.items_data = "items"
        ad.values_data = "values"

        # Accessing the method should still work
        assert callable(ad.keys)

        # Accessing the data should work via item access
        assert ad["keys_data"] == "data"

        # But attribute access will get the data, not the method
        # (because __getattr__ is only called when normal lookup fails)
        assert ad.keys_data == "data"

    def test_example_from_docstring(self):
        """Test the example provided in the user's query."""
        cfg = AttrDict({"a": 1})
        cfg.b = 2  # sets cfg['b'] = 2
        assert cfg.a == 1  # reads cfg['a']
        assert cfg["b"] == 2
        del cfg.b  # deletes key 'b'
        assert "b" not in cfg


class TestAttrDictUseCases:
    """Real-world use case tests for AttrDict."""

    def test_configuration_object(self):
        """Test using AttrDict as a configuration object."""
        config = AttrDict(
            {
                "database_url": "postgresql://localhost/db",
                "debug": True,
                "max_connections": 10,
            }
        )

        # Easy attribute access
        assert config.database_url == "postgresql://localhost/db"
        assert config.debug is True

        # Add new configuration
        config.cache_enabled = True
        assert config["cache_enabled"] is True

        # Update configuration
        config.max_connections = 20
        assert config["max_connections"] == 20

    def test_api_response_handling(self):
        """Test using AttrDict to handle API responses."""
        response = AttrDict(
            {
                "status": "success",
                "data": {
                    "user_id": 123,
                    "username": "john_doe",
                },
                "metadata": {
                    "timestamp": "2025-10-11T12:00:00Z",
                },
            }
        )

        assert response.status == "success"
        assert response["data"]["user_id"] == 123

        # Can still use dict methods
        assert "metadata" in response
        assert list(response.keys()) == ["status", "data", "metadata"]

    def test_builder_pattern(self):
        """Test using AttrDict in a builder-like pattern."""
        params = AttrDict()
        params.learning_rate = 0.01
        params.batch_size = 32
        params.epochs = 100
        params.optimizer = "adam"

        # Convert to dict for passing to functions
        params_dict = params.to_dict()
        assert params_dict == {
            "learning_rate": 0.01,
            "batch_size": 32,
            "epochs": 100,
            "optimizer": "adam",
        }

    def test_dynamic_attribute_creation(self):
        """Test dynamically creating attributes based on runtime data."""
        data = AttrDict()

        # Simulate dynamic attribute creation
        for i in range(5):
            key = f"item_{i}"
            data[key] = i * 10

        # Access dynamically created attributes
        assert data.item_0 == 0
        assert data.item_4 == 40
        assert len(data) == 5

    def test_namespace_like_usage(self):
        """Test using AttrDict as a namespace."""
        ns = AttrDict()
        ns.PI = 3.14159
        ns.E = 2.71828
        ns.PHI = 1.61803

        # Clean attribute access like a namespace
        circle_area = ns.PI * (5**2)
        assert abs(circle_area - 78.53975) < 0.00001

    def test_hierarchical_configuration(self):
        """Test hierarchical configuration with nested AttrDicts."""
        config = AttrDict(
            {
                "server": AttrDict(
                    {
                        "host": "localhost",
                        "port": 8080,
                    }
                ),
                "database": AttrDict(
                    {
                        "host": "db.example.com",
                        "port": 5432,
                        "name": "myapp",
                    }
                ),
            }
        )

        # Easy nested access
        assert config.server.host == "localhost"
        assert config.database.port == 5432

        # Add new nested config
        config.cache = AttrDict({"enabled": True, "ttl": 3600})
        assert config.cache.ttl == 3600


class TestMapCollection:
    """Tests for map_collection function."""

    def test_scalar_values(self):
        """Test map_collection with scalar values."""
        # Integer
        assert map_collection(5, lambda x: x * 2) == 10

        # String
        assert map_collection("hello", lambda x: x.upper()) == "HELLO"

        # Float
        assert map_collection(3.14, lambda x: x * 2) == 6.28

        # Boolean
        assert map_collection(True, lambda x: not x) is False

        # None
        assert map_collection(None, lambda x: x) is None

    def test_list_transformation(self):
        """Test map_collection with lists."""
        # Simple list
        assert map_collection([1, 2, 3], lambda x: x * 2) == [2, 4, 6]

        # Empty list
        assert map_collection([], lambda x: x * 2) == []

        # List with mixed types
        result = map_collection([1, "hello", 3.14], lambda x: str(x))
        assert result == ["1", "hello", "3.14"]

    def test_nested_list_transformation(self):
        """Test map_collection with nested lists."""
        # Nested lists
        assert map_collection([[1, 2], [3, 4]], lambda x: x * 2, recurse=True) == [[2, 4], [6, 8]]

        # Deeply nested lists
        assert map_collection([[[1, 2]], [[3]]], lambda x: x * 2, recurse=True) == [[[2, 4]], [[6]]]

        # Mixed nesting levels
        result = map_collection([1, [2, 3], [4, [5, 6]]], lambda x: x * 2, recurse=True)
        assert result == [2, [4, 6], [8, [10, 12]]]

    def test_tuple_transformation(self):
        """Test map_collection with tuples."""
        # Simple tuple
        result = map_collection((1, 2, 3), lambda x: x * 2, recurse=True)
        assert isinstance(result, tuple)
        assert result == (2, 4, 6)

        # Empty tuple
        result = map_collection((), lambda x: x * 2, recurse=True)
        assert isinstance(result, tuple)
        assert result == ()

        # Nested tuples
        result = map_collection(((1, 2), (3, 4)), lambda x: x * 2, recurse=True)
        assert isinstance(result, tuple)
        assert result == ((2, 4), (6, 8))

    def test_set_transformation(self):
        """Test map_collection with sets."""
        # Simple set
        result = map_collection({1, 2, 3}, lambda x: x * 2, recurse=True)
        assert isinstance(result, set)
        assert result == {2, 4, 6}

        # Empty set
        result = map_collection(set(), lambda x: x * 2, recurse=True)
        assert isinstance(result, set)
        assert result == set()

    def test_frozenset_transformation(self):
        """Test map_collection with frozensets."""
        # Simple frozenset
        result = map_collection(frozenset({1, 2, 3}), lambda x: x * 2, recurse=True)
        assert isinstance(result, frozenset)
        assert result == frozenset({2, 4, 6})

        # Empty frozenset
        result = map_collection(frozenset(), lambda x: x * 2, recurse=True)
        assert isinstance(result, frozenset)
        assert result == frozenset()

    def test_dict_transformation(self):
        """Test map_collection with dictionaries (only values transformed)."""
        # Simple dict
        assert map_collection({"a": 1, "b": 2}, lambda x: x * 2, recurse=True) == {"a": 2, "b": 4}

        # Empty dict
        assert map_collection({}, lambda x: x * 2, recurse=True) == {}

        # Keys are not transformed, only values
        result = map_collection({"one": 1, "two": 2}, lambda x: x * 10, recurse=True)
        assert result == {"one": 10, "two": 20}
        assert "one" in result  # Keys unchanged

    def test_nested_dict_transformation(self):
        """Test map_collection with nested dictionaries."""
        # Nested dicts
        result = map_collection({"x": {"a": 1, "b": 2}}, lambda x: x * 2, recurse=True)
        assert result == {"x": {"a": 2, "b": 4}}

        # Deeply nested dicts
        result = map_collection({"x": {"y": {"z": 1}}}, lambda x: x * 2, recurse=True)
        assert result == {"x": {"y": {"z": 2}}}

    def test_mixed_nested_structures(self):
        """Test map_collection with mixed nested structures."""
        # Dict with lists
        result = map_collection({"nums": [1, 2, 3]}, lambda x: x * 2, recurse=True)
        assert result == {"nums": [2, 4, 6]}

        # List with dicts
        result = map_collection([{"a": 1}, {"b": 2}], lambda x: x * 2, recurse=True)
        assert result == [{"a": 2}, {"b": 4}]

        # Complex nesting
        data = {"numbers": [1, 2, 3], "nested": {"values": [4, 5], "data": {"x": 6}}, "tuples": (7, 8)}
        result = map_collection(data, lambda x: x * 2, recurse=True)
        assert result == {
            "numbers": [2, 4, 6],
            "nested": {"values": [8, 10], "data": {"x": 12}},
            "tuples": (14, 16),
        }

    def test_non_recursive_mode(self):
        """Test map_collection with recurse=False."""
        # Should only apply to immediate values, not nested
        result = map_collection([1, [2, 3]], lambda x: x * 2 if isinstance(x, int) else x, recurse=False)
        # The nested list [2, 3] is not multiplied, stays as is
        assert result == [2, [2, 3]]

        # Dict with nested values
        result = map_collection(
            {"a": 1, "b": [2, 3]}, lambda x: x * 2 if isinstance(x, int) else x, recurse=False
        )
        assert result == {"a": 2, "b": [2, 3]}

    def test_type_preservation(self):
        """Test that collection types are preserved."""
        # List stays list
        result = map_collection([1, 2], lambda x: x, recurse=True)
        assert isinstance(result, list)

        # Tuple stays tuple
        result = map_collection((1, 2), lambda x: x, recurse=True)
        assert isinstance(result, tuple)

        # Set stays set
        result = map_collection({1, 2}, lambda x: x, recurse=True)
        assert isinstance(result, set)

        # Frozenset stays frozenset
        result = map_collection(frozenset({1, 2}), lambda x: x, recurse=True)
        assert isinstance(result, frozenset)

        # Dict stays dict
        result = map_collection({"a": 1}, lambda x: x, recurse=True)
        assert isinstance(result, dict)

    def test_type_conversion_function(self):
        """Test map_collection with type conversion functions."""

        # Convert all leaf values to strings
        def to_str(x):
            if isinstance(x, (list, dict, tuple, set, frozenset)):
                return x
            return str(x)

        result = map_collection([1, 2, {"a": 3}], to_str, recurse=True)
        assert result == ["1", "2", {"a": "3"}]

        # Convert to uppercase for strings only
        def upper_if_str(x):
            return x.upper() if isinstance(x, str) else x

        result = map_collection(["hello", 123, "world"], upper_if_str, recurse=True)
        assert result == ["HELLO", 123, "WORLD"]

    def test_conditional_transformation(self):
        """Test map_collection with conditional logic."""

        # Only transform even numbers
        def transform_even(x):
            if isinstance(x, int) and x % 2 == 0:
                return x * 10
            return x

        result = map_collection([1, 2, 3, 4, 5], transform_even, recurse=True)
        assert result == [1, 20, 3, 40, 5]

        # Nested conditional
        result = map_collection([[1, 2], [3, 4]], transform_even, recurse=True)
        assert result == [[1, 20], [3, 40]]

    def test_complex_real_world_example(self):
        """Test with a realistic data transformation scenario."""
        # Simulate converting string numbers to integers in a config
        config = {
            "server": {"port": "8080", "max_connections": "100"},
            "workers": ["4", "8", "16"],
            "timeouts": ("30", "60", "120"),
            "features": {"cache_size": "1000"},
        }

        def str_to_int(x):
            if isinstance(x, str) and x.isdigit():
                return int(x)
            return x

        result = map_collection(config, str_to_int, recurse=True)

        assert result["server"]["port"] == 8080
        assert result["server"]["max_connections"] == 100
        assert result["workers"] == [4, 8, 16]
        assert result["timeouts"] == (30, 60, 120)
        assert result["features"]["cache_size"] == 1000

    def test_with_none_values(self):
        """Test map_collection with None values in collections."""
        # List with None
        result = map_collection([1, None, 3], lambda x: x if x is None else x * 2, recurse=True)
        assert result == [2, None, 6]

        # Dict with None values
        result = map_collection(
            {"a": 1, "b": None, "c": 3}, lambda x: x if x is None else x * 2, recurse=True
        )
        assert result == {"a": 2, "b": None, "c": 6}

    def test_empty_collections(self):
        """Test map_collection with various empty collections."""
        assert map_collection([], lambda x: x * 2, recurse=True) == []
        assert map_collection({}, lambda x: x * 2, recurse=True) == {}
        assert map_collection((), lambda x: x * 2, recurse=True) == ()
        assert map_collection(set(), lambda x: x * 2, recurse=True) == set()
        assert map_collection(frozenset(), lambda x: x * 2, recurse=True) == frozenset()

    def test_with_callable_that_raises(self):
        """Test map_collection when the callable raises an exception."""

        def raise_on_negative(x):
            if isinstance(x, int) and x < 0:
                raise ValueError("Negative value not allowed")
            return x * 2

        # Should work fine with positive values
        assert map_collection([1, 2, 3], raise_on_negative, recurse=True) == [2, 4, 6]

        # Should raise when encountering negative
        with pytest.raises(ValueError, match="Negative value not allowed"):
            map_collection([1, -2, 3], raise_on_negative, recurse=True)
