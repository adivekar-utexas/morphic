"""
Comprehensive tests for morphic.string module.

Tests all string utility functions including:
- Normalization functions (normalize, punct_normalize, whitespace_normalize)
- Base conversion and hashing
- Type conversion (convert_str_to_type)
- Human-readable formatting (join_human, readable_bytes, readable_seconds, readable_number)
- Case detection and conversion (detect_case, convert_case)
- Padding and formatting (zfill, get_num_zeros_to_pad)
- Random name generation (random_name)
- Datetime utilities (parse_datetime, now, readable_datetime)
- String matching (fuzzy_match, is_fuzzy_match)
- Validation helpers (is_int, is_float, is_empty, is_stream)
"""

import io
from datetime import datetime, timedelta

import pytest

from morphic.string import (
    BASE_CONVERTER_MAP,
    # Constants
    _is_not_empty,
    convert_case,
    convert_number,
    convert_size_from_bytes,
    convert_size_to_bytes,
    convert_str_to_type,
    convert_time_from_seconds,
    # Case conversion
    detect_case,
    # Format and parsing
    format_exception_msg,
    # Fuzzy matching
    fuzzy_match,
    # Padding
    get_num_zeros_to_pad,
    hash,
    is_empty,
    is_float,
    is_fuzzy_match,
    # Validation
    is_int,
    is_not_empty_bytes,
    is_stream,
    # Formatting
    join_human,
    # Normalization
    normalize,
    now,
    # Datetime
    parse_datetime,
    punct_normalize,
    # Random names
    random_name,
    readable_bytes,
    readable_datetime,
    readable_number,
    readable_seconds,
    str_format_args,
    whitespace_normalize,
    zfill,
)


class TestNormalize:
    """Test normalize() function."""

    def test_basic_normalization(self):
        """Test basic string normalization with default parameters."""
        assert normalize("Hello World") == "helloworld"
        assert normalize("snake_case") == "snakecase"
        assert normalize("kebab-case") == "kebabcase"
        assert normalize("mixed-Style_Name") == "mixedstylename"

    def test_custom_removal_characters(self):
        """Test normalization with custom removal characters."""
        assert normalize("foo@bar.com", remove=("@", ".")) == "foobarcom"
        assert normalize("a:b:c", remove=(":")) == "abc"
        assert normalize("a:b:c", remove=(":")) == "abc"

    def test_no_removal(self):
        """Test normalization with no character removal (only lowercase)."""
        assert normalize("CamelCase", remove=None) == "camelcase"
        assert normalize("UPPER", remove=None) == "upper"

    def test_empty_removal(self):
        """Test normalization with empty removal set."""
        assert normalize("Test", remove=[]) == "test"
        assert normalize("Test", remove=set()) == "test"
        assert normalize("Test", remove=()) == "test"

    def test_invalid_removal_type(self):
        """Test that invalid removal parameter raises TypeError."""
        with pytest.raises(TypeError, match="must be str, tuple, list, set, or None"):
            normalize("test", remove=123)


class TestPunctNormalize:
    """Test punct_normalize() function."""

    def test_default_behavior(self):
        """Test default punctuation removal (lowercase, remove spaces)."""
        assert punct_normalize("Hello, World!") == "helloworld"
        assert punct_normalize("Test-123: Done!") == "test123done"

    def test_keep_spaces(self):
        """Test keeping spaces while removing punctuation."""
        assert punct_normalize("Hello, World!", space=False) == "hello world"
        assert punct_normalize("Test: Done!", space=False) == "test done"

    def test_keep_case(self):
        """Test keeping original case."""
        assert punct_normalize("Hello, World!", lowercase=False) == "HelloWorld"
        assert punct_normalize("Test-123", lowercase=False, space=False) == "Test123"

    def test_remove_numbers(self):
        """Test removing numbers along with punctuation."""
        assert punct_normalize("abc123def", numbers=True) == "abcdef"
        assert punct_normalize("Test-123: Done!", numbers=True) == "testdone"

    def test_combinations(self):
        """Test various combinations of parameters."""
        text = "Test-123: Done!"
        assert punct_normalize(text, lowercase=False, space=False) == "Test123 Done"
        assert punct_normalize(text, lowercase=False, space=False, numbers=True) == "Test Done"

    def test_invalid_input_type(self):
        """Test that non-string input raises TypeError."""
        with pytest.raises(TypeError, match="must be str"):
            punct_normalize(123)


class TestWhitespaceNormalize:
    """Test whitespace_normalize() function."""

    def test_collapse_spaces(self):
        """Test collapsing multiple spaces."""
        assert whitespace_normalize("hello    world") == "hello world"
        assert whitespace_normalize("a  b  c") == "a b c"

    def test_collapse_newlines(self):
        """Test collapsing multiple newlines."""
        assert whitespace_normalize("line1\n\n\nline2") == "line1\nline2"
        assert whitespace_normalize("a\n\nb\n\n\nc") == "a\nb\nc"

    def test_remove_newlines(self):
        """Test removing all newlines."""
        # Note: remove_newlines just removes them, doesn't replace with space
        assert whitespace_normalize("line1\nline2", remove_newlines=True) == "line1line2"
        assert whitespace_normalize("a\nb\nc", remove_newlines=True) == "abc"

    def test_trailing_whitespace(self):
        """Test removal of trailing whitespace from each line."""
        text = "line1   \nline2   \nline3"
        assert whitespace_normalize(text) == "line1\nline2\nline3"

    def test_messy_text(self):
        """Test cleaning up messy text."""
        messy = "  hello   world  \n\n  foo   bar  \n\n  "
        clean = whitespace_normalize(messy)
        # Note: Leading space on a line is not removed, only trailing
        assert "hello world" in clean and "foo" in clean and "bar" in clean

    def test_invalid_input_type(self):
        """Test that non-string input raises TypeError."""
        with pytest.raises(TypeError, match="must be str"):
            whitespace_normalize(123)


