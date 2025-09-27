# Typed

Typed provides enhanced data modeling capabilities with automatic validation, type conversion, default value processing, and seamless integration with Morphic's Registry and AutoEnum systems.

## Overview

Typed is a Python-only implementation that provides Pydantic-like functionality without external dependencies. Subclasses automatically become dataclasses with enhanced features including:

- **Automatic dataclass transformation** - No `@dataclass` decorator needed
- **Type validation and conversion** - Automatic type checking and conversion from strings/dicts
- **Default value validation** - Validates and converts default values at class definition time
- **Hierarchical type support** - Nested Typed objects, lists, and dictionaries
- **Mutable default handling** - Automatically prevents shared mutable state
- **Registry integration** - Works seamlessly with the Registry system
- **AutoEnum support** - Automatic enum conversion with fuzzy matching

## Basic Usage

### Simple Data Models

```python
from morphic import Typed
from typing import Optional

class UserModel(Typed):
    name: str
    email: str
    age: int
    is_active: bool = True
    bio: Optional[str] = None

# Create instances with automatic validation
user = UserModel(
    name="Alice Johnson",
    email="alice@example.com",
    age=30
)

print(f"User: {user.name}, Active: {user.is_active}")
# Output: User: Alice Johnson, Active: True
```

### Type Conversion and Validation

Typed automatically converts compatible types and validates all fields:

```python
class ConfigModel(Typed):
    port: int
    debug: bool
    timeout: float

    def validate(self):
        if self.port < 1 or self.port > 65535:
            raise ValueError("Port must be between 1 and 65535")

# Automatic type conversion from strings
config = ConfigModel.from_dict({
    "port": "8080",      # String converted to int
    "debug": "true",     # String converted to bool
    "timeout": "30.5"    # String converted to float
})

print(f"Port: {config.port} ({type(config.port).__name__})")
# Output: Port: 8080 (int)
```

## Default Value Validation and Conversion

Typed validates and converts default values at class definition time, ensuring type safety and preventing common errors.

### Automatic Default Value Conversion

```python
class ServerConfig(Typed):
    # Strings automatically converted to appropriate types
    port: int = "8080"        # Converted to int(8080)
    debug: bool = "false"     # Converted to bool(False)
    timeout: float = "30.5"   # Converted to float(30.5)

    # Optional fields
    description: Optional[str] = None

# All defaults are properly converted and typed
server = ServerConfig()
assert server.port == 8080
assert isinstance(server.port, int)
assert server.debug is False
assert isinstance(server.debug, bool)
```

### Invalid Default Detection

Invalid defaults are caught at class definition time with clear error messages:

```python
try:
    class BadConfig(Typed):
        count: int = "not_a_number"  # Cannot convert to int

except TypeError as e:
    print(f"Error: {e}")
    # Output: Invalid default value for field 'count' in class 'BadConfig':
    # Default value for field 'count' in class 'BadConfig' expected type <class 'int'>,
    # got str with value 'not_a_number'
```

### Hierarchical Default Conversion

Typed automatically converts nested structures in default values:

```python
class Contact(Typed):
    name: str
    email: str

class ContactList(Typed):
    # Dict converted to Contact object automatically
    primary: Contact = {"name": "Admin", "email": "admin@example.com"}

    # List of dicts converted to list of Contact objects
    contacts: List[Contact] = [
        {"name": "John", "email": "john@example.com"},
        {"name": "Jane", "email": "jane@example.com"}
    ]

    # Dict of dicts converted to dict of Contact objects
    by_role: Dict[str, Contact] = {
        "admin": {"name": "Administrator", "email": "admin@company.com"},
        "user": {"name": "Regular User", "email": "user@company.com"}
    }

# All defaults are properly converted and validated
contacts = ContactList()
assert isinstance(contacts.primary, Contact)
assert isinstance(contacts.contacts[0], Contact)
assert isinstance(contacts.by_role["admin"], Contact)
```

### Mutable Default Handling

Typed automatically converts mutable defaults to `default_factory` to prevent shared state:

