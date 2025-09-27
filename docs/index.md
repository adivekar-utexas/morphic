# Morphic

Welcome to **Morphic** - a powerful Python library providing dynamic utilities for class registration, creation, and type checking.

## What is Morphic?

Morphic is designed to simplify complex Python patterns through:

- **Registry System**: Dynamic class registration and factory patterns
- **AutoEnum**: Automatic enumeration creation from class hierarchies
- **Typed**: Enhanced data modeling capabilities

## Key Features

- ✨ **Dynamic Class Registration**: Automatically register and discover classes
- 🏭 **Factory Patterns**: Create instances through flexible factory methods
- 🔄 **Type Safety**: Built-in type checking and validation
- 📊 **Auto Enumeration**: Generate enums from class hierarchies
- 🚀 **High Performance**: Optimized for production use

## Quick Start

```python
from morphic import Registry, AutoEnum
from abc import ABC

# Base registry class
class Service(Registry, ABC):
    pass

# Classes automatically register when inheriting from Registry
class MyService(Service):
    pass

# Create instances through factory methods
instance = Service.of("MyService")

# Generate enums from class hierarchies
ServiceEnum = AutoEnum.create(Service)
```

## Why Choose Morphic?

Morphic eliminates boilerplate code and provides elegant solutions for common Python patterns. Whether you're building frameworks, implementing plugin systems, or managing complex object hierarchies, Morphic has you covered.

## Next Steps

- [Installation Guide](installation.md) - Get started with Morphic
- [Getting Started](user-guide/getting-started.md) - Learn the basics
- [API Reference](api/index.md) - Detailed API documentation
- [Examples](examples.md) - Real-world usage examples

## Community and Support

- 🐛 [Report Issues](https://github.com/adivekar/morphic/issues)
- 💬 [Discussions](https://github.com/adivekar/morphic/discussions)
- 📖 [Documentation](https://adivekar-utexas.github.io/morphic/)

!!! tip "Pro Tip"
    Check out the [Registry System](user-guide/registry.md) guide to see how Morphic can streamline your class management patterns.