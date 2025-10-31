import io
import math
import random
import re
import string
from ast import literal_eval
from datetime import datetime, timedelta
from hashlib import sha256
from typing import Any, Dict, KeysView, List, Literal, Optional, Set, Tuple, Type, Union, ValuesView

from .autoenum import AutoEnum
from .string_data import RANDOM_ADJECTIVES, RANDOM_NOUNS, RANDOM_VERBS

EMPTY: str = ""
SPACE: str = " "
DOUBLE_SPACE: str = SPACE * 2
FOUR_SPACE: str = SPACE * 4
TAB: str = "\t"
NEWLINE: str = "\n"
WINDOWS_NEWLINE: str = "\r"
BACKSLASH: str = "\\"
SLASH: str = "/"
PIPE: str = "|"
SINGLE_QUOTE: str = "'"
DOUBLE_QUOTE: str = '"'
COMMA: str = ","
COMMA_SPACE: str = ", "
COMMA_NEWLINE: str = ",\n"
HYPHEN: str = "-"
DOUBLE_HYPHEN: str = "--"
DOT: str = "."
ASTERISK: str = "*"
DOUBLE_ASTERISK: str = "**"
QUESTION_MARK: str = "?"
CARET: str = "^"
DOLLAR: str = "$"
UNDERSCORE: str = "_"
COLON: str = ":"
SEMICOLON: str = ";"
EQUALS: str = "="
LEFT_PAREN: str = "("
RIGHT_PAREN: str = ")"
BACKTICK: str = "`"
TILDE: str = "~"

MATCH_ALL_REGEX_SINGLE_LINE: str = CARET + DOT + ASTERISK + DOLLAR
MATCH_ALL_REGEX_MULTI_LINE: str = DOT + ASTERISK


DEFAULT_CHUNK_NAME_PREFIX: str = "part"

FILES_TO_IGNORE: str = ["_SUCCESS", ".DS_Store"]

UTF_8: str = "utf-8"

FILE_SIZE_UNITS: Tuple[str, ...] = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
## FILE_SIZE_REGEX taken from: https://rgxdb.com/r/4IG91ZFE
## Matches: "2", "2.5", "2.5b", "2.5B", "2.5k", "2.5K", "2.5kb", "2.5Kb", "2.5KB", "2.5kib", "2.5KiB", "2.5kiB"
## Does not match: "2.", "2ki", "2ib", "2.5KIB"
FILE_SIZE_REGEX = r"^(\d*\.?\d+)((?=[KMGTkgmt])([KMGTkgmt])(?:i?[Bb])?|[Bb]?)$"


_PUNCTUATION_REMOVAL_TABLE = str.maketrans(
    "",
    "",
    string.punctuation,  ## Will be removed
)
_PUNCTUATION_REMOVAL_TABLE_WITH_LOWERCASE = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "abcdefghijklmnopqrstuvwxyz",
    string.punctuation,  ## Will be removed
)
_PUNCTUATION_REMOVAL_TABLE_WITH_SPACE = str.maketrans(
    "",
    "",
    " " + string.punctuation,  ## Will be removed
)
_PUNCTUATION_REMOVAL_TABLE_WITH_LOWERCASE_AND_SPACE = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "abcdefghijklmnopqrstuvwxyz",
    " " + string.punctuation,  ## Will be removed
)

_PUNCTUATION_REMOVAL_TABLE_WITH_NUMBERS = str.maketrans(
    "",
    "",
    "1234567890" + string.punctuation,  ## Will be removed
)
_PUNCTUATION_REMOVAL_TABLE_WITH_LOWERCASE_AND_NUMBERS = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "abcdefghijklmnopqrstuvwxyz",
    "1234567890" + string.punctuation,  ## Will be removed
)
_PUNCTUATION_REMOVAL_TABLE_WITH_SPACE_AND_NUMBERS = str.maketrans(
    "",
    "",
    "1234567890 " + string.punctuation,  ## Will be removed
)
_PUNCTUATION_REMOVAL_TABLE_WITH_LOWERCASE_AND_SPACE_AND_NUMBERS = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "abcdefghijklmnopqrstuvwxyz",
    "1234567890 " + string.punctuation,  ## Will be removed
)


def normalize(
    x: Union[str, AutoEnum],
    *,
    remove: Optional[Union[str, Tuple, List, Set]] = (" ", "-", "_"),
) -> str:
    """
    Normalize a string by removing specified characters and converting to lowercase.

    This function is optimized for performance and found to be faster than .translate()
    and re.sub() on Python 3.10.6+. Useful for creating canonical identifiers,
    comparing strings in a case-insensitive way, or cleaning up user input.

    Args:
        x: The string or AutoEnum to normalize.
        remove: Characters to remove from the string. Can be:
            - str: Single character or string of characters to remove
            - Tuple/List/Set: Collection of characters to remove
            - None: No characters removed (only lowercase)
            Defaults to (" ", "-", "_").

    Returns:
        Normalized string with specified characters removed and converted to lowercase.

    Examples:
        ```python
        # Basic usage
        assert normalize("Hello World") == "helloworld"
        assert normalize("snake_case") == "snakecase"
        assert normalize("kebab-case") == "kebabcase"

        # Custom removal characters
        assert normalize("foo@bar.com", remove=("@", ".")) == "foobarcom"

        # No removal, just lowercase
        assert normalize("CamelCase", remove=None) == "camelcase"

        # With AutoEnum
        from morphic import AutoEnum
        class Color(AutoEnum):
            DARK_BLUE = ()
        assert normalize(Color.DARK_BLUE) == "darkblue"
        ```

    Note:
        This function only removes characters, it does not replace them. Use
        convert_case() if you need to convert between different naming conventions.
    """
    if remove is None:
        remove: Set[str] = set()
    if isinstance(remove, str):
        remove: Set[str] = set(remove)
    if not isinstance(remove, (list, tuple, set)):
        raise TypeError(
            f"Parameter 'remove' must be str, tuple, list, set, or None; found {type(remove).__name__}"
        )
    if len(remove) == 0:
        return str(x).lower()
    out: str = str(x)
    for rem in set(remove).intersection(set(out)):
        out: str = out.replace(rem, "")
    out: str = out.lower()
    return out


def punct_normalize(x: str, *, lowercase: bool = True, space: bool = True, numbers: bool = False) -> str:
    """
    Normalize a string by removing punctuation and optionally spaces/numbers.

    This function uses precomputed translation tables for maximum performance.
    Useful for text processing, search normalization, and creating clean identifiers.

    Args:
        x: The string to normalize.
        lowercase: If True, convert to lowercase. Defaults to True.
        space: If True, remove spaces. Defaults to True.
        numbers: If True, remove numbers (0-9). Defaults to False.

    Returns:
        Normalized string with punctuation removed and optional transformations applied.

    Examples:
        ```python
        # Basic usage - removes punctuation, spaces, and lowercases
        assert punct_normalize("Hello, World!") == "helloworld"

        # Keep spaces
        assert punct_normalize("Hello, World!", space=False) == "hello world"

        # Keep case
        assert punct_normalize("Hello, World!", lowercase=False) == "HelloWorld"

        # Remove numbers too
        assert punct_normalize("abc123def", numbers=True) == "abcdef"

        # Keep everything except punctuation
        assert punct_normalize("Test-123: Done!", lowercase=False, space=False) == "Test123 Done"
        ```

    Note:
        Punctuation is defined by Python's string.punctuation constant:
        !"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~
    """
    if not isinstance(x, str):
        raise TypeError(f"Parameter 'x' must be str; found {type(x).__name__}")
    punct_table = {
        (False, False, False): _PUNCTUATION_REMOVAL_TABLE,
        (True, False, False): _PUNCTUATION_REMOVAL_TABLE_WITH_LOWERCASE,
        (False, True, False): _PUNCTUATION_REMOVAL_TABLE_WITH_SPACE,
        (True, True, False): _PUNCTUATION_REMOVAL_TABLE_WITH_LOWERCASE_AND_SPACE,
        (False, False, True): _PUNCTUATION_REMOVAL_TABLE_WITH_NUMBERS,
        (True, False, True): _PUNCTUATION_REMOVAL_TABLE_WITH_LOWERCASE_AND_NUMBERS,
        (False, True, True): _PUNCTUATION_REMOVAL_TABLE_WITH_SPACE_AND_NUMBERS,
        (True, True, True): _PUNCTUATION_REMOVAL_TABLE_WITH_LOWERCASE_AND_SPACE_AND_NUMBERS,
    }[(lowercase, space, numbers)]
    return x.translate(punct_table)