```python
class TaskList(Typed):
    name: str = "Default List"

    # Mutable defaults automatically converted to default_factory
    tasks: List[str] = ["initial task"]  # Each instance gets its own copy
    metadata: Dict[str, str] = {"created": "now"}

# Each instance gets independent mutable objects
list1 = TaskList()
list2 = TaskList()

list1.tasks.append("new task")
assert len(list1.tasks) == 2  # Modified
assert len(list2.tasks) == 1  # Unchanged - independent copy
```

## Advanced Type Conversion

### Union Types

Typed handles Union types by attempting conversion in declaration order:

```python
class FlexibleModel(Typed):
    # Tries int conversion first, then str
    value: Union[int, str] = "42"  # Converts to int(42)

    # Tries str conversion first, then int
    mixed: Union[str, int] = 42    # Keeps as int(42) since str(42) = "42" changes meaning

flexible = FlexibleModel()
assert flexible.value == 42
assert isinstance(flexible.value, int)
```

### Optional Fields

Typed properly handles Optional types with None defaults:

```python
class OptionalModel(Typed):
    required: str
    optional_str: Optional[str] = None
    optional_list: Optional[List[str]] = None

    # Optional with non-None default
    optional_with_default: Optional[int] = 42

model = OptionalModel(required="test")
assert model.optional_str is None
assert model.optional_with_default == 42
```

### Complex Nested Structures

Typed supports deeply nested hierarchical structures:

```python
class Item(Typed):
    name: str
    value: int

class Category(Typed):
    name: str
    items: List[Item]

class Inventory(Typed):
    # Complex nested default structure
    categories: Dict[str, Category] = {
        "electronics": {
            "name": "Electronics",
            "items": [
                {"name": "Phone", "value": 500},
                {"name": "Laptop", "value": 1000}
            ]
        },
        "books": {
            "name": "Books",
            "items": [{"name": "Python Guide", "value": 50}]
        }
    }

inventory = Inventory()
# All nested structures properly converted
assert isinstance(inventory.categories["electronics"], Category)
assert isinstance(inventory.categories["electronics"].items[0], Item)
assert inventory.categories["electronics"].items[0].name == "Phone"
```

## Serialization and Deserialization

Typed provides built-in methods for converting to/from dictionaries with hierarchical support:

```python
class Address(Typed):
    street: str
    city: str
    country: str = "US"

class Person(Typed):
    name: str
    age: int
    address: Address
    tags: List[str] = []

# Create instance with nested data
person = Person(
    name="John Doe",
    age=30,
    address={"street": "123 Main St", "city": "NYC"},
    tags=["developer", "python"]
)

# Convert to dictionary (hierarchical serialization)
person_dict = person.to_dict()
print(person_dict)
# Output: {
#     'name': 'John Doe',
#     'age': 30,
#     'address': {'street': '123 Main St', 'city': 'NYC', 'country': 'US'},
#     'tags': ['developer', 'python']
# }

# Create from dictionary (hierarchical deserialization)
restored_person = Person.from_dict(person_dict)
assert isinstance(restored_person.address, Address)
assert restored_person.address.street == "123 Main St"
```

### Serialization Options

Control what gets included in serialization:

```python
class ModelWithOptions(Typed):
    name: str
    value: Optional[int] = None
    internal: bool = True

model = ModelWithOptions(name="test")

# Include all fields
all_fields = model.to_dict()
# {'name': 'test', 'value': None, 'internal': True}

# Exclude None values
no_none = model.to_dict(exclude_none=True)
# {'name': 'test', 'internal': True}

# Exclude default values
no_defaults = model.to_dict(exclude_defaults=True)
# {'name': 'test'}
```

## Registry Integration

Typed works seamlessly with the Registry system for polymorphic configurations:

```python
from morphic import Typed, Registry
from abc import ABC, abstractmethod

class ServiceConfig(Typed):
    name: str
    timeout: float = 30.0
    retries: int = 3

class Service(Registry, ABC):
    def __init__(self, config: ServiceConfig):
        self.config = config

    @abstractmethod
    def process(self) -> str:
        pass

class WebService(Service):
    def process(self) -> str:
        return f"Web service {self.config.name} (timeout: {self.config.timeout}s)"

class DatabaseService(Service):
    def process(self) -> str:
        return f"DB service {self.config.name} (retries: {self.config.retries})"

# Create services with validated configuration
web_config = ServiceConfig(name="API", timeout=60.0)
db_config = ServiceConfig(name="UserDB", retries=5)

web_service = Service.of("WebService", config=web_config)
db_service = Service.of("DatabaseService", config=db_config)

print(web_service.process())
# Output: Web service API (timeout: 60.0s)
```

## AutoEnum Integration

Typed works with AutoEnum for type-safe enumeration handling:

```python
from morphic import Typed, AutoEnum
from enum import Enum

class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class TaskModel(Typed):
    title: str
    priority: Priority = "medium"  # String automatically converted to enum
    completed: bool = False

# String conversion to enum
task = TaskModel(
    title="Fix bug",
    priority="high"  # Automatically converted to Priority.HIGH
)

assert task.priority == Priority.HIGH
assert isinstance(task.priority, Priority)

# Works with default values too
class TaskWithDefault(Typed):
    title: str
    priority: Priority = "low"  # Default string converted to Priority.LOW

default_task = TaskWithDefault(title="Review code")
assert default_task.priority == Priority.LOW
```

## Validation Features

### Automatic Type Validation

Typed automatically validates all field types:

```python
class ValidatedModel(Typed):
    name: str
    age: int
    scores: List[float]

try:
    # Type validation catches mismatches
    invalid = ValidatedModel(
        name=123,        # Should be str
        age="thirty",    # Should be int
        scores="not_a_list"  # Should be List[float]
    )
except TypeError as e:
    print(f"Validation error: {e}")
```

### Custom Validation

Add custom validation logic with the `validate()` method:

```python
class EmailModel(Typed):
    email: str
    age: int

    def validate(self):
        if "@" not in self.email:
            raise ValueError("Invalid email format")
        if self.age < 0 or self.age > 150:
            raise ValueError("Invalid age range")

# Custom validation runs automatically
try:
    invalid_email = EmailModel(email="invalid-email", age=25)
except ValueError as e:
    print(f"Custom validation failed: {e}")
```

### Hierarchical Validation

Validation works recursively for nested structures:

```python
class ValidatedAddress(Typed):
    street: str
    zip_code: str

    def validate(self):
        if not self.zip_code.isdigit() or len(self.zip_code) != 5:
            raise ValueError("ZIP code must be 5 digits")

class ValidatedPerson(Typed):
    name: str
    address: ValidatedAddress

try:
    # Validation error in nested object is caught
    person = ValidatedPerson(
        name="John",
        address={"street": "123 Main St", "zip_code": "invalid"}
    )
except ValueError as e:
    print(f"Nested validation error: {e}")
```

## Performance and Best Practices

### Default Value Processing

- Default value validation occurs only once at class definition time
- Converted default values are cached and reused for all instances
- Mutable defaults are automatically handled to prevent shared state issues
- Large or complex default structures are efficiently handled via `default_factory`

```python
class OptimizedModel(Typed):
    # These conversions happen once at class definition time
    port: int = "8080"              # Converted once to int(8080)
    features: List[str] = ["auth"]  # Converted once to default_factory

# All instances reuse the converted defaults
model1 = OptimizedModel()  # Fast - uses cached conversion
model2 = OptimizedModel()  # Fast - uses cached conversion
```

### Type Conversion Best Practices

Use Optional[T] for fields that can legitimately be None:

```python
# Good - explicit about None possibility
class GoodModel(Typed):
    name: str
    description: Optional[str] = None

# Less clear - might be confusing
class UnclearModel(Typed):
    name: str
    description: str = None  # Type checker warning
```

Follow the same conversion rules as `from_dict()` for consistency:

```python
class ConsistentModel(Typed):
    port: int = "8080"  # Same as from_dict({"port": "8080"})

# Both create identical objects
model1 = ConsistentModel()
model2 = ConsistentModel.from_dict({"port": "8080"})
assert model1.port == model2.port
```