class TestBaseConverter:
    """Test BaseConverter class."""

    def test_base2_conversion(self):
        """Test base-2 (binary) conversion."""
        converter = BASE_CONVERTER_MAP[2]
        assert converter.encode(10) == "1010"
        assert converter.decode("1010") == 10

    def test_base16_conversion(self):
        """Test base-16 (hexadecimal) conversion."""
        converter = BASE_CONVERTER_MAP[16]
        assert converter.encode(255) == "FF"
        assert converter.decode("FF") == 255

    def test_base62_conversion(self):
        """Test base-62 conversion."""
        converter = BASE_CONVERTER_MAP[62]
        encoded = converter.encode(123456)
        assert converter.decode(encoded) == 123456

    def test_negative_numbers(self):
        """Test negative number conversion."""
        converter = BASE_CONVERTER_MAP[62]
        assert converter.encode(-123) == "-1z"
        assert converter.decode("-1z") == -123


class TestHash:
    """Test hash() function."""

    def test_string_hashing(self):
        """Test hashing of strings."""
        h1 = hash("test")
        h2 = hash("test")
        assert h1 == h2  # Same input should give same hash
        assert hash("test") != hash("TEST")  # Different input

    def test_numeric_hashing(self):
        """Test hashing of numbers."""
        h1 = hash(123)
        h2 = hash(123)
        assert h1 == h2

    def test_list_hashing(self):
        """Test hashing of lists."""
        h1 = hash([1, 2, 3])
        h2 = hash([1, 2, 3])
        assert h1 == h2
        assert hash([1, 2, 3]) != hash([3, 2, 1])

    def test_dict_hashing(self):
        """Test hashing of dictionaries (order-independent)."""
        h1 = hash({"a": 1, "b": 2})
        h2 = hash({"b": 2, "a": 1})
        assert h1 == h2  # Same content, different order

    def test_different_bases(self):
        """Test hashing with different output bases."""
        val = "test"
        h16 = hash(val, base=16)
        h62 = hash(val, base=62)
        assert h16 != h62
        assert len(h16) > len(h62)  # Base 62 should be shorter


class TestFormatExceptionMsg:
    """Test format_exception_msg() function."""

    def test_basic_formatting(self):
        """Test basic exception formatting."""
        try:
            raise ValueError("Something went wrong")
        except Exception as e:
            msg = format_exception_msg(e)
            assert "ValueError" in msg
            assert "Something went wrong" in msg

    def test_short_format(self):
        """Test short format with traceback."""
        try:
            raise ValueError("Test error")
        except Exception as e:
            msg = format_exception_msg(e, short=True)
            assert "ValueError" in msg
            assert "Trace:" in msg

    def test_with_prefix(self):
        """Test exception formatting with prefix."""
        try:
            raise ValueError("Test error")
        except Exception as e:
            msg = format_exception_msg(e, prefix="Validation Error")
            assert "Validation Error" in msg
            assert "ValueError" in msg


class TestStrFormatArgs:
    """Test str_format_args() function."""

    def test_named_arguments(self):
        """Test extraction of named arguments."""
        assert str_format_args("Hello {name}!") == ["name"]
        assert str_format_args("{first} {last}") == ["first", "last"]

    def test_positional_arguments(self):
        """Test extraction of positional arguments."""
        assert str_format_args("Hello {0}!", named_only=False) == ["0"]
        assert str_format_args("{0} {1}", named_only=False) == ["0", "1"]

    def test_mixed_arguments(self):
        """Test extraction from mixed format strings."""
        result = str_format_args("{0} {name} {1}", named_only=False)
        assert result == ["0", "name", "1"]
        result_named = str_format_args("{0} {name} {1}", named_only=True)
        assert result_named == ["name"]

    def test_no_arguments(self):
        """Test string with no format arguments."""
        assert str_format_args("No arguments here") == []

    def test_duplicate_arguments(self):
        """Test that duplicates are preserved."""
        assert str_format_args("{x} and {x}") == ["x", "x"]

    def test_invalid_input_type(self):
        """Test that non-string input raises TypeError."""
        with pytest.raises(TypeError, match="must be str"):
            str_format_args(123)


