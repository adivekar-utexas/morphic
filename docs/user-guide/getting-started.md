# Getting Started

This guide will walk you through the core concepts and basic usage of Morphic.

## Core Concepts

Morphic provides three main components:

1. **Registry System** - Inheritance-based class registration with hierarchical factory patterns
2. **AutoEnum** - Automatic enumeration creation from class hierarchies
3. **Typed** - Enhanced data modeling capabilities with validation

## Registry System Basics

The Registry system automatically registers classes through inheritance and provides hierarchical factory methods for instance creation.

### Automatic Class Registration

Classes automatically register themselves when they inherit from `Registry`:

```python
from morphic.registry import Registry
from abc import ABC, abstractmethod

# Base registry class
class Animal(Registry, ABC):
    @abstractmethod
    def speak(self) -> str:
        pass

# Classes automatically register when inheriting
class Dog(Animal):
    def __init__(self, name: str = "Buddy"):
        self.name = name

    def speak(self) -> str:
        return f"{self.name} says Woof!"

class Cat(Animal):
    def __init__(self, name: str = "Whiskers"):
        self.name = name

    def speak(self) -> str:
        return f"{self.name} says Meow!"
```

### Hierarchical Factory Pattern

The Registry provides intelligent factory methods that work differently based on class hierarchy:

#### Direct Instantiation (Concrete Classes)

```python
# Concrete classes can be instantiated directly without registry keys
dog = Dog.of()  # Creates Dog with default name "Buddy"
cat = Cat.of(name="Shadow")  # Creates Cat with custom name

print(dog.speak())  # "Buddy says Woof!"
print(cat.speak())  # "Shadow says Meow!"
```

#### Factory Method (Abstract Classes)

```python
# Abstract classes require registry keys and look only in their hierarchy
dog = Animal.of("Dog", name="Rex")  # Uses registry key to find Dog class
cat = Animal.of("Cat", name="Fluffy")  # Uses registry key to find Cat class

print(dog.speak())  # "Rex says Woof!"
print(cat.speak())  # "Fluffy says Meow!"
```

#### Hierarchical Scoping

The factory method respects class inheritance - classes can only create instances of their subclasses:

```python
class Mammal(Animal, ABC):
    warm_blooded = True

class Cat(Mammal, ABC):  # Abstract cat base
    def __init__(self, name: str = "Cat"):
        self.name = name

class TabbyCat(Cat):
    def speak(self) -> str:
        return f"{self.name} the tabby says Meow!"

class Dog(Mammal):  # Concrete dog
    def __init__(self, name: str = "Dog"):
        self.name = name

    def speak(self) -> str:
        return f"{self.name} says Woof!"

# Hierarchical factory usage
tabby = Cat.of("TabbyCat", name="Stripey")  # ✅ Works - TabbyCat is subclass of Cat
dog = Mammal.of("Dog", name="Buddy")        # ✅ Works - Dog is subclass of Mammal

# This would fail - Dog is not a subclass of Cat
# dog = Cat.of("Dog")  # ❌ Raises KeyError

# Direct instantiation works for concrete classes
direct_dog = Dog.of(name="Rex")  # ✅ Works - no registry key needed
```

### Class Aliases

Provide alternative names for your classes:

```python
class DatabaseConnection(Registry):
    aliases = ["db", "database", "connection"]

    def __init__(self, host: str = "localhost"):
        self.host = host

# All of these create the same type of object
db1 = DatabaseConnection.of()  # Direct instantiation
db2 = DatabaseConnection.of("db", host="remote.db")
db3 = DatabaseConnection.of("database", host="prod.db")
db4 = DatabaseConnection.of("connection", host="test.db")
```

## AutoEnum Integration

AutoEnum works seamlessly with Registry to create enumerations from registered classes:

```python
from morphic.autoenum import AutoEnum

# Create enum from registered classes
AnimalTypes = AutoEnum.create(Animal)

# Use the enum
for animal_type in AnimalTypes:
    print(f"Available: {animal_type.name}")  # Dog, Cat, etc.

    # Create instance using enum value
    animal = Animal.of(animal_type.value, name=f"Test {animal_type.name}")
    print(animal.speak())
```

## Typed Integration

Typed provides enhanced data modeling with automatic validation, type conversion, and default value processing that works seamlessly with Registry:

### Basic Typed Usage