def whitespace_normalize(text: str, remove_newlines: bool = False) -> str:
    """
    Normalize whitespace in a string by removing extra spaces and newlines.

    This function performs several whitespace cleanup operations:
    - Removes trailing whitespace at the end of each line
    - Collapses multiple consecutive newlines into single newlines (or removes them)
    - Collapses multiple consecutive spaces into single spaces
    - Strips leading/trailing whitespace from the entire string

    Args:
        text: The string to normalize.
        remove_newlines: If True, removes all newlines. If False, collapses
            multiple newlines into single newlines. Defaults to False.

    Returns:
        Normalized string with cleaned up whitespace.

    Examples:
        ```python
        # Basic usage - collapses whitespace
        assert whitespace_normalize("hello    world") == "hello world"
        assert whitespace_normalize("line1\\n\\n\\nline2") == "line1\\nline2"

        # Remove newlines entirely
        assert whitespace_normalize("line1\\nline2", remove_newlines=True) == "line1 line2"

        # Clean up messy text
        messy = "  hello   world  \\n\\n  foo   bar  \\n\\n  "
        clean = whitespace_normalize(messy)
        assert clean == "hello world\\nfoo bar"

        # Trailing whitespace removed from each line
        text = "line1   \\nline2   \\nline3"
        assert whitespace_normalize(text) == "line1\\nline2\\nline3"
        ```

    Note:
        This function is useful for cleaning up text from various sources
        (user input, scraped HTML, log files) before further processing.
    """
    if not isinstance(text, str):
        raise TypeError(f"Parameter 'text' must be str; found {type(text).__name__}")

    ## Remove trailing whitespace at the end of each line
    text: str = re.sub(r"\s+$", "", text, flags=re.MULTILINE)

    if remove_newlines:
        text: str = text.replace("\n", "")
    else:
        ## Replace double newlines with single newlines
        text: str = re.sub(r"\n\n+", "\n", text)

    ## Replace double spaces with single spaces
    text: str = re.sub(r"  +", " ", text)
    return text.strip()


