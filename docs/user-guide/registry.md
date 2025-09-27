# Registry System

The Registry system is Morphic's powerful inheritance-based class registration and hierarchical factory pattern. It allows classes to automatically register themselves through inheritance and provides sophisticated factory methods for instance creation.

## Core Concept

In Morphic's Registry system, classes automatically register themselves when they inherit from `Registry`. The system then provides hierarchical factory methods that respect class inheritance relationships.

```python
from morphic.registry import Registry
from abc import ABC, abstractmethod

class Animal(Registry, ABC):
    @abstractmethod
    def speak(self) -> str:
        pass

# Classes automatically register when they inherit from a Registry subclass
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

## Hierarchical Factory Pattern

The Registry provides a hierarchical `of()` factory method that works intelligently based on the class hierarchy:

### 1. Concrete Class Direct Instantiation

For concrete (non-abstract) classes, you can create instances directly without specifying a registry key:

```python
# Direct instantiation of concrete classes
dog = Dog.of()  # Creates Dog with default name "Buddy"
cat = Cat.of(name="Shadow")  # Creates Cat with custom name

print(dog.speak())  # "Buddy says Woof!"
print(cat.speak())  # "Shadow says Meow!"
```

### 2. Abstract Class Factory

Abstract classes require a registry key to specify which subclass to instantiate, and they only look within their own hierarchy:

```python
# Using abstract base class as factory
dog = Animal.of("Dog", name="Rex")
cat = Animal.of("Cat", name="Fluffy")

print(dog.speak())  # "Rex says Woof!"
print(cat.speak())  # "Fluffy says Meow!"
```

### 3. Hierarchical Scoping

The factory method respects class hierarchies - each class can only instantiate its own subclasses:

```python
class Mammal(Animal, ABC):
    warm_blooded = True

class Cat(Mammal, ABC):
    def __init__(self, name: str = "Cat"):
        self.name = name

class TabbyCat(Cat):
    def __init__(self, name: str = "Tabby", stripes: bool = True):
        super().__init__(name)
        self.stripes = stripes

    def speak(self) -> str:
        return f"{self.name} the tabby says Meow!"

class OrangeCat(Cat):
    def __init__(self, name: str = "Orange", fluffy: bool = True):
        super().__init__(name)
        self.fluffy = fluffy

    def speak(self) -> str:
        return f"{self.name} the orange cat says Meow!"

class Dog(Mammal):  # Concrete dog class
    def __init__(self, name: str = "Dog"):
        self.name = name

    def speak(self) -> str:
        return f"{self.name} says Woof!"

# Hierarchical factory usage
tabby = Cat.of("TabbyCat", name="Stripey")  # ✅ Works - TabbyCat is subclass of Cat
orange = Cat.of("OrangeCat", name="Ginger")  # ✅ Works - OrangeCat is subclass of Cat

# This would fail - Dog is not a subclass of Cat
# dog = Cat.of("Dog")  # ❌ Raises KeyError

# But this works - Dog is a subclass of Mammal
dog = Mammal.of("Dog", name="Buddy")  # ✅ Works

# Direct instantiation works for concrete classes
direct_dog = Dog.of(name="Rex")  # ✅ Works - no registry key needed
```

## Advanced Features

### Class Aliases

You can provide aliases for classes to make them accessible by multiple keys:

```python
class DatabaseConnection(Registry):
    aliases = ["db", "database", "connection"]

    def __init__(self, host: str = "localhost", port: int = 5432):
        self.host = host
        self.port = port

# All of these work
db1 = DatabaseConnection.of()  # Direct instantiation
db2 = DatabaseConnection.of("db", host="remote.db")
db3 = DatabaseConnection.of("database", port=3306)
db4 = DatabaseConnection.of("connection", host="prod.db", port=5433)
```

### Custom Registry Keys

Classes can define custom registry keys through the `_registry_keys()` method:

```python
class HTTPProtocol(Registry):
    aliases = ["http", "web"]

    @classmethod
    def _registry_keys(cls):
        return [("protocol", "http"), "http_protocol"]

    def __init__(self, port: int = 80, secure: bool = False):
        self.port = port
        self.secure = secure

