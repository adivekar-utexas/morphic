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

## Typed vs MutableTyped

Morphic provides two main data modeling classes:

- **`Typed`** - Immutable models (frozen by default) for data integrity and functional programming patterns
- **`MutableTyped`** - Mutable models that allow field modification after instantiation while maintaining validation

Both classes share the same validation, type conversion, and feature set - the only difference is mutability.

## Basic Usage

### Simple Data Models

```python
from morphic import Typed, MutableTyped
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

### Mutable Data Models

```python
class MutableUserModel(MutableTyped):
    name: str
    email: str
    age: int
    is_active: bool = True
    bio: Optional[str] = None

# Create mutable instance
mutable_user = MutableUserModel(
    name="Alice Johnson",
    email="alice@example.com",
    age=30
)

print(f"Initial: {mutable_user.name}, Active: {mutable_user.is_active}")
# Output: Initial: Alice Johnson, Active: True

# Can modify fields after creation (no validation by default for performance)
mutable_user.name = "Bob Smith"
mutable_user.age = 31
mutable_user.is_active = False

print(f"Modified: {mutable_user.name}, Age: {mutable_user.age}, Active: {mutable_user.is_active}")
# Output: Modified: Bob Smith, Age: 31, Active: False

# By default, no validation on assignment for high performance
mutable_user.age = "anything"  # Allowed for performance!

# To enable validation, explicitly set validate_assignment=True
from pydantic import ConfigDict

class ValidatedUserModel(MutableTyped):
    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,  # Enable validation
    )
    
    name: str
    age: int

validated_user = ValidatedUserModel(name="John", age=30)
try:
    validated_user.age = "not_a_number"  # Now raises ValidationError
except ValidationError:
    print("Invalid type assignment rejected")
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

### MutableTyped Configuration

MutableTyped uses the same configuration as Typed with key differences:

- `frozen=False` - Models can be modified after instantiation
- `validate_assignment=False` - No validation on assignment by default (for performance)
- `validate_private_assignment=False` - Private attribute validation also disabled by default

```python
class MutableConfig(MutableTyped):
    name: str
    value: int

config = MutableConfig(name="test", value=42)

# Can modify fields without validation (for performance)
config.name = "updated"
config.value = 100
config.value = "anything"  # Allowed! No validation for performance

# To enable validation on assignment:
from pydantic import ConfigDict

class ValidatedMutableConfig(MutableTyped):
    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,  # Enable validation
    )
    
    name: str
    value: int

validated_config = ValidatedMutableConfig(name="test", value=42)
validated_config.value = 100  # Valid

try:
    validated_config.value = "not_a_number"  # Now raises ValidationError
except ValidationError:
    print("Assignment validation failed")
```

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

### Mutable Models with Direct Modification

MutableTyped allows direct field modification without validation by default for performance:

```python
class MutableTaskList(MutableTyped):
    name: str = "Default List"
    tasks: List[str] = Field(default_factory=lambda: ["initial task"])
    metadata: Dict[str, str] = Field(default_factory=lambda: {"created": "now"})

# Create mutable instance
mutable_list = MutableTaskList()

# Can modify fields directly (no validation for performance)
mutable_list.name = "Updated List"
mutable_list.tasks = ["task1", "task2", "task3"]
mutable_list.metadata = {"updated": "now", "version": "2.0"}

print(f"Name: {mutable_list.name}")
print(f"Tasks: {mutable_list.tasks}")
print(f"Metadata: {mutable_list.metadata}")

# By default, no validation on assignment
mutable_list.tasks = "not_a_list"  # Allowed for performance!

# To enable validation, use validate_assignment=True
from pydantic import ConfigDict

class ValidatedTaskList(MutableTyped):
    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,  # Enable validation
    )
    
    name: str = "Default List"
    tasks: List[str] = Field(default_factory=list)

validated_list = ValidatedTaskList()
try:
    validated_list.tasks = "not_a_list"  # Now raises ValidationError
except ValidationError:
    print("Invalid assignment rejected")
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
from morphic import Typed, MutableTyped, Registry
from abc import ABC, abstractmethod

class ServiceConfig(Typed):
    name: str
    timeout: float = 30.0
    retries: int = 3

class MutableServiceConfig(MutableTyped):
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

# MutableTyped can be used for dynamic configuration updates
mutable_config = MutableServiceConfig(name="DynamicService", timeout=45.0)
mutable_config.timeout = 90.0  # Can update configuration
mutable_config.retries = 10

dynamic_service = Service.of("WebService", config=mutable_config)
print(dynamic_service.process())
# Output: Web service DynamicService (timeout: 90.0s)
```

## AutoEnum Integration

Typed works with AutoEnum for type-safe enumeration handling:

```python
from morphic import Typed, MutableTyped, AutoEnum
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

# MutableTyped allows priority updates
class MutableTaskModel(MutableTyped):
    title: str
    priority: Priority = "medium"
    completed: bool = False

mutable_task = MutableTaskModel(title="Dynamic task", priority="low")

# Can update priority
mutable_task.priority = "high"
mutable_task.completed = True

assert mutable_task.priority == Priority.HIGH
assert mutable_task.completed is True
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

## Lifecycle Hooks

Typed provides four lifecycle hooks that allow you to customize initialization and validation behavior:

### Hook Overview

The hooks execute in this order:

1. **`pre_initialize` (classmethod)**: Set up derived fields before validation
2. **`pre_validate` (classmethod)**: Validate and normalize input data
3. **Pydantic field validation**: Type conversion and constraint validation
4. **`post_initialize` (instance method)**: Perform side effects after validation
5. **`post_validate` (instance method)**: Validate the completed instance

### pre_initialize Hook

Use `pre_initialize` to set up derived fields that depend on multiple input fields:

```python
from datetime import datetime
from typing import Optional

