"""Enhanced base configuration class with Pydantic-like functionality."""

from dataclasses import Field, fields, MISSING
from typing import Any, ClassVar, Dict, Type, TypeVar, Union, get_args, get_origin, Callable
from functools import wraps
import inspect

T = TypeVar("T", bound="Typed")


class Typed:
    """Base class for all configuration classes with enhanced dict conversion and validation.

    This class provides Pydantic-like functionality for dataclasses without external dependencies.
    Subclasses automatically become dataclasses - no @dataclass decorator needed!
    Validation is automatically called after instance creation.

    Features:
    - Automatic dataclass transformation for subclasses
    - Automatic type validation for all field types
    - Automatic nested Typed conversion in constructor
    - Automatic validation after instance creation
    - Automatic type conversion from dictionaries
    - **Default value validation and conversion at class definition time**
    - **Automatic mutable default handling with default_factory**
    - **Hierarchical default value conversion (nested Typeds, lists, dicts)**
    - AutoEnum string conversion with fuzzy matching and aliases (if morphic.AutoEnum is available)
    - Nested object support with validation
    - Serialization/deserialization with filtering options
    - Field caching for performance
    - Copy with modifications

    Default Value Features:
    - Default values are validated and converted at class definition time
    - Invalid defaults raise clear errors when the class is defined
    - Convertible defaults are automatically transformed (e.g., "25" -> 25 for int fields)
    - Mutable defaults (lists, dicts, Typed objects) are automatically converted to default_factory
    - Hierarchical structures in defaults are recursively converted
    - Supports Optional fields, Union types, and complex nested structures

    Basic Usage Examples:
        ```python
        from morphic import Typed, AutoEnum, alias
        from typing import List, Dict, Optional, Union

        # Simple dataclass with automatic validation
        class User(Typed):
            name: str
            age: int
            active: bool = True

            def validate(self):
                if self.age < 0:
                    raise ValueError("Age must be non-negative")

        # Validation happens automatically during creation
        user = User(name="John", age=30)
        print(user.name, user.age, user.active)  # John 30 True

        # Type validation catches mismatches immediately
        try:
            User(name=123, age=30)  # Raises TypeError - name must be str
        except TypeError as e:
            print(f"Type error: {e}")

        # from_dict with automatic type conversion
        user = User.from_dict({"name": "John", "age": "30"})  # "30" -> int(30)
        assert user.age == 30 and isinstance(user.age, int)

        # Custom validation runs after type validation
        try:
            User(name="John", age=-5)  # Raises ValueError from validate()
        except ValueError as e:
            print(f"Validation error: {e}")
        ```

    Advanced Examples:
        ```python
        # Nested Typed objects with automatic conversion
        class Address(Typed):
            street: str
            city: str
            zip_code: str = "00000"

        class Company(Typed):
            name: str
            address: Address
            employees: List[str] = []

        # Dict automatically converted to Address object
        company = Company(
            name="Tech Corp",
            address={"street": "123 Main St", "city": "NYC", "zip_code": "10001"}
        )
        assert isinstance(company.address, Address)
        assert company.address.street == "123 Main St"

        # Works with from_dict too
        company_data = {
            "name": "Tech Corp",
            "address": {"street": "456 Oak Ave", "city": "SF"},
            "employees": ["Alice", "Bob", "Charlie"]
        }
        company2 = Company.from_dict(company_data)
        assert company2.address.zip_code == "00000"  # Default value

        # Complex nested structures
        class Project(Typed):
            name: str
            team_lead: User
            members: List[User]
            settings: Dict[str, Union[str, int]]

        project = Project.from_dict({
            "name": "Alpha Project",
            "team_lead": {"name": "Alice", "age": 30},
            "members": [
                {"name": "Bob", "age": 25},
                {"name": "Charlie", "age": 28}
            ],
            "settings": {"priority": "high", "budget": 50000}
        })

        assert isinstance(project.team_lead, User)
        assert all(isinstance(member, User) for member in project.members)
        assert project.settings["budget"] == 50000
        ```

    Default Value Validation Examples:
        ```python
        # Basic default value conversion
        class Config(Typed):
            port: int = "8080"        # String automatically converted to int
            debug: bool = "true"      # String automatically converted to bool
            timeout: float = "30.5"   # String automatically converted to float

        config = Config()
        assert config.port == 8080    # Converted to int
        assert isinstance(config.port, int)

        # Invalid defaults caught at class definition time
        try:
            class BadConfig(Typed):
                count: int = "not_a_number"  # Raises TypeError immediately
        except TypeError as e:
            print(f"Invalid default caught: {e}")

        # Hierarchical default conversion
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

        # Each instance gets its own copy of mutable defaults
        contacts2 = ContactList()
        contacts.contacts.append(Contact(name="New", email="new@example.com"))
        assert len(contacts.contacts) == 3   # Modified
        assert len(contacts2.contacts) == 2  # Unchanged

        # Optional fields with proper None handling
        class OptionalConfig(Typed):
            name: str
            description: Optional[str] = None  # None is valid for Optional types
            settings: Optional[Dict[str, str]] = None

        config = OptionalConfig(name="test")
        assert config.description is None
        assert config.settings is None
        ```

    Error Handling:
        Default value validation provides clear error messages that include:
        - The class name where the error occurred
        - The specific field name with the invalid default
        - The expected type and actual type/value received
        - Whether the error occurred during conversion or validation

        ```python
        # Example error message:
        # TypeError: Invalid default value for field 'port' in class 'Config':
        # Default value for field 'port' in class 'Config' expected type <class 'int'>,
        # got str with value 'invalid_port_number'
        ```

    Performance and Best Practices:
        - Default value validation occurs only once at class definition time
        - Converted default values are cached and reused for all instances
        - Mutable defaults are automatically handled to prevent shared state issues
        - Use Optional[T] for fields that can legitimately be None
        - Large or complex default structures are efficiently handled via default_factory
        - Type conversion follows the same rules as from_dict() for consistency

    Advanced Features:
        - Supports Union types: Union[int, str] defaults try conversion in declaration order
        - Handles deeply nested structures: Dict[str, List[Typed]] with full conversion
        - Integrates with custom validation: default values must pass validate() method
        - Compatible with dataclass field() for advanced default_factory scenarios
        - Works seamlessly with AutoEnum string conversion and aliases
    """

    # Class-level cache for field information
    _field_cache: ClassVar[Dict[Type, Dict[str, Field]]] = {}

    def __init_subclass__(cls, **kwargs):
        """Automatically cache field information for subclasses and apply dataclass transformation."""
        super().__init_subclass__(**kwargs)

        # Validate and convert default values BEFORE applying dataclass transformation
        # This ensures dataclass uses the converted values
        cls._validate_and_convert_class_defaults()

        # Automatically apply dataclass transformation if not already applied
        if not hasattr(cls, "__dataclass_fields__"):
            # Import dataclass here to avoid circular imports
            from dataclasses import dataclass

            # Apply dataclass transformation
            dataclass_cls = dataclass(cls)

            # Copy dataclass attributes back to the original class
            # This is necessary because dataclass() returns a new class
            cls.__dataclass_fields__ = dataclass_cls.__dataclass_fields__
            cls.__init__ = dataclass_cls.__init__
            cls.__repr__ = dataclass_cls.__repr__
            cls.__eq__ = dataclass_cls.__eq__

            # Copy any other dataclass-specific attributes that might exist
            for attr_name in dir(dataclass_cls):
                if attr_name.startswith("__dataclass") and not hasattr(cls, attr_name):
                    setattr(cls, attr_name, getattr(dataclass_cls, attr_name))

        # Cache field information and validate default_factory after dataclass transformation
        if hasattr(cls, "__dataclass_fields__"):
            cls._field_cache[cls] = cls.__dataclass_fields__
            cls._validate_default_factories()

    def __post_init__(self) -> None:
        """Automatically called after dataclass initialization to run validation."""
        self._convert_field_values()
        self._validate_types()
        self.validate()

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any], *, strict: bool = False) -> T:
        """Create config instance from dictionary with automatic type conversion.

        Args:
            data: Dictionary to convert
            strict: If True, raise error on unknown fields

        Returns:
            Instance of the config class

        Raises:
            TypeError: If data is not a dictionary
            ValueError: If strict=True and unknown fields are present
        """
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict, got {type(data)}")

        # Get cached field information
        field_info = cls._get_field_info()
        constructor_inputs = {}

        for field_name, value in data.items():
            if field_name not in field_info:
                if strict:
                    raise ValueError(f"Unknown field '{field_name}' for {cls.__name__}")
                continue

            field = field_info[field_name]
            constructor_inputs[field_name] = cls._convert_value(field, value)

        return cls(**constructor_inputs)

    @classmethod
    def _get_field_info(cls) -> Dict[str, Field]:
        """Get field information, using cache when available."""
        if cls not in cls._field_cache:
            cls._field_cache[cls] = {field.name: field for field in fields(cls)}
        return cls._field_cache[cls]

    @classmethod
    def _convert_value(cls, field: Field, value: Any) -> Any:
        """Convert a value to the appropriate type for a field."""
        if value is None:
            return None

        field_type = field.type

        # Handle Union types (e.g., Optional[int] = Union[int, None])
        if get_origin(field_type) is Union:
            union_args = get_args(field_type)
            # Try each type in the union
            for arg_type in union_args:
                if arg_type is type(None):
                    continue
                try:
                    return cls._convert_single_type(arg_type, value)
                except (ValueError, TypeError):
                    continue
            # If no conversion worked, return as-is
            return value

        return cls._convert_single_type(field_type, value)

    @classmethod
    def _convert_single_type(cls, target_type: Type, value: Any) -> Any:
        """Convert value to a single target type."""
        # Handle generic types first before isinstance check
        origin_type = get_origin(target_type)
        if origin_type is not None:
            # Handle List[Typed] or similar list structures
            if origin_type is list:
                type_args = get_args(target_type)
                if type_args and isinstance(value, (list, tuple)):
                    element_type = type_args[0]
                    # Convert each element if it's a Typed type
                    if cls._is_Typed_type(element_type):
                        return [cls._convert_single_type(element_type, item) for item in value]
                    # For non-Typed types, try basic conversion
                    else:
                        return [cls._convert_single_type(element_type, item) for item in value]
                return value

            # Handle Dict[str, Typed] or similar dict structures
            elif origin_type is dict:
                type_args = get_args(target_type)
                if len(type_args) >= 2 and isinstance(value, dict):
                    key_type, value_type = type_args[0], type_args[1]
                    # Convert dict values
                    converted_dict = {}
                    for k, v in value.items():
                        converted_key = cls._convert_single_type(key_type, k)
                        converted_value = cls._convert_single_type(value_type, v)
                        converted_dict[converted_key] = converted_value
                    return converted_dict
                return value

            # For other generic types, return as-is
            return value

        # If already the right type, return as-is (only for non-generic types)
        try:
            if isinstance(value, target_type):
                return value
        except TypeError:
            # Some types (like subscripted generics) can't be used with isinstance
            pass

        # Handle AutoEnum conversion (if available in morphic)
        if hasattr(target_type, "__bases__"):
            try:
                # Try to import from morphic package
                from .autoenum import AutoEnum

                if any(
                    issubclass(base, AutoEnum) for base in target_type.__bases__ if isinstance(base, type)
                ):
                    if isinstance(value, str):
                        # Use from_str method for better conversion with fuzzy matching
                        return target_type.from_str(value)
                    return value
            except ImportError:
                pass

            # Handle standard Python enum types
            try:
                import enum

                if issubclass(target_type, enum.Enum):
                    if isinstance(value, str):
                        return target_type(value)
                    return value
            except (TypeError, ImportError):
                # Not an enum or enum not available, continue with other checks
                pass

            # Handle other enum types by looking for common enum characteristics
            if (
                hasattr(target_type, "_value_")
                or hasattr(target_type, "value")
                or any(hasattr(base, "_value_") for base in target_type.__bases__ if isinstance(base, type))
            ):
                if isinstance(value, str):
                    return target_type(value)
                return value

        # Handle nested Typed objects
        if hasattr(target_type, "__bases__") and any(
            issubclass(base, Typed) for base in target_type.__bases__ if isinstance(base, type)
        ):
            if isinstance(value, dict):
                return target_type.from_dict(value)
            return value

        # Handle basic type conversions
        if target_type in (int, float, str, bool):
            try:
                return target_type(value)
            except (ValueError, TypeError):
                # If conversion fails, return as-is and let dataclass validation handle it
                pass

        # For complex types, return as-is and let dataclass handle it
        return value

    def to_dict(self, *, exclude_none: bool = False, exclude_defaults: bool = False) -> Dict[str, Any]:
        """Convert instance to dictionary.

        Args:
            exclude_none: If True, exclude fields with None values
            exclude_defaults: If True, exclude fields with default values

        Returns:
            Dictionary representation of the instance
        """
        result = {}
        field_info = self._get_field_info()

        for field_name, field in field_info.items():
            value = getattr(self, field_name)

            if exclude_none and value is None:
                continue

            if exclude_defaults and self._is_default_value(field, value):
                continue

            # Convert nested Typed objects
            if hasattr(value, "to_dict"):
                result[field_name] = value.to_dict(
                    exclude_none=exclude_none, exclude_defaults=exclude_defaults
                )
            # Handle lists that might contain Typed objects
            elif isinstance(value, list):
                converted_list = []
                for item in value:
                    if hasattr(item, "to_dict"):
                        converted_list.append(
                            item.to_dict(exclude_none=exclude_none, exclude_defaults=exclude_defaults)
                        )
                    elif hasattr(item, "value"):
                        # Handle enums in lists
                        try:
                            from .autoenum import AutoEnum

                            if isinstance(item, AutoEnum):
                                converted_list.append(str(item))
                            else:
                                converted_list.append(item.value)
                        except ImportError:
                            converted_list.append(item.value if hasattr(item, "value") else str(item))
                    else:
                        converted_list.append(item)
                result[field_name] = converted_list
            # Handle dictionaries that might contain Typed objects
            elif isinstance(value, dict):
                converted_dict = {}
                for k, v in value.items():
                    if hasattr(v, "to_dict"):
                        converted_dict[k] = v.to_dict(
                            exclude_none=exclude_none, exclude_defaults=exclude_defaults
                        )
                    elif hasattr(v, "value"):
                        # Handle enums in dict values
                        try:
                            from .autoenum import AutoEnum

                            if isinstance(v, AutoEnum):
                                converted_dict[k] = str(v)
                            else:
                                converted_dict[k] = v.value
                        except ImportError:
                            converted_dict[k] = v.value if hasattr(v, "value") else str(v)
                    else:
                        converted_dict[k] = v
                result[field_name] = converted_dict
            # Convert enums to their value (AutoEnum and other enums)
            elif hasattr(value, "value"):
                try:
                    # Try to import from morphic package
                    from .autoenum import AutoEnum

                    if isinstance(value, AutoEnum):
                        # AutoEnum stores the name as the value, just use str() representation
                        result[field_name] = str(value)
                    else:
                        result[field_name] = value.value
                except ImportError:
                    result[field_name] = value.value if hasattr(value, "value") else str(value)
            else:
                result[field_name] = value

        return result

    def _is_default_value(self, field: Field, value: Any) -> bool:
        """Check if a value is the default value for a field."""
        if field.default is not MISSING:
            return value == field.default
        elif field.default_factory is not MISSING:
            return value == field.default_factory()

        return False

    def copy(self: T, **changes) -> T:
        """Create a copy of this instance with optional field changes.

        Args:
            **changes: Field changes to apply to the copy

        Returns:
            New instance with changes applied
        """
        current_dict = self.to_dict()
        current_dict.update(changes)
        return self.__class__.from_dict(current_dict)

    def validate(self) -> None:
        """Override in subclasses to add custom validation logic.

        This method is called automatically after instance creation.
        """
        pass

    def _convert_field_values(self) -> None:
        """Convert field values to appropriate types before validation.

        This enables automatic conversion of dictionaries to nested Typed objects
        and basic type conversion (like string to int) in the regular constructor.
        This makes the constructor behavior consistent with from_dict().
        """
        field_info = self._get_field_info()

        for field_name, field in field_info.items():
            current_value = getattr(self, field_name)

            # Use full conversion logic (same as from_dict)
            converted_value = self._convert_value(field, current_value)

            # Update the field value if it was converted
            if converted_value is not current_value:
                setattr(self, field_name, converted_value)

    @classmethod
    def _convert_value_strict(cls, field: Field, value: Any) -> Any:
        """Convert a value with strict rules (only nested Typeds and enums).

        This is used in the constructor to maintain strict type validation while
        still allowing dict-to-Typed conversion for nested objects.
        """
        if value is None:
            return None

        field_type = field.type

        # Handle Union types (e.g., Optional[Typed])
        if get_origin(field_type) is Union:
            union_args = get_args(field_type)
            # Try each type in the union
            for arg_type in union_args:
                if arg_type is type(None):
                    continue
                try:
                    return cls._convert_single_type_strict(arg_type, value)
                except (ValueError, TypeError):
                    continue
            # If no conversion worked, return as-is
            return value

        return cls._convert_single_type_strict(field_type, value)

    @classmethod
    def _convert_single_type_strict(cls, target_type: Type, value: Any) -> Any:
        """Convert value to a single target type with strict rules.

        Only converts nested Typed objects and enums, not basic types.
        Also handles hierarchical structures like List[Typed] and Dict[str, Typed].
        """
        # Handle generic types (e.g., List[Typed], Dict[str, Typed])
        origin_type = get_origin(target_type)
        if origin_type is not None:
            # Handle List[Typed] or similar list structures
            if origin_type is list:
                type_args = get_args(target_type)
                if type_args and isinstance(value, list):
                    element_type = type_args[0]
                    # Convert each element if it's a Typed type
                    if cls._is_Typed_type(element_type) and all(isinstance(item, dict) for item in value):
                        return [element_type(**item) for item in value]
                    # Also handle nested conversions for existing Typed instances
                    elif cls._is_Typed_type(element_type):
                        converted_items = []
                        for item in value:
                            if isinstance(item, dict):
                                converted_items.append(element_type(**item))
                            else:
                                converted_items.append(item)
                        return converted_items
                return value

            # Handle Dict[str, Typed] or similar dict structures
            elif origin_type is dict:
                type_args = get_args(target_type)
                if len(type_args) >= 2 and isinstance(value, dict):
                    value_type = type_args[1]  # Second type arg is the value type
                    # Convert dict values if they're Typed types
                    if cls._is_Typed_type(value_type):
                        converted_dict = {}
                        for k, v in value.items():
                            if isinstance(v, dict):
                                converted_dict[k] = value_type(**v)
                            else:
                                converted_dict[k] = v
                        return converted_dict
                return value

            # For other generic types, don't try to convert - return as-is
            # Validation will handle checking the container type
            return value

        # Handle direct type match
        try:
            if isinstance(value, target_type):
                return value
        except TypeError:
            # Some types (like complex generics) can't be used with isinstance
            # Return as-is and let validation handle it
            return value

        # Handle AutoEnum conversion (if available in morphic)
        if hasattr(target_type, "__bases__"):
            try:
                # Try to import from morphic package
                from .autoenum import AutoEnum

                if any(
                    issubclass(base, AutoEnum) for base in target_type.__bases__ if isinstance(base, type)
                ):
                    if isinstance(value, str):
                        # Try conversion, but don't raise errors - let validation handle it
                        try:
                            return target_type.from_str(value)
                        except ValueError:
                            # Invalid enum value - return as-is for validation to catch
                            return value
                    return value
            except ImportError:
                pass

            # Handle other enum types by looking for common enum characteristics
            if (
                hasattr(target_type, "_value_")
                or hasattr(target_type, "value")
                or any(hasattr(base, "_value_") for base in target_type.__bases__ if isinstance(base, type))
            ):
                if isinstance(value, str):
                    try:
                        return target_type(value)
                    except ValueError:
                        # Invalid enum value - return as-is for validation to catch
                        return value
                return value

        # Handle nested Typed objects
        if hasattr(target_type, "__bases__") and any(
            issubclass(base, Typed) for base in target_type.__bases__ if isinstance(base, type)
        ):
            if isinstance(value, dict):
                # Create nested object directly to maintain strict validation
                # The nested object's own validation will catch type errors
                return target_type(**value)
            return value

        # Do NOT convert basic types (int, float, str, bool) - maintain strict validation
        # Return value as-is and let validation catch type mismatches
        return value

    @classmethod
    def _is_Typed_type(cls, target_type: Type) -> bool:
        """Check if a type is a Typed subclass.

        Args:
            target_type: The type to check

        Returns:
            True if target_type is a subclass of Typed, False otherwise

        Note:
            This method safely handles types that may not be classes or may
            not support isinstance/issubclass operations.
        """
        if not hasattr(target_type, "__bases__"):
            return False
        try:
            return any(issubclass(base, Typed) for base in target_type.__bases__ if isinstance(base, type))
        except TypeError:
            return False

    @classmethod
    def _validate_and_convert_class_defaults(cls) -> None:
        """Validate and convert default values at class definition time.

        This method is called during class creation (in __init_subclass__) to:
        1. Convert default values to appropriate types (e.g., "25" -> 25 for int fields)
        2. Handle hierarchical defaults (convert dicts to Typed objects)
        3. Convert mutable defaults to default_factory to prevent shared mutable state
        4. Validate that converted defaults comply with their type annotations
        5. Provide clear error messages for invalid defaults

        The validation happens before dataclass transformation to ensure that
        dataclass receives properly typed default values.

        Raises:
            TypeError: If a default value cannot be converted or is invalid for its type

        Examples:
            ```python
            class Config(Typed):
                port: int = "8080"  # Converted to int(8080)
                users: List[User] = [{"name": "admin"}]  # Converted to default_factory

            # Raises TypeError at class definition:
            class BadConfig(Typed):
                count: int = "invalid"  # Cannot convert to int
            ```
        """
        # Get type hints directly from the class
        if not hasattr(cls, "__annotations__"):
            return

        annotations = cls.__annotations__
        for field_name, field_type in annotations.items():
            # Check if there's a class attribute with a default value
            if hasattr(cls, field_name):
                default_value = getattr(cls, field_name)

                # Skip if this looks like a Field object or method
                if hasattr(default_value, "__call__") or str(type(default_value)).startswith(
                    "<class 'dataclasses."
                ):
                    continue

                try:
                    # Create a mock field object for conversion
                    mock_field = type("MockField", (), {"type": field_type})()

                    # Try to convert the default value
                    converted_default = cls._convert_value(mock_field, default_value)

                    # Handle mutable defaults - convert to default_factory
                    # Include Typed objects as they are also mutable
                    is_mutable = isinstance(converted_default, (list, dict, set)) or (
                        hasattr(converted_default, "__dict__")
                        and hasattr(converted_default.__class__, "__bases__")
                        and any(
                            issubclass(base, Typed)
                            for base in converted_default.__class__.__bases__
                            if isinstance(base, type)
                        )
                    )

                    if is_mutable:
                        # Import field here to avoid circular imports
                        from dataclasses import field

                        # Create a factory function that returns a copy of the converted default
                        def make_factory(value):
                            def factory():
                                if isinstance(value, list):
                                    return value.copy()
                                elif isinstance(value, dict):
                                    return value.copy()
                                elif isinstance(value, set):
                                    return value.copy()
                                elif hasattr(value, "copy"):
                                    # For Typed objects that might have a copy method
                                    try:
                                        return value.copy()
                                    except (AttributeError, TypeError):
                                        # If copy fails, create a new instance from dict
                                        return value.__class__.from_dict(value.to_dict())
                                else:
                                    # For other Typed objects, create new instance
                                    if hasattr(value, "to_dict") and hasattr(value.__class__, "from_dict"):
                                        return value.__class__.from_dict(value.to_dict())
                                    return value

                            return factory

                        # Replace the class attribute with a field() using default_factory
                        setattr(cls, field_name, field(default_factory=make_factory(converted_default)))
                    else:
                        # Update the class attribute with the converted value for immutable types
                        if converted_default is not default_value:
                            setattr(cls, field_name, converted_default)

                    # Basic type validation - create temp instance for validation methods
                    temp_instance = object.__new__(cls)
                    temp_instance._Typed__dict = {}  # Initialize to avoid AttributeError

                    # Special handling for None values with Optional types
                    if converted_default is None and temp_instance._type_allows_none(field_type):
                        # None is valid for Optional types, skip validation
                        pass
                    elif not temp_instance._is_value_valid_for_type(converted_default, field_type):
                        raise TypeError(
                            f"Default value for field '{field_name}' in class '{cls.__name__}' "
                            f"expected type {field_type}, got {type(converted_default).__name__} "
                            f"with value {converted_default!r}"
                        )
                except Exception as e:
                    # Re-raise with more context
                    raise TypeError(
                        f"Invalid default value for field '{field_name}' in class '{cls.__name__}': {e}"
                    ) from e

    @classmethod
    def _validate_default_factories(cls) -> None:
        """Validate default_factory callables after dataclass transformation.

        This method ensures that all default_factory values are callable.
        It's called after dataclass transformation because some default_factory
        values may be created automatically during mutable default conversion.

        Raises:
            TypeError: If a default_factory is not callable

        Note:
            This validation cannot check the return type of default_factory
            functions since they are called at instance creation time, not
            class definition time.
        """
        if cls not in cls._field_cache:
            return

        field_info = cls._field_cache[cls]
        for field_name, field in field_info.items():
            # Check default_factory values
            if field.default_factory is not MISSING:
                if not callable(field.default_factory):
                    raise TypeError(
                        f"default_factory for field '{field_name}' in class '{cls.__name__}' "
                        f"must be callable, got {type(field.default_factory).__name__}"
                    )

    def _validate_types(self) -> None:
        """Validate that all field values match their type annotations."""
        field_info = self._get_field_info()

        for field_name, field in field_info.items():
            value = getattr(self, field_name)
            field_type = field.type

            # Skip validation for None values if the field type allows None
            if value is None:
                if self._type_allows_none(field_type):
                    continue
                else:
                    raise TypeError(f"Field '{field_name}' cannot be None, expected {field_type}")

            # Validate the value against the field type
            if not self._is_value_valid_for_type(value, field_type):
                raise TypeError(
                    f"Field '{field_name}' expected type {field_type}, got {type(value).__name__} with value {value!r}"
                )

    def _type_allows_none(self, field_type: Type) -> bool:
        """Check if a type annotation allows None values."""
        # Handle Union types (e.g., Optional[int] = Union[int, None])
        if get_origin(field_type) is Union:
            union_args = get_args(field_type)
            return type(None) in union_args

        return False

    def _is_value_valid_for_type(self, value: Any, field_type: Type) -> bool:
        """Check if a value is valid for the given type annotation."""
        # Handle Union types (e.g., Optional[int] = Union[int, None])
        if get_origin(field_type) is Union:
            union_args = get_args(field_type)
            # Value is valid if it matches any type in the union (except None, handled separately)
            for arg_type in union_args:
                if arg_type is type(None):
                    continue
                if self._is_value_valid_for_single_type(value, arg_type):
                    return True
            return False

        return self._is_value_valid_for_single_type(value, field_type)

    def _is_value_valid_for_single_type(self, value: Any, target_type: Type) -> bool:
        """Check if a value is valid for a single target type."""
        # Handle generic types (e.g., List[str], Dict[str, int])
        origin_type = get_origin(target_type)
        if origin_type is not None:
            # For generic types, check if value is instance of the origin type
            # We don't check the type parameters for simplicity - just the container type
            try:
                return isinstance(value, origin_type)
            except TypeError:
                # Some types might not work with isinstance, fallback to basic checks
                return False

        # Handle direct type match
        try:
            if isinstance(value, target_type):
                return True
        except TypeError:
            # Some types (like complex generics) can't be used with isinstance
            # In this case, we'll be permissive and allow the value
            return True

        # Handle AutoEnum types (if available in morphic)
        if hasattr(target_type, "__bases__"):
            try:
                # Try to import from morphic package
                from .autoenum import AutoEnum

                if any(
                    issubclass(base, AutoEnum) for base in target_type.__bases__ if isinstance(base, type)
                ):
                    return isinstance(value, target_type)
            except ImportError:
                pass

            # Handle other enum types
            if (
                hasattr(target_type, "_value_")
                or hasattr(target_type, "value")
                or any(hasattr(base, "_value_") for base in target_type.__bases__ if isinstance(base, type))
            ):
                return isinstance(value, target_type)

        # Handle nested Typed objects
        if hasattr(target_type, "__bases__") and any(
            issubclass(base, Typed) for base in target_type.__bases__ if isinstance(base, type)
        ):
            return isinstance(value, target_type)

        # For basic types, only allow exact type matches for strict validation
        # This means str won't auto-convert to int, etc.
        try:
            return isinstance(value, target_type)
        except TypeError:
            # If isinstance fails, be permissive
            return True

    def __repr__(self) -> str:
        """Enhanced repr that shows all fields clearly."""
        field_info = self._get_field_info()
        field_strs = []

        for field_name in field_info:
            value = getattr(self, field_name)
            field_strs.append(f"{field_name}={value!r}")

        return f"{self.__class__.__name__}({', '.join(field_strs)})"