### Memory Optimization

Use `__slots__` for memory-critical applications:

```python
class MemoryOptimized(Typed):
    __slots__ = ['name', 'value']

    name: str
    value: int
```

## Error Handling

### Default Value Errors

Default value errors are caught at class definition time:

```python
try:
    class InvalidDefaults(Typed):
        port: int = "not_a_number"
        items: List[str] = "not_a_list"

except TypeError as e:
    # Clear error message with field name, class name, and expected type
    print(f"Definition error: {e}")
```

### Runtime Type Errors

Runtime type validation provides detailed error messages:

```python
try:
    invalid = ValidatedModel(name=123, age="thirty")
except TypeError as e:
    print(f"Runtime error: {e}")
    # Output: Field 'name' expected type <class 'str'>, got int with value 123
```

### Nested Validation Errors

Errors in nested structures are clearly reported:

```python
try:
    person = Person(
        name="John",
        address={"street": 123, "city": "NYC"}  # street should be str
    )
except TypeError as e:
    print(f"Nested error: {e}")
    # Reports exactly which nested field failed validation
```

## Advanced Examples

### Configuration Management System

```python
from morphic import Typed, Registry
from typing import Dict, List, Optional
import os

class DatabaseConfig(Typed):
    host: str = "localhost"
    port: int = 5432
    username: str
    password: str
    database: str
    ssl: bool = True

    def validate(self):
        if not self.username or not self.password:
            raise ValueError("Database credentials required")

class CacheConfig(Typed):
    host: str = "localhost"
    port: int = 6379
    ttl: int = 3600
    max_connections: int = 20

class AppConfig(Typed):
    app_name: str
    version: str = "1.0.0"
    debug: bool = False
    database: DatabaseConfig
    cache: CacheConfig
    features: List[str] = []  # Mutable default handled automatically

    @classmethod
    def from_env(cls) -> 'AppConfig':
        """Create configuration from environment variables with type conversion."""
        return cls.from_dict({
            "app_name": os.getenv("APP_NAME", "MyApp"),
            "debug": os.getenv("DEBUG", "false"),  # String converted to bool
            "database": {
                "username": os.getenv("DB_USER"),
                "password": os.getenv("DB_PASSWORD"),
                "database": os.getenv("DB_NAME"),
                "port": os.getenv("DB_PORT", "5432")  # String converted to int
            },
            "cache": {
                "ttl": os.getenv("CACHE_TTL", "7200")  # String converted to int
            },
            "features": os.getenv("FEATURES", "auth,notifications").split(",")
        })

# Usage with automatic validation and conversion
config = AppConfig.from_env()
```

### Plugin System with Typed

```python
class PluginConfig(Typed):
    name: str
    version: str = "1.0"
    enabled: bool = True
    settings: Dict[str, str] = {}  # Mutable default handled automatically

class Plugin(Registry, ABC):
    def __init__(self, config: PluginConfig):
        self.config = config

    @abstractmethod
    def execute(self) -> str:
        pass

class LoggingPlugin(Plugin):
    def execute(self) -> str:
        level = self.config.settings.get("level", "INFO")
        return f"Logging at {level} level"

class MetricsPlugin(Plugin):
    def execute(self) -> str:
        interval = self.config.settings.get("interval", "60")
        return f"Collecting metrics every {interval}s"

class PluginManager:
    def load_from_config(self, plugin_configs: List[Dict[str, any]]) -> List[Plugin]:
        plugins = []

        for config_data in plugin_configs:
            plugin_type = config_data.pop("type")

            # Automatic validation and conversion
            config = PluginConfig.from_dict(config_data)

            if config.enabled:
                plugin = Plugin.of(plugin_type, config=config)
                plugins.append(plugin)

        return plugins

# Configuration with mixed types - all automatically converted
plugin_configs = [
    {
        "type": "LoggingPlugin",
        "name": "logger",
        "enabled": "true",  # String converted to bool
        "settings": {"level": "DEBUG"}
    },
    {
        "type": "MetricsPlugin",
        "name": "metrics",
        "settings": {"interval": "30"}
    }
]

manager = PluginManager()
plugins = manager.load_from_config(plugin_configs)

for plugin in plugins:
    print(plugin.execute())
```