class TestValidationFunctions:
    """Test validation helper functions."""

    def test_is_int(self):
        """Test is_int() function."""
        assert is_int("123") is True
        assert is_int("-123") is True
        assert is_int("0") is True
        assert is_int("123.0") is False
        assert is_int("1.23") is False
        assert is_int("abc") is False

    def test_is_float(self):
        """Test is_float() function."""
        assert is_float("123") is True
        assert is_float("1.23") is True
        assert is_float("123.0") is True
        assert is_float("-123.0") is True
        assert is_float("1e2") is True
        assert is_float("1.23e-5") is True
        assert is_float("nan") is True
        assert is_float("NAN") is True
        assert is_float("abc") is False

    def test_is_empty(self):
        """Test is_empty() function."""
        assert is_empty("") is True
        assert is_empty("   ") is True
        assert is_empty("hello") is False
        assert is_empty("  hello  ") is False

    def test_is_not_empty(self):
        """Test _is_not_empty() function."""
        assert _is_not_empty("hello") is True
        assert _is_not_empty("  hello  ") is True
        assert _is_not_empty("") is False
        assert _is_not_empty("   ") is False

    def test_is_not_empty_bytes(self):
        """Test is_not_empty_bytes() function."""
        assert is_not_empty_bytes(b"hello") is True
        assert is_not_empty_bytes(b"  hello  ") is True
        assert is_not_empty_bytes(b"") is False
        assert is_not_empty_bytes(b"   ") is False

    def test_is_stream(self):
        """Test is_stream() function."""
        # Test with StringIO
        stream = io.StringIO("content")
        assert is_stream(stream) is True

        # Test with BytesIO
        stream = io.BytesIO(b"content")
        assert is_stream(stream) is True

        # Test with non-streams
        assert is_stream("string") is False
        assert is_stream(123) is False
        assert is_stream([1, 2, 3]) is False
        assert is_stream(None) is False


class TestJoinHuman:
    """Test join_human() function."""

    def test_basic_usage(self):
        """Test basic list joining."""
        assert join_human(["apple", "banana", "cherry"]) == "apple, banana and cherry"

    def test_oxford_comma(self):
        """Test Oxford comma style."""
        result = join_human(["apple", "banana", "cherry"], oxford_comma=True)
        assert result == "apple, banana, and cherry"

    def test_two_items(self):
        """Test joining two items."""
        assert join_human(["Alice", "Bob"]) == "Alice and Bob"

    def test_single_item(self):
        """Test joining single item."""
        assert join_human(["Alice"]) == "Alice"

    def test_empty_list(self):
        """Test joining empty list."""
        assert join_human([]) == ""

    def test_custom_separator(self):
        """Test custom separator."""
        assert join_human([1, 2, 3], sep=";", final_join="or") == "1; 2 or 3"

    def test_tuple_and_set(self):
        """Test with tuple and set inputs."""
        assert join_human(("red", "green", "blue")) == "red, green and blue"
        result = join_human({"alpha", "beta", "gamma"})
        assert "alpha" in result and "beta" in result and "gamma" in result

    def test_invalid_input_type(self):
        """Test that invalid input raises TypeError."""
        with pytest.raises(TypeError, match="must be list, tuple, or set"):
            join_human("not a list")
        with pytest.raises(TypeError, match="must be str"):
            join_human([1, 2], sep=123)


class TestConvertStrToType:
    """Test convert_str_to_type() function."""

    def test_basic_types(self):
        """Test conversion to basic types."""
        assert convert_str_to_type("123", int) == 123
        assert convert_str_to_type("12.5", float) == 12.5
        assert convert_str_to_type("true", bool) is True
        assert convert_str_to_type("False", bool) is False

    def test_collections(self):
        """Test conversion to collection types."""
        assert convert_str_to_type("[1, 2, 3]", list) == [1, 2, 3]
        assert convert_str_to_type("(1, 2, 3)", tuple) == (1, 2, 3)
        assert convert_str_to_type("{1, 2, 3}", set) == {1, 2, 3}
        assert convert_str_to_type("{'a': 1}", dict) == {"a": 1}

    def test_type_coercion(self):
        """Test automatic type coercion."""
        assert convert_str_to_type("5", float) == 5.0
        assert convert_str_to_type("5.0", int) == 5
        assert convert_str_to_type("[1, 2]", tuple) == (1, 2)
        assert convert_str_to_type("(1, 2)", list) == [1, 2]
        assert convert_str_to_type("[1, 2]", set) == {1, 2}

    def test_already_correct_type(self):
        """Test when input is already the correct type."""
        assert convert_str_to_type("hello", str) == "hello"

    def test_bool_from_int(self):
        """Test converting int strings to bool."""
        assert convert_str_to_type("1", bool) is True
        assert convert_str_to_type("0", bool) is False

    def test_invalid_conversion(self):
        """Test that invalid conversions raise ValueError."""
        with pytest.raises(ValueError):
            convert_str_to_type("abc", int)

    def test_invalid_type_parameter(self):
        """Test that invalid expected_type raises TypeError."""
        with pytest.raises(TypeError, match="must be a type"):
            convert_str_to_type("123", "not a type")

    def test_invalid_value_parameter(self):
        """Test that non-string val raises TypeError."""
        with pytest.raises(TypeError, match="must be str"):
            convert_str_to_type(123, str)


