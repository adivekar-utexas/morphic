# Typed + Registry Integration

Learn how to combine morphic's `Typed` validation with `Registry` factory patterns for powerful, type-safe model hierarchies.

## Overview

The integration between `Typed` and `Registry` provides the best of both worlds:

- **Pydantic Validation**: Automatic type checking, conversion, and validation
- **Factory Patterns**: Hierarchical class registration and intelligent instantiation  
- **Seamless API**: Single `of()` method that handles both patterns intelligently

## Inheritance Order

**Important**: When inheriting from both `Typed` and `Registry`, always use the order `Typed, Registry`:

```python
# ✅ Correct inheritance order
class MyModel(Typed, Registry, ABC):
    pass

# ❌ Incorrect order - Registry's of() method won't delegate properly
class MyModel(Registry, Typed, ABC):
    pass
```

This ensures that `Typed`'s enhanced `of()` method can properly delegate to `Registry` when needed.

## Basic Usage

### Simple Hierarchy with Validation

```python
from morphic.typed import Typed
from morphic.registry import Registry
from abc import ABC, abstractmethod

class Animal(Typed, Registry, ABC):
    name: str
    species: str
    age: int = 0
    
    @abstractmethod
    def speak(self) -> str:
        pass

class Dog(Animal):
    aliases = ["canine", "puppy"]
    
    def speak(self) -> str:
        return f"{self.name} says Woof!"

class Cat(Animal):
    aliases = ["feline", "kitty"]
    
    def speak(self) -> str:
        return f"{self.name} says Meow!"

# Registry factory with automatic validation
dog = Animal.of("Dog", name="Rex", species="Canis lupus", age="3")
print(f"{dog.name} is {dog.age} years old")  # age converted from string to int
print(dog.speak())  # "Rex says Woof!"

# Alias support with validation
cat = Animal.of("feline", name="Shadow", species="Felis catus", age=2)
print(cat.speak())  # "Shadow says Meow!"
```

### Direct Concrete Instantiation

```python
# Concrete classes can be instantiated directly
buddy = Dog.of(name="Buddy", species="Canis lupus", age="5")
print(f"{buddy.name} is {buddy.age} years old")

# Registry key also works for concrete classes
rex = Dog.of("Dog", name="Rex", species="Canis lupus")
```

## Key Features

### 1. Automatic Type Conversion

All Pydantic type conversions work seamlessly with Registry factories:

```python
class DatabaseConfig(Typed, Registry, ABC):
    host: str = "localhost"
    port: int = 5432
    ssl: bool = False
    timeout: float = 30.0
    max_connections: Optional[int] = None

class PostgreSQLConfig(DatabaseConfig):
    aliases = ["postgres", "pg"]

# String values automatically converted to correct types
db = DatabaseConfig.of(
    "postgres",
    host="remote.db",
    port="5433",           # str → int
    ssl="true",            # str → bool
    timeout="45.5",        # str → float
    max_connections="100"  # str → int
)

print(f"Port: {db.port} ({type(db.port)})")  # Port: 5433 (<class 'int'>)
print(f"SSL: {db.ssl} ({type(db.ssl)})")     # SSL: True (<class 'bool'>)
```

### 2. Nested Model Validation

Nested Typed models are automatically validated:

```python
class Address(Typed):
    street: str
    city: str
    zipcode: str

class Person(Typed, Registry, ABC):
    name: str
    age: int
    address: Address

class Employee(Person):
    department: str = "general"

# Nested dict automatically converted to Address model
employee = Person.of(
    "Employee",
    name="Alice",
    age="30",
    address={  # Dict converted to Address instance
        "street": "123 Main St",
        "city": "Springfield", 
        "zipcode": "12345"
    },
    department="engineering"
)

print(f"{employee.name} works in {employee.department}")
print(f"Address: {employee.address.street}, {employee.address.city}")
```

### 3. Field Constraints and Validation

Pydantic field constraints work with Registry factories:

```python
from pydantic import Field

class Product(Typed, Registry, ABC):
    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., gt=0)
    quantity: int = Field(default=1, ge=0)

class Electronics(Product):
    warranty_months: int = Field(default=12, ge=0, le=120)

# Valid product with constraint validation
laptop = Product.of(
    "Electronics",
    name="Gaming Laptop",
    price="1299.99",      # Converted and validated > 0
    quantity="5",         # Converted and validated >= 0
    warranty_months="24"  # Converted and validated 0 <= x <= 120
)

# Constraint violations raise detailed errors
try:
    Product.of("Electronics", name="", price="-100")  # Invalid name and price
except ValueError as e:
    print(f"Validation error: {e}")
```

### 4. Hierarchical Scoping

Registry's hierarchical scoping is preserved with validation:

```python
class Transport(Typed, Registry, ABC):
    name: str
    max_speed: int

class LandTransport(Transport, ABC):
    wheels: int = 4
    
class WaterTransport(Transport, ABC):
    draft: float = 1.0

class Car(LandTransport):
    fuel_type: str = "gasoline"

class Boat(WaterTransport):
    hull_type: str = "fiberglass"

# Hierarchical scoping enforced
car = LandTransport.of("Car", name="Sedan", max_speed=120, wheels=4, fuel_type="electric")
boat = WaterTransport.of("Boat", name="Yacht", max_speed=30, draft=2.5, hull_type="aluminum")

# Cross-hierarchy access fails
try:
    LandTransport.of("Boat", name="Invalid")  # KeyError
except KeyError as e:
    print("Correctly rejected cross-hierarchy access")
```

## Advanced Patterns

### 1. AutoEnum Integration

Use AutoEnum for semantic registry keys:

```python
from morphic.autoenum import AutoEnum, auto

class ServiceType(AutoEnum):
    WEB = auto()
    DATABASE = auto()
    CACHE = auto()

class Service(Typed, Registry, ABC):
    name: str
    version: str = "1.0"
    port: int

class WebService(Service):
    aliases = [ServiceType.WEB]
    protocol: str = "http"

class DatabaseService(Service):
    aliases = [ServiceType.DATABASE]
    engine: str = "postgresql"

# Use AutoEnum as registry key
web = Service.of(ServiceType.WEB, name="api", port=8080, protocol="https")
db = Service.of(ServiceType.DATABASE, name="primary", port=5432, engine="mysql")
```

### 2. Complex Validation Patterns

Combine custom validators with Registry patterns:

```python
from pydantic import field_validator

class User(Typed, Registry, ABC):
    email: str
    age: int
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v.lower()
    
    @field_validator('age')
    @classmethod
    def validate_age(cls, v):
        if v < 0 or v > 150:
            raise ValueError('Age must be between 0 and 150')
        return v

class AdminUser(User):
    permissions: List[str] = []

# Validation runs during Registry factory
admin = User.of(
    "AdminUser",
    email="ADMIN@EXAMPLE.COM",  # Converted to lowercase
    age="30",                   # Converted to int and validated
    permissions=["read", "write", "admin"]
)

print(admin.email)  # "admin@example.com"
```

### 3. Optional Fields and Defaults

Handle optional fields elegantly:

```python
class APIConfig(Typed, Registry, ABC):
    endpoint: str
    api_key: Optional[str] = None
    timeout: float = 30.0
    retries: int = 3
    headers: Dict[str, str] = {}

class RESTConfig(APIConfig):
    method: str = "GET"

# Minimal configuration
config = APIConfig.of(
    "RESTConfig",
    endpoint="https://api.example.com"
    # All other fields use defaults
)

# Full configuration with type conversion
config2 = APIConfig.of(
    "RESTConfig",
    endpoint="https://api.example.com",
    api_key="secret-key",
    timeout="45.0",  # str → float
    retries="5",     # str → int
    headers={"Authorization": "Bearer token"},
    method="POST"
)
```

## Error Handling

The integration preserves both Registry and Pydantic error patterns:

### Registry Errors

```python
class Service(Typed, Registry, ABC):
    name: str

class WebService(Service):
    pass

try:
    Service.of("UnknownService", name="test")
except KeyError as e:
    print(f"Registry error: {e}")
    # Shows available keys in hierarchy
```

### Validation Errors

```python
try:
    Service.of("WebService", name="test", port="invalid")
except ValueError as e:
    print(f"Validation error: {e}")
    # Detailed Pydantic validation error with field info
```

### Combined Errors