## Migration Guide

### From Standard Dataclasses

Typed is a drop-in replacement for standard dataclasses with additional features:

```python
# Before: Standard dataclass
from dataclasses import dataclass

@dataclass
class OldModel:
    name: str
    value: int = 0

# After: Typed (no decorator needed)
class NewModel(Typed):
    name: str
    value: int = 0  # Now with automatic validation and conversion
```

### From Pydantic

Typed provides similar functionality to Pydantic BaseModel:

```python
# Pydantic-style
from pydantic import BaseModel

class PydanticModel(BaseModel):
    name: str
    age: int

# Typed equivalent
class Typed(Typed):
    name: str
    age: int

    # Built-in validation, conversion, and serialization
    # No external dependencies required
```

## Edge Cases and Advanced Scenarios

### Complex Type Validation

Typed handles sophisticated type scenarios:

```python
# Union types with complex conversion
class FlexibleConfig(Typed):
    value: Union[int, str, List[str]]
    optional_setting: Optional[Dict[str, Any]] = None

# Union conversion tries types in declaration order
config1 = FlexibleConfig.from_dict({"value": "123"})        # Stays as str
config2 = FlexibleConfig.from_dict({"value": 123})          # Stays as int
config3 = FlexibleConfig.from_dict({"value": ["a", "b"]})   # List[str]

# Complex nested structures with validation
class NestedEdgeCases(Typed):
    deeply_nested: Dict[str, List[Optional[Dict[str, str]]]]

data = {
    "deeply_nested": {
        "group1": [{"key": "value"}, None, {"another": "item"}],
        "group2": [None, {"final": "entry"}]
    }
}
nested = NestedEdgeCases.from_dict(data)
assert nested.deeply_nested["group1"][1] is None  # None preserved in Optional
```

### Default Value Edge Cases

```python
# Mutable defaults are automatically converted to default_factory
class MutableDefaults(Typed):
    items: List[str] = ["default"]          # Becomes default_factory
    config: Dict[str, str] = {"key": "val"} # Becomes default_factory
    metadata: Optional[Dict[str, Any]] = None  # None is immutable, stays as default

# Each instance gets its own copy of mutable defaults
instance1 = MutableDefaults()
instance2 = MutableDefaults()

instance1.items.append("new_item")
assert len(instance1.items) == 2  # ["default", "new_item"]
assert len(instance2.items) == 1  # ["default"] - unchanged

# Invalid defaults caught at class definition time
try:
    class BadDefaults(Typed):
        count: int = "not_a_number"  # Caught immediately when class is defined
except TypeError as e:
    print(f"Class definition failed: {e}")
```

### Performance and Memory Characteristics

```python
# Field information is cached for performance
class LargeModel(Typed):
    # Many fields for testing performance
    field1: str
    field2: int
    field3: bool
    # ... many more fields ...
    field50: Optional[str] = None

# Field info cached after first access
model = LargeModel(field1="test", field2=42, field3=True)

# Repeated to_dict/from_dict operations use cached field info
import time
start = time.time()
for _ in range(10000):
    data = model.to_dict()
    new_model = LargeModel.from_dict(data)
duration = time.time() - start
print(f"10K conversions: {duration:.3f}s")  # Very fast due to caching
```

### Integration with External Systems

```python
# Typed works with serialization libraries
import json
from typing import Any

class SerializableConfig(Typed):
    app_name: str
    version: str
    features: List[str]
    settings: Dict[str, Any]

config = SerializableConfig(
    app_name="MyApp",
    version="1.0.0",
    features=["auth", "logging"],
    settings={"debug": True, "max_connections": 100}
)

# Seamless JSON serialization
json_str = json.dumps(config.to_dict())
loaded_data = json.loads(json_str)
restored_config = SerializableConfig.from_dict(loaded_data)

assert config.app_name == restored_config.app_name
assert config.settings == restored_config.settings

# Works with exclude options for clean APIs
api_data = config.to_dict(exclude_defaults=True)
print("API data:", api_data)  # Only non-default values
```