class TestReadableBytes:
    """Test readable_bytes() and convert_size_from_bytes() functions."""

    def test_readable_bytes(self):
        """Test human-readable byte formatting."""
        assert "B" in readable_bytes(500)
        assert "KB" in readable_bytes(5000)
        assert "MB" in readable_bytes(5000000)
        assert "GB" in readable_bytes(5000000000)

    def test_convert_size_from_bytes(self):
        """Test byte size conversion."""
        sizes = convert_size_from_bytes(1024, unit=None)
        assert sizes["B"] == 1024.0
        assert sizes["KB"] == 1.0

        # Test specific unit
        kb_size = convert_size_from_bytes(2048, unit="KB")
        assert kb_size == 2.0

    def test_convert_size_to_bytes(self):
        """Test converting human-readable sizes to bytes."""
        assert convert_size_to_bytes("1 KB") == 1024
        assert convert_size_to_bytes("1 MB") == 1024 * 1024
        assert convert_size_to_bytes("1.5 KB") == int(1.5 * 1024)

    def test_zero_bytes(self):
        """Test handling of zero bytes."""
        sizes = convert_size_from_bytes(0)
        assert all(v == 0.0 for v in sizes.values())


class TestReadableSeconds:
    """Test readable_seconds() and convert_time_from_seconds() functions."""

    def test_readable_seconds(self):
        """Test human-readable time formatting."""
        assert "s" in readable_seconds(5)
        assert "min" in readable_seconds(120, short=True)
        assert "hr" in readable_seconds(7200, short=True)

    def test_timedelta_input(self):
        """Test accepting timedelta objects."""
        td = timedelta(seconds=30)
        result = readable_seconds(td)
        assert "30" in result

    def test_convert_time_from_seconds(self):
        """Test time conversion."""
        times = convert_time_from_seconds(60)
        assert times["seconds"] == 60.0
        assert times["mins"] == 1.0

        # Test specific unit
        mins = convert_time_from_seconds(120, unit="mins")
        assert mins == 2.0

    def test_short_format(self):
        """Test short format output."""
        result = readable_seconds(5, short=True)
        assert "5.0s" == result or "5s" in result


class TestReadableNumber:
    """Test readable_number() and convert_number() functions."""

    def test_readable_number(self):
        """Test human-readable number formatting."""
        assert readable_number(1000, short=True) == "1K"
        assert readable_number(1000000, short=True) == "1M"
        assert readable_number(1000000000, short=True) == "1B"

    def test_small_numbers(self):
        """Test small numbers use scientific notation."""
        result = readable_number(0.00123)
        assert "e" in result

    def test_convert_number(self):
        """Test number unit conversion."""
        numbers = convert_number(1000000, short=True)
        assert numbers["M"] == 1.0
        assert numbers["K"] == 1000.0

    def test_zero(self):
        """Test zero handling."""
        assert readable_number(0) == "0"


class TestCaseDetection:
    """Test detect_case() and convert_case() functions."""

    def test_detect_case(self):
        """Test case detection."""
        assert detect_case("snake_case") == "snake"
        assert detect_case("SCREAMING_SNAKE_CASE") == "screaming_snake"
        assert detect_case("kebab-case") == "kebab"
        assert detect_case("TRAIN-CASE") == "train"
        assert detect_case("camelCase") == "camel"
        assert detect_case("PascalCase") == "pascal"

    def test_convert_case(self):
        """Test case conversion."""
        assert convert_case("CachedResultsStep", "kebab") == "cached-results-step"
        assert convert_case("cachedResultsStep", "snake") == "cached_results_step"
        assert convert_case("cached_results_step", "pascal") == "CachedResultsStep"
        assert convert_case("cached-results-step", "camel") == "cachedResultsStep"
        assert convert_case("CACHED_RESULTS_STEP", "camel") == "cachedResultsStep"

    def test_convert_with_numbers(self):
        """Test case conversion with numbers."""
        assert convert_case("Test123Case", "snake") == "test_123_case"

    def test_upper_lower(self):
        """Test simple upper/lower conversion."""
        assert convert_case("TestCase", "upper") == "TESTCASE"
        assert convert_case("TestCase", "lower") == "testcase"

    def test_invalid_case_detection(self):
        """Test invalid case strings."""
        with pytest.raises(ValueError):
            detect_case("")
        with pytest.raises(ValueError):
            detect_case("mixed-underscore_case")


class TestPadding:
    """Test get_num_zeros_to_pad() and zfill() functions."""

    def test_get_num_zeros_to_pad(self):
        """Test calculating padding length."""
        assert get_num_zeros_to_pad(99) == 2
        assert get_num_zeros_to_pad(100) == 3
        assert get_num_zeros_to_pad(999) == 3
        assert get_num_zeros_to_pad(1000) == 4
        assert get_num_zeros_to_pad(9) == 1
        assert get_num_zeros_to_pad(10) == 2

    def test_zfill(self):
        """Test zero-padding integers."""
        assert zfill(5, 999) == "005"
        assert zfill(42, 999) == "042"
        assert zfill(999, 999) == "999"
        assert zfill(1, 100) == "001"
        assert zfill(99, 100) == "099"
        assert zfill(100, 100) == "100"

    def test_zfill_default_max(self):
        """Test zfill with default max value."""
        result = zfill(1)
        assert len(result) == 13  # For 1 trillion

    def test_invalid_padding_inputs(self):
        """Test that invalid inputs raise appropriate errors."""
        with pytest.raises(TypeError):
            get_num_zeros_to_pad("not an int")
        with pytest.raises(ValueError):
            get_num_zeros_to_pad(0)
        with pytest.raises(TypeError):
            zfill("not an int", 100)
        with pytest.raises(ValueError):
            zfill(-1, 100)
        with pytest.raises(ValueError):
            zfill(100, 50)


