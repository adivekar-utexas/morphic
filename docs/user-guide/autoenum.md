# AutoEnum

AutoEnum is Morphic's ultra-fast enumeration system with fuzzy string matching and alias support. It provides powerful string-to-enum conversion with case-insensitive, flexible matching that handles various naming conventions and provides meaningful aliases.

## Why AutoEnum?

Python's built-in `Enum` has [many problems](https://www.acooke.org/cute/Pythonssad0.html). The standard way of defining enums is not Pythonic:

```python
from enum import Enum
class Animal(Enum):
    Antelope = 1
    Bandicoot = 2
    Cat = 3
    Dog = 4
```

Python 3 introduced the `auto` function to automatically assign values:

```python
from enum import Enum, auto
class Animal(Enum):
    Antelope = auto()
    Bandicoot = auto()
    Cat = auto()
    Dog = auto()
```

But built-in Python enums still have problems:
- Case-sensitivity
- No fuzzy-matching
- No support for aliases
- Incompatible str() and repr() outputs
- Unable to convert to JSON
- No Pydantic compatibility

AutoEnum fixes all these problems:

```python
from morphic import AutoEnum, auto
class Animal(AutoEnum):   # Only the superclass changes
    Antelope = auto()
    Bandicoot = auto()
    Cat = auto()
    Dog = auto()
```

AutoEnum allows you to do:

```python
# Default usage, recommended in main codebase
Animal.Antelope   # Antelope

# Fuzzy-match a string entered by a user
Animal('Antelope')  # Antelope

# Spacing, casing and underscores are handled
Animal('     antElope_ ')  # Antelope

# Throws an error for invalid values
Animal('Jaguar')  # ValueError: Could not find enum with value Jaguar

# The error can be suppressed
Animal.from_str('Jaguar', raise_error=False)  # None
```

## Basic Usage

### Creating Enums with Fuzzy Matching

AutoEnum provides robust naming convention support. Different teams use different conventions:
- `NamesLikeThis` (PascalCase; class-name convention)
- `NAMES_LIKE_THIS` (Java and C++ enum convention)
- `namesLikeThis` (camelCase; JS convention)
- `Names_Like_this` for proper nouns (e.g., `Los_Angeles`)

AutoEnum accepts all conventions and gives you the enum value you need:

```python
from morphic import AutoEnum, alias, auto

class Status(AutoEnum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETE = auto()
    FAILED = auto()

# Fuzzy matching works with various formats
status1 = Status("pending")      # Direct match
status2 = Status("RUNNING")      # Case insensitive
status3 = Status("Complete")     # Case insensitive
status4 = Status("failed")       # Case insensitive

print(status1)  # PENDING
print(status2)  # RUNNING
```

### Using Aliases for Better Matching

```python
from morphic import AutoEnum, alias

class TaskStatus(AutoEnum):
    PENDING = alias("waiting", "queued", "not_started")
    RUNNING = alias("active", "in_progress", "executing")
    COMPLETE = alias("done", "finished", "success", "completed")
    FAILED = alias("error", "failure", "crashed", "aborted")

# All these work due to aliases
status1 = TaskStatus("waiting")      # PENDING (alias)
status2 = TaskStatus("in_progress")  # RUNNING (alias)
status3 = TaskStatus("done")         # COMPLETE (alias)
status4 = TaskStatus("error")        # FAILED (alias)

# Fuzzy matching also works on aliases
status5 = TaskStatus("In Progress")  # RUNNING (fuzzy alias)
status6 = TaskStatus("NOT-STARTED")  # PENDING (fuzzy alias)
```

## Advanced Features

### String Normalization and Fuzzy Matching

AutoEnum provides powerful fuzzy matching that normalizes strings by:
- Converting to lowercase
- Removing spaces, dashes, underscores, dots, colons, semicolons, commas
- Handling various naming conventions