### Error Handling Patterns

```python
# Comprehensive error handling for production use
def safe_config_load(data: dict) -> Optional[SerializableConfig]:
    """Safely load configuration with detailed error reporting."""
    try:
        return SerializableConfig.from_dict(data)
    except TypeError as e:
        print(f"Type validation failed: {e}")
        return None
    except ValueError as e:
        print(f"Custom validation failed: {e}")
        return None

# Validation with fallbacks
def load_config_with_fallbacks(primary_data: dict, fallback_data: dict) -> SerializableConfig:
    """Load config with fallback values on validation failure."""
    config = safe_config_load(primary_data)
    if config is None:
        print("Primary config failed, using fallback")
        config = SerializableConfig.from_dict(fallback_data)
    return config

# Usage
primary = {"app_name": 123}  # Invalid - app_name should be string
fallback = {"app_name": "DefaultApp", "version": "1.0.0", "features": [], "settings": {}}

config = load_config_with_fallbacks(primary, fallback)
assert config.app_name == "DefaultApp"  # Used fallback
```

## Function Validation with @validate

Typed includes a powerful `@validate` decorator that brings the same type conversion and validation capabilities to regular functions. This decorator provides Pydantic-like function argument validation using Typed's type system.

### Basic Function Validation

The `@validate` decorator automatically validates and converts function arguments:

```python
from morphic import validate, Typed

@validate
def add_numbers(a: int, b: int) -> int:
    return a + b

# Automatic type conversion
result = add_numbers("5", "10")  # Strings converted to ints
assert result == 15
assert isinstance(result, int)

# Works with existing typed values
result = add_numbers(3, 7)
assert result == 10
```

### Typed Integration

The decorator works seamlessly with Typed objects:

```python
class User(Typed):
    name: str
    age: int
    active: bool = True

@validate
def create_user(user_data: User) -> str:
    return f"Created user: {user_data.name} (age {user_data.age})"

# Dict automatically converted to User object
result = create_user({"name": "John", "age": "30"})  # age converted from string
assert result == "Created user: John (age 30)"

# Existing Typed object passes through
user = User(name="Jane", age=25)
result = create_user(user)
assert result == "Created user: Jane (age 25)"
```

### Complex Type Validation

The decorator handles complex types including lists, dictionaries, and nested structures:

```python
from typing import List, Dict, Optional, Union

@validate
def process_users(users: List[User]) -> int:
    return len(users)

# List of dicts converted to list of User objects
count = process_users([
    {"name": "Alice", "age": "25"},
    {"name": "Bob", "age": "30"}
])
assert count == 2

@validate
def analyze_data(data: Dict[str, List[int]]) -> int:
    return sum(sum(values) for values in data.values())

# Complex nested type conversion
result = analyze_data({
    "group1": ["1", "2", "3"],  # Strings converted to ints
    "group2": [4, 5, 6]         # Already ints
})
assert result == 21
```

### Optional and Union Types

The decorator properly handles Optional and Union type annotations:

```python
@validate
def greet_user(name: str, title: Optional[str] = None) -> str:
    if title:
        return f"Hello, {title} {name}"
    return f"Hello, {name}"

# None is valid for Optional types
result = greet_user("John", None)
assert result == "Hello, John"

# Works with defaults
result = greet_user("Jane")
assert result == "Hello, Jane"

@validate
def format_value(value: Union[int, str]) -> str:
    return f"Value: {value}"

# Union types try conversion in declaration order
result = format_value("123")  # Converted to int(123) first
assert result == "Value: 123"
```

### Return Value Validation

Enable return value validation with the `validate_return` parameter:

```python
@validate(validate_return=True)
def get_user_name(user_id: int) -> str:
    if user_id > 0:
        return f"user_{user_id}"
    else:
        return 123  # This would raise ValidationError

# Valid return passes through
name = get_user_name(5)
assert name == "user_5"

# Invalid return type raises error
try:
    get_user_name(0)  # Returns int instead of str
except ValidationError as e:
    print(f"Return validation failed: {e}")
```

### Default Parameter Validation

The decorator automatically validates default parameter values at decoration time with comprehensive type checking:

```python
from typing import List, Dict
from morphic import ValidationError

# Valid defaults work normally
@validate
def process_items(items: List[str], count: int = 10) -> str:
    return f"Processing {count} of {len(items)} items"

result = process_items(["a", "b", "c"])
assert result == "Processing 10 of 3 items"

# String defaults are converted to appropriate types
@validate
def create_server(port: int = "8080", debug: bool = "false") -> str:
    return f"Server on port {port}, debug={debug}"

server = create_server()
assert server == "Server on port 8080, debug=True"  # Note: "false" -> True (non-empty string)

# Complex nested defaults are validated
@validate
def setup_users(
    users: List[User] = [{"name": "Admin", "age": "30"}],  # Dict converted to User
    config: Dict[str, int] = {"port": "8080", "workers": "4"}  # Strings converted to ints
) -> str:
    return f"Setup {len(users)} users, port={config['port']}"

result = setup_users()
# All nested conversions happen at decoration time

# Invalid defaults are caught when the function is defined
try:
    @validate
    def bad_function(port: int = "not_a_number"):  # Invalid conversion
        return port
except ValidationError as e:
    print(f"Invalid default caught at decoration time: {e}")

# Invalid nested structures are also caught
try:
    @validate
    def bad_nested(numbers: List[int] = ["1", "2", "invalid"]):  # Invalid list element
        return sum(numbers)
except ValidationError as e:
    print(f"Invalid list element caught at decoration time: {e}")

# Invalid Typed defaults are caught too
try:
    @validate
    def bad_user_default(user: User = {"name": "John", "age": "invalid_age"}):
        return user.name
except ValidationError as e:
    print(f"Invalid Typed default caught: {e}")
```

#### Enhanced Default Validation Features

- **Deep Structure Validation**: Lists, dictionaries, and nested Typed objects in defaults are fully validated
- **Type Conversion**: String defaults are intelligently converted (e.g., `"8080"` → `8080`, `"true"` → `True`)
- **Early Error Detection**: All validation happens at decoration time, not at runtime
- **Clear Error Messages**: Detailed error reporting showing exactly what failed and where
- **Nested Typed Support**: Dictionary defaults are converted to Typed instances with full validation

### Function Metadata Preservation

The decorator preserves function metadata and provides access to the original function:

```python
@validate
def documented_function(x: int, y: int) -> int:
    """Add two numbers together."""
    return x + y

# Metadata is preserved
assert documented_function.__name__ == "documented_function"
assert documented_function.__doc__ == "Add two numbers together."

# Original function is accessible
original = documented_function.raw_function
assert original.__name__ == "documented_function"
```

### Variable Arguments Support

The decorator works with functions that have *args and **kwargs:

```python
@validate
def flexible_function(a: int, *args, b: str = "default", **kwargs):
    return f"a={a}, args={args}, b={b}, kwargs={kwargs}"

# Type validation applies to annotated parameters only
result = flexible_function("5", 10, 20, b="test", extra="value")
# a is converted to int(5), others passed through unchanged
assert "a=5" in result
assert "args=(10, 20)" in result
assert "b=test" in result
assert "extra=value" in str(result)
```

### Error Handling

The decorator provides clear error messages for validation failures:

```python
from morphic import ValidationError

@validate
def divide_numbers(a: int, b: int) -> float:
    return a / b

# Type conversion failures are clearly reported
try:
    divide_numbers("not_a_number", 5)
except ValidationError as e:
    print(f"Validation error: {e}")
    # Output: Argument 'a' expected type <class 'int'>, got str with value 'not_a_number'

# Missing arguments are also caught
try:
    divide_numbers()
except ValidationError as e:
    print(f"Argument error: {e}")
```