```python
class ComplexService(Typed, Registry, ABC):
    name: str
    config: Dict[str, Any]

try:
    # Multiple error possibilities
    ComplexService.of("NonExistent", name="", config="invalid")
except (KeyError, ValueError) as e:
    if isinstance(e, KeyError):
        print("Registry lookup failed")
    else:
        print("Validation failed")
```

## Performance Considerations

The integration adds minimal overhead:

- **Registry Delegation**: Single MRO check (O(1))
- **Pydantic Validation**: Standard Pydantic performance
- **Factory Lookup**: Hash table operations (O(1))

```python
# Performance is maintained even with many subclasses
class BaseProcessor(Typed, Registry, ABC):
    name: str

# 100+ registered subclasses perform well
for i in range(100):
    processor = BaseProcessor.of(f"Processor{i}", name=f"proc_{i}")
```

## Best Practices

### 1. Define All Fields in Typed Models

Since Typed models are frozen, define all fields in the base model:

```python
# ✅ Good: All fields defined in Typed model
class Animal(Typed, Registry, ABC):
    name: str
    species: str
    breed: str = "unknown"
    age: int = 0

class Dog(Animal):
    def speak(self):
        return f"{self.name} barks"

# ❌ Avoid: Adding fields in __init__ after Typed validation
class Cat(Animal):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.custom_field = "value"  # Error: frozen instance
```

### 2. Use Meaningful Registry Keys

Combine semantic keys with Pydantic validation:

```python
class MLModel(Typed, Registry, ABC):
    name: str
    version: str
    accuracy: float = Field(..., ge=0.0, le=1.0)

class RandomForest(MLModel):
    @classmethod
    def _registry_keys(cls):
        return [
            ("algorithm", "random_forest"),
            ("type", "ensemble"),
            "rf"
        ]

# Semantic access with validation
model = MLModel.of(
    ("algorithm", "random_forest"),
    name="Forest Classifier",
    version="2.1",
    accuracy="0.95"  # Converted and validated
)
```

### 3. Leverage Type Hints

Full type safety with IDE support:

```python
from typing import TypeVar

T = TypeVar('T', bound='Service')

class Service(Typed, Registry, ABC):
    name: str
    
    @classmethod
    def of(cls: Type[T], registry_key: Optional[Any] = None, **data) -> T:
        # IDE knows return type is subclass of Service
        return super().of(registry_key, **data)

# Full type safety
web_service: WebService = Service.of("WebService", name="api")
```

## Migration Guide

### From Pure Registry

```python
# Before: Pure Registry
class OldService(Registry, ABC):
    def __init__(self, name, port=80):
        self.name = name
        self.port = port

# After: Typed + Registry  
class NewService(Typed, Registry, ABC):
    name: str
    port: int = 80

# Same factory API, now with validation
service = NewService.of("ServiceImpl", name="api", port="8080")
```

### From Pure Typed

```python
# Before: Pure Typed
class OldModel(Typed):
    name: str
    
    @classmethod
    def create_user_model(cls, name: str):
        return cls(name=name)

# After: Typed + Registry
class NewModel(Typed, Registry, ABC):
    name: str

class UserModel(NewModel):
    pass

# Enhanced factory with registry support
user = NewModel.of("UserModel", name="john")
```

## Troubleshooting

### Common Issues

1. **Frozen Instance Error**: Add all fields to the Typed model instead of `__init__`
2. **Wrong Inheritance Order**: Use `Typed, Registry, ABC` order  
3. **Registry Not Found**: Ensure concrete classes inherit from the base
4. **Validation Ignored**: Check that Typed comes first in MRO

### Debug Tips

```python
# Check method resolution order
print(MyClass.__mro__)

# Verify Registry integration
from morphic.registry import Registry
print(Registry in MyClass.__mro__)

# Test validation separately
try:
    instance = MyClass(field="invalid")
except ValueError as e:
    print(f"Direct validation: {e}")
```

## Summary

The Typed + Registry integration provides:

- ✅ **Automatic Validation**: All Registry factories include Pydantic validation
- ✅ **Type Safety**: Full type conversion and constraint checking  
- ✅ **Hierarchical Factories**: Registry's powerful factory patterns preserved
- ✅ **Backward Compatible**: Existing code continues to work
- ✅ **Performance**: Minimal overhead with maximum functionality

This combination enables building robust, validated model hierarchies with powerful factory patterns for complex applications.