# Multiple ways to create instances
http1 = HTTPProtocol.of()  # Direct
http2 = HTTPProtocol.of("http", port=8080)  # Alias
http3 = HTTPProtocol.of("http_protocol", secure=True)  # Custom key
http4 = HTTPProtocol.of(("protocol", "http"), port=443, secure=True)  # Tuple key
```

### Registry Inspection

Explore what's available in the registry:

```python
# Get all subclasses of a registry class
animal_types = Animal.subclasses()  # Returns set of registered concrete classes
mammal_types = Mammal.subclasses()  # Only mammal subclasses

# Include abstract classes in the results
all_animals = Animal.subclasses(keep_abstract=True)

# Get specific subclass by key
dog_class = Animal.get_subclass("Dog")  # Returns the Dog class (not instance)
cat_class = Animal.get_subclass("Cat")
```

## Design Patterns

### Plugin System

```python
from abc import ABC, abstractmethod

class Plugin(Registry, ABC):
    @abstractmethod
    def execute(self) -> str:
        pass

class CSVExporter(Plugin):
    aliases = ["csv"]

    def execute(self) -> str:
        return "Exporting data to CSV format"

class JSONExporter(Plugin):
    aliases = ["json"]

    def execute(self) -> str:
        return "Exporting data to JSON format"

class XMLExporter(Plugin):
    aliases = ["xml"]

    def execute(self) -> str:
        return "Exporting data to XML format"

# Plugin manager using hierarchical factory
class PluginManager:
    def get_available_plugins(self) -> set:
        return Plugin.subclasses()

    def execute_plugin(self, plugin_type: str) -> str:
        plugin = Plugin.of(plugin_type)
        return plugin.execute()

# Usage
manager = PluginManager()
result = manager.execute_plugin("csv")  # "Exporting data to CSV format"
```

### Hierarchical Service Architecture

```python
class Service(Registry, ABC):
    @abstractmethod
    def process(self, data: str) -> str:
        pass

class DataService(Service, ABC):
    """Base class for data processing services."""
    pass

class FileService(DataService):
    """Handles file operations."""

    def process(self, data: str) -> str:
        return f"Processing file data: {data}"

class DatabaseService(DataService):
    """Handles database operations."""

    def process(self, data: str) -> str:
        return f"Processing database data: {data}"

class NotificationService(Service, ABC):
    """Base class for notification services."""
    pass

class EmailService(NotificationService):
    def process(self, data: str) -> str:
        return f"Sending email: {data}"

class SMSService(NotificationService):
    def process(self, data: str) -> str:
        return f"Sending SMS: {data}"

# Hierarchical service creation
file_service = DataService.of("FileService")  # ✅ FileService is DataService subclass
email_service = NotificationService.of("EmailService")  # ✅ EmailService is NotificationService subclass

# This would fail - EmailService is not a DataService
# email_as_data = DataService.of("EmailService")  # ❌ KeyError

# But this works - both are Service subclasses
any_service = Service.of("EmailService")  # ✅ Works from common base
```

### Factory with Configuration

```python
from typing import Dict, Any
import json

class LoggerConfig(Registry, ABC):
    @abstractmethod
    def log(self, message: str) -> None:
        pass

class FileLogger(LoggerConfig):
    aliases = ["file"]

    def __init__(self, filename: str, level: str = "INFO"):
        self.filename = filename
        self.level = level

    def log(self, message: str) -> None:
        print(f"[{self.level}] {message} -> {self.filename}")

class ConsoleLogger(LoggerConfig):
    aliases = ["console"]

    def __init__(self, level: str = "INFO"):
        self.level = level

    def log(self, message: str) -> None:
        print(f"[{self.level}] {message}")

class LoggerFactory:
    @staticmethod
    def create_from_config(config: Dict[str, Any]):
        logger_type = config["type"]
        logger_args = config.get("args", {})
        return LoggerConfig.of(logger_type, **logger_args)

# Configuration-based creation
config = {
    "type": "file",
    "args": {"filename": "app.log", "level": "DEBUG"}
}

logger = LoggerFactory.create_from_config(config)
logger.log("Application started")  # [DEBUG] Application started -> app.log
```

## Registry Configuration

### Controlling Registration Behavior

```python
class StrictService(Registry, ABC):
    # Prevent multiple subclasses from using the same key
    _allow_multiple_subclasses = False  # Default

    # Prevent subclass overriding
    _allow_subclass_override = False  # Default

