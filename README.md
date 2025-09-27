# Morphic

[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue.svg)](https://adivekar-utexas.github.io/morphic/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Dynamic Python utilities for class registration, creation, and type checking.

## Features

- **Registry**: Dynamic class registration and factory pattern for building extensible architectures
- **AutoEnum**: Automatic enumeration creation from class hierarchies with type safety
- **Typed**: Enhanced data modeling with validation and serialization capabilities

## Installation

### From PyPI

```bash
pip install morphic
```

### From Source

```bash
pip install git+https://github.com/adivekar-utexas/morphic.git
```

### Development Installation

```bash
git clone https://github.com/adivekar-utexas/morphic.git
cd morphic

# Install with all dependencies (dev + docs)
pip install -e ".[all]"

# Or install specific dependency groups
pip install -e ".[dev]"      # Development dependencies only
pip install -e ".[docs]"     # Documentation dependencies only
pip install -e ".[dev,docs]" # Both dev and docs
```

## Quick Start

### Registry System: Inheritance-Based Class Registration

```python
from morphic import Registry
from abc import ABC, abstractmethod

# Create base registry class
class NotificationService(Registry, ABC):
    @abstractmethod
    def send(self, to: str, message: str) -> bool:
        pass

# Classes automatically register when inheriting
class EmailService(NotificationService):
    aliases = ["email", "mail"]  # Multiple aliases supported

    def __init__(self, smtp_server: str = "localhost"):
        self.smtp_server = smtp_server

    def send(self, to: str, message: str) -> bool:
        print(f"Sending email to {to} via {self.smtp_server}")
        return True

class SMSService(NotificationService):
    aliases = ["sms", "text"]

    def send(self, to: str, message: str) -> bool:
        print(f"Sending SMS to {to}")
        return True

# Hierarchical factory pattern - create instances through base class
email_service = NotificationService.of("EmailService", smtp_server="mail.example.com")
sms_service = NotificationService.of("sms")  # Works with aliases too!

# Direct instantiation works for concrete classes
email_direct = EmailService.of(smtp_server="direct.mail.com")

# Use the services
email_service.send("user@example.com", "Hello!")
sms_service.send("+1234567890", "Hello!")
```

### AutoEnum: Ultra-Fast Fuzzy-Matching Enums

```python
from morphic import AutoEnum, alias, auto
import json

# Create enum with fuzzy matching and aliases
class TaskStatus(AutoEnum):
    PENDING = alias("waiting", "queued", "not_started")
    RUNNING = alias("active", "in_progress", "executing")
    COMPLETE = alias("done", "finished", "success")
    FAILED = alias("error", "failure", "crashed")

# Fuzzy matching works with various formats
status1 = TaskStatus("pending")       # Direct match
status2 = TaskStatus("IN PROGRESS")   # Case insensitive + space handling
status3 = TaskStatus("not-started")   # Alias with different formatting
status4 = TaskStatus("Done")          # Alias with different case

# JSON compatibility (unlike standard enums!)
data = [TaskStatus.PENDING, TaskStatus.RUNNING]
json_str = json.dumps(data)  # Works! -> '["PENDING", "RUNNING"]'
recovered = TaskStatus.convert_list(json.loads(json_str))  # Back to enums!

# Dynamic enum creation
Priority = AutoEnum.create("Priority", ["low", "medium", "high", "urgent"])
print(Priority.Low)        # Low
print(Priority("MEDIUM"))  # Medium (fuzzy matched)

# Perfect for configuration and user input
config_status = TaskStatus(user_input)  # Handles "In Progress", "IN_PROGRESS", etc.
```

### Typed

```python
from morphic import Typed
from typing import Optional, List

class User(Typed):
    name: str
    email: str
    age: int
    is_active: bool = True
    bio: Optional[str] = None
    tags: List[str] = []  # Default empty list

    def validate(self):
        if self.age < 0:
            raise ValueError("Age must be non-negative")
        if "@" not in self.email:
            raise ValueError("Invalid email format")

# Instantiate like any class with auto type-conversion:
user = User(
    name="Alice Johnson",
    email="alice@example.com",
    age="30",  # String automatically converts to int
    is_active="true",  # String automatically converts to bool
    tags=("python", "ai", "data"),  # Tuple of strings converted to list of strings.
)
print(f"User: {user.name}, Age: {user.age} ({type(user.age)}), Tags: {user.tags}")
# Output: 
# User: Alice Johnson, Age: 30 (<class 'int'>), Tags: ['python', 'ai', 'data']

# Create from dict:
user = User.from_dict({
    "name": "Alice Johnson",
    "email": "alice@example.com",
    "age": "30",  # String automatically converts to int
    "is_active": "true",  # String automatically converts to bool
    "tags": ["python", "ai", "data"]  # List of strings
})
print(f"User: {user.name}, Age: {user.age} ({type(user.age)}), Tags: {user.tags}")
# Output: 
# Same as above.

# Hierarchical field handling for nested data
class Company(Typed):
    name: str
    employees: List[User]  # Automatically converts dicts to User instances

company_data = {
    "name": "TechCorp",
    "employees": [
        {"name": "Alice", "email": "alice@tech.com", "age": "30"},
        {"name": "Bob", "email": "bob@tech.com", "age": "25"}
    ]
}

company = Company.from_dict(company_data)
print(f"Company: {company.name}, Employees: {len(company.employees)}")
```

## Documentation

Comprehensive documentation is available at [https://adivekar.github.io/morphic/](https://adivekar.github.io/morphic/)

### Building Documentation Locally

To build and serve the documentation locally:

```bash
# Install documentation dependencies
pip install -e ".[docs]"

# Serve documentation locally
mkdocs serve
```

The documentation will be available at http://localhost:8000

### Documentation Structure

- **[User Guide](https://adivekar.github.io/morphic/user-guide/getting-started/)**: Comprehensive tutorials and examples
- **[API Reference](https://adivekar.github.io/morphic/api/)**: Detailed API documentation generated from docstrings
- **[Examples](https://adivekar.github.io/morphic/examples/)**: Real-world usage examples and patterns
- **[Contributing](https://adivekar.github.io/morphic/contributing/)**: Guidelines for contributors

## Development

### Setting Up Development Environment

1. **Clone the repository**:
   ```bash
   git clone https://github.com/adivekar/morphic.git
   cd morphic
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install in development mode**:
   ```bash
   # Install all dependencies (recommended for contributors)
   pip install -e ".[all]"

   # Or install specific groups
   pip install -e ".[dev]"      # Just development tools
   pip install -e ".[docs]"     # Just documentation tools
   ```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=morphic --cov-report=html

# Run specific test file
pytest tests/test_registry.py
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

### Documentation Deployment

Documentation is automatically deployed to GitHub Pages when changes are pushed to the main branch via GitHub Actions. The deployment workflow:

1. **Builds documentation** using MkDocs with Material theme
2. **Generates API documentation** automatically from docstrings using mkdocstrings
3. **Deploys to GitHub Pages** at https://adivekar.github.io/morphic/

## Performance

Morphic is optimized for production use:
- **AutoEnum**: 5.7M+ lookups/second with fuzzy matching
- **Registry**: O(1) class lookup with hierarchical inheritance
- **Typed**: Efficient type conversion with caching

## Requirements

- Python 3.10.9 or higher
- typing-extensions >= 4.0.0

## Contributing

We welcome contributions! Please see our [Contributing Guide](https://adivekar.github.io/morphic/contributing/) for details on:

- Setting up the development environment
- Running tests and quality checks
- Code style and documentation standards
- Pull request process

## License

MIT License - see the [LICENSE](LICENSE) file for details.