```python
class Protocol(AutoEnum):
    HTTP_SECURE = alias("HTTPS", "http-secure", "http_secure", "HTTP Secure")
    FILE_TRANSFER = alias("FTP", "file-transfer", "file_transfer")

# All variations work due to normalization
protocol1 = Protocol("HTTP-SECURE")    # HTTP_SECURE
protocol2 = Protocol("http_secure")    # HTTP_SECURE
protocol3 = Protocol("HTTP Secure")    # HTTP_SECURE
protocol4 = Protocol("HTTPSECURE")     # HTTP_SECURE (spaces removed)

protocol5 = Protocol("file-transfer")  # FILE_TRANSFER (alias)
protocol6 = Protocol("FILE_TRANSFER")  # FILE_TRANSFER (normalized)
```

### Dynamic Enum Creation

Create enums dynamically from lists of strings:

```python
# Create enum dynamically
Color = AutoEnum.create("Color", ["red", "green grass", "Blue33", "Yellow!!!!!!!!!!!!3"])

# Access members (identifiers are cleaned up)
print(Color.Red)         # Red
print(Color.Green_Grass) # Green_Grass
print(Color.Blue33)      # Blue33
print(Color.Yellow_3)    # Yellow_3

# Original strings still work via fuzzy matching
color1 = Color("red")           # Red
color2 = Color("green grass")   # Green_Grass
color3 = Color("Yellow3")       # Yellow_3
```

### Error Handling and Validation

```python
class Priority(AutoEnum):
    LOW = alias("low_priority", "minor")
    MEDIUM = alias("normal", "standard")
    HIGH = alias("urgent", "critical", "important")

# Safe conversion with error handling
def get_priority_safe(priority_str: str) -> Optional[Priority]:
    try:
        return Priority(priority_str)
    except ValueError:
        return None

# Using from_str method for explicit control
priority1 = Priority.from_str("urgent")                    # HIGH
priority2 = Priority.from_str("invalid", raise_error=False)  # None

# Check if string matches any enum value
if Priority.matches_any("critical"):
    print("Critical is a valid priority")

# Check specific enum member
if Priority.HIGH.matches("urgent"):
    print("HIGH priority matches 'urgent'")
```

## Practical Examples

### Configuration System with Enums

```python
from morphic import AutoEnum, alias
from typing import Optional
import json

class Environment(AutoEnum):
    DEVELOPMENT = alias("dev", "local", "development")
    TESTING = alias("test", "qa", "testing")
    STAGING = alias("stage", "uat", "staging")
    PRODUCTION = alias("prod", "live", "production")

class LogLevel(AutoEnum):
    DEBUG = alias("debug", "verbose")
    INFO = alias("info", "information")
    WARNING = alias("warn", "warning")
    ERROR = alias("err", "error", "critical")

class ConfigManager:
    def __init__(self, config_data: dict):
        # Convert string values to enums with fuzzy matching
        self.env = Environment(config_data.get("environment", "dev"))
        self.log_level = LogLevel(config_data.get("log_level", "info"))
        self.debug = config_data.get("debug", self.env == Environment.DEVELOPMENT)

    @classmethod
    def from_json(cls, json_str: str) -> 'ConfigManager':
        config = json.loads(json_str)
        return cls(config)

    def to_dict(self) -> dict:
        return {
            "environment": str(self.env),
            "log_level": str(self.log_level),
            "debug": self.debug
        }

# Usage with various input formats
configs = [
    {"environment": "dev", "log_level": "DEBUG"},           # Direct
    {"environment": "PRODUCTION", "log_level": "Error"},    # Case insensitive
    {"environment": "staging", "log_level": "warn"},        # Aliases
    {"environment": "QA", "log_level": "information"},      # Mixed aliases
]

for config_data in configs:
    config = ConfigManager(config_data)
    print(f"Env: {config.env}, Log: {config.log_level}, Debug: {config.debug}")

# Output:
# Env: DEVELOPMENT, Log: DEBUG, Debug: True
# Env: PRODUCTION, Log: ERROR, Debug: False
# Env: STAGING, Log: WARNING, Debug: False
# Env: TESTING, Log: INFO, Debug: False
```

### Data Processing with Collections