```python
from morphic import Typed
from typing import List, Optional

# No @dataclass decorator needed - automatic dataclass transformation
class ProcessorConfig(Typed):
    name: str
    threads: int = "4"           # String automatically converted to int
    timeout: float = "30.5"      # String automatically converted to float
    debug: bool = "false"        # String automatically converted to bool
    features: List[str] = []     # Mutable default automatically handled

    def validate(self):
        if self.threads < 1:
            raise ValueError("Threads must be positive")

# All defaults are validated and converted at class definition time
config = ProcessorConfig(name="FastProcessor")
assert config.threads == 4
assert isinstance(config.threads, int)
assert config.timeout == 30.5
assert isinstance(config.timeout, float)
```

### Registry + Typed Integration

```python
class DataProcessor(Registry, ABC):
    def __init__(self, config: ProcessorConfig):
        # Config is automatically validated by Typed
        self.config = config

    @abstractmethod
    def process(self, data: str) -> str:
        pass

class CSVProcessor(DataProcessor):
    def process(self, data: str) -> str:
        return f"Processing CSV with {self.config.threads} threads: {data}"

class JSONProcessor(DataProcessor):
    def process(self, data: str) -> str:
        return f"Processing JSON '{self.config.name}': {data}"

# Create processors with type-safe configuration
config = ProcessorConfig(name="FastProcessor", threads="8")  # String converted to int

csv_processor = DataProcessor.of("CSVProcessor", config=config)
json_processor = DataProcessor.of("JSONProcessor", config=config)

print(csv_processor.process("test data"))
print(json_processor.process("test data"))
```

### Hierarchical Typed Support

Typed supports complex nested structures with automatic conversion:

```python
class DatabaseConfig(Typed):
    host: str = "localhost"
    port: int = "5432"  # String converted to int
    ssl: bool = "true"  # String converted to bool

class ServiceConfig(Typed):
    name: str
    database: DatabaseConfig = {  # Dict automatically converted to DatabaseConfig
        "host": "prod.db",
        "port": "5433",
        "ssl": "false"
    }
    features: List[str] = ["auth", "logging"]  # Mutable default handled safely

# Create with automatic nested conversion
service_config = ServiceConfig(name="UserService")
assert isinstance(service_config.database, DatabaseConfig)
assert service_config.database.port == 5433  # Converted from string
assert service_config.database.ssl is False  # Converted from string

# Can also use from_dict for external data
external_config = ServiceConfig.from_dict({
    "name": "AuthService",
    "database": {
        "host": "auth.db",
        "port": "5434"  # Automatic conversion
    }
})
```

## Practical Example: Payment System

Here's a complete example combining all three components:

```python
from morphic.registry import Registry
from morphic.autoenum import AutoEnum
from morphic.typed import Typed
from abc import ABC, abstractmethod
from dataclasses import dataclass

# Configuration model with automatic validation and conversion
class PaymentConfig(Typed):
    api_key: str
    fee_percentage: float = "2.9"      # String converted to float
    max_amount: float = "10000.0"      # String converted to float
    retry_attempts: int = "3"          # String converted to int
    features: List[str] = ["logging"]  # Mutable default handled automatically

    def validate(self):
        if self.fee_percentage < 0 or self.fee_percentage > 100:
            raise ValueError("Fee percentage must be between 0 and 100")
        if self.max_amount <= 0:
            raise ValueError("Max amount must be positive")

# Registry-based payment system
class PaymentProcessor(Registry, ABC):
    @abstractmethod
    def process_payment(self, amount: float) -> bool:
        pass

class StripeProcessor(PaymentProcessor):
    aliases = ["stripe", "card"]

    def __init__(self, config: PaymentConfig):
        self.config = config

    def process_payment(self, amount: float) -> bool:
        if amount > self.config.max_amount:
            return False
        print(f"Stripe: Processing ${amount} (fee: {self.config.fee_percentage}%)")
        return True

class PayPalProcessor(PaymentProcessor):
    aliases = ["paypal", "pp"]

    def __init__(self, config: PaymentConfig):
        self.config = config

    def process_payment(self, amount: float) -> bool:
        if amount > self.config.max_amount:
            return False
        print(f"PayPal: Processing ${amount} (fee: {self.config.fee_percentage}%)")
        return True

class BankTransferProcessor(PaymentProcessor):
    aliases = ["bank", "transfer", "ach"]

    def __init__(self, config: PaymentConfig):
        self.config = config

    def process_payment(self, amount: float) -> bool:
        if amount > self.config.max_amount:
            return False
        print(f"Bank: Processing ${amount} (fee: {self.config.fee_percentage}%)")
        return True

# Create enum for available processors
ProcessorTypes = AutoEnum.create(PaymentProcessor)

# Factory function with type safety and automatic conversion
def create_processor(processor_type: str, **config_kwargs) -> PaymentProcessor:
    # Typed automatically validates and converts types
    config = PaymentConfig(**config_kwargs)
    return PaymentProcessor.of(processor_type, config=config)

def create_processor_from_dict(processor_type: str, config_dict: dict) -> PaymentProcessor:
    # from_dict provides automatic type conversion from external data
    config = PaymentConfig.from_dict(config_dict)
    return PaymentProcessor.of(processor_type, config=config)

# Usage examples

# 1. Direct processor creation with type conversion
stripe_config = PaymentConfig(
    api_key="sk_test_123",
    fee_percentage="2.9",    # String automatically converted to float
    max_amount="5000.0"      # String automatically converted to float
)
stripe = StripeProcessor.of(config=stripe_config)

# 2. Factory creation with automatic type conversion
paypal = create_processor(
    "pp",
    api_key="paypal_key_456",
    fee_percentage="3.5",    # String converted to float
    max_amount="8000.0"      # String converted to float
)

# 3. From external configuration (e.g., JSON, environment variables)
config_data = {
    "api_key": "bank_key_789",
    "fee_percentage": "1.5",  # All strings automatically converted
    "max_amount": "15000",
    "retry_attempts": "5"
}
bank_processor = create_processor_from_dict("bank", config_data)

# 3. Using enum values
for processor_type in ProcessorTypes:
    print(f"Available processor: {processor_type.name}")

# 4. Dynamic processor selection
def process_payment_with_fallback(amount: float, preferred: str, fallback: str):
    processors = [preferred, fallback]

    for processor_name in processors:
        try:
            # Create processor with default config
            processor = create_processor(
                processor_name,
                api_key=f"key_{processor_name}",
                fee_percentage=3.0
            )

            if processor.process_payment(amount):
                print(f"Payment successful with {processor_name}")
                return True
            else:
                print(f"Payment failed with {processor_name}, trying fallback...")

        except KeyError:
            print(f"Processor {processor_name} not available")

    return False

# Test the payment system
print("=== Payment Processing Demo ===")

# Direct usage
stripe.process_payment(100.0)
paypal.process_payment(250.0)

# With fallback
process_payment_with_fallback(500.0, "stripe", "paypal")
process_payment_with_fallback(15000.0, "bank", "paypal")  # Exceeds limit

# List all available processors
print("\nAvailable payment processors:")
available_processors = PaymentProcessor.subclasses()
for processor_class in available_processors:
    print(f"- {processor_class.__name__}")
    if hasattr(processor_class, 'aliases'):
        print(f"  Aliases: {processor_class.aliases}")
```

## Best Practices

### 1. Use Clear Inheritance Hierarchies

```python
# Good - organized hierarchy
class Service(Registry, ABC):
    pass

class DataService(Service, ABC):
    """Base for all data-related services."""
    pass

class NotificationService(Service, ABC):
    """Base for all notification services."""
    pass

class EmailService(NotificationService):  # Clear inheritance path
    pass

class DatabaseService(DataService):  # Clear inheritance path
    pass
```

### 2. Provide Meaningful Aliases

```python
class PostgreSQLConnection(Registry):
    aliases = ["postgres", "postgresql", "pg", "db-postgres"]

    def __init__(self, host: str = "localhost", port: int = 5432):
        self.host = host
        self.port = port

# Users can choose their preferred naming
db1 = PostgreSQLConnection.of("postgres", host="prod.db")
db2 = PostgreSQLConnection.of("pg", port=5433)
```

### 3. Combine with Typed for Validation

```python
class ServerConfig(Typed):
    host: str = "localhost"
    port: int = "8080"        # String automatically converted to int
    ssl: bool = "true"        # String automatically converted to bool
    timeout: float = "30.0"   # String automatically converted to float

    def validate(self):
        if self.port < 1 or self.port > 65535:
            raise ValueError("Port must be between 1 and 65535")

class WebServer(Registry):
    def __init__(self, config: ServerConfig):
        # Config is automatically validated by Typed
        self.config = config

# Typed provides automatic type conversion and validation
server1 = WebServer.of(config=ServerConfig(host="0.0.0.0"))  # Uses converted defaults

# Can also create from external data sources
server2 = WebServer.of(config=ServerConfig.from_dict({
    "host": "production.com",
    "port": "9000",     # String converted to int
    "ssl": "false",     # String converted to bool
    "timeout": "60.5"   # String converted to float
}))

# Invalid defaults caught at class definition time
try:
    class BadConfig(Typed):
        port: int = "not_a_number"  # Raises TypeError immediately

except TypeError as e:
    print(f"Invalid default: {e}")
```