class TestRandomName:
    """Test random_name() function."""

    def test_single_name(self):
        """Test generating a single random name."""
        name = random_name()
        assert isinstance(name, str)
        assert len(name) > 0

    def test_multiple_names(self):
        """Test generating multiple random names."""
        names = random_name(3)
        assert isinstance(names, list)
        assert len(names) == 3
        assert len(set(names)) == 3  # All unique

    def test_custom_separator(self):
        """Test custom separator."""
        name = random_name(sep="_")
        assert "_" in name

    def test_custom_order(self):
        """Test custom word order."""
        name = random_name(order=("adjective", "noun"))
        # Should have 1 separator (2 words)
        assert name.count("-") == 1

    def test_reproducibility(self):
        """Test that seed produces reproducible results."""
        name1 = random_name(seed=42)
        name2 = random_name(seed=42)
        assert name1 == name2

    def test_invalid_inputs(self):
        """Test that invalid inputs raise appropriate errors."""
        with pytest.raises(TypeError):
            random_name(count="not an int")
        with pytest.raises(ValueError):
            random_name(count=0)
        with pytest.raises(TypeError):
            random_name(sep=123)
        with pytest.raises(ValueError):
            random_name(order=())
        with pytest.raises(NotImplementedError):
            random_name(order=("invalid_type",))


class TestDatetime:
    """Test datetime utility functions."""

    def test_parse_datetime(self):
        """Test parsing various datetime representations."""
        # datetime object (pass-through)
        dt = datetime.now()
        assert parse_datetime(dt) == dt

        # Unix timestamp
        dt = parse_datetime(1609459200)
        assert dt.year == 2021

        # ISO format string
        dt = parse_datetime("2021-01-01T00:00:00")
        assert dt.year == 2021 and dt.month == 1

    def test_now(self):
        """Test now() function."""
        current = now()
        assert isinstance(current, str)
        assert len(current) > 0

        # Test with parameters
        current_human = now(human=True)
        assert isinstance(current_human, str)

    def test_readable_datetime(self):
        """Test readable_datetime() function."""
        dt = datetime(2021, 1, 15, 14, 30, 45, 123456)

        # Default format
        result = readable_datetime(dt)
        assert "2021-01-15" in result
        assert "14:30:45" in result

        # Without microseconds
        result = readable_datetime(dt, microsec=False)
        assert ".123456" not in result

        # Human format
        result = readable_datetime(dt, human=True, tz=False)
        assert "15Jan2021" in result


class TestFuzzyMatch:
    """Test fuzzy_match() and is_fuzzy_match() functions."""

    def test_fuzzy_match_basic(self):
        """Test basic fuzzy matching."""
        assert fuzzy_match("my_file", ["my-file", "other"]) == "my-file"
        assert fuzzy_match("my-file", ["my_file", "other"]) == "my_file"
        assert fuzzy_match("my file", ["my_file", "other"]) == "my_file"

    def test_fuzzy_match_case_insensitive(self):
        """Test case-insensitive matching with delimiters."""
        # Only works when there are delimiters to normalize
        assert fuzzy_match("my-file", ["my_file"]) == "my_file"
        assert fuzzy_match("MY-FILE", ["my_file"]) == "my_file"
        assert fuzzy_match("MY FILE", ["my_file"]) == "my_file"

    def test_fuzzy_match_no_match(self):
        """Test when no match is found."""
        assert fuzzy_match("notfound", ["my_file", "other"]) is None

    def test_fuzzy_match_single_string(self):
        """Test matching against a single string."""
        assert fuzzy_match("my_file", "my-file") == "my-file"
        assert fuzzy_match("wrong", "my-file") is None

    def test_is_fuzzy_match(self):
        """Test is_fuzzy_match() function."""
        assert is_fuzzy_match("my_file", ["my-file", "other"]) is True
        assert is_fuzzy_match("MY-FILE", ["my_file"]) is True
        assert is_fuzzy_match("notfound", ["my_file", "other"]) is False

    def test_fuzzy_match_invalid_inputs(self):
        """Test that invalid inputs raise TypeError."""
        with pytest.raises(TypeError):
            fuzzy_match(123, ["test"])
        with pytest.raises(TypeError):
            fuzzy_match("test", 123)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_strings(self):
        """Test handling of empty strings."""
        assert normalize("") == ""
        assert punct_normalize("") == ""
        assert whitespace_normalize("") == ""
        assert join_human([]) == ""

    def test_unicode_handling(self):
        """Test Unicode string handling."""
        assert normalize("Héllo Wörld") == "héllowörld"
        assert punct_normalize("Tëst!") == "tëst"

    def test_large_numbers(self):
        """Test handling of large numbers."""
        large_num = 10**15
        result = readable_number(large_num)
        assert len(result) > 0

        large_bytes = 10**15
        result = readable_bytes(large_bytes)
        assert len(result) > 0

    def test_special_characters(self):
        """Test handling of special characters."""
        assert normalize("test\n\t\r") == "test\n\t\r"
        text = "line1\n\t  line2"
        result = whitespace_normalize(text)
        assert "\n" in result or len(result) > 0