```python
from morphic import AutoEnum, alias
from typing import List, Dict, Set

class Status(AutoEnum):
    PENDING = alias("pending", "waiting", "queued")
    PROCESSING = alias("running", "active", "in_progress")
    COMPLETED = alias("done", "finished", "success")
    FAILED = alias("error", "failure", "aborted")

# AutoEnum provides powerful collection conversion methods
tasks_data = [
    "pending", "running", "DONE", "error", "waiting",
    "in_progress", "success", "FAILED", "queued"
]

# Convert list of strings to enums
task_statuses = Status.convert_list(tasks_data)
print("Task statuses:", task_statuses)
# Output: [PENDING, PROCESSING, COMPLETED, FAILED, PENDING, PROCESSING, COMPLETED, FAILED, PENDING]

# Convert dictionary values
status_counts = {
    "pending": 5,
    "running": 3,
    "done": 12,
    "error": 2
}

enum_counts = Status.convert_dict_values(status_counts)
print("Status counts:", enum_counts)
# Output: {PENDING: 5, PROCESSING: 3, COMPLETED: 12, FAILED: 2}

# Convert dictionary keys
performance_data = {
    "pending": 1.2,
    "running": 45.6,
    "done": 0.8,
    "error": 120.3
}

enum_performance = Status.convert_keys(performance_data)
print("Performance by status:", enum_performance)
# Output: {PENDING: 1.2, PROCESSING: 45.6, COMPLETED: 0.8, FAILED: 120.3}

# Check membership with fuzzy matching (Python 3.12+)
if "in progress" in Status:
    print("'in progress' is a valid status")
```

### Display Names and User-Friendly Output

```python
from morphic import AutoEnum, alias

class UserRole(AutoEnum):
    SUPER_ADMIN = alias("super_admin", "root", "administrator")
    CONTENT_MANAGER = alias("content_mgr", "cms_admin")
    REGULAR_USER = alias("user", "member", "customer")
    GUEST_USER = alias("guest", "visitor", "anonymous")

# Get human-readable display names
for role in UserRole:
    print(f"Role: {role.display_name()}")

# Output:
# Role: Super Admin
# Role: Content Manager
# Role: Regular User
# Role: Guest User

# Custom separator for display names
for role in UserRole:
    print(f"Role: {role.display_name(sep='-')}")

# Output:
# Role: Super-Admin
# Role: Content-Manager
# Role: Regular-User
# Role: Guest-User

# Get display names for all members
print("All roles:", UserRole.display_names())
# Output: All roles: ['Super Admin', 'Content Manager', 'Regular User', 'Guest User']
```

## Best Practices

### 1. Use Descriptive Enum Names

```python
# Good - clear and descriptive
class TaskStatus(AutoEnum):
    PENDING = alias("waiting", "queued")
    RUNNING = alias("active", "executing")
    COMPLETE = alias("done", "finished")

# Avoid generic names
class Status(AutoEnum):  # Too generic
    VALUE_1 = auto()
    VALUE_2 = auto()
```

### 2. Provide Meaningful Aliases

```python
# Good - aliases match real-world usage
class Environment(AutoEnum):
    DEVELOPMENT = alias("dev", "local", "development")
    PRODUCTION = alias("prod", "live", "production")

# Bad - confusing or misleading aliases
class Environment(AutoEnum):
    DEVELOPMENT = alias("prod", "live")  # Misleading!
```

### 3. Handle Case Variations in Input

```python
# AutoEnum automatically handles case variations
class Priority(AutoEnum):
    HIGH = alias("urgent", "critical")
    MEDIUM = alias("normal", "standard")
    LOW = alias("minor", "trivial")

# All these work automatically:
# Priority("HIGH"), Priority("high"), Priority("High")
# Priority("URGENT"), Priority("urgent"), Priority("Urgent")
```

### 4. Use Type Hints for Better IDE Support

```python
from typing import Optional

def process_task(status: TaskStatus) -> str:
    """Process task based on status with type safety."""
    if status == TaskStatus.PENDING:
        return "Task is waiting to be processed"
    elif status == TaskStatus.RUNNING:
        return "Task is currently being processed"
    else:
        return "Task processing is complete"

def safe_status_convert(status_str: str) -> Optional[TaskStatus]:
    """Safely convert string to status with error handling."""
    try:
        return TaskStatus(status_str)
    except ValueError:
        return None
```