class ValidationError(ValueError):
    """Exception raised when function argument validation fails."""

    pass


def validate(func: Callable = None, /, *, validate_return: bool = False) -> Callable:
    """Decorator that validates function arguments using type annotations.

    This decorator provides Pydantic-like validation for function arguments,
    using the same type conversion and validation system as Typed.

    Args:
        func: The function to decorate (when used as @validate)
        validate_return: Whether to validate the return value. Default: False

    Returns:
        Decorated function with argument validation

    Raises:
        ValidationError: When function arguments don't match their type annotations

    Examples:
        ```python
        from morphic import Typed, validate

        # Basic usage
        @validate
        def add_numbers(a: int, b: int) -> int:
            return a + b

        result = add_numbers("5", "10")  # Strings converted to ints: 15

        # With return validation
        @validate(validate_return=True)
        def process_data(data: Any, count: int = 10) -> str:
            return f"Processed {count} items: {data}"

        # With return validation
        @validate(validate_return=True)
        def get_user_name(user_id: int) -> str:
            return f"user_{user_id}"  # Return value validated as str

        # With Typed types
        class User(Typed):
            name: str
            age: int

        @validate
        def create_user(user_data: User) -> User:
            return user_data

        # Dict automatically converted to User object
        user = create_user({"name": "John", "age": 30})
        assert isinstance(user, User)
        ```

    Configuration:
        This decorator always uses the following configuration:
        - arbitrary_types_allowed: True - allows any type annotations
        - validate_default: True - validates default parameter values at decoration time

    Features:
        - Automatic type conversion (e.g., "5" -> 5 for int parameters)
        - Typed object creation from dictionaries
        - AutoEnum string conversion with fuzzy matching
        - List and dict conversion for nested structures
        - Union type support (tries each type in order)
        - Optional parameter validation
        - Default value validation (if validate_default=True)
        - Return value validation (if validate_return=True)
        - Preserves original function signature and metadata
        - Works with both sync and async functions

    Performance Notes:
        - Validation overhead occurs on every function call
        - Type conversion is cached for repeated calls with same types
        - Original function accessible via decorated_func.raw_function
    """
    # Fixed configuration with pydantic-compatible settings
    config = {"arbitrary_types_allowed": True, "validate_default": True}

    def decorator(f: Callable) -> Callable:
        # Get function signature for parameter validation
        sig = inspect.signature(f)

        # Validate default values (always enabled)
        _validate_function_defaults(f, sig)

        @wraps(f)
        def wrapper(*args, **kwargs):
            # Bind arguments to parameters
            try:
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
            except TypeError as e:
                raise ValidationError(f"Invalid function arguments: {e}") from e

            # Validate and convert each argument
            validated_args = {}
            for param_name, value in bound_args.arguments.items():
                param = sig.parameters[param_name]

                # Skip validation for *args and **kwargs parameters
                if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                    validated_args[param_name] = value
                    continue

                # Skip if no type annotation
                if param.annotation == inspect.Parameter.empty:
                    validated_args[param_name] = value
                    continue

                # Create a mock field for the Typed conversion system
                mock_field = type("MockField", (), {"type": param.annotation})()

                try:
                    # Use Typed's type conversion system
                    converted_value = Typed._convert_value(mock_field, value)

                    # Validate the converted value (always using arbitrary_types_allowed=True)
                    if not _is_value_valid_for_annotation(converted_value, param.annotation):
                        raise ValidationError(
                            f"Argument '{param_name}' expected type {param.annotation}, "
                            f"got {type(converted_value).__name__} with value {converted_value!r}"
                        )

                    validated_args[param_name] = converted_value

                except Exception as e:
                    if isinstance(e, ValidationError):
                        raise
                    raise ValidationError(f"Failed to validate argument '{param_name}': {e}") from e

            # Call the original function
            result = f(**validated_args)

            # Validate return value if requested
            if validate_return and sig.return_annotation != inspect.Parameter.empty:
                try:
                    # For return validation, we're stricter - don't do automatic conversion
                    # Just validate that the return value matches the expected type
                    if not _is_value_valid_for_annotation(result, sig.return_annotation):
                        raise ValidationError(
                            f"Return value expected type {sig.return_annotation}, "
                            f"got {type(result).__name__} with value {result!r}"
                        )
                except Exception as e:
                    if isinstance(e, ValidationError):
                        raise
                    raise ValidationError(f"Failed to validate return value: {e}") from e

            return result

        # Store original function for access
        wrapper.raw_function = f
        wrapper.__signature__ = sig

        return wrapper

    # Handle both @validate and @validate(...) usage
    if func is None:
        return decorator
    else:
        return decorator(func)