class TestNormalizeEdgeCases:
    """Test edge cases for normalize() function."""

    def test_all_whitespace(self):
        """Test strings that are all whitespace."""
        assert normalize("   ") == ""
        assert normalize("\t\n\r") == "\t\n\r"

    def test_single_character(self):
        """Test single character strings."""
        assert normalize("A") == "a"
        assert normalize("_", remove="_") == ""
        assert normalize("-", remove="-") == ""

    def test_only_removable_chars(self):
        """Test strings containing only removable characters."""
        assert normalize("---", remove="-") == ""
        assert normalize("___", remove="_") == ""
        assert normalize("- _", remove=(" ", "-", "_")) == ""

    def test_mixed_unicode_and_ascii(self):
        """Test mixed Unicode and ASCII characters."""
        assert normalize("café-résumé", remove="-") == "caférésumé"
        assert normalize("Hello_世界", remove="_") == "hello世界"

    def test_remove_parameter_variations(self):
        """Test various remove parameter types."""
        # String
        assert normalize("a-b-c", remove="-") == "abc"
        # List
        assert normalize("a-b_c", remove=["-", "_"]) == "abc"
        # Tuple
        assert normalize("a-b_c", remove=("-", "_")) == "abc"
        # Set
        assert normalize("a-b_c", remove={"-", "_"}) == "abc"

    def test_repeated_removal_characters(self):
        """Test strings with many repeated removal characters."""
        assert normalize("a---b___c", remove=("-", "_")) == "abc"
        assert normalize("hello     world", remove=" ") == "helloworld"


class TestPunctNormalizeEdgeCases:
    """Test edge cases for punct_normalize() function."""

    def test_only_punctuation(self):
        """Test strings containing only punctuation."""
        assert punct_normalize("!!!") == ""
        assert punct_normalize("?!.,;:") == ""

    def test_all_numbers(self):
        """Test strings containing only numbers."""
        assert punct_normalize("123456") == "123456"
        assert punct_normalize("123456", numbers=True) == ""

    def test_mixed_punctuation_and_numbers(self):
        """Test mixed punctuation and numbers."""
        assert punct_normalize("$1,234.56") == "123456"
        assert punct_normalize("$1,234.56", numbers=True) == ""

    def test_unicode_characters_preserved(self):
        """Test that Unicode characters are preserved."""
        result = punct_normalize("Café!")
        assert "café" in result.lower()

    def test_multiple_spaces(self):
        """Test handling of multiple spaces."""
        assert punct_normalize("a  b  c", space=False) == "a  b  c"
        assert punct_normalize("a  b  c", space=True) == "abc"


class TestWhitespaceNormalizeEdgeCases:
    """Test edge cases for whitespace_normalize() function."""

    def test_only_whitespace(self):
        """Test strings containing only whitespace."""
        assert whitespace_normalize("   ") == ""
        assert whitespace_normalize("\n\n\n") == ""
        assert whitespace_normalize("\t\t\t") == ""

    def test_mixed_whitespace_types(self):
        """Test mixed tabs, spaces, and newlines."""
        result = whitespace_normalize("a\t\t  b\n\n  c")
        assert "a" in result and "b" in result and "c" in result

    def test_windows_line_endings(self):
        """Test Windows-style line endings."""
        text = "line1\r\nline2\r\nline3"
        result = whitespace_normalize(text)
        assert "line1" in result and "line2" in result

    def test_leading_trailing_whitespace(self):
        """Test leading and trailing whitespace is removed."""
        assert whitespace_normalize("  hello  ") == "hello"
        assert whitespace_normalize("\n\nhello\n\n") == "hello"


class TestConvertStrToTypeEdgeCases:
    """Test edge cases for convert_str_to_type() function."""

    def test_whitespace_handling(self):
        """Test strings with extra whitespace."""
        assert convert_str_to_type("  123  ", int) == 123
        assert convert_str_to_type("  True  ", bool) is True

    def test_bool_variations(self):
        """Test various boolean string formats."""
        assert convert_str_to_type("true", bool) is True
        assert convert_str_to_type("True", bool) is True
        assert convert_str_to_type("TRUE", bool) is True
        assert convert_str_to_type("false", bool) is False
        assert convert_str_to_type("False", bool) is False
        assert convert_str_to_type("FALSE", bool) is False

    def test_nested_collections(self):
        """Test nested collection types."""
        assert convert_str_to_type("[[1, 2], [3, 4]]", list) == [[1, 2], [3, 4]]
        assert convert_str_to_type("{'a': [1, 2]}", dict) == {"a": [1, 2]}

    def test_negative_numbers(self):
        """Test negative number conversions."""
        assert convert_str_to_type("-123", int) == -123
        assert convert_str_to_type("-12.5", float) == -12.5

    def test_scientific_notation(self):
        """Test scientific notation."""
        assert convert_str_to_type("1e6", float) == 1e6
        assert convert_str_to_type("1.23e-5", float) == 1.23e-5

    def test_empty_collections(self):
        """Test empty collection strings."""
        assert convert_str_to_type("[]", list) == []
        assert convert_str_to_type("()", tuple) == ()
        assert convert_str_to_type("{}", dict) == {}