class FlexibleService(Registry, ABC):
    # Allow multiple subclasses per key
    _allow_multiple_subclasses = True

    # Allow subclass overriding
    _allow_subclass_override = True

class SkippedService(Registry):
    # Prevent this class from registering itself
    _dont_register = True
```

### String Normalization

The registry automatically normalizes string keys for flexible, case-insensitive matching:

**Normalization Rules:**
- Convert to lowercase
- Remove spaces, dashes, underscores
- Handle various naming conventions

```python
class HTTPProtocol(Registry):
    aliases = ["HTTP-SECURE", "http_secure", "http secure"]

# All these variations resolve to the same class due to normalization
protocol1 = HTTPProtocol.of("HTTP-SECURE")    # Direct alias
protocol2 = HTTPProtocol.of("http_secure")    # Underscore variation
protocol3 = HTTPProtocol.of("http secure")    # Space variation
protocol4 = HTTPProtocol.of("HTTPSECURE")     # No separators
protocol5 = HTTPProtocol.of("httpsecure")     # All lowercase
protocol6 = HTTPProtocol.of("Http-Secure")    # Mixed case

# All create the same HTTPProtocol instance
assert type(protocol1) == type(protocol2) == type(protocol3)
```

**Tuple Key Normalization:**
```python
class DataService(Registry):
    @classmethod
    def _registry_keys(cls):
        return [("data", "processing"), ("DATA", "PROCESSING")]

# Both work due to string normalization within tuples
service1 = DataService.of(("data", "processing"))
service2 = DataService.of(("DATA", "PROCESSING"))
service3 = DataService.of(("Data", "Processing"))  # Mixed case works too

assert type(service1) == type(service2) == type(service3)
```

## Error Handling

### Registry Errors with Detailed Messages

```python
from morphic.registry import Registry
from abc import ABC

class Transport(Registry, ABC):
    pass

class LandTransport(Transport, ABC):
    pass

class Car(LandTransport):
    aliases = ["auto", "vehicle"]

class Boat(Transport):
    aliases = ["ship", "vessel"]

# Registry key not found - shows hierarchical context
try:
    transport = LandTransport.of("Boat")  # Boat not in LandTransport hierarchy
except KeyError as e:
    print(f"Error: {e}")
    # Output: Could not find subclass of LandTransport using registry_key: "Boat"
    # Available keys in this hierarchy are: ['Car', 'auto', 'vehicle']

# Abstract class without key
try:
    transport = Transport.of()  # Abstract class needs registry_key
except TypeError as e:
    print(f"Error: {e}")
    # Output: Cannot instantiate abstract class 'Transport' without specifying a registry_key

# Calling Registry.of() directly
try:
    instance = Registry.of("SomeClass")  # Cannot call on Registry base class
except TypeError as e:
    print(f"Error: {e}")
    # Output: The 'of' factory method cannot be called directly on Registry class

# Multiple subclasses with same key (when _allow_multiple_subclasses=True)
class FlexibleService(Registry, ABC):
    _allow_multiple_subclasses = True

class EmailService(FlexibleService):
    aliases = ["notification"]

class SMSService(FlexibleService):
    aliases = ["notification"]  # Same alias as EmailService

try:
    service = FlexibleService.of("notification")  # Ambiguous key
except TypeError as e:
    print(f"Error: {e}")
    # Output: Cannot instantiate using registry_key 'notification' because
    # multiple subclasses are registered: ['EmailService', 'SMSService']
```

### Registry Registration Conflicts

```python
# Duplicate registration without override permission
class StrictService(Registry, ABC):
    pass  # _allow_subclass_override = False (default)

class EmailService(StrictService):
    pass

try:
    # This will fail - same class name registered twice
    class EmailService(StrictService):  # Different implementation
        version = 2
except KeyError as e:
    print(f"Registration conflict: {e}")
    # Output: A subclass with name 'EmailService' is already registered

# Multiple classes with same key without permission
class RestrictiveService(Registry, ABC):
    pass  # _allow_multiple_subclasses = False (default)

class Service1(RestrictiveService):
    aliases = ["common"]

try:
    class Service2(RestrictiveService):
        aliases = ["common"]  # Same alias as Service1