class Order(Typed):
    subtotal: float
    tax_rate: float = 0.1
    total: Optional[float] = None
    order_date: Optional[str] = None

    @classmethod
    def pre_initialize(cls, data: Dict) -> None:
        # Compute total from subtotal and tax_rate
        if 'subtotal' in data:
            subtotal = float(data['subtotal'])
            tax_rate = float(data.get('tax_rate', 0.1))
            data['total'] = subtotal * (1 + tax_rate)

        # Set order date if not provided
        if data.get('order_date') is None:
            data['order_date'] = datetime.now().isoformat()

order = Order(subtotal=100.0)
assert order.total == 110.0
assert order.order_date is not None
```

Key features:
- Called after default values are set
- Can modify the input data dictionary
- Ideal for computing derived fields
- Parent class hooks are called automatically (no need for super())

### pre_validate Hook

Use `pre_validate` to normalize and validate input data:

```python
class User(Typed):
    first_name: str
    last_name: str
    email: str
    
    full_name: Optional[str] = None

    @classmethod
    def pre_initialize(cls, data: Dict) -> None:
        # Compute full_name in pre_initialize
        if 'first_name' in data and 'last_name' in data:
            data['full_name'] = f"{data['first_name']} {data['last_name']}"

    @classmethod
    def pre_validate(cls, data: Dict) -> None:
        # Normalize and validate in pre_validate
        if 'email' in data:
            data['email'] = data['email'].lower().strip()
            if '@' not in data['email']:
                raise ValueError("Invalid email format")
        
        if 'first_name' in data:
            data['first_name'] = data['first_name'].strip().title()
        
        if 'last_name' in data:
            data['last_name'] = data['last_name'].strip().title()

user = User(
    first_name="john",
    last_name="doe",
    email="  JOHN@EXAMPLE.COM  "
)
assert user.first_name == "John"
assert user.last_name == "Doe"
assert user.email == "john@example.com"
assert user.full_name == "john doe"  # Uses raw values before normalization
```

Key features:
- Called after `pre_initialize`
- Can modify the input data dictionary
- Ideal for normalization and validation
- Parent class hooks are called automatically

### post_initialize Hook

Use `post_initialize` for side effects after validation:

```python
class User(Typed):
    name: str
    email: str
    created_at: Optional[str] = None

    @classmethod
    def pre_initialize(cls, data: Dict) -> None:
        if data.get('created_at') is None:
            data['created_at'] = datetime.now().isoformat()

    def post_initialize(self) -> None:
        # Log user creation (side effect only)
        print(f"User {self.name} created at {self.created_at}")

user = User(name="John Doe", email="john@example.com")
# Output: User John Doe created at 2024-01-01T12:00:00
```

Key features:
- Called after Pydantic validation
- Works on the validated instance (read-only)
- Cannot modify frozen instance
- Ideal for logging, notifications, external system integration
- Parent class hooks are called automatically

### post_validate Hook

Use `post_validate` for cross-field validation on the completed instance:

```python
class DateRange(Typed):
    start_date: str
    end_date: str

    def post_validate(self) -> None:
        from datetime import datetime
        start = datetime.fromisoformat(self.start_date)
        end = datetime.fromisoformat(self.end_date)
        if start >= end:
            raise ValueError("start_date must be before end_date")

# Valid range
date_range = DateRange(start_date="2024-01-01", end_date="2024-01-10")

# Invalid range raises error
try:
    DateRange(start_date="2024-01-10", end_date="2024-01-01")
except ValueError as e:
    print(e)  # "start_date must be before end_date"
```

Key features:
- Called after `post_initialize`
- Works on the validated instance (read-only)
- Cannot modify frozen instance
- Ideal for validating relationships between fields
- Parent class hooks are called automatically

### Complete Lifecycle Example

Here's a complete example showing all four hooks working together:

```python
from datetime import datetime
from typing import Optional

class Invoice(Typed):
    items: List[str]
    subtotal: float
    tax_rate: float = 0.08
    
    # Derived fields
    tax_amount: Optional[float] = None
    total: Optional[float] = None
    invoice_date: Optional[str] = None
    invoice_id: Optional[str] = None

    @classmethod
    def pre_initialize(cls, data: Dict) -> None:
        """Set up derived fields before validation."""
        if 'subtotal' in data:
            subtotal = float(data['subtotal'])
            tax_rate = float(data.get('tax_rate', 0.08))
            data['tax_amount'] = round(subtotal * tax_rate, 2)
            data['total'] = round(subtotal + data['tax_amount'], 2)
        
        if data.get('invoice_date') is None:
            data['invoice_date'] = datetime.now().isoformat()

    @classmethod
    def pre_validate(cls, data: Dict) -> None:
        """Normalize and validate input data."""
        # Generate invoice ID
        if data.get('invoice_id') is None:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            data['invoice_id'] = f"INV-{timestamp}"
        
        # Validate subtotal is positive
        if 'subtotal' in data and data['subtotal'] <= 0:
            raise ValueError("Subtotal must be positive")

    def post_initialize(self) -> None:
        """Perform side effects after validation."""
        print(f"Invoice {self.invoice_id} created for ${self.total:.2f}")

    def post_validate(self) -> None:
        """Validate the completed instance."""
        if not self.items:
            raise ValueError("Invoice must have at least one item")
        
        # Verify total calculation
        expected_total = self.subtotal + self.tax_amount
        if abs(self.total - expected_total) > 0.01:
            raise ValueError(f"Total mismatch: expected {expected_total}, got {self.total}")

# Create invoice - all hooks execute automatically
invoice = Invoice(
    items=["Widget A", "Widget B"],
    subtotal=100.00
)

