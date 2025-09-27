# API Reference

Welcome to the Morphic API reference documentation. This section provides detailed information about all classes, functions, and modules in the Morphic library.

## Core Modules

### [Registry](registry.md)
Dynamic class registration and factory pattern implementation.

**Key Classes:**
- `Registry` - Main registry class for class registration and instance creation

**Key Methods:**
- `Registry.register()` - Register classes with the registry
- `Registry.of()` - Factory method to create instances
- `Registry.registered_keys()` - Get all registered class keys

### [AutoEnum](autoenum.md)
Automatic enumeration creation from class hierarchies.

**Key Classes:**
- `AutoEnum` - Main class for automatic enum generation

**Key Methods:**
- `AutoEnum.create()` - Create enums from class hierarchies

### [Typed](typed.md)
Enhanced data modeling with validation and serialization.

**Key Classes:**
- `Typed` - Base class for data models with validation

## Module Overview

The Morphic library is organized into focused modules:

```
morphic/
├── __init__.py          # Main exports
├── registry.py          # Registry system implementation
├── autoenum.py         # AutoEnum functionality
└── Typed.py        # Typed base class
```

## Quick Reference

### Import Patterns

```python
# Import main classes
from morphic import Registry, AutoEnum, Typed

# Import specific modules
from morphic.registry import Registry
from morphic.autoenum import AutoEnum
from morphic.typed import Typed
```

### Common Usage Patterns

```python
# Registry pattern
from abc import ABC

class Service(Registry, ABC):
    pass

class MyService(Service):
    pass

instance = Service.of("MyService")

# AutoEnum pattern
MyEnum = AutoEnum.create(BaseClass)

# Typed pattern
class MyModel(Typed):
    field: str
```

## Type Information

Morphic is fully typed and supports static type checking with mypy. All public APIs include comprehensive type annotations.

### Type Hints

```python
from typing import Type, Any, Dict
from morphic import Registry

# Registry factory with type hints
def create_instance(class_name: str, **kwargs: Any) -> Any:
    return Registry.of(class_name, **kwargs)

# Type-safe factory
def create_typed_instance[T](class_type: Type[T], **kwargs: Any) -> T:
    return Registry.of(class_type.__name__, **kwargs)
```

## Error Handling

All Morphic APIs use standard Python exceptions:

- `KeyError` - Class not found in registry
- `ValueError` - Invalid arguments or configuration
- `TypeError` - Type validation failures

## Next Steps

- Browse the detailed API documentation for each module
- Check out the [examples](../examples.md) for practical usage patterns
- Review the [user guide](../user-guide/getting-started.md) for comprehensive tutorials