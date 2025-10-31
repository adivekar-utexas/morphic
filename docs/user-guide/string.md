# String Utilities

Morphic provides a comprehensive suite of string manipulation, formatting, and validation utilities through the `morphic.string` module. This guide covers the most commonly used functions organized by category.

## Overview

The string utilities cover:

- **Text Normalization** - Clean and standardize text
- **Case Conversion** - Convert between naming conventions
- **Formatting** - Human-readable output for numbers, bytes, time
- **Validation** - Type checking and validation
- **Hashing** - Generate consistent hashes
- **Name Generation** - Create human-readable random names
- **DateTime Utilities** - Format and parse dates
- **Fuzzy Matching** - Flexible string matching

## Text Normalization

### Basic Normalization

Remove characters and convert to lowercase for consistent comparisons:

```python
from morphic.string import normalize

# Remove spaces, hyphens, underscores (default)
assert normalize("Hello World") == "helloworld"
assert normalize("snake_case") == "snakecase"
assert normalize("kebab-case") == "kebabcase"

# Custom removal characters
assert normalize("foo@bar.com", remove=("@", ".")) == "foobarcom"

# Only lowercase, no removal
assert normalize("CamelCase", remove=None) == "camelcase"
```

### Punctuation Normalization

Remove punctuation with optional space and number removal:

```python
from morphic.string import punct_normalize

# Basic usage - removes punctuation, spaces, and lowercases
assert punct_normalize("Hello, World!") == "helloworld"

# Keep spaces
assert punct_normalize("Hello, World!", space=False) == "hello world"

# Keep case
assert punct_normalize("Hello, World!", lowercase=False) == "HelloWorld"

# Remove numbers too
assert punct_normalize("abc123def", numbers=True) == "abcdef"
```

### Whitespace Normalization

Clean up messy whitespace:

```python
from morphic.string import whitespace_normalize

# Collapse multiple spaces
assert whitespace_normalize("hello    world") == "hello world"

# Collapse multiple newlines
assert whitespace_normalize("line1\n\n\nline2") == "line1\nline2"

# Remove newlines entirely
assert whitespace_normalize("line1\nline2", remove_newlines=True) == "line1line2"

# Clean up messy text
messy = "  hello   world  \n\n  foo   bar  \n\n  "
clean = whitespace_normalize(messy)
assert clean == "hello world\nfoo bar"
```

## Case Conversion

Convert between different naming conventions:

```python
from morphic.string import convert_case, detect_case

# Snake case
assert convert_case("CamelCase", "snake") == "camel_case"
assert convert_case("PascalCase", "snake") == "pascal_case"

# Camel case
assert convert_case("snake_case", "camel") == "snakeCase"
assert convert_case("kebab-case", "camel") == "kebabCase"

# Pascal case
assert convert_case("snake_case", "pascal") == "SnakeCase"
assert convert_case("camelCase", "pascal") == "CamelCase"

# Kebab case
assert convert_case("PascalCase", "kebab") == "pascal-case"
assert convert_case("snake_case", "kebab") == "snake-case"

# Detect current case
assert detect_case("snake_case") == "snake"
assert detect_case("camelCase") == "camel"
assert detect_case("PascalCase") == "pascal"
assert detect_case("kebab-case") == "kebab"
assert detect_case("SCREAMING_SNAKE") == "screaming_snake"
```

## Human-Readable Formatting

### File Sizes

Format bytes into human-readable sizes:

```python
from morphic.string import readable_bytes, convert_size_from_bytes, convert_size_to_bytes

# Automatic unit selection
assert "KB" in readable_bytes(5000)
assert "MB" in readable_bytes(5000000)
assert "GB" in readable_bytes(5000000000)

# Get all conversions
sizes = convert_size_from_bytes(1024)
assert sizes["B"] == 1024.0
assert sizes["KB"] == 1.0

# Get specific unit
kb_size = convert_size_from_bytes(2048, unit="KB")
assert kb_size == 2.0

# Parse human-readable sizes
assert convert_size_to_bytes("1 KB") == 1024
assert convert_size_to_bytes("1 MB") == 1024 * 1024
assert convert_size_to_bytes("1.5 KB") == int(1.5 * 1024)
```

### Time Durations

Format seconds into human-readable durations:

```python
from morphic.string import readable_seconds, convert_time_from_seconds
from datetime import timedelta

# Automatic unit selection
result = readable_seconds(5)
assert "s" in result  # "5.0 seconds" or "5s"

result = readable_seconds(120)
assert "min" in result  # "2 mins" or "2min"

result = readable_seconds(7200)
assert "hr" in result or "hours" in result

# Short format
assert readable_seconds(5, short=True) in ["5.0s", "5s"]

# With timedelta
td = timedelta(seconds=30)
result = readable_seconds(td)
assert "30" in result

# Get all conversions
times = convert_time_from_seconds(60)
assert times["seconds"] == 60.0
assert times["mins"] == 1.0

# Short format keys
times = convert_time_from_seconds(5, short=True)
assert "s" in times
assert "ms" in times
```

### Numbers

Format large numbers with unit suffixes:

```python
from morphic.string import readable_number, convert_number

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

# Get all conversions
numbers = convert_number(1000000, short=True)
assert numbers["M"] == 1.0
assert numbers["K"] == 1000.0
```

## Validation Functions

Check types and validate inputs:

```python
from morphic.string import is_int, is_float, is_empty, is_stream

# Integer validation
assert is_int("123") is True
assert is_int("-123") is True
assert is_int("123.0") is False  # Has decimal point
assert is_int("abc") is False

# Float validation
assert is_float("123") is True
assert is_float("1.23") is True
assert is_float("123.0") is True
assert is_float("1e2") is True
assert is_float("nan") is True
assert is_float("inf") is True

# Empty string validation
assert is_empty("") is True
assert is_empty("   ") is True
assert is_empty("hello") is False

# Stream validation
import io
stream = io.StringIO("content")
assert is_stream(stream) is True
assert is_stream("string") is False
```

## String Utilities

### Hashing

Generate consistent SHA256 hashes:

```python
from morphic.string import hash

# Hash strings
h1 = hash("hello")
h2 = hash("hello")
assert h1 == h2  # Consistent

# Hash numbers
h = hash(42)

# Hash collections
h1 = hash([1, 2, 3])
h2 = hash([1, 2, 3])
assert h1 == h2

# Hash dictionaries (order-independent)
h1 = hash({"a": 1, "b": 2})
h2 = hash({"b": 2, "a": 1})
assert h1 == h2

# Different bases
h_base62 = hash("test", base=62)  # Default
h_base36 = hash("test", base=36)
```

### Join Human-Readable Lists

Create grammatically correct lists:

```python
from morphic.string import join_human

# Basic usage
assert join_human(["apple", "banana", "cherry"]) == "apple, banana and cherry"

# With Oxford comma
assert join_human(["apple", "banana", "cherry"], oxford_comma=True) == "apple, banana, and cherry"

# Two items
assert join_human(["Alice", "Bob"]) == "Alice and Bob"

# Custom separator and conjunction
assert join_human([1, 2, 3], sep=";", final_join="or") == "1; 2 or 3"
```

### Random Name Generation

Generate human-readable random names:

```python
from morphic.string import random_name

# Single name
name = random_name()  # e.g., "happy-running-dog"

# Multiple names
names = random_name(3)
# e.g., ["quick-jumping-fox", "lazy-sleeping-cat", "brave-flying-eagle"]

# Custom separator
name = random_name(sep="_")  # e.g., "brave_flying_eagle"

# Custom order
name = random_name(order=("adjective", "noun"))  # e.g., "blue-sky"
name = random_name(order=("verb", "noun"))  # e.g., "running-tiger"

# Reproducible with seed
name1 = random_name(seed=42)
name2 = random_name(seed=42)
assert name1 == name2
```

### Zero-Padding

Pad numbers for consistent width:

```python
from morphic.string import zfill, get_num_zeros_to_pad

# Basic usage
assert zfill(5, 999) == "005"
assert zfill(42, 999) == "042"
assert zfill(999, 999) == "999"

# For filenames that sort correctly
for i in range(100):
    filename = f"file_{zfill(i, 100)}.txt"
    # Results in: file_000.txt, file_001.txt, ..., file_099.txt

# Calculate padding needed
assert get_num_zeros_to_pad(99) == 2
assert get_num_zeros_to_pad(100) == 3
assert get_num_zeros_to_pad(999) == 3
assert get_num_zeros_to_pad(1000) == 4
```

## DateTime Utilities

### Formatting

Format datetimes in various styles:

```python
from morphic.string import readable_datetime, now
from datetime import datetime

dt = datetime(2021, 1, 15, 14, 30, 45, 123456)

# ISO 8601 format (default)
result = readable_datetime(dt)
# "2021-01-15T14:30:45.123456+00:00"

# Human-readable format
result = readable_datetime(dt, human=True)
# "15Jan2021-14:30:45+UTC"

# Without microseconds
result = readable_datetime(dt, microsec=False)
# "2021-01-15T14:30:45+00:00"

# Without timezone
result = readable_datetime(dt, tz=False)
# "2021-01-15T14:30:45.123456"

# Get current time
current = now()  # ISO format with microseconds and timezone
current = now(human=True)  # Human-readable format
```

### Parsing

Parse various datetime formats:

```python
from morphic.string import parse_datetime
from datetime import datetime

# datetime object (pass-through)
dt = datetime.now()
assert parse_datetime(dt) == dt

# Unix timestamp (int)
dt = parse_datetime(1609459200)
assert dt.year == 2021

# Unix timestamp (float with microseconds)
dt = parse_datetime(1609459200.5)
assert dt.microsecond > 0

# ISO format string
dt = parse_datetime("2021-01-01T00:00:00")
assert dt.year == 2021 and dt.month == 1

# With timezone
dt = parse_datetime("2021-01-01T00:00:00+00:00")
assert dt.tzinfo is not None
```

## Fuzzy Matching

Match strings with different delimiters or case:

```python
from morphic.string import fuzzy_match, is_fuzzy_match

# Basic matching with different delimiters
assert fuzzy_match("my_file", ["my-file", "other"]) == "my-file"
assert fuzzy_match("my-file", ["my_file", "other"]) == "my_file"
assert fuzzy_match("my file", ["my_file", "other"]) == "my_file"

# Case-insensitive
assert fuzzy_match("MyFile", ["my_file"]) == "my_file"
assert fuzzy_match("MY-FILE", ["my_file"]) == "my_file"

# No match
assert fuzzy_match("notfound", ["my_file", "other"]) is None

# Check for match existence
assert is_fuzzy_match("my_file", ["my-file", "other"]) is True
assert is_fuzzy_match("notfound", ["my_file", "other"]) is False

# Custom replacements
assert fuzzy_match("a.b.c", ["a_b_c"], replacements=(".",)) == "a_b_c"
```

## Advanced Usage

### String Format Arguments

Extract format string arguments:

```python
from morphic.string import str_format_args

# Named arguments
assert str_format_args("Hello {name}!") == ["name"]
assert str_format_args("{first} {last}") == ["first", "last"]

# Positional arguments (with named_only=False)
assert str_format_args("Hello {0}!", named_only=False) == ["0"]
assert str_format_args("{0} {name} {1}", named_only=False) == ["0", "name", "1"]
assert str_format_args("{0} {name} {1}", named_only=True) == ["name"]
```

### Type Conversion

Convert string representations to Python types:

```python
from morphic.string import convert_str_to_type

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
assert convert_str_to_type("5.0", int) == 5    # float to int (if whole)
assert convert_str_to_type("[1, 2]", tuple) == (1, 2)  # list to tuple
```

## Best Practices

### Text Processing Pipeline

Combine multiple utilities for robust text processing:

```python
from morphic.string import normalize, punct_normalize, whitespace_normalize

def clean_text(text: str) -> str:
    """Clean text for comparison."""
    # Remove extra whitespace
    text = whitespace_normalize(text)
    # Remove punctuation
    text = punct_normalize(text, space=False)
    # Normalize for comparison
    text = normalize(text)
    return text

# Use it
clean = clean_text("  Hello,   World!  \n  How   are you?  ")
```

### Configuration Keys

Many string functions are used internally by Morphic. Use them for consistent formatting:

```python
from morphic.string import readable_bytes, readable_seconds

def format_stats(bytes_used: int, time_elapsed: float) -> str:
    """Format statistics in a consistent way."""
    return f"Used {readable_bytes(bytes_used)} in {readable_seconds(time_elapsed)}"

stats = format_stats(1024 * 1024 * 5, 12.5)
# "Used 5.0 MB in 12.5 seconds"
```

### Case Conversion for APIs

Handle different naming conventions:

```python
from morphic.string import convert_case

def api_response_to_python(data: dict) -> dict:
    """Convert API camelCase keys to Python snake_case."""
    return {
        convert_case(key, "snake"): value
        for key, value in data.items()
    }

api_data = {"firstName": "John", "lastName": "Doe"}
python_data = api_response_to_python(api_data)
# {"first_name": "John", "last_name": "Doe"}
```

## Next Steps

- See the [API Reference](../api/string.md) for detailed function signatures
- Check out [Examples](../examples.md#string-utilities) for more usage patterns
- Learn about [Typed](typed.md) which uses string utilities for validation