assert invoice.tax_amount == 8.00
assert invoice.total == 108.00
assert invoice.invoice_id.startswith("INV-")
assert invoice.invoice_date is not None
# Output: Invoice INV-20240101120000 created for $108.00
```

### Inheritance and Hook Execution

Parent class hooks are called automatically in method resolution order (MRO), from base to derived. This means you **don't need to call `super()`** in your hooks - the framework handles it automatically.

#### Basic Inheritance

```python
class BaseModel(Typed):
    name: str
    base_info: Optional[str] = None

    @classmethod
    def pre_initialize(cls, data: Dict) -> None:
        if 'name' in data:
            data['base_info'] = f"Base: {data['name']}"

class ExtendedModel(BaseModel):
    age: int
    extended_info: Optional[str] = None

    @classmethod
    def pre_initialize(cls, data: Dict) -> None:
        # Parent's pre_initialize is called automatically before this
        if 'name' in data and 'age' in data:
            data['extended_info'] = f"Extended: {data['name']} is {data['age']} years old"

model = ExtendedModel(name="John", age=30)
assert model.base_info == "Base: John"  # From parent's pre_initialize
assert model.extended_info == "Extended: John is 30 years old"  # From child's pre_initialize
```

#### Three-Level Inheritance with Mixed Hooks

This example shows how hooks at different levels of inheritance work together:

```python
class Level1(Typed):
    """Base class with pre_initialize and post_initialize."""
    name: str
    level1_computed: Optional[str] = None

    @classmethod
    def pre_initialize(cls, data: Dict) -> None:
        """Called first - sets up base computed field."""
        if 'name' in data:
            data['level1_computed'] = f"L1: {data['name']}"

    def post_initialize(self) -> None:
        """Called after validation - performs side effects."""
        print(f"Level1 initialized: {self.level1_computed}")

class Level2(Level1):
    """Middle class with pre_validate."""
    value: int
    level2_normalized: Optional[str] = None

    @classmethod
    def pre_validate(cls, data: Dict) -> None:
        """Called after pre_initialize - normalizes data."""
        if 'name' in data:
            data['level2_normalized'] = data['name'].upper()

class Level3(Level2):
    """Final class with post_validate."""
    extra: str

    def post_validate(self) -> None:
        """Called last - validates the complete instance."""
        if not self.level1_computed or not self.level2_normalized:
            raise ValueError("Missing computed fields")
        print(f"Level3 validated: {self.level2_normalized}")

# Execution order:
# 1. Default values set
# 2. Level1.pre_initialize() - sets level1_computed
# 3. Level2.pre_validate() - sets level2_normalized  
# 4. Pydantic validation
# 5. Level1.post_initialize() - prints message
# 6. Level3.post_validate() - validates and prints message

model = Level3(name="test", value=42, extra="hello")
# Output:
# Level1 initialized: L1: test
# Level3 validated: TEST

assert model.level1_computed == "L1: test"
assert model.level2_normalized == "TEST"
```

#### Multiple Hooks at Different Levels

When different classes in the hierarchy define different hooks:

```python
class A(Typed):
    """Has pre_initialize only."""
    field_a: str
    a_data: Optional[str] = None

    @classmethod
    def pre_initialize(cls, data: Dict) -> None:
        if 'field_a' in data:
            data['a_data'] = f"A: {data['field_a']}"

class B(A):
    """Has pre_initialize only."""
    field_b: str
    b_data: Optional[str] = None

    @classmethod
    def pre_initialize(cls, data: Dict) -> None:
        if 'field_b' in data:
            data['b_data'] = f"B: {data['field_b']}"

class C(B):
    """Has post_initialize only."""
    field_c: str

    def post_initialize(self) -> None:
        print(f"Created C with: {self.a_data}, {self.b_data}")

# When creating C, the execution order is:
# 1. Default values
# 2. A.pre_initialize() - sets a_data
# 3. B.pre_initialize() - sets b_data
# 4. Pydantic validation
# 5. C.post_initialize() - prints message

model = C(field_a="x", field_b="y", field_c="z")
assert model.a_data == "A: x"
assert model.b_data == "B: y"
```

#### Parent and Child with Same Hook

When both parent and child define the same hook, both are called in order:

```python
class Parent(Typed):
    name: str
    parent_field: Optional[str] = None

    @classmethod
    def pre_initialize(cls, data: Dict) -> None:
        if 'name' in data:
            data['parent_field'] = f"Parent: {data['name']}"

class Child(Parent):
    age: int
    child_field: Optional[str] = None

    @classmethod
    def pre_initialize(cls, data: Dict) -> None:
        # Parent's hook is called first automatically
        if 'name' in data:
            data['child_field'] = f"Child: {data['name']}"

model = Child(name="john", age=30)

# Both hooks run - parent first, then child
assert model.parent_field == "Parent: john"
assert model.child_field == "Child: john"
```

#### Important Notes on Inheritance

**Automatic Hook Execution:**
- All parent hooks are called automatically in MRO order (base to derived)
- You **don't need** to call `super().pre_initialize(data)` or similar
- Hooks are only called once per class in the hierarchy

**Hook Execution Order:**
1. **Pre-hooks** (classmethod): Called on raw input dict, from base to derived
   - All `pre_initialize` hooks (base → derived)
   - All `pre_validate` hooks (base → derived)
2. **Pydantic validation**: Type conversion and field validation
3. **Post-hooks** (instance method): Called on validated instance, from base to derived
   - All `post_initialize` hooks (base → derived)
   - All `post_validate` hooks (base → derived)

**Overriding Behavior:**
If you need custom control over hook execution order, override `pre_set_validate_inputs()` or `post_set_validate_inputs()`:

```python
class CustomOrder(Typed):
    name: str

    @classmethod
    def pre_set_validate_inputs(cls, data: Dict) -> Dict:
        """Override to customize pre-hook execution."""
        data = AttrDict(data)
        cls._set_default_values(data)
        
        # Custom order: skip parent hooks if needed
        cls.pre_initialize(data)
        cls.pre_validate(data)
        
        return data.to_dict()