## Error Handling

### Common Errors and Solutions

```python
class Status(AutoEnum):
    ACTIVE = alias("running", "live")
    INACTIVE = alias("stopped", "down")

# Invalid enum values
try:
    status = Status("invalid_status")
except ValueError as e:
    print(f"Invalid status: {e}")
    # Output: Could not find enum with value 'invalid_status'; available: ['ACTIVE', 'INACTIVE']

# Safe conversion methods
def get_status_safe(status_str: str) -> Optional[Status]:
    """Safely convert string to Status enum."""
    return Status.from_str(status_str, raise_error=False)

# Usage
status = get_status_safe("invalid")  # Returns None instead of raising
if status:
    print(f"Valid status: {status}")
else:
    print("Invalid status provided")

# Check before conversion
if Status.matches_any("running"):
    status = Status("running")
    print(f"Status: {status}")
```

### Input Validation Patterns

```python
class PaymentMethod(AutoEnum):
    CREDIT_CARD = alias("card", "credit", "visa", "mastercard")
    PAYPAL = alias("pp", "paypal_account")
    BANK_TRANSFER = alias("wire", "ach", "bank")

def validate_payment_method(method_str: str) -> PaymentMethod:
    """Validate and convert payment method with helpful error messages."""
    if not isinstance(method_str, str):
        raise TypeError(f"Payment method must be a string, got {type(method_str)}")

    if not method_str.strip():
        raise ValueError("Payment method cannot be empty")

    try:
        return PaymentMethod(method_str)
    except ValueError:
        available_methods = [member.name for member in PaymentMethod]
        available_aliases = []
        for member in PaymentMethod:
            available_aliases.extend(member.aliases)

        raise ValueError(
            f"Invalid payment method '{method_str}'. "
            f"Available options: {available_methods} "
            f"or aliases: {available_aliases}"
        )

# Usage
try:
    method = validate_payment_method("bitcoin")  # Invalid
except ValueError as e:
    print(f"Error: {e}")
```

## Performance Characteristics

### Ultra-Fast Lookups
- **O(1) lookups** using cached hash maps
- **Thread-safe** initialization with locking
- **LRU cached** string normalization for repeated lookups
- **Identity-based** equality for maximum performance

### Performance Testing Results
Based on the test suite, AutoEnum achieves:
- **1M+ lookups per second** with warm cache
- **100K+ lookups per second** with cold cache
- **Consistent performance** regardless of enum size
- **Fast iteration** and collection conversion

```python
# Performance example - all operations are very fast
import time

class LargeEnum(AutoEnum):
    # Create enum with many members
    MEMBER_1 = alias("alias_1", "alt_1")
    MEMBER_2 = alias("alias_2", "alt_2")
    # ... many more members ...

# Repeated lookups are cached and very fast
start = time.time()
for _ in range(100000):
    status = LargeEnum("alias_1")  # Cached lookup
duration = time.time() - start
print(f"100K lookups took {duration:.3f} seconds")
```

## Integration with Other Morphic Components

### Typed Integration
AutoEnum works seamlessly with Typed for configuration management:

```python
from morphic import Typed, AutoEnum, alias

class LogLevel(AutoEnum):
    DEBUG = alias("debug", "verbose")
    INFO = alias("info", "information")
    WARNING = alias("warn", "warning")
    ERROR = alias("error", "critical")

class AppConfig(Typed):
    app_name: str
    log_level: LogLevel = LogLevel.INFO  # Default enum value
    debug_mode: bool = False

# String conversion works automatically in Typed.from_dict()
config = AppConfig.from_dict({
    "app_name": "MyApp",
    "log_level": "debug",  # Automatically converted to LogLevel.DEBUG
    "debug_mode": True
})

assert config.log_level == LogLevel.DEBUG
```

## Next Steps

- Learn about [Typed](typed.md) for enhanced configuration management
- Explore [Registry System](registry.md) for hierarchical class organization
- Check out complete [Examples](../examples.md) combining all Morphic features