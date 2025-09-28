# Typed

Typed provides enhanced data modeling capabilities with automatic validation, type conversion, default value processing, and seamless integration with Morphic's Registry and AutoEnum systems. Built on Pydantic 2+, Typed leverages Pydantic's powerful validation engine while providing additional morphic-specific functionality.

## Overview

Typed is built on Pydantic's BaseModel and provides a robust foundation for data modeling with enhanced features including:

- **Pydantic-powered validation** - Built on Pydantic 2+ for robust type validation and conversion
- **Immutable by default** - Models are frozen by default to prevent accidental modification
- **Strict validation** - Extra fields are forbidden by default for data integrity
- **Arbitrary types support** - Can handle complex custom types through Pydantic's arbitrary_types_allowed
- **Advanced error handling** - Enhanced error messages with detailed validation information
- **Hierarchical type support** - Nested Typed objects, lists, and dictionaries with automatic conversion
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

# Create instances with automatic Pydantic validation
user = UserModel(
    name="Alice Johnson",
    email="alice@example.com",
    age=30
)

print(f"User: {user.name}, Active: {user.is_active}")
# Output: User: Alice Johnson, Active: True

# Models are immutable by default
try:
    user.name = "Bob"  # This will raise an error
except ValidationError:
    print("Cannot modify immutable model")
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

# Automatic type conversion from strings using Pydantic's model_validate
config = ConfigModel.model_validate({
    "port": "8080",      # String converted to int
    "debug": "true",     # String converted to bool
    "timeout": "30.5"    # String converted to float
})

print(f"Port: {config.port} ({type(config.port).__name__})")
# Output: Port: 8080 (int)

# Direct instantiation also performs type conversion
config2 = ConfigModel(port="9000", debug=False, timeout="45.0")
print(f"Port: {config2.port} ({type(config2.port).__name__})")
# Output: Port: 9000 (int)
```

## Pydantic Configuration and Behavior

Typed leverages Pydantic's powerful configuration system to provide robust data validation and conversion. The default configuration includes:

- `extra="forbid"` - Extra fields are not allowed, ensuring data integrity
- `frozen=True` - Models are immutable by default
- `validate_default=True` - Default values are validated
- `arbitrary_types_allowed=True` - Custom types are supported

## Default Value Validation and Conversion

Pydantic validates and converts default values automatically, ensuring type safety and preventing common errors.

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

except ValidationError as e:
    print(f"Error: {e}")
    # Pydantic will raise a ValidationError for invalid default values
```

### Hierarchical Default Conversion

Typed automatically converts nested structures in default values:

```python
class Contact(Typed):
    name: str
    email: str

from pydantic import Field

class ContactList(Typed):
    # Dict converted to Contact object automatically by Pydantic
    primary: Contact = {"name": "Admin", "email": "admin@example.com"}

    # List of dicts converted to list of Contact objects by Pydantic
    contacts: List[Contact] = Field(default=[
        {"name": "John", "email": "john@example.com"},
        {"name": "Jane", "email": "jane@example.com"}
    ])

    # Dict of dicts converted to dict of Contact objects by Pydantic
    by_role: Dict[str, Contact] = Field(default={
        "admin": {"name": "Administrator", "email": "admin@company.com"},
        "user": {"name": "Regular User", "email": "user@company.com"}
    })

# All defaults are properly converted and validated by Pydantic
contacts = ContactList()
assert isinstance(contacts.primary, Contact)
assert isinstance(contacts.contacts[0], Contact)
assert isinstance(contacts.by_role["admin"], Contact)

# Pydantic automatically handles the conversion during model creation
```

### Immutable Models and Safe Defaults

Pydantic's configuration ensures models are immutable by default and handles mutable defaults safely:

```python
from pydantic import Field

class TaskList(Typed):
    name: str = "Default List"

    # Use Field with default_factory for mutable defaults
    tasks: List[str] = Field(default_factory=lambda: ["initial task"])
    metadata: Dict[str, str] = Field(default_factory=lambda: {"created": "now"})

# Models are immutable - cannot modify after creation
list1 = TaskList()
list2 = TaskList()

# Cannot modify immutable model directly
try:
    list1.tasks.append("new task")  # This will fail
except Exception:
    print("Cannot modify frozen model")

# Use model_copy to create modified versions
modified_list = list1.model_copy(update={"tasks": ["initial task", "new task"]})
assert len(modified_list.tasks) == 2
assert len(list1.tasks) == 1  # Original unchanged
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

Typed leverages Pydantic's powerful serialization methods for converting to/from dictionaries with hierarchical support:

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

# Convert to dictionary using Pydantic's model_dump (hierarchical serialization)
person_dict = person.model_dump()
print(person_dict)
# Output: {
#     'name': 'John Doe',
#     'age': 30,
#     'address': {'street': '123 Main St', 'city': 'NYC', 'country': 'US'},
#     'tags': ['developer', 'python']
# }

# Create from dictionary using Pydantic's model_validate (hierarchical deserialization)
restored_person = Person.model_validate(person_dict)
assert isinstance(restored_person.address, Address)
assert restored_person.address.street == "123 Main St"
```

### Serialization Options

Control what gets included in serialization using Pydantic's model_dump options:

```python
class ModelWithOptions(Typed):
    name: str
    value: Optional[int] = None
    internal: bool = True

model = ModelWithOptions(name="test")

# Include all fields
all_fields = model.model_dump()
# {'name': 'test', 'value': None, 'internal': True}

# Exclude None values
no_none = model.model_dump(exclude_none=True)
# {'name': 'test', 'internal': True}

# Exclude default values
no_defaults = model.model_dump(exclude_defaults=True)
# {'name': 'test'}

# Exclude specific fields
exclude_internal = model.model_dump(exclude={'internal'})
# {'name': 'test', 'value': None}

# Include only specific fields
only_name = model.model_dump(include={'name'})
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

### Automatic Type Validation with Pydantic

Typed leverages Pydantic's robust validation system to automatically validate all field types:

```python
class ValidatedModel(Typed):
    name: str
    age: int
    scores: List[float]

try:
    # Pydantic's type validation catches mismatches
    invalid = ValidatedModel(
        name=123,        # Will be converted to str "123"
        age="thirty",    # Cannot convert to int - ValidationError
        scores="not_a_list"  # Cannot convert to List[float] - ValidationError
    )
except ValidationError as e:
    print(f"Validation error: {e}")
    # Pydantic provides detailed error information
    for error in e.errors():
        print(f"Field: {error['loc']}, Error: {error['msg']}")
```

### Custom Validation with Pydantic Validators

Add custom validation logic using Pydantic's field validators:

```python
from pydantic import field_validator

class EmailModel(Typed):
    email: str
    age: int

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v

    @field_validator('age')
    @classmethod
    def validate_age(cls, v):
        if v < 0 or v > 150:
            raise ValueError("Invalid age range")
        return v

# Custom validation runs automatically during model creation
try:
    invalid_email = EmailModel(email="invalid-email", age=25)
except ValidationError as e:
    print(f"Custom validation failed: {e}")
```

### Hierarchical Validation with Pydantic

Pydantic automatically validates nested structures recursively:

```python
from pydantic import field_validator

class ValidatedAddress(Typed):
    street: str
    zip_code: str

    @field_validator('zip_code')
    @classmethod
    def validate_zip_code(cls, v):
        if not v.isdigit() or len(v) != 5:
            raise ValueError("ZIP code must be 5 digits")
        return v

class ValidatedPerson(Typed):
    name: str
    address: ValidatedAddress

try:
    # Validation error in nested object is caught automatically
    person = ValidatedPerson(
        name="John",
        address={"street": "123 Main St", "zip_code": "invalid"}
    )
except ValidationError as e:
    print(f"Nested validation error: {e}")
    # Pydantic provides detailed location information for nested errors