```

**Key Differences from Manual super() Calls:**
- ✅ **Automatic**: Parent hooks called even if you forget
- ✅ **Complete**: All ancestors' hooks are called, not just immediate parent
- ✅ **Correct Order**: Guaranteed base-to-derived execution
- ❌ **Less Control**: Can't easily skip parent hooks (override `pre_set_validate_inputs` if needed)

### Hook Best Practices

1. **Use pre_initialize for derived fields** - Compute fields that depend on multiple inputs
2. **Use pre_validate for normalization and validation** - Clean and validate input data
3. **Use post_initialize for side effects** - Logging, notifications, external system integration
4. **Use post_validate for cross-field validation** - Validate relationships between fields
5. **Remember instance is frozen** - post_initialize and post_validate cannot modify the instance
6. **Leverage automatic inheritance** - Parent hooks are called automatically

### MutableTyped and Hooks

`MutableTyped` is a variant of `Typed` that allows field modification after creation. It has key differences optimized for performance:

1. **`frozen=False`**: Fields can be modified after instantiation
2. **`validate_assignment=False`**: No validation on assignment by default (for high performance)
3. **`validate_private_assignment=False`**: Private attrs also not validated by default

#### Basic Usage

```python
from morphic.typed import MutableTyped

class User(MutableTyped):
    name: str
    age: int
    active: bool = True

# Create instance (full validation at creation)
user = User(name="John", age=30)

# Can modify fields without validation (for performance)
user.name = "Jane"
user.age = 25
user.age = "anything"  # Allowed! No validation for performance
print(user.name)  # "Jane"

# To enable validation, set validate_assignment=True
from pydantic import ConfigDict

class ValidatedUser(MutableTyped):
    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,  # Enable validation
    )
    
    name: str
    age: int

validated_user = ValidatedUser(name="John", age=30)
try:
    validated_user.age = "not a number"  # Now raises ValidationError!
except ValidationError as e:
    print(e)
```

#### Hooks with MutableTyped

**Important**: Use pre-hooks for derived fields, not post-hooks. Post-hooks should only perform side effects.

```python
class UserWithScore(MutableTyped):
    name: str
    age: int
    score: Optional[int] = None

    @classmethod
    def pre_initialize(cls, data: Dict) -> None:
        # ✅ CORRECT: Set derived fields in pre_initialize
        if 'age' in data:
            data['score'] = data['age'] * 10

    def post_initialize(self) -> None:
        # ✅ CORRECT: Use post hooks for side effects only
        print(f"User {self.name} created with score {self.score}")

user = UserWithScore(name="John", age=30)
print(user.score)  # 300
```

#### Assignment Does NOT Trigger Hooks by Default

**Key Behavior**: By default, assignments in `MutableTyped` do NOT trigger validation or hooks. This is optimized for performance in tight loops and frequent modifications:

```python
class Product(MutableTyped):
    price: float
    tax_rate: float = 0.1
    total: Optional[float] = None

    @classmethod
    def pre_initialize(cls, data: Dict) -> None:
        if 'price' in data:
            tax_rate = data.get('tax_rate', 0.1)
            data['total'] = data['price'] * (1 + tax_rate)

product = Product(price=100.0)
print(product.total)  # 110.0

# By default, assignment does NOT trigger hooks (for performance)
product.price = 200.0
print(product.total)  # Still 110.0! (NOT recomputed)

# To enable hook triggering, set validate_assignment=True
from pydantic import ConfigDict

class ValidatedProduct(MutableTyped):
    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,  # Enable validation and hooks
    )
    
    price: float
    tax_rate: float = 0.1
    total: Optional[float] = None

    @classmethod
    def pre_initialize(cls, data: Dict) -> None:
        if 'price' in data:
            tax_rate = data.get('tax_rate', 0.1)
            data['total'] = data['price'] * (1 + tax_rate)

validated_product = ValidatedProduct(price=100.0)
print(validated_product.total)  # 110.0

# Now assignment triggers pre_initialize!
validated_product.price = 200.0
print(validated_product.total)  # 220.0 (automatically recomputed!)
```

#### Why Post-Hooks Can't Modify Instance

**Don't** try to modify the instance in post-hooks, even in `MutableTyped`:

```python
# ❌ WRONG - Don't do this!
class BadExample(MutableTyped):
    value: int
    doubled: Optional[int] = None

    def post_initialize(self) -> None:
        # This causes infinite recursion!
        # Assignment triggers validation → calls post_initialize → assignment...
        self.doubled = self.value * 2  # ❌ BAD!

# ✅ CORRECT - Use pre_initialize instead
class GoodExample(MutableTyped):
    value: int
    doubled: Optional[int] = None

    @classmethod
    def pre_initialize(cls, data: Dict) -> None:
        if 'value' in data:
            data['doubled'] = data['value'] * 2  # ✅ GOOD!
```

#### When to Use MutableTyped vs Typed

**Use `Typed` (frozen) when:**
- Immutability is desired for thread safety
- Data should not change after validation
- Working with configuration or settings
- Building data transfer objects (DTOs)
- Need hashable objects (dict keys, set members)

**Use `MutableTyped` when:**
- Need to modify fields after creation
- Building state machines or mutable models
- Working with ORM-like patterns
- Frequent field updates in tight loops (benefits from no validation overhead)
- Want optional validation with `validate_assignment=True` when needed

#### Performance Considerations

**By default, `MutableTyped` is optimized for performance:**
- No validation overhead on assignment (fast modifications)
- No hook execution on assignment (minimal overhead)
- Ideal for tight loops and frequent updates

```python
class Counter(MutableTyped):
    count: int = 0
    label: str = "counter"