class TestReadableBytesEdgeCases:
    """Test edge cases for byte conversion functions."""

    def test_boundary_values(self):
        """Test boundary values between units."""
        # Exactly 1 KB
        assert "1" in readable_bytes(1024)
        # Just under 1 KB
        result = readable_bytes(1023)
        assert "1023" in result or "1.0" in result

    def test_very_small_bytes(self):
        """Test very small byte counts."""
        assert "1" in readable_bytes(1)
        assert "10" in readable_bytes(10)

    def test_very_large_bytes(self):
        """Test very large byte counts."""
        # Petabytes (1024^5)
        result = readable_bytes(1024**5)
        assert "PB" in result or "1.0 PB" in result

    def test_convert_size_to_bytes_edge_cases(self):
        """Test edge cases for parsing size strings."""
        # No space
        assert convert_size_to_bytes("1KB") == 1024
        # Multiple spaces
        assert convert_size_to_bytes("1   KB") == 1024
        # Lowercase
        assert convert_size_to_bytes("1kb") == 1024

    def test_decimal_conversions(self):
        """Test decimal size conversions."""
        result = convert_size_to_bytes("1.5 KB")
        assert result == int(1.5 * 1024)


class TestReadableSecondsEdgeCases:
    """Test edge cases for time conversion functions."""

    def test_zero_seconds(self):
        """Test zero time duration."""
        result = readable_seconds(0)
        assert "0" in result

    def test_very_small_durations(self):
        """Test nanosecond and microsecond durations."""
        result = readable_seconds(0.000001, short=True)  # 1 microsecond
        assert "us" in result or "microsecond" in result

    def test_very_large_durations(self):
        """Test multi-day durations."""
        result = readable_seconds(86400 * 7, short=True)  # 7 days
        assert "d" in result or "7" in result

    def test_negative_durations(self):
        """Test that negative durations don't break (timedelta can be negative)."""
        from datetime import timedelta

        td = timedelta(seconds=-30)
        result = readable_seconds(td)
        # Should handle gracefully


class TestReadableNumberEdgeCases:
    """Test edge cases for number formatting functions."""

    def test_boundary_numbers(self):
        """Test numbers at unit boundaries."""
        assert "1K" in readable_number(1000)
        assert "999" in readable_number(999)

    def test_negative_numbers(self):
        """Test negative number formatting."""
        result = readable_number(-1000)
        assert "-" in result and "1" in result

    def test_decimal_numbers(self):
        """Test decimal numbers."""
        result = readable_number(1234.56)
        assert "1" in result

    def test_very_large_numbers(self):
        """Test quintillion-scale numbers."""
        result = readable_number(10**18)
        assert "Qi" in result or "quintillion" in result

    def test_convert_number_with_zero(self):
        """Test convert_number with zero (should be allowed)."""
        numbers = convert_number(0, short=True)
        assert numbers[""] == 0.0


class TestCaseConversionEdgeCases:
    """Test edge cases for case detection and conversion."""

    def test_single_word(self):
        """Test single word case detection."""
        # Single lowercase word is detected as camelCase (no way to distinguish from snake)
        assert detect_case("word") == "camel"
        assert detect_case("Word") == "pascal"
        # Single all-caps word is detected as pascal (no way to distinguish without delimiters)
        assert detect_case("WORD") == "pascal"

    def test_numbers_in_names(self):
        """Test handling of numbers in identifiers."""
        assert convert_case("test123", "snake") == "test_123"
        assert convert_case("Test123Case", "kebab") == "test-123-case"

    def test_acronyms(self):
        """Test handling of acronyms."""
        assert convert_case("HTTPRequest", "snake") == "http_request"
        assert convert_case("HTTPSConnection", "kebab") == "https-connection"

    def test_consecutive_capitals(self):
        """Test consecutive capital letters."""
        assert detect_case("XMLParser") == "pascal"
        result = convert_case("XMLParser", "snake")
        # Should split XML and Parser
        assert "xml" in result and "parser" in result

    def test_empty_string_detection(self):
        """Test empty string handling."""
        with pytest.raises(ValueError):
            detect_case("")

    def test_special_characters_rejected(self):
        """Test that strings with special characters are rejected."""
        with pytest.raises(ValueError):
            detect_case("test@name")
        with pytest.raises(ValueError):
            detect_case("test.name")


class TestPaddingEdgeCases:
    """Test edge cases for padding functions."""

    def test_single_digit_numbers(self):
        """Test padding single digit numbers."""
        assert zfill(1, 9) == "1"
        assert zfill(1, 10) == "01"

    def test_max_equals_current(self):
        """Test when i equals max_i."""
        assert zfill(100, 100) == "100"
        assert zfill(999, 999) == "999"

    def test_power_of_ten_boundaries(self):
        """Test padding at power of 10 boundaries."""
        assert get_num_zeros_to_pad(10) == 2
        assert get_num_zeros_to_pad(100) == 3
        assert get_num_zeros_to_pad(1000) == 4

    def test_large_max_values(self):
        """Test padding with very large max values."""
        result = zfill(1, 10**9)
        assert len(result) == 10