def _validate_function_defaults(func: Callable, sig: inspect.Signature) -> None:
    """Validate default parameter values against their type annotations."""
    for param_name, param in sig.parameters.items():
        # Skip if no default value or no annotation
        if param.default == inspect.Parameter.empty or param.annotation == inspect.Parameter.empty:
            continue

        # Skip *args and **kwargs
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue

        try:
            # Create mock field for validation
            mock_field = type("MockField", (), {"type": param.annotation})()

            # Use stricter validation for default parameters
            converted_default = _convert_and_validate_default(mock_field, param.default, param.annotation)

            # Additional validation check
            if not _is_value_valid_for_annotation(converted_default, param.annotation):
                raise ValidationError(
                    f"Default value for parameter '{param_name}' in function '{func.__name__}' "
                    f"expected type {param.annotation}, got {type(converted_default).__name__} "
                    f"with value {converted_default!r}"
                )

        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(
                f"Invalid default value for parameter '{param_name}' in function '{func.__name__}': {e}"
            ) from e


def _convert_and_validate_default(mock_field: Any, value: Any, annotation: Type) -> Any:
    """Convert and validate default parameter values with strict validation.

    This function is stricter than Typed._convert_value and will raise
    ValidationError for any conversion that fails, ensuring default values
    are properly validated at decoration time.
    """
    if value is None:
        # Handle None for Optional types
        if get_origin(annotation) is Union:
            union_args = get_args(annotation)
            if type(None) in union_args:
                return None
            else:
                raise ValidationError(f"None not allowed for non-Optional type {annotation}")
        else:
            raise ValidationError(f"None not allowed for type {annotation}")

    # Handle Union types
    if get_origin(annotation) is Union:
        union_args = get_args(annotation)
        last_error = None
        # Try each type in the union
        for arg_type in union_args:
            if arg_type is type(None):
                continue
            try:
                return _convert_and_validate_default_single_type(value, arg_type)
            except (ValueError, TypeError, ValidationError) as e:
                last_error = e
                continue
        # If no conversion worked, raise the last error
        raise ValidationError(f"Could not convert {value!r} to any type in {annotation}") from last_error

    return _convert_and_validate_default_single_type(value, annotation)