counter = Counter()

# Very fast - no validation overhead
for i in range(1000000):
    counter.count = i  # Direct assignment, no validation

# If you need validation, enable it explicitly
from pydantic import ConfigDict

class ValidatedCounter(MutableTyped):
    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,  # Enable validation
    )
    
    count: int = 0

validated_counter = ValidatedCounter()

# Now has validation overhead (but ensures correctness)
for i in range(1000):
    validated_counter.count = i  # Validated each time
```

**When to enable `validate_assignment=True`:**
- Data integrity is critical
- Assignments come from untrusted sources
- Catching type errors during development
- Assignment frequency is low

**When to keep `validate_assignment=False` (default):**
- High-performance scenarios (tight loops, frequent updates)
- Internal state management where types are controlled
- You trust the assignment sources
- You want minimal overhead

### Nested Typed Objects and Hooks

When working with nested `Typed` objects, **automatic conversion happens before hooks run**, making it easy to work with nested data.

#### Automatic Nested Type Conversion

Nested `Typed` fields are **automatically converted from dicts to objects** before any hooks (`pre_initialize`, `pre_validate`, etc.) are called. This means you can directly access nested objects and their computed fields without manual conversion:

```python
class Address(Typed):
    street: str
    city: str
    full_address: Optional[str] = None

    @classmethod
    def pre_initialize(cls, data: Dict) -> None:
        if 'street' in data and 'city' in data:
            data['full_address'] = f"{data['street']}, {data['city']}"

class Person(Typed):
    name: str
    address: Address
    summary: Optional[str] = None

    @classmethod
    def pre_initialize(cls, data: Dict) -> None:
        # address is already an Address object (not a dict!)
        if 'address' in data:
            addr = data['address']
            assert isinstance(addr, Address)
            # Can access computed fields directly
            data['summary'] = f"{data['name']} from {addr.full_address}"

# Pass nested data as dict - automatic conversion happens
person = Person(
    name="John",
    address={"street": "123 Main St", "city": "NYC"}
)
assert person.summary == "John from 123 Main St, NYC"
assert person.address.full_address == "123 Main St, NYC"
```

#### Hook Execution Order with Nesting

With automatic conversion, the execution order is:

```python
class Inner(Typed):
    value: int
    inner_computed: Optional[str] = None

    @classmethod
    def pre_initialize(cls, data: Dict) -> None:
        if 'value' in data:
            data['inner_computed'] = f"Inner: {data['value']}"

class Outer(Typed):
    name: str
    inner: Inner
    outer_computed: Optional[str] = None

    @classmethod
    def pre_initialize(cls, data: Dict) -> None:
        # inner is already an Inner object
        if 'inner' in data:
            data['outer_computed'] = f"Outer: {data['inner'].inner_computed}"

# Execution order:
# 1. Set default values for Outer
# 2. Convert nested dicts to objects:
#    a. Set default values for Inner
#    b. Inner.pre_initialize
#    c. Inner.pre_validate
#    d. Inner Pydantic validation
# 3. Outer.pre_initialize (inner is now an object)
# 4. Outer.pre_validate
# 5. Outer Pydantic validation
# 6. Inner.post_initialize
# 7. Inner.post_validate
# 8. Outer.post_initialize
# 9. Outer.post_validate

outer = Outer(name="test", inner={"value": 42})
```

#### Supported Nested Conversions

Automatic conversion works for:

- **Direct fields**: `address: Address` → dict converted to Address
- **Optional fields**: `address: Optional[Address]` → dict converted to Address (if not None)
- **Lists**: `addresses: List[Address]` → all dicts in list converted to Address objects
- **Dicts**: `locations: Dict[str, Address]` → all dict values converted to Address objects

```python
class Item(Typed):
    name: str
    price: float
    display: Optional[str] = None

    @classmethod
    def pre_initialize(cls, data: Dict) -> None:
        if 'name' in data and 'price' in data:
            data['display'] = f"{data['name']}: ${data['price']}"

class Order(Typed):
    items: List[Item]
    total: float
    summary: Optional[str] = None

    @classmethod
    def pre_initialize(cls, data: Dict) -> None:
        # All items are already Item objects
        if 'items' in data:
            items = data['items']
            assert all(isinstance(item, Item) for item in items)
            # Access computed fields
            displays = [item.display for item in items]
            data['summary'] = f"Order: {', '.join(displays)}"

order = Order(
    items=[
        {"name": "Widget", "price": 10.0},
        {"name": "Gadget", "price": 20.0}
    ],
    total=30.0
)
assert order.summary == "Order: Widget: $10.0, Gadget: $20.0"
```

#### Deeply Nested Objects

Automatic conversion works recursively for deeply nested structures:

```python
class Level3(Typed):
    value: str
    level3_data: Optional[str] = None

    @classmethod
    def pre_initialize(cls, data: Dict) -> None:
        if 'value' in data:
            data['level3_data'] = f"L3: {data['value']}"

class Level2(Typed):
    level3: Level3
    level2_data: Optional[str] = None

    @classmethod
    def pre_initialize(cls, data: Dict) -> None:
        # Nested object is already converted
        if 'level3' in data:
            level3_obj = data['level3']
            assert isinstance(level3_obj, Level3)
            # Access its computed field
            data['level2_data'] = f"L2: {level3_obj.level3_data}"