except KeyError as e:
    print(f"Alias conflict: {e}")
    # Output: Key common is already registered to subclass Service1
```

### Safe Registry Usage Patterns

```python
# Safe key lookup with fallback
def get_service_safe(service_key: str, fallback_class=None):
    """Safely get service class with optional fallback."""
    try:
        return MyService.get_subclass(service_key)
    except KeyError:
        if fallback_class:
            return fallback_class
        return None

# Safe instantiation with error handling
def create_service_safe(service_key: str, **kwargs):
    """Safely create service instance with error handling."""
    try:
        return MyService.of(service_key, **kwargs)
    except (KeyError, TypeError) as e:
        print(f"Failed to create service '{service_key}': {e}")
        return None

# Validate key before usage
available_keys = list(MyService._registry.keys())
if "email" in available_keys:
    email_service = MyService.of("email")
else:
    print("Email service not available")
```

### Constructor Errors

```python
class ConfiguredService(Registry):
    def __init__(self, required_param: str, optional_param: str = "default"):
        self.required = required_param
        self.optional = optional_param

# Missing required parameter
try:
    service = ConfiguredService.of()  # Missing required_param
except TypeError as e:
    print(f"Constructor error: {e}")

# Correct usage
service = ConfiguredService.of(required_param="value", optional_param="custom")
```

## Best Practices

### 1. Use Clear Inheritance Hierarchies

```python
# Good - clear hierarchy
class Transport(Registry, ABC):
    pass

class LandTransport(Transport, ABC):
    pass

class AirTransport(Transport, ABC):
    pass

class Car(LandTransport):
    pass

class Airplane(AirTransport):
    pass

# Usage respects hierarchy
car = LandTransport.of("Car")  # ✅ Works
plane = AirTransport.of("Airplane")  # ✅ Works
# plane = LandTransport.of("Airplane")  # ❌ Would fail - wrong hierarchy
```

### 2. Provide Meaningful Aliases

```python
class PostgreSQLDatabase(Registry):
    aliases = ["postgres", "postgresql", "pg", "database-postgres"]

    def __init__(self, host: str = "localhost", port: int = 5432):
        self.host = host
        self.port = port

# Multiple ways to create the same service
db1 = PostgreSQLDatabase.of("postgres", host="remote")
db2 = PostgreSQLDatabase.of("pg", port=5433)
```

### 3. Use Abstract Base Classes for Organization

```python
from abc import ABC, abstractmethod

class StorageProvider(Registry, ABC):
    @abstractmethod
    def store(self, key: str, data: bytes) -> bool:
        pass

    @abstractmethod
    def retrieve(self, key: str) -> bytes:
        pass

class CloudStorage(StorageProvider, ABC):
    """Base class for cloud storage providers."""
    pass

class LocalStorage(StorageProvider, ABC):
    """Base class for local storage providers."""
    pass

class S3Storage(CloudStorage):
    def store(self, key: str, data: bytes) -> bool:
        # S3 implementation
        return True

    def retrieve(self, key: str) -> bytes:
        # S3 implementation
        return b"data"

class FileStorage(LocalStorage):
    def store(self, key: str, data: bytes) -> bool:
        # File system implementation
        return True

    def retrieve(self, key: str) -> bytes:
        # File system implementation
        return b"data"

# Hierarchical creation
cloud_storage = CloudStorage.of("S3Storage")  # Only cloud storage options
local_storage = LocalStorage.of("FileStorage")  # Only local storage options
any_storage = StorageProvider.of("S3Storage")  # Any storage provider
```

### 4. Validate Constructor Arguments

```python
class ConfiguredService(Registry):
    def __init__(self, config: dict):
        required_keys = ["host", "port", "timeout"]
        for key in required_keys:
            if key not in config:
                raise ValueError(f"Missing required config key: {key}")

        if not isinstance(config["port"], int) or config["port"] <= 0:
            raise ValueError("Port must be a positive integer")

        self.config = config

# Usage with validation
try:
    service = ConfiguredService.of(config={
        "host": "localhost",
        "port": 8080,
        "timeout": 30
    })
except ValueError as e:
    print(f"Configuration error: {e}")
```

### 5. Use Type Hints for Better IDE Support

```python
from typing import Protocol, TypeVar

class ProcessorProtocol(Protocol):
    def process(self, data: str) -> str: ...