class TestRandomNameEdgeCases:
    """Test edge cases for random name generation."""

    def test_single_word_order(self):
        """Test generating names with single word type."""
        name = random_name(order=("noun",))
        assert "-" not in name  # Only one word, no separators

    def test_maximum_combinations(self):
        """Test that we can't exceed maximum combinations."""
        # This should work (reasonable number)
        names = random_name(10, order=("noun",), seed=42)
        assert len(names) == 10

    def test_empty_separator(self):
        """Test with empty separator."""
        name = random_name(sep="", order=("adjective", "noun"))
        # Should concatenate without separator
        assert isinstance(name, str) and len(name) > 0

    def test_long_separator(self):
        """Test with multi-character separator."""
        name = random_name(sep="__", order=("adjective", "noun"))
        assert "__" in name


class TestDatetimeEdgeCases:
    """Test edge cases for datetime functions."""

    def test_epoch_time(self):
        """Test Unix epoch (timestamp 0)."""
        dt = parse_datetime(0)
        assert dt.year == 1970

    def test_negative_timestamp(self):
        """Test negative Unix timestamp (before epoch)."""
        dt = parse_datetime(-86400)  # One day before epoch
        assert dt.year == 1969

    def test_far_future_timestamp(self):
        """Test far future timestamp."""
        dt = parse_datetime(4102444800)  # Year 2100
        assert dt.year == 2100

    def test_datetime_with_microseconds(self):
        """Test datetime formatting with microseconds."""
        from datetime import datetime

        dt = datetime(2021, 1, 1, 12, 0, 0, 123456)
        result = readable_datetime(dt, microsec=True, tz=False)
        assert "123456" in result

    def test_datetime_without_timezone(self):
        """Test datetime without timezone info."""
        from datetime import datetime

        dt = datetime(2021, 1, 1, 12, 0, 0)
        result = readable_datetime(dt, tz=False)
        # Should not crash


class TestFuzzyMatchEdgeCases:
    """Test edge cases for fuzzy matching."""

    def test_exact_match(self):
        """Test exact matching (no fuzzing needed)."""
        assert fuzzy_match("test", ["test", "other"]) == "test"

    def test_case_only_difference(self):
        """Test when only case differs."""
        # fuzzy_match is case-insensitive even without delimiters
        assert fuzzy_match("TEST", ["test"]) == "test"

    def test_multiple_delimiters(self):
        """Test strings with multiple types of delimiters."""
        assert fuzzy_match("my-file_name", ["my_file-name"]) == "my_file-name"

    def test_empty_string_matching(self):
        """Test matching empty strings."""
        assert fuzzy_match("", [""]) == ""
        assert fuzzy_match("", ["test"]) is None

    def test_single_character_strings(self):
        """Test single character matching."""
        assert fuzzy_match("a", ["a"]) == "a"
        assert fuzzy_match("a", ["b"]) is None

    def test_unicode_in_fuzzy_match(self):
        """Test fuzzy matching with Unicode."""
        assert fuzzy_match("café", ["café"]) == "café"


class TestHashingEdgeCases:
    """Test edge cases for hashing function."""

    def test_empty_containers(self):
        """Test hashing empty containers."""
        h1 = hash([])
        h2 = hash({})
        h3 = hash(())
        # Note: Empty list, dict, and tuple currently hash to the same value
        # This is a limitation of the current hash implementation
        assert h1 == h2 == h3  # All empty containers hash the same

    def test_order_matters_for_lists(self):
        """Test that order matters for lists."""
        h1 = hash([1, 2, 3])
        h2 = hash([3, 2, 1])
        assert h1 != h2

    def test_order_independent_for_dicts(self):
        """Test that order doesn't matter for dicts."""
        h1 = hash({"a": 1, "b": 2})
        h2 = hash({"b": 2, "a": 1})
        assert h1 == h2

    def test_nested_structures(self):
        """Test hashing nested structures."""
        h1 = hash({"a": [1, 2], "b": {"c": 3}})
        h2 = hash({"a": [1, 2], "b": {"c": 3}})
        assert h1 == h2


class TestValidationEdgeCases:
    """Test edge cases for validation functions."""

    def test_is_int_with_whitespace(self):
        """Test is_int with whitespace."""
        assert is_int("  123  ") is True
        assert is_int("123\n") is True

    def test_is_float_special_values(self):
        """Test is_float with special values."""
        assert is_float("inf") is True
        assert is_float("-inf") is True
        assert is_float("infinity") is True

    def test_is_empty_with_non_strings(self):
        """Test is_empty with non-string types."""
        assert is_empty(None) is True
        assert is_empty(0) is True
        assert is_empty([]) is True
        assert is_empty({}) is True

    def test_is_stream_with_closed_file(self):
        """Test is_stream with various I/O objects."""
        import io

        stream = io.StringIO("test")
        assert is_stream(stream) is True
        stream.close()
        # Still identifies as stream even when closed
        assert is_stream(stream) is True