class Level1(Typed):
    level2: Level2
    level1_data: Optional[str] = None

    @classmethod
    def pre_initialize(cls, data: Dict) -> None:
        # Can traverse nested objects directly
        if 'level2' in data:
            level2_obj = data['level2']
            assert isinstance(level2_obj, Level2)
            # Access deeply nested computed field
            data['level1_data'] = f"L1: {level2_obj.level3.level3_data}"

model = Level1(level2={"level3": {"value": "deep"}})
assert model.level1_data == "L1: L3: deep"
assert model.level2.level2_data == "L2: L3: deep"
assert model.level2.level3.level3_data == "L3: deep"
```

#### Nested MutableTyped Behavior

With `MutableTyped`, modifying a nested object's field triggers its hooks, but doesn't update the parent:

```python
class MutableInner(MutableTyped):
    value: int
    doubled: Optional[int] = None

    @classmethod
    def pre_initialize(cls, data: Dict) -> None:
        if 'value' in data:
            data['doubled'] = data['value'] * 2

class MutableOuter(MutableTyped):
    name: str
    inner: MutableInner
    summary: Optional[str] = None

    @classmethod
    def pre_initialize(cls, data: Dict) -> None:
        if 'name' in data and 'inner' in data:
            inner_obj = data['inner']
            # Already converted to object
            assert isinstance(inner_obj, MutableInner)
            data['summary'] = f"{data['name']}: {inner_obj.doubled}"

outer = MutableOuter(name="test", inner={"value": 10})
assert outer.summary == "test: 20"

# Modify nested object
outer.inner.value = 15
assert outer.inner.doubled == 30  # Inner hook ran, recomputed!

# Parent's summary is NOT automatically updated
assert outer.summary == "test: 20"  # Still old value
```

#### Best Practices for Nested Objects

1. **No manual conversion needed**: Nested objects are automatically converted before hooks
2. **Access computed fields directly**: Nested objects have already run their hooks
3. **Type checking**: Objects are guaranteed to be the correct type (not dicts)
4. **Deep nesting works seamlessly**: All levels are recursively converted
5. **MutableTyped caveat**: Parent objects don't auto-update when children change

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

# MutableTyped for mutable models
class MutableTypedModel(MutableTyped):
    name: str
    age: int
    
    # Same features as Typed but allows field modification
    
# Both work similarly for basic operations
model1 = PydanticModel(name="John", age=30)
model2 = TypedModel(name="John", age=30)
model3 = MutableTypedModel(name="John", age=30)

# But Typed provides additional morphic integration
# and is configured with sensible defaults for morphic use cases

# MutableTyped allows modification
model3.name = "Jane"
model3.age = 25
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

## Private Attribute Validation

Typed provides automatic validation for private attributes (those prefixed with `_`) when `validate_private_assignment=True`. This ensures type safety for private attributes used for internal state management, caching, or computed values.

### Overview

By default, Pydantic does not validate private attributes defined with `PrivateAttr()`. However, `Typed` extends this behavior to provide automatic validation when the model has `validate_private_assignment=True` enabled (which is the default for `Typed`).

**Key Features:**
- Automatic validation of private attributes against their type annotations
- Type coercion works the same as for public fields
- Supports all Pydantic types: primitives, Optional, Union, collections, nested Typed models
- Supports arbitrary types (like `threading.Thread`, custom classes) with isinstance checks
- Respects the `validate_private_assignment` configuration setting
- Untyped private attributes (no type hint) remain unvalidated for flexibility

### Basic Usage

```python
from pydantic import PrivateAttr
from morphic import Typed

class Counter(Typed):
    name: str
    _count: int = PrivateAttr(default=0)
    _cache: Optional[str] = PrivateAttr(default=None)
    
    def post_initialize(self) -> None:
        # Private attributes are validated when set
        self._count = 10  # ✓ Valid: int
        self._cache = "cached_value"  # ✓ Valid: str

counter = Counter(name="MyCounter")

# Can modify private attributes (unlike public fields which are frozen)
counter._count = 20  # ✓ Valid: int value
counter._count = "42"  # ✓ Valid: string coerced to int(42)

# Invalid assignments raise ValidationError with detailed error message
try:
    counter._count = "invalid"  # ✗ Cannot convert to int
except ValidationError as e:
    print(e)
    # Output: Pydantic ValidationError with structured error information
```

### Type Coercion

Private attributes benefit from the same type coercion as public fields:

```python
class Model(Typed):
    name: str
    _score: float = PrivateAttr(default=0.0)
    _active: bool = PrivateAttr(default=False)
    _tags: List[str] = PrivateAttr(default_factory=list)

model = Model(name="test")

# Type coercion works automatically
model._score = "3.14"  # String → float(3.14)
model._active = "true"  # String → bool (Pydantic conversion)
model._tags = ["tag1", "tag2"]  # List validation with element coercion
```

### Complex Types

Private attributes support all Pydantic type annotations:

```python
from typing import Optional, Union, List, Dict

class System(Typed):
    name: str
    
    # Optional types
    _config: Optional[Dict[str, str]] = PrivateAttr(default=None)
    
    # Union types
    _value: Union[int, str] = PrivateAttr(default=0)
    
    # Collections
    _items: List[int] = PrivateAttr(default_factory=list)
    
    # Nested Typed models
    _metadata: Optional["ConfigModel"] = PrivateAttr(default=None)

system = System(name="MySystem")

# All types are validated
system._config = {"key": "value"}  # ✓ Valid
system._value = 42  # ✓ Valid: int
system._value = "hello"  # ✓ Valid: str (Union allows both)
system._items = ["1", "2", "3"]  # ✓ Valid: strings coerced to ints
system._metadata = {"setting": "value"}  # ✓ Valid: dict converted to ConfigModel
```

### Nested Typed Models

Private attributes can hold nested Typed models with automatic conversion:

```python
class Config(Typed):
    host: str
    port: int