### 4. Use Type Hints for Better IDE Support

```python
from typing import Protocol

class StorageProtocol(Protocol):
    def save(self, key: str, data: bytes) -> bool: ...
    def load(self, key: str) -> bytes: ...

class Storage(Registry, ABC):
    @abstractmethod
    def save(self, key: str, data: bytes) -> bool:
        pass

    @abstractmethod
    def load(self, key: str) -> bytes:
        pass

def create_storage(storage_type: str, **kwargs) -> StorageProtocol:
    """Type-safe factory function with full IDE support."""
    return Storage.of(storage_type, **kwargs)
```

## Error Handling

### Registry Errors

```python
try:
    # This will raise KeyError if the class isn't registered
    unknown = Animal.of("UnknownAnimal")
except KeyError as e:
    print(f"Animal type not found: {e}")

try:
    # This will raise TypeError for abstract class without registry_key
    animal = Animal.of()  # Missing registry_key for abstract class
except TypeError as e:
    print(f"Cannot instantiate abstract class: {e}")
```

### Constructor Errors

```python
class ConfiguredService(Registry):
    def __init__(self, required_param: str):
        self.param = required_param

try:
    # Missing required parameter
    service = ConfiguredService.of()  # Will raise TypeError
except TypeError as e:
    print(f"Constructor error: {e}")

# Correct usage
service = ConfiguredService.of(required_param="value")
```

### Typed Validation Errors

```python
class Config(Typed):
    host: str
    port: int = "8080"  # Default converted at class definition time

    def validate(self):
        if self.port < 1000:
            raise ValueError("Port must be >= 1000")

try:
    # Type validation error
    invalid_config = Config(host=123, port="not_an_int")
except TypeError as e:
    print(f"Type error: {e}")

try:
    # Custom validation error
    invalid_port = Config(host="localhost", port=80)
except ValueError as e:
    print(f"Validation error: {e}")

# Default value errors caught at class definition time
try:
    class BadDefaults(Typed):
        timeout: int = "not_a_number"  # Error raised immediately

except TypeError as e:
    print(f"Default value error: {e}")
```

## Performance Tips

### 1. Cache Frequently Used Classes

```python
class ServiceFactory:
    def __init__(self):
        self._class_cache = {}

    def get_service_class(self, service_type: str):
        if service_type not in self._class_cache:
            self._class_cache[service_type] = Service.get_subclass(service_type)
        return self._class_cache[service_type]

    def create_service(self, service_type: str, **kwargs):
        service_class = self.get_service_class(service_type)
        return service_class(**kwargs)
```

### 2. Use Direct Instantiation When Possible

```python
# If you know the exact class, use direct instantiation
dog = Dog.of(name="Buddy")  # Faster than Animal.of("Dog", name="Buddy")

# Use factory only when you need dynamic selection
animal_type = user_selection  # e.g., "Dog" or "Cat"
animal = Animal.of(animal_type, name="Dynamic")
```

## Advanced Patterns

### Plugin Architecture

```python
class Plugin(Registry, ABC):
    @abstractmethod
    def execute(self) -> str:
        pass

class PluginManager:
    def load_plugin(self, plugin_name: str) -> Plugin:
        return Plugin.of(plugin_name)

    def get_available_plugins(self) -> set:
        return Plugin.subclasses()

    def execute_all_plugins(self):
        for plugin_class in self.get_available_plugins():
            plugin = plugin_class()  # Direct instantiation
            print(plugin.execute())
```

### Configuration-Driven Architecture

```python
import json
from typing import Dict, Any

class ConfigurableService(Registry, ABC):
    @abstractmethod
    def process(self, data: Any) -> Any:
        pass

def create_service_from_config(config_file: str) -> ConfigurableService:
    with open(config_file) as f:
        config = json.load(f)

    service_type = config["service_type"]
    service_args = config.get("args", {})

    return ConfigurableService.of(service_type, **service_args)

# config.json:
# {
#   "service_type": "EmailService",
#   "args": {
#     "smtp_host": "smtp.example.com",
#     "port": 587
#   }
# }

service = create_service_from_config("config.json")
```

## Next Steps

- Learn more about the [Registry System](registry.md) advanced features
- Explore [AutoEnum](autoenum.md) for automatic enumeration creation
- Understand [Typed](typed.md) validation and conversion capabilities
- Check out complete [Examples](../examples.md) with real-world use cases