def _convert_and_validate_default_single_type(value: Any, target_type: Type) -> Any:
    """Convert value to a single target type with strict validation for defaults."""
    # Handle generic types first
    origin_type = get_origin(target_type)
    if origin_type is not None:
        # Handle List[Type]
        if origin_type is list:
            if not isinstance(value, (list, tuple)):
                raise ValidationError(f"Expected list for {target_type}, got {type(value).__name__}")

            type_args = get_args(target_type)
            if type_args:
                element_type = type_args[0]
                converted_items = []
                for i, item in enumerate(value):
                    try:
                        converted_item = _convert_and_validate_default_single_type(item, element_type)
                        converted_items.append(converted_item)
                    except Exception as e:
                        raise ValidationError(f"Invalid list element at index {i}: {e}") from e
                return converted_items
            return list(value)

        # Handle Dict[KeyType, ValueType]
        elif origin_type is dict:
            if not isinstance(value, dict):
                raise ValidationError(f"Expected dict for {target_type}, got {type(value).__name__}")

            type_args = get_args(target_type)
            if len(type_args) >= 2:
                key_type, value_type = type_args[0], type_args[1]
                converted_dict = {}
                for k, v in value.items():
                    try:
                        converted_key = _convert_and_validate_default_single_type(k, key_type)
                        converted_value = _convert_and_validate_default_single_type(v, value_type)
                        converted_dict[converted_key] = converted_value
                    except Exception as e:
                        raise ValidationError(f"Invalid dict entry {k!r}: {e}") from e
                return converted_dict
            return dict(value)

        # For other generic types, return as-is
        return value

    # If already the right type, return as-is
    try:
        if isinstance(value, target_type):
            return value
    except TypeError:
        # Some types can't be used with isinstance
        pass

    # Handle Typed types
    if hasattr(target_type, "__bases__") and any(
        issubclass(base, Typed) for base in target_type.__bases__ if isinstance(base, type)
    ):
        if isinstance(value, dict):
            try:
                return target_type.from_dict(value)
            except Exception as e:
                raise ValidationError(f"Could not create {target_type.__name__} from dict: {e}") from e
        return value

    # Handle basic type conversions with strict validation
    if target_type in (int, float, str, bool):
        try:
            if target_type is bool and isinstance(value, str):
                # Handle string to bool conversion more strictly
                lower_val = value.lower()
                if lower_val in ("true", "1", "yes", "on"):
                    return True
                elif lower_val in ("false", "0", "no", "off", ""):
                    return False
                else:
                    raise ValueError(f"Cannot convert '{value}' to bool")
            else:
                converted = target_type(value)
                # Additional validation for string to number conversion
                if target_type in (int, float) and isinstance(value, str):
                    # Make sure the conversion actually makes sense
                    if str(converted) != str(value).strip():
                        # Allow for float precision differences
                        if target_type is float:
                            try:
                                if abs(float(value) - converted) > 1e-10:
                                    raise ValueError(f"Conversion changed value: '{value}' -> {converted}")
                            except (ValueError, TypeError):
                                raise ValueError(f"Cannot convert '{value}' to {target_type.__name__}")
                return converted
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Cannot convert {value!r} to {target_type.__name__}: {e}") from e

    # For complex types we can't handle, return as-is and let validation catch issues
    return value


def _is_value_valid_for_annotation(value: Any, annotation: Type) -> bool:
    """Check if a value is valid for a type annotation (always with arbitrary_types_allowed=True)."""
    # Handle None for Optional types
    if value is None:
        if get_origin(annotation) is Union:
            union_args = get_args(annotation)
            return type(None) in union_args
        return False

    # Use Typed's validation logic (with arbitrary types allowed)
    temp_instance = object.__new__(Typed)
    temp_instance._Typed__dict = {}  # Initialize to avoid AttributeError
    return temp_instance._is_value_valid_for_type(value, annotation)