```

## Performance and Best Practices

### Pydantic Performance Characteristics

- Pydantic compiles validators for optimal runtime performance
- Model fields are cached at the class level for efficient access
- Type conversion is optimized through Pydantic's type system
- Immutable models prevent accidental state mutations and related bugs
- JSON serialization/deserialization is highly optimized

```python
from pydantic import Field

class OptimizedModel(Typed):
    # Pydantic optimizes these conversions
    port: int = 8080  # Prefer native types when possible
    features: List[str] = Field(default_factory=lambda: ["auth"])  # Proper default_factory

# Pydantic's compiled validators make instantiation efficient
model1 = OptimizedModel()  # Fast - optimized validation
model2 = OptimizedModel()  # Fast - reuses compiled validators
```

### Type Conversion Best Practices with Pydantic

Use Optional[T] for fields that can legitimately be None:

```python
# Good - explicit about None possibility
class GoodModel(Typed):
    name: str
    description: Optional[str] = None

# Also acceptable with Pydantic - Union[str, None]
class FlexibleModel(Typed):
    name: str
    description: Union[str, None] = None
```

Leverage Pydantic's consistent conversion behavior:

```python
class ConsistentModel(Typed):
    port: int = 8080  # Prefer native types

# Both create identical objects using Pydantic's validation
model1 = ConsistentModel()
model2 = ConsistentModel.model_validate({"port": "8080"})
assert model1.port == model2.port

# Direct instantiation also performs type conversion
model3 = ConsistentModel(port="8080")
assert model1.port == model3.port
```

### Memory Optimization with Pydantic

Pydantic models are already memory-efficient, but you can further optimize:

```python
# Pydantic models are inherently efficient
class MemoryOptimized(Typed):
    name: str
    value: int

# For extreme memory optimization, consider Pydantic's __slots__
# Note: __slots__ with Pydantic requires careful consideration of inheritance
class SlottedModel(Typed):
    model_config = ConfigDict(extra='forbid', frozen=True)
    
    name: str
    value: int
```

## Error Handling with Pydantic

### Validation Errors

Pydantic provides comprehensive error handling with detailed information:

```python
try:
    class InvalidDefaults(Typed):
        port: int = "not_a_number"  # Invalid conversion
        items: List[str] = "not_a_list"  # Invalid type

except ValidationError as e:
    # Pydantic provides detailed error information
    print(f"Definition error: {e}")
    for error in e.errors():
        print(f"Field: {error['loc']}, Type: {error['type']}, Message: {error['msg']}")
```

### Runtime Validation Errors

Pydantic's validation provides detailed error messages with context:

```python
try:
    invalid = ValidatedModel(name=123, age="thirty")
except ValidationError as e:
    print(f"Runtime error: {e}")
    # Pydantic shows all validation errors at once
    for error in e.errors():
        print(f"Field: {error['loc']}, Input: {error['input']}, Message: {error['msg']}")
    
    # Get JSON representation of errors
    print("JSON errors:", e.json())
```

### Nested Validation Errors

Pydantic provides precise error location information for nested structures:

```python
try:
    person = Person(
        name="John",
        address={"street": 123, "city": "NYC"}  # street should be str
    )
except ValidationError as e:
    print(f"Nested error: {e}")
    # Pydantic shows the exact path to the error
    for error in e.errors():
        print(f"Location: {'.'.join(str(loc) for loc in error['loc'])}")
        print(f"Error: {error['msg']}")
    # Example output: Location: address.street, Error: Input should be a valid string
```

## Advanced Examples

### Configuration Management System

```python
from morphic import Typed, Registry
from typing import Dict, List, Optional
import os

from pydantic import field_validator

class DatabaseConfig(Typed):
    host: str = "localhost"
    port: int = 5432
    username: str
    password: str
    database: str
    ssl: bool = True

    @field_validator('username', 'password')
    @classmethod
    def validate_credentials(cls, v):
        if not v:
            raise ValueError("Database credentials required")
        return v