class Service(Typed):
    name: str
    _config: Optional[Config] = PrivateAttr(default=None)
    
    def post_initialize(self) -> None:
        # Set initial configuration
        self._config = {"host": "localhost", "port": 8080}

service = Service(name="API")

# Dict automatically converted to Config instance
assert isinstance(service._config, Config)
assert service._config.host == "localhost"

# Can also set Config instances directly
service._config = Config(host="0.0.0.0", port=9000)
```

### Arbitrary Types

Private attributes support arbitrary types (like `threading.Thread`, custom classes, etc.) that Pydantic can't automatically validate. When Pydantic's TypeAdapter cannot create a schema for a type, Typed falls back to simple `isinstance()` checks:

```python
import threading
from pydantic import PrivateAttr

class ThreadManager(Typed):
    name: str
    _thread: Optional[threading.Thread] = PrivateAttr(default=None)
    _worker_thread: Optional[threading.Thread] = PrivateAttr(default=None)
    
    def post_initialize(self) -> None:
        # Can set arbitrary types like Thread
        self._thread = threading.Thread(target=lambda: None)
        self._worker_thread = threading.Thread(target=self.work)
    
    def work(self):
        print("Working...")

manager = ThreadManager(name="BackgroundManager")

# Arbitrary types are validated with isinstance()
assert isinstance(manager._thread, threading.Thread)

# Can modify private attributes
new_thread = threading.Thread(target=lambda: print("New task"))
manager._thread = new_thread  # ✓ Valid: Thread instance

# Type checking still enforced
try:
    manager._thread = "not a thread"  # ✗ TypeError
except ValidationError as e:
    print(e)  # Error: Pydantic ValidationError with type mismatch details
```

**How It Works:**
1. Typed first tries to use Pydantic's TypeAdapter for validation
2. If TypeAdapter can't create a schema (for arbitrary types), falls back to:
   - For concrete types (like `threading.Thread`): simple `isinstance()` check
   - For `Optional[ArbitraryType]`: checks for None or isinstance of the inner type
   - For other generic types with arbitrary inner types: no validation (too complex without TypeAdapter)

**Supported Patterns:**
- Direct arbitrary types: `_thread: threading.Thread`
- Optional arbitrary types: `_thread: Optional[threading.Thread]`
- Union of arbitrary types: `_resource: Union[ThreadType, ProcessType]` (with isinstance checks)

### Untyped Private Attributes

Private attributes without type hints are not validated, providing flexibility:

```python
class FlexibleModel(Typed):
    name: str
    
    def post_initialize(self) -> None:
        # No type annotation = no validation
        self._anything = "string"

model = FlexibleModel(name="test")

# Can set to any type - no validation
model._anything = "string"
model._anything = 123
model._anything = [1, 2, 3]
model._anything = {"key": "value"}
```

### Configuration Control

Private attribute validation respects the `validate_private_assignment` configuration:

```python
from pydantic import ConfigDict, PrivateAttr

# Validation enabled (default for Typed)
class ValidatedModel(Typed):
    name: str
    _count: int = PrivateAttr(default=0)

model = ValidatedModel(name="test")
model._count = 42  # ✓ Validated
# model._count = "invalid"  # ✗ Raises ValidationError

# Validation disabled
class UnvalidatedModel(Typed):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_private_assignment=False,  # Disable private attribute validation
    )
    
    name: str
    _count: int = PrivateAttr(default=0)

model2 = UnvalidatedModel(name="test")
model2._count = "anything"  # ✓ No validation (assignment allowed)
```

**Note:** This is separate from Pydantic's `validate_assignment` setting, which controls validation of **public** field assignments. For `Typed` (frozen models), `validate_assignment` is not needed since public fields cannot be modified. For `MutableTyped`, `validate_assignment=True` enables validation of public field modifications.

### Inheritance

Private attribute validation works across inheritance hierarchies:

```python
class Parent(Typed):
    name: str
    _parent_data: int = PrivateAttr(default=0)

class Child(Parent):
    age: int
    _child_data: str = PrivateAttr(default="")

child = Child(name="test", age=10)

# Both parent and child private attributes are validated
child._parent_data = 42  # ✓ Valid: int
child._child_data = "data"  # ✓ Valid: str

# Both enforce their types
# child._parent_data = "invalid"  # ✗ ValidationError
# child._child_data = 123  # ✗ ValidationError
```

Child classes can override parent private attribute types:

```python
class Parent(Typed):
    name: str
    _value: int = PrivateAttr(default=0)

class Child(Parent):
    age: int
    _value: str = PrivateAttr(default="")  # Override with different type

child = Child(name="test", age=10)

# Child's type annotation takes precedence
child._value = "hello"  # ✓ Valid: str (child's type)
# child._value = 123  # ✗ ValidationError (child expects str)
```

### Using with post_initialize

Private attributes are commonly set in `post_initialize` hooks:

```python
class Rectangle(Typed):
    width: int
    height: int
    _area: int = PrivateAttr()
    _perimeter: int = PrivateAttr()
    
    def post_initialize(self) -> None:
        # Compute derived values - all validated
        self._area = self.width * self.height
        self._perimeter = 2 * (self.width + self.height)

rect = Rectangle(width=5, height=3)
assert rect._area == 15
assert rect._perimeter == 16

# Can update computed values later
rect._area = 20  # ✓ Valid: int
```

### Error Messages

Validation errors provide detailed information:

```python
from pydantic import PrivateAttr

class Model(Typed):
    name: str
    _count: int = PrivateAttr(default=0)

model = Model(name="test")

try:
    model._count = "invalid"