### Configuration and Behavior

The `@validate` decorator uses fixed configuration that matches pydantic's behavior:

- `arbitrary_types_allowed=True`: Allows any type annotations
- `validate_default=True`: Validates default parameter values at decoration time

```python
# These behaviors are always enabled:

@validate
def complex_function(
    data: Any,                    # Any type allowed (arbitrary_types_allowed)
    config: Dict[str, Any],       # Complex types supported
    count: int = "10"             # Default validated and converted
) -> str:
    return f"Processed {len(config)} items"

# Works with any types and complex structures
result = complex_function(
    data={"anything": "goes"},
    config={"setting1": "value1", "setting2": "value2"}
)
assert result == "Processed 2 items"
```

### Performance Considerations

The decorator adds validation overhead to function calls:

```python
@validate
def fast_function(x: int, y: int) -> int:
    return x + y

# Validation happens on every call
# For performance-critical code, consider:
# 1. Using the raw_function for unvalidated calls
# 2. Validating inputs at boundaries rather than every function
# 3. Pre-validating data structures before processing

# Access unvalidated function when needed
fast_result = fast_function.raw_function(5, 10)  # No validation overhead
```

### Integration with Typed Ecosystem

The decorator integrates perfectly with Typed, Registry, and AutoEnum:

```python
from morphic import Typed, Registry, AutoEnum

class Status(AutoEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"

class Task(Typed):
    name: str
    status: Status = Status.PENDING
    priority: int = 1

class Processor(Registry):
    pass

@Processor.register
class TaskProcessor(Processor):
    @validate
    def process_task(self, task: Task, retries: int = 3) -> str:
        return f"Processing {task.name} (status: {task.status}, retries: {retries})"

# All type conversion and validation happens automatically
processor = Processor.of("TaskProcessor")
result = processor.process_task(
    task={"name": "important_task", "status": "processing", "priority": "5"},
    retries="2"
)
# All strings converted to appropriate types
```

### Use Cases and Patterns

#### API Endpoint Validation

```python
@validate
def create_user_endpoint(
    name: str,
    email: str,
    age: int,
    is_admin: bool = False
) -> Dict[str, Any]:
    """API endpoint with automatic request validation."""
    user = User(name=name, email=email, age=age, active=True)
    return {
        "user_id": hash(user.email),
        "message": f"Created user {name}",
        "is_admin": is_admin
    }

# Request data automatically validated and converted
response = create_user_endpoint(
    name="John Doe",
    email="john@example.com",
    age="30",        # String converted to int
    is_admin="true"  # String converted to bool
)
```

#### Configuration Processing

```python
@validate
def initialize_service(
    config: ServiceConfig,
    debug: bool = False,
    workers: int = 1
) -> str:
    """Initialize service with validated configuration."""
    if debug:
        return f"Debug mode: {config.name} with {workers} workers"
    return f"Production: {config.name} running on port {config.port}"

# Configuration dict automatically converted to ServiceConfig object
result = initialize_service(
    config={"name": "API", "port": "8080", "timeout": "30"},
    workers="4"
)
```

#### Data Processing Pipelines

```python
@validate
def transform_data(
    input_data: List[Dict[str, Any]],
    schema: Typed,
    filters: Optional[Dict[str, str]] = None
) -> List[Typed]:
    """Transform raw data using validated schema."""
    results = []
    for item in input_data:
        validated_item = schema.from_dict(item)
        if not filters or all(
            getattr(validated_item, k, None) == v
            for k, v in filters.items()
        ):
            results.append(validated_item)
    return results

# Complex data processing with automatic validation
processed = transform_data(
    input_data=[
        {"name": "Alice", "age": "25", "active": "true"},
        {"name": "Bob", "age": "30", "active": "false"}
    ],
    schema=User,
    filters={"active": True}
)
```

## Next Steps

- Learn more about [Registry System](registry.md) integration patterns
- Explore [AutoEnum](autoenum.md) for automatic enumeration creation
- Check out complete [Examples](../examples.md) with real-world use cases