class CacheConfig(Typed):
    host: str = "localhost"
    port: int = 6379
    ttl: int = 3600
    max_connections: int = 20

from pydantic import Field

class AppConfig(Typed):
    app_name: str
    version: str = "1.0.0"
    debug: bool = False
    database: DatabaseConfig
    cache: CacheConfig
    features: List[str] = Field(default_factory=list)  # Proper default_factory for mutable

    @classmethod
    def from_env(cls) -> 'AppConfig':
        """Create configuration from environment variables with Pydantic's type conversion."""
        return cls.model_validate({
            "app_name": os.getenv("APP_NAME", "MyApp"),
            "debug": os.getenv("DEBUG", "false"),  # Pydantic converts string to bool
            "database": {
                "username": os.getenv("DB_USER"),
                "password": os.getenv("DB_PASSWORD"),
                "database": os.getenv("DB_NAME"),
                "port": os.getenv("DB_PORT", "5432")  # Pydantic converts string to int
            },
            "cache": {
                "ttl": os.getenv("CACHE_TTL", "7200")  # Pydantic converts string to int
            },
            "features": os.getenv("FEATURES", "auth,notifications").split(",")
        })

# Usage with automatic validation and conversion
config = AppConfig.from_env()
```

### Plugin System with Typed

```python
from pydantic import Field

class PluginConfig(Typed):
    name: str
    version: str = "1.0"
    enabled: bool = True
    settings: Dict[str, str] = Field(default_factory=dict)  # Proper default_factory

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

            # Automatic validation and conversion with Pydantic
            config = PluginConfig.model_validate(config_data)

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

Typed provides a Pydantic-powered alternative to standard dataclasses:

```python
# Before: Standard dataclass
from dataclasses import dataclass

@dataclass
class OldModel:
    name: str
    value: int = 0
    
    def __post_init__(self):
        # Manual validation
        if not isinstance(self.name, str):
            raise TypeError("name must be a string")

# After: Typed with Pydantic validation
class NewModel(Typed):
    name: str
    value: int = 0
    
    # Automatic validation, type conversion, and immutability
    # No manual validation needed
```

### From Pydantic BaseModel

Typed is built on Pydantic BaseModel with additional morphic-specific features:

```python
# Standard Pydantic
from pydantic import BaseModel

class PydanticModel(BaseModel):
    name: str
    age: int

# Typed with enhanced features
class TypedModel(Typed):
    name: str
    age: int
    
    # Inherits all Pydantic functionality plus:
    # - Integrated with morphic Registry system
    # - Enhanced error handling
    # - AutoEnum support
    # - Additional morphic-specific utilities
    
# Both work similarly for basic operations
model1 = PydanticModel(name="John", age=30)
model2 = TypedModel(name="John", age=30)

# But Typed provides additional morphic integration
# and is configured with sensible defaults for morphic use cases
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

# Complex nested structures with Pydantic validation
class NestedEdgeCases(Typed):
    deeply_nested: Dict[str, List[Optional[Dict[str, str]]]]

data = {
    "deeply_nested": {
        "group1": [{"key": "value"}, None, {"another": "item"}],
        "group2": [None, {"final": "entry"}]
    }
}
nested = NestedEdgeCases.model_validate(data)
assert nested.deeply_nested["group1"][1] is None  # None preserved in Optional
```

### Default Value Edge Cases