except ValidationError as e:
    print(e)
    # Output: Pydantic ValidationError with structured error information
    # Including:
    # Cannot set private attribute '_count'.
    # Expected type: int, got value of type str: 'invalid'
    # Validation errors:
    # Input should be a valid integer, unable to parse string as an integer
```

### Best Practices

1. **Use Type Hints**: Always provide type annotations for private attributes you want validated
2. **Leverage Defaults**: Use `PrivateAttr(default=...)` or `PrivateAttr(default_factory=...)` for initialization
3. **Computed Values**: Set derived values in `post_initialize` or `pre_initialize` hooks
4. **Respect Configuration**: Models can opt out with `validate_private_assignment=False` if needed
5. **Untyped Flexibility**: Omit type hints for truly dynamic private attributes

### When to Use Private Attribute Validation

**Good Use Cases:**
- Caching computed values with type safety
- Internal state management requiring validation
- Derived fields that depend on multiple public fields
- Memoization of expensive operations

**Consider Alternatives:**
- For truly dynamic values, use untyped private attributes
- For public API, use regular fields (with `frozen=False` via `MutableTyped`)
- For complex validation, use `post_validate` hooks instead

### MutableTyped and Private Attributes

`MutableTyped` does NOT validate private attributes by default (for performance):

```python
class MutableCounter(MutableTyped):
    name: str
    _count: int = PrivateAttr(default=0)

counter = MutableCounter(name="test")

# By default, no validation for performance
counter._count = 10  # ✓ Valid
counter._count = "anything"  # ✓ Also valid (no validation)

# Public fields can also be modified without validation
counter.name = "updated"  # ✓ Valid (no validation by default)

# To enable validation, set validate_assignment=True and validate_private_assignment=True
from pydantic import ConfigDict

class ValidatedCounter(MutableTyped):
    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,  # Validate public fields
        validate_private_assignment=True,  # Validate private attrs
    )
    
    name: str
    _count: int = PrivateAttr(default=0)

validated_counter = ValidatedCounter(name="test")
validated_counter._count = 10  # ✓ Valid
# validated_counter._count = "invalid"  # ✗ Now raises ValidationError
```

**Configuration Summary:**
- `Typed`: `frozen=True`, `validate_assignment=False`, `validate_private_assignment=True` (private attrs validated, public fields frozen)
- `MutableTyped`: `frozen=False`, `validate_assignment=False`, `validate_private_assignment=False` (neither validated by default for performance)

## Choosing Between Typed and MutableTyped

### When to Use Typed (Immutable)

Use `Typed` when you want:
- **Data integrity** - Prevent accidental modifications
- **Functional programming** - Immutable data structures
- **Thread safety** - Immutable objects are inherently thread-safe
- **Hashable objects** - Can be used as dictionary keys
- **Configuration objects** - Settings that shouldn't change after creation

```python
class DatabaseConfig(Typed):
    host: str
    port: int
    database: str

# Configuration is immutable - prevents accidental changes
config = DatabaseConfig(host="localhost", port=5432, database="myapp")
# config.port = 3306  # This would raise an error
```

### When to Use MutableTyped

Use `MutableTyped` when you need:
- **Dynamic updates** - Fields that change during runtime
- **State management** - Objects that represent changing state
- **High-frequency updates** - Tight loops or frequent modifications (benefits from no validation)
- **Performance-critical code** - Fast modifications without validation overhead
- **User input processing** - Forms or data that gets updated
- **Caching objects** - Data that gets refreshed periodically
- **Builder patterns** - Objects constructed incrementally

```python
class UserSession(MutableTyped):
    user_id: str
    login_time: datetime
    last_activity: datetime
    permissions: List[str] = []
    request_count: int = 0

# Session state can be updated frequently without validation overhead
session = UserSession(user_id="123", login_time=datetime.now(), last_activity=datetime.now())

# Fast updates in tight loop (no validation)
for _ in range(10000):
    session.request_count += 1  # Very fast!

session.permissions = ["read", "write"]
```

### Performance Considerations

**Creation time**: Both `Typed` and `MutableTyped` have identical validation at creation.

**After creation**:
- **Typed** - Cannot modify fields (fastest, most secure)
- **MutableTyped (default)** - Fast modifications without validation (optimized for performance)
- **MutableTyped (validate_assignment=True)** - Validated modifications (slower but ensures correctness)

```python
# Performance comparison
class TypedCounter(Typed):
    count: int = 0

class MutableCounter(MutableTyped):
    count: int = 0

class ValidatedMutableCounter(MutableTyped):
    model_config = ConfigDict(frozen=False, validate_assignment=True)
    count: int = 0

# Typed: Cannot modify after creation
typed = TypedCounter()
# typed.count = 1  # Error!

# MutableTyped: Fast modifications (no validation)
mutable = MutableCounter()
for i in range(1000000):
    mutable.count = i  # Very fast!

# ValidatedMutableCounter: Validated modifications (slower)
validated = ValidatedMutableCounter()
for i in range(1000):
    validated.count = i  # Slower due to validation
```

### Best Practices

1. **Default to Typed** - Use immutable models unless you specifically need mutability
2. **Use MutableTyped for state** - When objects represent changing state or frequent updates
3. **Enable validation when needed** - Set `validate_assignment=True` when data integrity is critical
4. **Optimize for performance** - Keep default `validate_assignment=False` for tight loops
5. **Consider thread safety** - `Typed` is thread-safe, `MutableTyped` requires synchronization
6. **Validate at boundaries** - Validate input at creation time, skip validation for internal updates
7. **Use appropriate patterns** - Immutable for functional/configuration, mutable for state/performance

## Next Steps

- Learn more about [Registry System](registry.md) integration patterns
- Explore [AutoEnum](autoenum.md) for automatic enumeration creation
- Check out complete [Examples](../examples.md) with real-world use cases