T = TypeVar('T', bound=ProcessorProtocol)

class ProcessorBase(Registry, ABC):
    @abstractmethod
    def process(self, data: str) -> str:
        pass

def create_processor(processor_type: str, **kwargs) -> ProcessorProtocol:
    """Type-safe factory function with IDE support."""
    return ProcessorBase.of(processor_type, **kwargs)
```

## Performance Considerations

### Registry Lookups
- Key lookups are O(1) hash table operations
- String normalization happens once during registration
- Hierarchical filtering is optimized for inheritance chains

### Memory Usage
- Each registry hierarchy maintains its own lookup table
- Classes are registered once regardless of how many keys they have
- Minimal memory overhead per registered class

### Best Practices for Performance
```python
# Cache frequently used classes if creating many instances
class ServiceCache:
    def __init__(self):
        self._cache = {}

    def get_service_class(self, service_type: str):
        if service_type not in self._cache:
            self._cache[service_type] = MyService.get_subclass(service_type)
        return self._cache[service_type]

    def create_service(self, service_type: str, **kwargs):
        service_class = self.get_service_class(service_type)
        return service_class(**kwargs)
```

## Advanced Use Cases

### Complex Registry Keys and Edge Cases

Based on the comprehensive test suite, Registry supports many advanced scenarios:

```python
# None values in registry keys are filtered out safely
class Widget(Registry, ABC):
    pass

class Button(Widget):
    aliases = ["btn", None, "button"]  # None is safely ignored

    @classmethod
    def _registry_keys(cls):
        return ["clickable", None, "interactive"]  # None values filtered

# Works with non-None values only
button1 = Widget.of("btn")          # Works
button2 = Widget.of("clickable")    # Works
button3 = Widget.of("interactive")  # Works

# Numeric and complex registry keys
class ServicePort(Registry):
    @classmethod
    def _registry_keys(cls):
        return [8080, 3.14, True, ("complex", "key")]

# Access via different key types
service1 = ServicePort.of(8080)               # Numeric key
service2 = ServicePort.of(3.14)               # Float key
service3 = ServicePort.of(True)               # Boolean key
service4 = ServicePort.of(("complex", "key")) # Tuple key

# Large-scale registry with many subclasses
class Component(Registry, ABC):
    _allow_multiple_subclasses = True

# Dynamically create many subclasses (from test_large_scale_registry)
for i in range(20):
    class_name = f"Component{i}"
    aliases = [f"comp{i}", f"c{i}", f"component_{i}"]

    cls = type(class_name, (Component,), {
        "aliases": aliases,
        "component_id": i,
        "_registry_keys": classmethod(lambda cls: [f"id_{cls.component_id}"]),
    })

# All subclasses are accessible
comp1 = Component.of("Component5")    # By class name
comp2 = Component.of("comp10")        # By alias
comp3 = Component.of("id_15")         # By custom registry key

print(f"Total registered components: {len(Component.subclasses())}")  # 20
```

### Registry Isolation and Multiple Hierarchies

```python
# Different registry hierarchies don't interfere with each other
class Animals(Registry, ABC):
    pass

class Vehicles(Registry, ABC):
    pass

class Dog(Animals):
    aliases = ["canine", "pup"]

class Car(Vehicles):
    aliases = ["auto", "vehicle"]

# Each registry only sees its own subclasses
dog = Animals.of("Dog")           # ✅ Works
car = Vehicles.of("Car")          # ✅ Works

# Cross-hierarchy access fails as expected
try:
    Animals.of("Car")             # ❌ Car not in Animals hierarchy
except KeyError:
    print("Car not found in Animals registry")

try:
    Vehicles.of("Dog")            # ❌ Dog not in Vehicles hierarchy
except KeyError:
    print("Dog not found in Vehicles registry")

# Subclasses are properly isolated
animal_types = Animals.subclasses()   # {Dog}
vehicle_types = Vehicles.subclasses() # {Car}

assert Dog in animal_types
assert Car not in animal_types
assert Car in vehicle_types
assert Dog not in vehicle_types
```

### Dynamic Subclass Management

```python
# Registry supports dynamic registration and removal
class DynamicService(Registry, ABC):
    _allow_subclass_override = True

# Initially empty
print(f"Services: {len(DynamicService.subclasses())}")  # 0