```python
# Use Field with default_factory for mutable defaults
from pydantic import Field
from typing import Any

class MutableDefaults(Typed):
    items: List[str] = Field(default_factory=lambda: ["default"])
    config: Dict[str, str] = Field(default_factory=lambda: {"key": "val"})
    metadata: Optional[Dict[str, Any]] = None  # None is immutable

# Models are immutable - cannot modify directly
instance1 = MutableDefaults()
instance2 = MutableDefaults()

# Cannot modify frozen model
try:
    instance1.items.append("new_item")  # This will fail
except Exception:
    print("Cannot modify frozen model")

# Use model_copy for modifications
modified = instance1.model_copy(update={"items": ["default", "new_item"]})
assert len(modified.items) == 2
assert len(instance1.items) == 1  # Original unchanged

# Invalid defaults caught by Pydantic validation
try:
    class BadDefaults(Typed):
        count: int = "not_a_number"  # Caught by Pydantic validation
except ValidationError as e:
    print(f"Class definition failed: {e}")
```

### Performance and Memory Characteristics

```python
# Pydantic optimizes field access and validation
class LargeModel(Typed):
    # Many fields for testing performance
    field1: str
    field2: int
    field3: bool
    # ... many more fields ...
    field50: Optional[str] = None

# Pydantic compiles validators for optimal performance
model = LargeModel(field1="test", field2=42, field3=True)

# Repeated model_dump/model_validate operations are optimized
import time
start = time.time()
for _ in range(10000):
    data = model.model_dump()
    new_model = LargeModel.model_validate(data)
duration = time.time() - start
print(f"10K conversions: {duration:.3f}s")  # Fast due to Pydantic's optimization
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

# Seamless JSON serialization with Pydantic
json_str = json.dumps(config.model_dump())
loaded_data = json.loads(json_str)
restored_config = SerializableConfig.model_validate(loaded_data)

assert config.app_name == restored_config.app_name
assert config.settings == restored_config.settings

# Pydantic also provides direct JSON methods
json_str = config.model_dump_json()  # Direct JSON serialization
restored_config = SerializableConfig.model_validate_json(json_str)  # Direct JSON parsing

# Works with exclude options for clean APIs
api_data = config.model_dump(exclude_defaults=True)
print("API data:", api_data)  # Only non-default values
```

### Error Handling Patterns

```python
# Comprehensive error handling for production use
def safe_config_load(data: dict) -> Optional[SerializableConfig]:
    """Safely load configuration with detailed Pydantic error reporting."""
    try:
        return SerializableConfig.model_validate(data)
    except ValidationError as e:
        print(f"Validation failed: {e}")
        # Pydantic provides detailed error information
        for error in e.errors():
            print(f"Field: {error['loc']}, Error: {error['msg']}")
        return None

# Validation with fallbacks
def load_config_with_fallbacks(primary_data: dict, fallback_data: dict) -> SerializableConfig:
    """Load config with fallback values on validation failure."""
    config = safe_config_load(primary_data)
    if config is None:
        print("Primary config failed, using fallback")
        config = SerializableConfig.model_validate(fallback_data)
    return config

# Usage
primary = {"app_name": 123}  # Invalid - app_name should be string
fallback = {"app_name": "DefaultApp", "version": "1.0.0", "features": [], "settings": {}}

config = load_config_with_fallbacks(primary, fallback)
assert config.app_name == "DefaultApp"  # Used fallback
```

## Function Validation with @validate

Typed includes a powerful `@validate` decorator built on Pydantic's `validate_call` that brings Pydantic's validation capabilities to regular functions. This decorator provides robust function argument validation using Pydantic's type system.

### Basic Function Validation

The `@validate` decorator leverages Pydantic's `validate_call` to automatically validate and convert function arguments:

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

The `@validate` decorator uses Pydantic's `validate_call` with optimized configuration:

- `populate_by_name=True`: Allows field population by original name and alias
- `arbitrary_types_allowed=True`: Allows any type annotations
- `validate_default=True`: Validates default parameter values at decoration time

```python
# These behaviors are enabled through Pydantic's validate_call:

@validate
def complex_function(
    data: Any,                    # Any type allowed (arbitrary_types_allowed)
    config: Dict[str, Any],       # Complex types supported
    count: int = "10"             # Default validated and converted by Pydantic
) -> str:
    return f"Processed {len(config)} items"

# Pydantic handles all validation and conversion
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