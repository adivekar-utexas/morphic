# Installation

## Requirements

Morphic requires Python 3.10.9 or higher and supports:

- Python 3.10
- Python 3.11
- Python 3.12

## Install from PyPI

!!! note "Coming Soon"
    Morphic will be available on PyPI once the initial release is published.

```bash
pip install morphic
```

## Install from Source

### Using pip

```bash
pip install git+https://github.com/adivekar/morphic.git
```

### Development Installation

For development work, clone the repository and install in editable mode:

```bash
git clone https://github.com/adivekar/morphic.git
cd morphic
pip install -e ".[dev]"
```

This installs Morphic in development mode with all development dependencies including:

- `pytest` - Testing framework
- `pytest-cov` - Coverage reporting
- `black` - Code formatting
- `ruff` - Linting and code analysis
- `mypy` - Static type checking
- `pydantic` - Data validation (for examples)

## Verify Installation

After installation, verify that Morphic is working correctly:

```python
import morphic
print(morphic.__version__)  # Should print the version number
```

Or run a quick test:

```python
from morphic import Registry
from abc import ABC

class Service(Registry, ABC):
    pass

class TestService(Service):
    pass

instance = Service.of("TestService")
print(type(instance).__name__)  # Should print "TestService"
```

## Dependencies

Morphic has minimal runtime dependencies:

- `typing-extensions>=4.0.0` - Enhanced type hints support

## Troubleshooting

### Python Version Issues

If you encounter issues with Python version compatibility:

```bash
python --version  # Check your Python version
pip install --upgrade pip  # Ensure latest pip version
```

### Import Errors

If you get import errors after installation:

1. Ensure you're using the correct Python environment
2. Try reinstalling: `pip uninstall morphic && pip install morphic`
3. Check for conflicting packages

### Development Setup Issues

For development installation issues:

```bash
# Clean installation
pip uninstall morphic
rm -rf build/ dist/ *.egg-info/
pip install -e ".[dev]"
```

## Next Steps

Once installed, head over to the [Getting Started](user-guide/getting-started.md) guide to learn how to use Morphic.