## Taken from: https://github.com/django/django/blob/master/django/utils/baseconv.py#L101
class BaseConverter:
    decimal_digits: str = "0123456789"

    def __init__(self, digits, sign="-"):
        self.sign = sign
        self.digits = digits
        if sign in self.digits:
            raise ValueError("Sign character found in converter base digits.")

    def __repr__(self):
        return "<%s: base%s (%s)>" % (self.__class__.__name__, len(self.digits), self.digits)

    def encode(self, i):
        neg, value = self.convert(i, self.decimal_digits, self.digits, "-")
        if neg:
            return self.sign + value
        return value

    def decode(self, s):
        neg, value = self.convert(s, self.digits, self.decimal_digits, self.sign)
        if neg:
            value = "-" + value
        return int(value)

    def convert(self, number, from_digits, to_digits, sign):
        if str(number)[0] == sign:
            number = str(number)[1:]
            neg = 1
        else:
            neg = 0

        # make an integer out of the number
        x = 0
        for digit in str(number):
            x = x * len(from_digits) + from_digits.index(digit)

        # create the result in base 'len(to_digits)'
        if x == 0:
            res = to_digits[0]
        else:
            res = ""
            while x > 0:
                digit = x % len(to_digits)
                res = to_digits[digit] + res
                x = int(x // len(to_digits))
        return neg, res


BASE2_ALPHABET: str = "01"
BASE16_ALPHABET: str = "0123456789ABCDEF"
BASE56_ALPHABET: str = "23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz"
BASE36_ALPHABET: str = "0123456789abcdefghijklmnopqrstuvwxyz"
BASE62_ALPHABET: str = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
BASE64_ALPHABET: str = BASE62_ALPHABET + "-_"

BASE_CONVERTER_MAP: Dict[int, BaseConverter] = {
    2: BaseConverter(BASE2_ALPHABET),
    16: BaseConverter(BASE16_ALPHABET),
    36: BaseConverter(BASE36_ALPHABET),
    56: BaseConverter(BASE56_ALPHABET),
    62: BaseConverter(BASE62_ALPHABET),
    64: BaseConverter(BASE64_ALPHABET, sign="$"),
}


def hash(
    val: Union[str, int, float, List, Dict],
    *,
    base: int = 62,
) -> str:
    """
    Constructs a hash of a JSON object or value.
    :param val: any valid JSON value (including str, int, float, list, and dict).
    :param base: the base of the output hash.
        Defaults to base56, which encodes the output in a ASCII-chars
    :return: SHA256 hash.
    """
    ## Import here to avoid circular imports.
    from .function import get_fn_spec, is_function

    def _hash_rec(val, base):
        if isinstance(val, (set, frozenset, KeysView)):
            val: List = sorted(list(val))
        if isinstance(val, (list, tuple, ValuesView)):
            return _hash_rec(",".join([_hash_rec(x, base=base) for x in val]), base=base)
        elif isinstance(val, dict):
            return _hash_rec(
                [
                    f"{_hash_rec(k, base=base)}:{_hash_rec(v, base=base)}"
                    for k, v in sorted(val.items(), key=lambda kv: kv[0])
                ],
                base=base,
            )
        elif is_function(val):
            return _hash_rec(get_fn_spec(val, parse_source=True).source_body)
        return _convert_integer_to_base_n_str(int(sha256(str(val).encode("utf8")).hexdigest(), 16), base=base)

    return _hash_rec(val, base)


def _convert_integer_to_base_n_str(integer: int, base: int) -> str:
    assert isinstance(integer, int)
    assert isinstance(base, int) and base in BASE_CONVERTER_MAP, (
        f"Param `base` must be an integer in {list(BASE_CONVERTER_MAP.keys())}; found: {base}"
    )
    return BASE_CONVERTER_MAP[base].encode(integer)


def format_exception_msg(ex: Exception, short: bool = False, prefix: Optional[str] = None) -> str:
    """
    Format exception messages with optional traceback information.

    Provides a utility for formatting exception messages with configurable detail levels
    and optional prefixes. Used internally by Typed for enhanced error reporting.

    Args:
        ex (Exception): The exception to format.
        short (bool, optional): Whether to use short format for traceback.
            Defaults to False (full traceback).
        prefix (Optional[str], optional): Optional prefix to add to the message.
            Defaults to None.

    Returns:
        str: Formatted exception message with traceback information.

    Examples:
        ```python
        try:
            raise ValueError("Something went wrong")
        except Exception as e:
            # Short format
            short_msg = format_exception_msg(e, short=True)
            print(short_msg)
            # "ValueError: 'Something went wrong'\\nTrace: file.py#123; "

            # Full format with prefix
            full_msg = format_exception_msg(e, prefix="Validation Error")
            print(full_msg)
            # "Validation Error: ValueError: 'Something went wrong'\\nTraceback:\\n\\tfile.py line 123, in function..."
        ```

    Note:
        This is primarily an internal utility function used by Typed's error handling.
        Reference: https://stackoverflow.com/a/64212552
    """
    ## Ref: https://stackoverflow.com/a/64212552
    tb = ex.__traceback__
    trace = []
    while tb is not None:
        trace.append(
            {
                "filename": tb.tb_frame.f_code.co_filename,
                "function_name": tb.tb_frame.f_code.co_name,
                "lineno": tb.tb_lineno,
            }
        )
        tb = tb.tb_next
    if prefix is not None:
        out = f'{prefix}: {type(ex).__name__}: "{str(ex)}"'
    else:
        out = f'{type(ex).__name__}: "{str(ex)}"'
    if short:
        out += "\nTrace: "
        for trace_line in trace:
            out += f"{trace_line['filename']}#{trace_line['lineno']}; "
    else:
        out += "\nTraceback:"
        for trace_line in trace:
            out += f"\n\t{trace_line['filename']} line {trace_line['lineno']}, in {trace_line['function_name']}..."
    return out.strip()


def str_format_args(x: str, *, named_only: bool = True) -> List[str]:
    """
    Extract format argument names from a format string.

    Parses a Python format string and returns the list of argument names/indices
    used in the string. Useful for validating format strings, introspection,
    and dynamic template processing.

    Args:
        x: A Python format string (e.g., "Hello {name}, you are {age} years old").
        named_only: If True, only return named arguments (not positional indices).
            Defaults to True.

    Returns:
        List of argument names/indices found in the format string.

    Examples:
        ```python
        # Named arguments
        assert str_format_args("Hello {name}!") == ["name"]
        assert str_format_args("{first} {last}") == ["first", "last"]

        # Positional arguments (with named_only=False)
        assert str_format_args("Hello {0}!", named_only=False) == ["0"]
        assert str_format_args("{0} {1}", named_only=False) == ["0", "1"]

        # Mixed arguments
        assert str_format_args("{0} {name} {1}", named_only=False) == ["0", "name", "1"]
        assert str_format_args("{0} {name} {1}", named_only=True) == ["name"]

        # No arguments
        assert str_format_args("No arguments here") == []

        # Duplicate arguments
        assert str_format_args("{x} and {x}") == ["x", "x"]
        ```

    Note:
        Reference: https://stackoverflow.com/a/46161774/4900327
    """
    if not isinstance(x, str):
        raise TypeError(f"Parameter 'x' must be str; found {type(x).__name__}")
    ## Ref: https://stackoverflow.com/a/46161774/4900327
    args: List[str] = [str(tup[1]) for tup in string.Formatter().parse(x) if tup[1] is not None]
    if named_only:
        args: List[str] = [arg for arg in args if not arg.isdigit() and len(arg) > 0]
    return args


def _assert_not_empty_and_strip(string: str, error_message: str = "") -> str:
    _assert_not_empty(string, error_message)
    return string.strip()


def _is_not_empty(string: str) -> bool:
    return isinstance(string, str) and len(string.strip()) > 0


def is_not_empty_bytes(string: bytes) -> bool:
    """
    Check if a bytes object is not empty (contains non-whitespace content).

    Args:
        string: The bytes object to check.

    Returns:
        True if the bytes object contains non-whitespace content, False otherwise.

    Examples:
        ```python
        assert is_not_empty_bytes(b"hello") is True
        assert is_not_empty_bytes(b"  content  ") is True
        assert is_not_empty_bytes(b"") is False
        assert is_not_empty_bytes(b"   ") is False
        ```
    """
    return isinstance(string, bytes) and len(string.strip()) > 0


def _is_not_empty_str_or_bytes(string: Union[str, bytes]) -> bool:
    return _is_not_empty(string) or is_not_empty_bytes(string)


def is_empty(string: Any) -> bool:
    """
    Check if a string is empty or contains only whitespace.

    Args:
        string: The value to check (typically a string).

    Returns:
        True if the string is empty or contains only whitespace, False otherwise.

    Examples:
        ```python
        assert is_empty("") is True
        assert is_empty("   ") is True
        assert is_empty("hello") is False
        assert is_empty("  hello  ") is False
        assert is_empty(123) is True  # Non-strings are considered empty
        ```

    Note:
        This is the inverse of _is_not_empty(). Non-string types are considered empty.
    """
    return not _is_not_empty(string)


def _is_empty_bytes(string: Any) -> bool:
    return not is_not_empty_bytes(string)


def _is_empty_str_or_bytes(string: Any) -> bool:
    return not _is_not_empty_str_or_bytes(string)


def _assert_not_empty(string: Any, error_message: str = ""):
    assert _is_not_empty(string), error_message


def _assert_not_empty_bytes(string: Any, error_message: str = ""):
    assert _is_not_empty_str_or_bytes(string), error_message


def _assert_not_empty_str_or_bytes(string: Any, error_message: str = ""):
    assert _is_not_empty_str_or_bytes(string), error_message


def is_int(string: Any) -> bool:
    """
    Check if a value can be parsed as an integer.

    Tests whether the input can be successfully converted to an integer using int().
    This function does NOT accept float strings like '123.0' as integers.

    Args:
        string: The value to check (typically a string).

    Returns:
        True if the value can be parsed as an integer, False otherwise.

    Examples:
        ```python
        # Valid integers
        assert is_int("123") is True
        assert is_int("-123") is True
        assert is_int("0") is True

        # Not integers
        assert is_int("123.0") is False  # Has decimal point
        assert is_int("1.23") is False
        assert is_int("-1.23") is False
        assert is_int("1e2") is False  # Scientific notation
        assert is_int("abc") is False
        assert is_int("") is False
        ```

    Note:
        This function accepts any type as input but returns True only for values
        that can be parsed as integers. It does not raise exceptions.
    """
    try:
        int(string)
        return True
    except Exception:
        return False


def is_float(string: Any) -> bool:
    """
    Check if a value can be parsed as a floating-point number.

    Tests whether the input can be successfully converted to a float using float().
    This function accepts integers, decimals, scientific notation, and special
    values like NaN and infinity.

    Args:
        string: The value to check (typically a string).

    Returns:
        True if the value can be parsed as a float, False otherwise.

    Examples:
        ```python
        # Valid floats
        assert is_float("123") is True
        assert is_float("1.23") is True
        assert is_float("123.0") is True
        assert is_float("-123") is True
        assert is_float("-123.0") is True
        assert is_float("1e2") is True
        assert is_float("1.23e-5") is True
        assert is_float("nan") is True
        assert is_float("NAN") is True
        assert is_float("inf") is True
        assert is_float("-inf") is True

        # Not floats
        assert is_float("abc") is False
        assert is_float("") is False
        assert is_float("12.34.56") is False
        ```

    Note:
        This function returns True for special float values like NaN and infinity.
        It accepts any type as input but returns True only for values that can
        be parsed as floats. It does not raise exceptions.
    """
    try:
        float(string)  ## Will return True for NaNs as well.
        return True
    except Exception:
        return False


def join_human(
    l: Union[List, Tuple, Set],
    sep: str = ",",
    final_join: str = "and",
    oxford_comma: bool = False,
) -> str:
    """
    Join a list of items into a human-readable string with proper grammar.

    Creates grammatically correct conjunctions for lists of items, with support
    for Oxford comma style. Useful for generating user-facing messages, error
    messages, and natural language output.

    Args:
        l: A list, tuple, or set of items to join.
        sep: Separator between items (except the last). Defaults to ",".
        final_join: Word to use before the last item. Defaults to "and".
        oxford_comma: If True, uses Oxford comma style (includes separator
            before final_join). Defaults to False.

    Returns:
        A human-readable string with proper grammar.

    Examples:
        ```python
        # Basic usage
        assert join_human(["apple", "banana", "cherry"]) == "apple, banana and cherry"

        # With Oxford comma
        assert join_human(["apple", "banana", "cherry"], oxford_comma=True) == "apple, banana, and cherry"

        # Two items
        assert join_human(["Alice", "Bob"]) == "Alice and Bob"

        # Single item
        assert join_human(["Alice"]) == "Alice"

        # Custom separator and conjunction
        assert join_human([1, 2, 3], sep=";", final_join="or") == "1; 2 or 3"

        # With tuple or set
        assert join_human(("red", "green", "blue")) == "red, green and blue"
        assert "alpha" in join_human({"alpha", "beta", "gamma"})
        ```

    Note:
        Empty lists/sets will return an empty string after stripping.
    """
    if not isinstance(l, (list, tuple, set)):
        raise TypeError(f"Parameter 'l' must be list, tuple, or set; found {type(l).__name__}")
    if not isinstance(sep, str):
        raise TypeError(f"Parameter 'sep' must be str; found {type(sep).__name__}")
    if not isinstance(final_join, str):
        raise TypeError(f"Parameter 'final_join' must be str; found {type(final_join).__name__}")

    l: List = list(l)
    if len(l) == 0:
        return ""
    if len(l) == 1:
        return str(l[0])
    out: str = ""
    for x in l[:-1]:
        out += " " + str(x) + sep
    if not oxford_comma:
        out: str = out.removesuffix(sep)
    x = l[-1]
    out += f" {final_join} " + str(x)
    return out.strip()


def convert_str_to_type(val: str, expected_type: Type) -> Any:
    """
    Convert a string representation to a specific Python type.

    Parses string literals and converts them to the expected Python type.
    Handles automatic type coercion between compatible types (e.g., int to float,
    list to tuple). Useful for parsing configuration files, command-line arguments,
    and user input.

    Args:
        val: String representation of the value to convert.
        expected_type: The target Python type (e.g., int, float, bool, list, dict, etc.).

    Returns:
        The converted value of the expected type.

    Raises:
        ValueError: If the string cannot be converted to the expected type.
        TypeError: If expected_type is not a type object.
        SyntaxError: If the string is not valid Python literal syntax.

    Examples:
        ```python
        # Basic types
        assert convert_str_to_type("123", int) == 123
        assert convert_str_to_type("12.5", float) == 12.5
        assert convert_str_to_type("true", bool) is True
        assert convert_str_to_type("False", bool) is False

        # Collections
        assert convert_str_to_type("[1, 2, 3]", list) == [1, 2, 3]
        assert convert_str_to_type("(1, 2, 3)", tuple) == (1, 2, 3)
        assert convert_str_to_type("{1, 2, 3}", set) == {1, 2, 3}
        assert convert_str_to_type("{'a': 1}", dict) == {'a': 1}

        # Type coercion
        assert convert_str_to_type("5", float) == 5.0  # int to float
        assert convert_str_to_type("5.0", int) == 5    # float to int (if whole number)
        assert convert_str_to_type("[1, 2]", tuple) == (1, 2)  # list to tuple
        assert convert_str_to_type("(1, 2)", list) == [1, 2]   # tuple to list

        # Already correct type
        assert convert_str_to_type("hello", str) == "hello"
        ```

    Note:
        This function uses ast.literal_eval() for safety, so only Python literal
        structures are supported (strings, numbers, tuples, lists, dicts, booleans, None).
        Arbitrary Python expressions are not evaluated.
    """
    if not isinstance(expected_type, type):
        raise TypeError(f"Parameter 'expected_type' must be a type; found {type(expected_type).__name__}")
    if not isinstance(val, str):
        raise TypeError(f"Parameter 'val' must be str; found {type(val).__name__}")

    if isinstance(val, expected_type):
        return val
    if expected_type is str:
        return str(val)
    if expected_type is bool and isinstance(val, str):
        val = val.lower().strip().capitalize()  ## literal_eval does not parse "false", only "False".
    out = literal_eval(_assert_not_empty_and_strip(str(val)))
    if expected_type is float and isinstance(out, int):
        out = float(out)
    if expected_type is int and isinstance(out, float) and int(out) == out:
        out = int(out)
    if expected_type is tuple and isinstance(out, list):
        out = tuple(out)
    if expected_type is list and isinstance(out, tuple):
        out = list(out)
    if expected_type is set and isinstance(out, (list, tuple)):
        out = set(out)
    if expected_type is bool and out in [0, 1]:
        out = bool(out)
    if type(out) is not expected_type:
        raise ValueError(f"Input value {val} cannot be converted to {str(expected_type)}")
    return out


def readable_bytes(size_in_bytes: int, decimals: int = 3) -> str:
    """
    Convert bytes to a human-readable string with appropriate units.

    Automatically selects the most appropriate unit (B, KB, MB, GB, etc.) based
    on the size, choosing the largest unit where the value is >= 1.

    Args:
        size_in_bytes: The size in bytes to format.
        decimals: Number of decimal places to round to. Defaults to 3.

    Returns:
        A formatted string with the size and unit (e.g., "5.2 MB", "1.5 GB").

    Examples:
        ```python
        assert "500" in readable_bytes(500) and "B" in readable_bytes(500)
        assert "KB" in readable_bytes(5000)
        assert "MB" in readable_bytes(5000000)
        assert "GB" in readable_bytes(5000000000)

        # With custom decimals
        result = readable_bytes(1500, decimals=1)
        assert "1.5 KB" in result or "1.465 KB" in result
        ```

    See Also:
        convert_size_from_bytes() for more control over unit selection.
    """
    sizes: Dict[str, float] = convert_size_from_bytes(size_in_bytes, unit=None, decimals=decimals)
    sorted_sizes: List[Tuple[str, float]] = [
        (k, v) for k, v in sorted(sizes.items(), key=lambda item: item[1])
    ]
    size_unit, size_val = None, None
    for size_unit, size_val in sorted_sizes:
        if size_val >= 1:
            break
    return f"{size_val} {size_unit}"


def convert_size_from_bytes(
    size_in_bytes: int,
    unit: Optional[str] = None,
    decimals: int = 3,
) -> Union[Dict, float]:
    """
    Convert bytes to various size units.

    Converts a byte count to all standard size units (B, KB, MB, GB, TB, PB, EB, ZB, YB).
    Can return all conversions or a specific unit.

    Args:
        size_in_bytes: The size in bytes to convert.
        unit: If specified, returns only this unit. Must be one of FILE_SIZE_UNITS.
            If None, returns a dict with all units. Defaults to None.
        decimals: Number of decimal places to round to. Defaults to 3.

    Returns:
        If unit is None: Dict mapping unit names to converted values.
        If unit is specified: Float value in that unit.

    Examples:
        ```python
        # Get all conversions
        sizes = convert_size_from_bytes(1024)
        assert sizes["B"] == 1024.0
        assert sizes["KB"] == 1.0

        # Get specific unit
        kb_size = convert_size_from_bytes(2048, unit="KB")
        assert kb_size == 2.0

        # Larger sizes
        sizes = convert_size_from_bytes(1024 * 1024 * 1024)  # 1 GB
        assert sizes["GB"] == 1.0
        ```

    Note:
        Conversion uses 1024-based units (binary), not 1000-based (decimal).
    """
    size_in_bytes = float(size_in_bytes)
    cur_size = size_in_bytes
    sizes = {}
    if size_in_bytes == 0:
        for size_name in FILE_SIZE_UNITS:
            sizes[size_name] = 0.0
    else:
        for size_name in FILE_SIZE_UNITS:
            val: float = round(cur_size, decimals)
            i = 1
            while val == 0:
                val = round(cur_size, decimals + i)
                i += 1
            sizes[size_name] = val
            i = int(math.floor(math.log(cur_size, 1024)))
            cur_size = cur_size / 1024
    if unit is not None:
        assert isinstance(unit, str)
        unit = unit.upper()
        assert unit in FILE_SIZE_UNITS
        return sizes[unit]
    return sizes


def convert_size_to_bytes(size_in_human_readable: str) -> int:
    """
    Parse a human-readable size string and convert to bytes.

    Accepts strings like "1 KB", "5.5 MB", "2GB" and converts them to bytes.
    Case-insensitive and spaces are optional.

    Args:
        size_in_human_readable: Size string with value and unit (e.g., "5 MB", "1.5GB").

    Returns:
        Size in bytes as an integer.

    Raises:
        ValueError: If the string format is invalid or unit is unrecognized.

    Examples:
        ```python
        assert convert_size_to_bytes("1 KB") == 1024
        assert convert_size_to_bytes("1 MB") == 1024 * 1024
        assert convert_size_to_bytes("1.5 KB") == int(1.5 * 1024)

        # Case insensitive
        assert convert_size_to_bytes("5 kb") == 5 * 1024
        assert convert_size_to_bytes("5KB") == 5 * 1024

        # Various formats
        assert convert_size_to_bytes("2 GB") == 2 * 1024 * 1024 * 1024
        assert convert_size_to_bytes("500 B") == 500
        ```

    Note:
        Uses 1024-based units (binary), not 1000-based (decimal).
    """
    size_in_human_readable: str = _assert_not_empty_and_strip(size_in_human_readable).upper()
    size_selection_regex = rf"""(\d+(?:\.\d+)?) *({PIPE.join(FILE_SIZE_UNITS)})"""  ## This uses a non-capturing group: https://stackoverflow.com/a/3512530/4900327
    matches = re.findall(size_selection_regex, size_in_human_readable)
    if len(matches) != 1 or len(matches[0]) != 2:
        raise ValueError(f'Cannot convert value "{size_in_human_readable}" to bytes.')
    val, unit = matches[0]
    val = float(val)
    for file_size_unit in FILE_SIZE_UNITS:
        if unit == file_size_unit:
            return int(round(val))
        val = val * 1024
    raise ValueError(f'Cannot convert value "{size_in_human_readable}" to bytes.')


def readable_seconds(
    time_in_seconds: Union[float, timedelta],
    *,
    decimals: int = 2,
    short: bool = False,
) -> str:
    """
    Convert seconds to a human-readable time string with appropriate units.

    Automatically selects the most appropriate time unit (ns, us, ms, s, min, hr, d)
    based on the duration, choosing the largest unit where the value is >= 1.

    Args:
        time_in_seconds: Time duration in seconds, or a timedelta object.
        decimals: Number of decimal places to round to. Defaults to 2.
        short: If True, uses short unit names (e.g., "s", "min", "hr").
            If False, uses long unit names (e.g., "seconds", "mins", "hours").
            Defaults to False.

    Returns:
        A formatted string with the time and unit (e.g., "5.2 seconds", "3 mins", "1.5 hr").

    Examples:
        ```python
        assert "5" in readable_seconds(5) and "s" in readable_seconds(5)
        assert "min" in readable_seconds(120, short=True) or "mins" in readable_seconds(120)
        assert "hr" in readable_seconds(7200, short=True) or "hours" in readable_seconds(7200)

        # With timedelta
        from datetime import timedelta
        td = timedelta(seconds=30)
        result = readable_seconds(td)
        assert "30" in result

        # Short format
        assert readable_seconds(5, short=True) in ["5.0s", "5s"]
        ```

    See Also:
        convert_time_from_seconds() for more control over unit selection.
    """
    if isinstance(time_in_seconds, timedelta):
        time_in_seconds: float = time_in_seconds.total_seconds()
    times: Dict[str, float] = convert_time_from_seconds(
        time_in_seconds,
        unit=None,
        decimals=decimals,
        short=short,
    )
    sorted_times: List[Tuple[str, float]] = [
        (k, v) for k, v in sorted(times.items(), key=lambda item: item[1])
    ]
    time_unit, time_val = None, None
    for time_unit, time_val in sorted_times:
        if time_val >= 1:
            break
    if decimals <= 0:
        time_val = int(time_val)
    if short:
        return f"{time_val}{time_unit}"
    return f"{time_val} {time_unit}"


def convert_time_from_seconds(
    time_in_seconds: float,
    unit: Optional[str] = None,
    decimals: int = 3,
    short: bool = False,
) -> Union[Dict, float]:
    """
    Convert seconds to various time units.

    Converts a duration in seconds to all standard time units (nanoseconds, microseconds,
    milliseconds, seconds, mins, hours, days). Can return all conversions or a specific unit.

    Args:
        time_in_seconds: The duration in seconds to convert.
        unit: If specified, returns only this unit (e.g., "mins", "hours").
            If None, returns a dict with all units. Defaults to None.
        decimals: Number of decimal places to round to. Defaults to 3.
        short: If True, uses short unit names in the returned dict keys
            (e.g., "s", "min", "hr"). If False, uses long names
            (e.g., "seconds", "mins", "hours"). Defaults to False.

    Returns:
        If unit is None: Dict mapping unit names to converted values.
        If unit is specified: Float value in that unit.

    Examples:
        ```python
        # Get all conversions
        times = convert_time_from_seconds(60)
        assert times["seconds"] == 60.0
        assert times["mins"] == 1.0

        # Get specific unit
        mins = convert_time_from_seconds(120, unit="mins")
        assert mins == 2.0

        # Short format
        times = convert_time_from_seconds(5, short=True)
        assert "s" in times
        assert "ms" in times
        assert times["s"] == 5.0
        assert times["ms"] == 5000.0
        ```

    Note:
        Unit names are case-insensitive when requesting a specific unit.
    """
    TIME_UNITS = {
        "nanoseconds": 1e-9,
        "microseconds": 1e-6,
        "milliseconds": 1e-3,
        "seconds": 1.0,
        "mins": 60,
        "hours": 60 * 60,
        "days": 24 * 60 * 60,
    }
    if short:
        TIME_UNITS = {
            "ns": 1e-9,
            "us": 1e-6,
            "ms": 1e-3,
            "s": 1.0,
            "min": 60,
            "hr": 60 * 60,
            "d": 24 * 60 * 60,
        }
    time_in_seconds = float(time_in_seconds)
    times: Dict[str, float] = {
        time_unit: round(time_in_seconds / TIME_UNITS[time_unit], decimals) for time_unit in TIME_UNITS
    }
    if unit is not None:
        assert isinstance(unit, str)
        unit = unit.lower()
        assert unit in TIME_UNITS
        return times[unit]
    return times


def readable_number(
    n: Union[float, int],
    decimals: int = 3,
    short: bool = True,
    scientific: bool = False,
) -> str:
    """
    Convert a number to a human-readable string with appropriate unit suffix.

    Automatically formats large numbers with unit suffixes (K, M, B, T, etc.) or
    uses scientific notation for small numbers. Useful for displaying statistics,
    counts, and metrics in a compact, readable format.

    Args:
        n: The number to format (positive or negative).
        decimals: Number of decimal places to round to. Defaults to 3.
        short: If True, uses short unit names (e.g., "K", "M", "B").
            If False, uses long unit names (e.g., "thousand", "million", "billion").
            Defaults to True.
        scientific: If True, forces scientific notation. If False, automatically
            uses scientific notation for numbers with 0 < abs(n) < 1.
            Defaults to False.

    Returns:
        A formatted string with the number and unit suffix (e.g., "1K", "5.2M", "3B").

    Examples:
        ```python
        # Large numbers with short units
        assert readable_number(1000, short=True) == "1K"
        assert readable_number(1000000, short=True) == "1M"
        assert readable_number(1000000000, short=True) == "1B"

        # Long format
        assert readable_number(1000, short=False) == "1 thousand"
        assert readable_number(1000000, short=False) == "1 million"

        # Small numbers use scientific notation
        result = readable_number(0.00123)
        assert "e" in result

        # Zero
        assert readable_number(0) == "0"

        # Negative numbers
        result = readable_number(-1500, short=True)
        assert "-" in result and ("1.5K" in result or "1500" in result)
        ```

    See Also:
        convert_number() for more control over unit selection.
    """
    if n == 0:
        return "0"
    assert abs(n) > 0
    if 0 < abs(n) < 1:
        scientific: bool = True
    if scientific:
        n_unit: str = ""
        n_val: str = f"{n:.{decimals}e}"
    else:
        numbers: Dict[str, float] = convert_number(
            abs(n),
            unit=None,
            decimals=decimals,
            short=short,
        )
        sorted_numbers: List[Tuple[str, float]] = [
            (k, v) for k, v in sorted(numbers.items(), key=lambda item: item[1])
        ]
        n_unit: Optional[str] = None
        n_val: Optional[float] = None
        for n_unit, n_val in sorted_numbers:
            if n_val >= 1:
                break
        if decimals <= 0:
            n_val: int = int(n_val)
        if n_val == int(n_val):
            n_val: int = int(n_val)
    if n < 0:
        n_val: str = f"-{n_val}"
    if short:
        return f"{n_val}{n_unit}".strip()
    return f"{n_val} {n_unit}".strip()


def convert_number(
    n: float,
    unit: Optional[str] = None,
    decimals: int = 3,
    short: bool = False,
) -> Union[Dict, float]:
    """
    Convert a number to various magnitude units.

    Converts a number to units like thousand, million, billion, etc. (or their
    short forms K, M, B). Can return all conversions or a specific unit.

    Args:
        n: The number to convert. Must be non-negative.
        unit: If specified, returns only this unit (e.g., "K", "million").
            If None, returns a dict with all units. Defaults to None.
        decimals: Number of decimal places to round to. Defaults to 3.
        short: If True, uses short unit names in the returned dict keys
            (e.g., "K", "M", "B"). If False, uses long names
            (e.g., "thousand", "million", "billion"). Defaults to False.

    Returns:
        If unit is None: Dict mapping unit names to converted values.
        If unit is specified: Float value in that unit.

    Examples:
        ```python
        # Get all conversions
        numbers = convert_number(1000000, short=True)
        assert numbers["M"] == 1.0
        assert numbers["K"] == 1000.0

        # Get specific unit
        millions = convert_number(5000000, unit="M", short=True)
        assert millions == 5.0

        # Long format
        numbers = convert_number(1000, short=False)
        assert "thousand" in numbers
        assert numbers["thousand"] == 1.0

        # Base unit (no suffix)
        numbers = convert_number(500, short=True)
        assert numbers[""] == 500.0  # Base unit has empty string key
        ```

    Raises:
        AssertionError: If n is negative.

    Note:
        The function requires n >= 0. Use abs(n) if you need to handle negative numbers.
    """
    assert n >= 0
    N_UNITS = {
        "": 1e0,
        "thousand": 1e3,
        "million": 1e6,
        "billion": 1e9,
        "trillion": 1e12,
        "quadrillion": 1e15,
        "quintillion": 1e18,
    }
    if short:
        N_UNITS = {
            "": 1e0,
            "K": 1e3,
            "M": 1e6,
            "B": 1e9,
            "T": 1e12,
            "Qa": 1e15,
            "Qi": 1e18,
        }
    n: float = float(n)
    numbers: Dict[str, float] = {n_unit: round(n / N_UNITS[n_unit], decimals) for n_unit in N_UNITS}
    if unit is not None:
        assert isinstance(unit, str)
        unit = unit.lower()
        assert unit in N_UNITS
        return numbers[unit]
    return numbers


def detect_case(
    s: str,
) -> Literal["snake", "screaming_snake", "kebab", "train", "camel", "pascal", "studly"]:
    """
    Detects the case of the input literal name.

    Returns:
        One of:
            - 'snake' for snake_case,
            - 'screaming_snake' for SCREAMING_SNAKE_CASE,
            - 'kebab' for kebab-case,
            - 'train' for TRAIN-CASE,
            - 'camel' for camelCase,
            - 'pascal' for PascalCase.
            - 'studly' for StUDlyCaSe

    Raises:
        ValueError: If the input string is empty, contains unsupported characters,
                    or uses mixed delimiters.
    """
    if len(s.strip()) == 0:
        raise ValueError("Empty string cannot be detected as a standard case for literal names.")

    # Early check: ensure string contains only allowed characters.
    if not re.fullmatch(r"[A-Za-z0-9_-]+", s):
        raise ValueError(
            f"String '{s}' contains unsupported characters in a literal name. "
            f"Only letters, digits, underscores, and hyphens are allowed."
        )
    if "-" in s and "_" in s:
        raise ValueError(
            f"String '{s}' contains mixed delimiters and is not a standard case format for literal names."
        )

    # If underscores are present, assume snake_case or screaming_snake.
    elif "_" in s:
        # Determine if the string is all uppercase (screaming snake) or not.
        if s.upper() == s:
            return "screaming_snake"  ## SCREAMING_SNAKE_CASE
        elif s.lower() == s:
            return "snake"  ## snake_case
        raise ValueError(
            f"String '{s}' contains both underscores and a combination of uppercase "
            f"and lowercase, which is not a standard case format for literal names."
        )

    # If hyphens are present, assume kebab-case.
    elif "-" in s:
        # Determine if the string is all uppercase (screaming snake) or not.
        if s.upper() == s:
            return "train"  ## TRAIN-CASE
        elif s.lower() == s:
            return "kebab"  ## kebab-case
        raise ValueError(
            f"String '{s}' contains both hyphens and a combination of uppercase "
            f"and lowercase, which is not a standard case format for literal names."
        )
    else:
        # For strings without delimiters, assume camelCase or PascalCase.
        if s[0].islower():
            return "camel"  ## camelCase
        elif s[0].isupper():
            return "pascal"  ## PascalCase
        else:
            return "studly"  ## StUDlyCaSe, sTuDlYCaSE, etc

    raise ValueError(f"String '{s}' does not match any of the supported case formats for literal names.")


def convert_case(
    s: str,
    target_case: Literal[
        "upper",
        "lower",
        "snake",
        "screaming_snake",
        "kebab",
        "train",
        "camel",
        "pascal",
        "studly",
    ],
) -> list:
    """
    Convert a string from one case format to another.

    This function detects the source case format automatically and converts
    the string to the specified target case format.

    Supported case formats:
        - 'snake': snake_case (words separated by underscores, all lowercase)
        - 'screaming_snake': SCREAMING_SNAKE_CASE (words separated by underscores, all uppercase)
        - 'kebab': kebab-case (words separated by hyphens, all lowercase)
        - 'train': TRAIN-CASE (words separated by hyphens, all uppercase)
        - 'camel': camelCase (no separators, first word lowercase, subsequent words capitalized)
        - 'pascal': PascalCase (no separators, all words capitalized)

    Args:
        s: The input string to convert
        target_case: The target case format to convert to

    Returns:
        The converted string in the target case format

    Raises:
        ValueError: If the source case cannot be detected or if the target case is unsupported

    Examples:
        >>> assert convert_case("CachedResultsStep", "kebab") == "cached-results-step"
        >>> assert convert_case("cachedResultsStep", "snake") == "cached_results_step"
        >>> assert convert_case("cached_results_step", "pascal") == "CachedResultsStep"
        >>> assert convert_case("cached-results-step", "camel") == "cachedResultsStep"
        >>> assert convert_case("CACHED_RESULTS_STEP", "camel") == "cachedResultsStep"
        >>> assert convert_case("Test123Case", "snake") == "test_123_case"
        >>> assert convert_case("another_test_case", "kebab") == "another-test-case"
    """
    target_case: str = (
        target_case.lower()
        .strip()
        .replace(" ", "_")
        .replace("-", "_")
        .removesuffix("_")
        .removesuffix("case")
        .removesuffix("_")
    )
    if target_case == "upper":
        return s.upper()
    elif target_case == "lower":
        return s.lower()
    source_case: str = detect_case(s)
    if source_case in ("snake", "screaming_snake"):
        words: List[str] = s.split("_")
    elif source_case in {"kebab", "train"}:
        words: List[str] = s.split("-")
    elif source_case in ("camel", "pascal"):
        # Regex handles:
        #  - Acronyms (e.g. "HTML"),
        #  - Normal words,
        #  - Numbers.
        words: List[str] = re.findall(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+", s)
    elif source_case == "studly":
        raise ValueError(
            "Due to its lack of standardization, it is not possible to convert from studly case yet."
        )
    else:
        raise ValueError(f"Unsupported input case: '{source_case}'")

    if target_case == "snake":
        return "_".join(word.lower() for word in words)
    elif target_case == "screaming_snake":
        return "_".join(word.upper() for word in words)
    elif target_case == "kebab":
        return "-".join(word.lower() for word in words)
    elif target_case == "train":
        return "-".join(word.lower() for word in words)
    elif target_case == "camel":
        if len(words) == 0:
            return ""
        return words[0].lower() + "".join(word.capitalize() for word in words[1:])
    elif target_case == "pascal":
        return "".join(word.capitalize() for word in words)
    elif target_case == "studly":
        return "".join(c.lower() if random.random() <= 0.5 else c.upper() for c in s)
    else:
        raise ValueError(f"Unsupported target case: '{target_case}'")


def get_num_zeros_to_pad(max_i: int) -> int:
    """
    Calculate the number of digits needed to pad numbers up to max_i.

    Determines how many digits are required to represent the largest number
    in a sequence, useful for creating zero-padded filenames, IDs, or indices
    that sort correctly.

    Args:
        max_i: The maximum integer value that needs to be represented.
            Must be >= 1.

    Returns:
        Number of digits needed for zero-padding.

    Examples:
        ```python
        # For numbers 1-99
        assert get_num_zeros_to_pad(99) == 2

        # For numbers 1-100
        assert get_num_zeros_to_pad(100) == 3

        # For numbers 1-999
        assert get_num_zeros_to_pad(999) == 3

        # For numbers 1-1000
        assert get_num_zeros_to_pad(1000) == 4

        # Single digit
        assert get_num_zeros_to_pad(9) == 1
        assert get_num_zeros_to_pad(10) == 2
        ```

    Note:
        Reference: https://stackoverflow.com/a/51837162/4900327
    """
    if not isinstance(max_i, int):
        raise TypeError(f"Parameter 'max_i' must be int; found {type(max_i).__name__}")
    if max_i < 1:
        raise ValueError(f"Parameter 'max_i' must be >= 1; found {max_i}")

    num_zeros = math.ceil(math.log10(max_i))  ## Ref: https://stackoverflow.com/a/51837162/4900327
    if max_i == 10**num_zeros:  ## If it is a power of 10
        num_zeros += 1
    return num_zeros


def zfill(i: int, max_i: int = int(1e12)) -> str:
    """
    Zero-pad an integer based on the maximum value in the sequence.

    Creates a zero-padded string representation of an integer, with padding
    length determined by the maximum value. Ensures all numbers in a sequence
    have the same width, which is important for lexicographic sorting.

    Args:
        i: The integer to zero-pad. Must be >= 0.
        max_i: The maximum integer in the sequence. Must be >= i.
            Defaults to 1 trillion (1e12).

    Returns:
        Zero-padded string representation of the integer.

    Examples:
        ```python
        # Basic usage - padding for numbers up to 999
        assert zfill(5, 999) == "005"
        assert zfill(42, 999) == "042"
        assert zfill(999, 999) == "999"

        # Padding for numbers up to 100
        assert zfill(1, 100) == "001"
        assert zfill(99, 100) == "099"
        assert zfill(100, 100) == "100"

        # Creating sorted filenames
        for i in range(10):
            filename = f"file_{zfill(i, 100)}.txt"
            # Results in: file_000.txt, file_001.txt, ..., file_009.txt

        # With default max (1 trillion)
        assert len(zfill(1)) == 13  # Padded to 13 digits
        ```

    Raises:
        TypeError: If i or max_i are not integers.
        ValueError: If i < 0 or max_i < i.

    Note:
        This is particularly useful for creating filenames that sort correctly
        in file explorers and when globbing files.
    """
    if not isinstance(i, int):
        raise TypeError(f"Parameter 'i' must be int; found {type(i).__name__}")
    if not isinstance(max_i, int):
        raise TypeError(f"Parameter 'max_i' must be int; found {type(max_i).__name__}")
    if i < 0:
        raise ValueError(f"Parameter 'i' must be >= 0; found {i}")
    if max_i < i:
        raise ValueError(f"Expected max_i to be >= current i; found max_i={max_i}, i={i}")

    num_zeros: int = get_num_zeros_to_pad(max_i)
    return f"{i:0{num_zeros}}"


def random_name(
    count: int = 1,
    *,
    sep: str = HYPHEN,
    order: Tuple[str, ...] = ("adjective", "verb", "noun"),
    seed: Optional[int] = None,
) -> Union[List[str], str]:
    """
    Generate random human-readable names from word combinations.

    Creates memorable random names by combining adjectives, verbs, and nouns
    (e.g., "quick-running-fox", "happy-jumping-dog"). Useful for generating
    unique identifiers, test data, project names, or placeholder names.

    Args:
        count: Number of random names to generate. Defaults to 1.
        sep: Separator between words. Defaults to "-" (hyphen).
        order: Tuple specifying the order and types of words to combine.
            Each element must be "adjective", "verb", or "noun".
            Defaults to ("adjective", "verb", "noun").
        seed: Random seed for reproducible results. Defaults to None (random).

    Returns:
        If count == 1, returns a single string.
        If count > 1, returns a list of strings.

    Raises:
        NotImplementedError: If order contains an unrecognized word type.
        ValueError: If count exceeds the number of possible combinations.
        TypeError: If parameters have incorrect types.

    Examples:
        ```python
        # Generate single name
        name = random_name()  # e.g., "happy-running-dog"

        # Generate multiple names
        names = random_name(3)  # e.g., ["quick-jumping-fox", "lazy-sleeping-cat", ...]

        # Custom separator
        name = random_name(sep="_")  # e.g., "brave_flying_eagle"

        # Custom order
        name = random_name(order=("adjective", "noun"))  # e.g., "blue-sky"
        name = random_name(order=("verb", "noun"))  # e.g., "running-tiger"

        # Reproducible with seed
        name1 = random_name(seed=42)
        name2 = random_name(seed=42)
        assert name1 == name2

        # Multiple with seed
        names = random_name(5, seed=123)  # Always generates same 5 names
        ```

    Note:
        The function ensures all generated names in a batch are unique.
        Maximum possible combinations depends on the word lists and order.
    """
    if not isinstance(count, int):
        raise TypeError(f"Parameter 'count' must be int; found {type(count).__name__}")
    if count < 1:
        raise ValueError(f"Parameter 'count' must be >= 1; found {count}")
    if not isinstance(sep, str):
        raise TypeError(f"Parameter 'sep' must be str; found {type(sep).__name__}")
    if not isinstance(order, (tuple, list)):
        raise TypeError(f"Parameter 'order' must be tuple or list; found {type(order).__name__}")
    if len(order) == 0:
        raise ValueError("Parameter 'order' must have at least one element")

    cartesian_product_parts: List[List[str]] = []
    for order_part in order:
        if order_part == "verb":
            cartesian_product_parts.append(RANDOM_VERBS)
        elif order_part == "adjective":
            cartesian_product_parts.append(RANDOM_ADJECTIVES)
        elif order_part == "noun":
            cartesian_product_parts.append(RANDOM_NOUNS)
        else:
            raise NotImplementedError(f'Unrecognized part of the order sequence: "{order_part}"')

    out: List[str] = [
        sep.join(parts) for parts in _random_cartesian_product(*cartesian_product_parts, seed=seed, n=count)
    ]
    if count == 1:
        return out[0]
    return out


def _random_cartesian_product(*lists, seed: Optional[int] = None, n: int):
    rnd = random.Random(seed)
    cartesian_idxs: Set[Tuple[int, ...]] = set()
    list_lens: List[int] = [len(l) for l in lists]
    max_count: int = 1
    for l_len in list_lens:
        max_count *= l_len
    if max_count < n:
        raise ValueError(f"At most {max_count} cartesian product elements can be created.")
    while len(cartesian_idxs) < n:
        rnd_idx: Tuple[int, ...] = tuple(rnd.randint(0, l_len - 1) for l_len in list_lens)
        if rnd_idx not in cartesian_idxs:
            cartesian_idxs.add(rnd_idx)
            elem = []
            for l_idx, l in zip(rnd_idx, lists):
                elem.append(l[l_idx])
            yield elem


def parse_datetime(dt: Union[str, int, float, datetime]) -> datetime:
    """
    Parse various datetime representations into a datetime object.

    Accepts multiple input formats and normalizes them to Python datetime objects.
    Useful for handling datetime inputs from various sources (APIs, databases, user input).

    Args:
        dt: The datetime to parse. Can be:
            - datetime object (returned as-is)
            - int/float (interpreted as Unix timestamp)
            - str (parsed as ISO format string)

    Returns:
        A datetime object.

    Raises:
        NotImplementedError: If the input type is not supported.
        ValueError: If the string format is invalid.

    Examples:
        ```python
        from datetime import datetime

        # datetime object (pass-through)
        dt = datetime.now()
        assert parse_datetime(dt) == dt

        # Unix timestamp (int)
        assert parse_datetime(1609459200).year == 2021

        # Unix timestamp (float with microseconds)
        assert parse_datetime(1609459200.5).microsecond > 0

        # ISO format string
        dt = parse_datetime("2021-01-01T00:00:00")
        assert dt.year == 2021 and dt.month == 1

        # ISO format with timezone
        dt = parse_datetime("2021-01-01T00:00:00+00:00")
        assert dt.tzinfo is not None
        ```

    Note:
        String parsing uses datetime.fromisoformat(), which supports
        ISO 8601 format: "YYYY-MM-DD[T]HH:MM:SS[.ffffff][+HH:MM]"
    """
    if isinstance(dt, datetime):
        return dt
    elif type(dt) in [int, float]:
        return datetime.fromtimestamp(dt)
    elif isinstance(dt, str):
        return datetime.fromisoformat(dt)
    raise NotImplementedError(f"Cannot parse datetime from value {dt} with type {type(dt)}")


def now(**kwargs) -> str:
    """
    Get the current datetime as a formatted string.

    Convenience function that combines datetime.now() with readable_datetime().

    Args:
        **kwargs: Passed to readable_datetime(). Supports:
            - human (bool): Human-readable format
            - microsec (bool): Include microseconds
            - tz (bool): Include timezone

    Returns:
        Formatted string representation of the current datetime.

    Examples:
        ```python
        # Default format (ISO 8601 with microseconds and timezone)
        # "2021-01-01T12:30:45.123456+00:00"
        current = now()

        # Human-readable format
        # "01Jan2021-12:30:45+UTC"
        current = now(human=True)

        # Without microseconds
        # "2021-01-01T12:30:45+00:00"
        current = now(microsec=False)

        # Without timezone
        # "2021-01-01T12:30:45.123456"
        current = now(tz=False)
        ```

    See Also:
        readable_datetime() for full formatting options.
    """
    dt: datetime = datetime.now()
    return readable_datetime(dt, **kwargs)


def readable_datetime(
    dt: datetime,
    *,
    human: bool = False,
    microsec: bool = True,
    tz: bool = True,
) -> str:
    """
    Format a datetime object as a readable string.

    Provides flexible datetime formatting with options for human-readable
    output, microsecond precision, and timezone information. Useful for
    logging, timestamps, and displaying dates to users.

    Args:
        dt: The datetime object to format.
        human: If True, uses human-readable format (e.g., "01Jan2021-12:30:45").
            If False, uses ISO 8601 format. Defaults to False.
        microsec: If True, includes microseconds. Automatically False when
            human=True. Defaults to True.
        tz: If True, includes timezone information. Defaults to True.

    Returns:
        Formatted datetime string.

    Examples:
        ```python
        from datetime import datetime

        dt = datetime(2021, 1, 15, 14, 30, 45, 123456)

        # Default: ISO 8601 with microseconds and timezone
        # "2021-01-15T14:30:45.123456+00:00"
        assert readable_datetime(dt).startswith("2021-01-15T14:30:45")

        # Human-readable format
        # "15Jan2021-14:30:45+UTC"
        readable_datetime(dt, human=True)

        # Without microseconds
        # "2021-01-15T14:30:45+00:00"
        readable_datetime(dt, microsec=False)

        # Without timezone
        # "2021-01-15T14:30:45.123456"
        readable_datetime(dt, tz=False)

        # Human without timezone
        # "15Jan2021-14:30:45"
        readable_datetime(dt, human=True, tz=False)
        ```

    Note:
        When human=True, microsec is automatically set to False.
        The timezone is automatically determined from the datetime object.
    """
    dt: datetime = dt.replace(tzinfo=dt.astimezone().tzinfo)
    if human:
        format_str: str = "%d%b%Y-%H:%M:%S"
        microsec: bool = False
    else:
        format_str: str = "%Y-%m-%dT%H:%M:%S"
    if microsec:
        format_str += ".%f"
    split_tz_colon: bool = False
    if tz and dt.tzinfo is not None:
        if human:
            format_str += "+%Z"
        else:
            format_str += "%z"
            split_tz_colon: bool = True
    out: str = dt.strftime(format_str).strip()
    if split_tz_colon:  ## Makes the output exactly like dt.isoformat()
        out: str = out[:-2] + ":" + out[-2:]
    return out


def fuzzy_match(
    string: str,
    strings_to_match: Union[str, List[str]],
    *,
    replacements: Tuple[str, ...] = (SPACE, HYPHEN, SLASH),
    repl_char: str = UNDERSCORE,
) -> Optional[str]:
    """
    Find a fuzzy match for a string from a list of candidates.

    Performs case-insensitive matching with character replacements to handle
    different naming conventions (e.g., "my_file", "my-file", "my file" all match).
    Returns the original string from the list if matched, or None if no match found.

    Args:
        string: The string to match.
        strings_to_match: A string or list of strings to search through.
        replacements: Characters to normalize (replace with repl_char) before matching.
            Defaults to (SPACE, HYPHEN, SLASH) = (" ", "-", "/").
        repl_char: Character to use as replacement. Defaults to "_" (underscore).

    Returns:
        The original matching string from strings_to_match, or None if no match.

    Examples:
        ```python
        # Basic matching with different delimiters
        assert fuzzy_match("my_file", ["my-file", "other"]) == "my-file"
        assert fuzzy_match("my-file", ["my_file", "other"]) == "my_file"
        assert fuzzy_match("my file", ["my_file", "other"]) == "my_file"

        # Case-insensitive
        assert fuzzy_match("MyFile", ["my_file"]) == "my_file"
        assert fuzzy_match("MY-FILE", ["my_file"]) == "my_file"

        # No match
        assert fuzzy_match("notfound", ["my_file", "other"]) is None

        # Single string (not a list)
        assert fuzzy_match("my_file", "my-file") == "my-file"
        assert fuzzy_match("wrong", "my-file") is None

        # Custom replacements
        assert fuzzy_match("a.b.c", ["a_b_c"], replacements=(".",)) == "a_b_c"
        ```

    Note:
        This function is useful for matching configuration keys, command names,
        or filenames where users might use different conventions.
    """
    if not isinstance(strings_to_match, (list, tuple)):
        if not isinstance(strings_to_match, str):
            raise TypeError(
                f"Parameter 'strings_to_match' must be str, list, or tuple; "
                f"found {type(strings_to_match).__name__}"
            )
        strings_to_match: List[str] = [strings_to_match]
    if not isinstance(string, str):
        raise TypeError(f"Parameter 'string' must be str; found {type(string).__name__}")

    string: str = str(string).lower()
    strings_to_match_repl: List[str] = [str(s).lower() for s in strings_to_match]
    for repl in replacements:
        string: str = string.replace(repl, repl_char)
        strings_to_match_repl: List[str] = [s.replace(repl, repl_char) for s in strings_to_match_repl]
    for i, s in enumerate(strings_to_match_repl):
        if string == s:
            return strings_to_match[i]
    return None


def is_fuzzy_match(string: str, strings_to_match: Union[str, List[str]]) -> bool:
    """
    Check if a string has a fuzzy match in a list of candidates.

    Convenience function that returns True if fuzzy_match() finds a match,
    False otherwise. Useful for validation and conditional logic.

    Args:
        string: The string to check.
        strings_to_match: A string or list of strings to search through.

    Returns:
        True if a fuzzy match is found, False otherwise.

    Examples:
        ```python
        # Has match
        assert is_fuzzy_match("my_file", ["my-file", "other"]) is True
        assert is_fuzzy_match("MY-FILE", ["my_file"]) is True

        # No match
        assert is_fuzzy_match("notfound", ["my_file", "other"]) is False

        # Validation example
        valid_options = ["enable", "disable", "auto"]
        user_input = "en-able"
        if is_fuzzy_match(user_input, valid_options):
            matched = fuzzy_match(user_input, valid_options)
            print(f"Matched: {matched}")
        ```

    See Also:
        fuzzy_match() for getting the actual matched string.
    """
    return fuzzy_match(string, strings_to_match) is not None


def is_stream(obj) -> bool:
    """
    Check if an object is a file-like stream.

    Determines whether an object is a readable stream (file object, StringIO, etc.)
    by checking if it inherits from io.IOBase and has a read() method.

    Args:
        obj: The object to check.

    Returns:
        True if the object is a readable stream, False otherwise.

    Examples:
        ```python
        import io

        # File object
        with open("file.txt", "r") as f:
            assert is_stream(f) is True

        # StringIO
        stream = io.StringIO("content")
        assert is_stream(stream) is True

        # BytesIO
        stream = io.BytesIO(b"content")
        assert is_stream(stream) is True

        # Not a stream
        assert is_stream("string") is False
        assert is_stream(123) is False
        assert is_stream([1, 2, 3]) is False
        assert is_stream(None) is False
        ```

    Note:
        This is useful for functions that accept either file paths or
        file-like objects, allowing flexible input handling.
    """
    return isinstance(obj, io.IOBase) and hasattr(obj, "read")