# Dynamically add service
class EmailService(DynamicService):
    def send(self, message):
        return f"Sending: {message}"

print(f"Services: {len(DynamicService.subclasses())}")  # 1

# Service is automatically registered and accessible
email_svc = DynamicService.of("EmailService")
print(email_svc.send("Hello"))  # "Sending: Hello"

# Remove service from registry
DynamicService.remove_subclass("EmailService")
result = DynamicService.get_subclass("EmailService", raise_error=False)
print(f"EmailService after removal: {result}")  # None

# Re-register with override allowed
class EmailService(DynamicService):  # Same name, new implementation
    version = 2
    def send(self, message):
        return f"V2 Sending: {message}"

new_svc = DynamicService.of("EmailService")
print(f"Version: {new_svc.version}")  # 2
print(new_svc.send("Hello"))          # "V2 Sending: Hello"
```

## API Reference

### Core Methods

#### `Registry.of(registry_key=None, *args, **kwargs)`
Hierarchical factory method for creating instances.

- **registry_key**: Optional key to look up subclass. If None and class is concrete, instantiates directly.
- **args**: Positional arguments for constructor
- **kwargs**: Keyword arguments for constructor
- **Returns**: Instance of the found subclass
- **Raises**: TypeError if abstract class called without key, KeyError if key not found

#### `Registry.get_subclass(key, raise_error=True)`
Get registered subclass by key without creating instance.

- **key**: Registry key to look up
- **raise_error**: Whether to raise KeyError if not found
- **Returns**: Class type or None

#### `Registry.subclasses(keep_abstract=False)`
Get all registered subclasses.

- **keep_abstract**: Include abstract subclasses
- **Returns**: Set of registered class types

### Configuration Attributes

- **aliases**: Class attribute list of alternative keys
- **_allow_multiple_subclasses**: Allow multiple classes per key
- **_allow_subclass_override**: Allow overriding existing registrations
- **_dont_register**: Skip automatic registration

## Edge Cases and Advanced Scenarios

### Edge Case Handling

Registry handles various edge cases gracefully:

```python
# None values in aliases and registry keys are safely filtered
class EdgeCaseService(Registry):
    aliases = ["service", None, "svc"]  # None is ignored

    @classmethod
    def _registry_keys(cls):
        return ["custom_key", None, ("composite", "key")]  # None filtered out

# Works with non-None values
service1 = EdgeCaseService.of("service")       # ✅ Works
service2 = EdgeCaseService.of("custom_key")    # ✅ Works

# Empty registries are handled properly
class EmptyBase(Registry, ABC):
    pass

# No concrete subclasses registered
empty_subclasses = EmptyBase.subclasses()
assert len(empty_subclasses) == 0

# Safe access with no registered subclasses
result = EmptyBase.get_subclass("anything", raise_error=False)
assert result is None
```

### Complex Inheritance Hierarchies

```python
# Multi-level inheritance with mixed abstract/concrete classes
class Transport(Registry, ABC):
    pass

class LandTransport(Transport, ABC):  # Abstract intermediate
    pass

class WaterTransport(Transport, ABC):  # Abstract intermediate
    pass

class Car(LandTransport):             # Concrete
    pass

class Truck(LandTransport):           # Concrete
    aliases = ["lorry", "semi"]

class Boat(WaterTransport):           # Concrete
    aliases = ["ship", "vessel"]

# Hierarchical scoping works correctly at each level
car = Transport.of("Car")           # ✅ Car is Transport subclass
truck = LandTransport.of("Truck")   # ✅ Truck is LandTransport subclass
boat = WaterTransport.of("Boat")    # ✅ Boat is WaterTransport subclass

# Cross-hierarchy access properly fails
try:
    LandTransport.of("Boat")        # ❌ Boat not in LandTransport hierarchy
except KeyError as e:
    print("Boat not available in LandTransport")

# Abstract intermediates can still factory their subclasses
land_vehicle = LandTransport.of("lorry")  # Creates Truck via alias
assert isinstance(land_vehicle, Truck)
```

## Next Steps

- Learn about [Typed](typed.md) for enhanced data modeling
- Explore [AutoEnum](autoenum.md) for fuzzy-matched enumerations
- Check out complete [Examples](../examples.md) combining all features