"""Enhanced base configuration class with Pydantic-like functionality."""

from dataclasses import Field, fields, MISSING
from typing import Any, ClassVar, Dict, Type, TypeVar, Union, get_args, get_origin

T = TypeVar("T", bound="DataModel")


class DataModel:
    """Base class for all configuration classes with enhanced dict conversion and validation.

    This class provides Pydantic-like functionality for dataclasses without external dependencies.
    Subclasses automatically become dataclasses - no @dataclass decorator needed!
    Validation is automatically called after instance creation.

    Features:
    - Automatic dataclass transformation for subclasses
    - Automatic type validation for all field types
    - Automatic nested DataModel conversion in constructor
    - Automatic validation after instance creation
    - Automatic type conversion from dictionaries
    - AutoEnum string conversion with fuzzy matching and aliases (if morphic.AutoEnum is available)
    - Nested object support with validation
    - Serialization/deserialization with filtering options
    - Field caching for performance
    - Copy with modifications

    Example:
        ```python
        from morphic import DataModel

        # No @dataclass decorator needed!
        class User(DataModel):
            name: str
            age: int
            active: bool = True

            def validate(self):
                if self.age < 0:
                    raise ValueError("Age must be non-negative")

        # Validation happens automatically during creation
        user = User(name="John", age=30)  # Type and custom validation called

        # Type validation catches type mismatches
        try:
            User(name=123, age=30)  # Raises TypeError - name must be str
        except TypeError:
            print("Type validation failed!")

        # Also works with from_dict (with type conversion)
        user = User.from_dict({"name": "John", "age": "30"})  # "30" converted to int

        # Invalid data raises validation error immediately
        try:
            User(name="John", age=-5)  # Raises ValueError from custom validation
        except ValueError:
            print("Custom validation failed!")

        # Nested DataModel support - automatic dict-to-object conversion
        class Address(DataModel):
            street: str
            city: str

        class Person(DataModel):
            name: str
            address: Address

        # Constructor automatically converts dict to Address object
        person = Person(name="John", address={"street": "123 Main St", "city": "NYC"})
        assert isinstance(person.address, Address)
        assert person.address.street == "123 Main St"

        # Type validation works on nested objects too
        try:
            Person(name="John", address={"street": 123, "city": "NYC"})  # street must be str
        except TypeError:
            print("Nested validation caught type error!")
        ```
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
            # Handle List[DataModel] or similar list structures
            if origin_type is list:
                type_args = get_args(target_type)
                if type_args and isinstance(value, list):
                    element_type = type_args[0]
                    # Convert each element if it's a DataModel type
                    if cls._is_datamodel_type(element_type):
                        return [cls._convert_single_type(element_type, item) for item in value]
                    # For non-DataModel types, try basic conversion
                    else:
                        return [cls._convert_single_type(element_type, item) for item in value]
                return value

            # Handle Dict[str, DataModel] or similar dict structures
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

            # Handle other enum types by looking for common enum characteristics
            if (
                hasattr(target_type, "_value_")
                or hasattr(target_type, "value")
                or any(hasattr(base, "_value_") for base in target_type.__bases__ if isinstance(base, type))
            ):
                if isinstance(value, str):
                    return target_type(value)
                return value

        # Handle nested DataModel objects
        if hasattr(target_type, "__bases__") and any(
            issubclass(base, DataModel) for base in target_type.__bases__ if isinstance(base, type)
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

            # Convert nested DataModel objects
            if hasattr(value, "to_dict"):
                result[field_name] = value.to_dict(
                    exclude_none=exclude_none, exclude_defaults=exclude_defaults
                )
            # Handle lists that might contain DataModel objects
            elif isinstance(value, list):
                converted_list = []
                for item in value:
                    if hasattr(item, "to_dict"):
                        converted_list.append(item.to_dict(exclude_none=exclude_none, exclude_defaults=exclude_defaults))
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
            # Handle dictionaries that might contain DataModel objects
            elif isinstance(value, dict):
                converted_dict = {}
                for k, v in value.items():
                    if hasattr(v, "to_dict"):
                        converted_dict[k] = v.to_dict(exclude_none=exclude_none, exclude_defaults=exclude_defaults)
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

        This enables automatic conversion of dictionaries to nested DataModel objects
        in the regular constructor. Unlike from_dict(), this only converts nested
        DataModel objects and enums, not basic types (to maintain strict validation).
        """
        field_info = self._get_field_info()

        for field_name, field in field_info.items():
            current_value = getattr(self, field_name)

            # Only convert if it could be a nested DataModel or enum, not basic types
            converted_value = self._convert_value_strict(field, current_value)

            # Update the field value if it was converted
            if converted_value is not current_value:
                setattr(self, field_name, converted_value)

    @classmethod
    def _convert_value_strict(cls, field: Field, value: Any) -> Any:
        """Convert a value with strict rules (only nested DataModels and enums).

        This is used in the constructor to maintain strict type validation while
        still allowing dict-to-DataModel conversion for nested objects.
        """
        if value is None:
            return None

        field_type = field.type

        # Handle Union types (e.g., Optional[DataModel])
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

        Only converts nested DataModel objects and enums, not basic types.
        Also handles hierarchical structures like List[DataModel] and Dict[str, DataModel].
        """
        # Handle generic types (e.g., List[DataModel], Dict[str, DataModel])
        origin_type = get_origin(target_type)
        if origin_type is not None:
            # Handle List[DataModel] or similar list structures
            if origin_type is list:
                type_args = get_args(target_type)
                if type_args and isinstance(value, list):
                    element_type = type_args[0]
                    # Convert each element if it's a DataModel type
                    if cls._is_datamodel_type(element_type) and all(isinstance(item, dict) for item in value):
                        return [element_type(**item) for item in value]
                    # Also handle nested conversions for existing DataModel instances
                    elif cls._is_datamodel_type(element_type):
                        converted_items = []
                        for item in value:
                            if isinstance(item, dict):
                                converted_items.append(element_type(**item))
                            else:
                                converted_items.append(item)
                        return converted_items
                return value

            # Handle Dict[str, DataModel] or similar dict structures
            elif origin_type is dict:
                type_args = get_args(target_type)
                if len(type_args) >= 2 and isinstance(value, dict):
                    value_type = type_args[1]  # Second type arg is the value type
                    # Convert dict values if they're DataModel types
                    if cls._is_datamodel_type(value_type):
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

        # Handle nested DataModel objects
        if hasattr(target_type, "__bases__") and any(
            issubclass(base, DataModel) for base in target_type.__bases__ if isinstance(base, type)
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
    def _is_datamodel_type(cls, target_type: Type) -> bool:
        """Check if a type is a DataModel subclass."""
        if not hasattr(target_type, "__bases__"):
            return False
        try:
            return any(
                issubclass(base, DataModel) for base in target_type.__bases__ if isinstance(base, type)
            )
        except TypeError:
            return False

    @classmethod
    def _validate_and_convert_class_defaults(cls) -> None:
        """Validate and potentially convert default values before dataclass transformation."""
        # Get type hints directly from the class
        if not hasattr(cls, '__annotations__'):
            return

        annotations = cls.__annotations__
        for field_name, field_type in annotations.items():
            # Check if there's a class attribute with a default value
            if hasattr(cls, field_name):
                default_value = getattr(cls, field_name)

                # Skip if this looks like a Field object or method
                if hasattr(default_value, '__call__') or str(type(default_value)).startswith('<class \'dataclasses.'):
                    continue

                try:
                    # Create a mock field object for conversion
                    mock_field = type('MockField', (), {'type': field_type})()

                    # Try to convert the default value
                    converted_default = cls._convert_value(mock_field, default_value)

                    # Handle mutable defaults - convert to default_factory
                    # Include DataModel objects as they are also mutable
                    is_mutable = isinstance(converted_default, (list, dict, set)) or (
                        hasattr(converted_default, '__dict__') and
                        hasattr(converted_default.__class__, '__bases__') and
                        any(issubclass(base, DataModel) for base in converted_default.__class__.__bases__ if isinstance(base, type))
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
                                elif hasattr(value, 'copy'):
                                    # For DataModel objects that might have a copy method
                                    try:
                                        return value.copy()
                                    except (AttributeError, TypeError):
                                        # If copy fails, create a new instance from dict
                                        return value.__class__.from_dict(value.to_dict())
                                else:
                                    # For other DataModel objects, create new instance
                                    if hasattr(value, 'to_dict') and hasattr(value.__class__, 'from_dict'):
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
                    temp_instance._DataModel__dict = {}  # Initialize to avoid AttributeError

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
        """Validate default_factory values after dataclass transformation."""
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

        # Handle nested DataModel objects
        if hasattr(target_type, "__bases__") and any(
            issubclass(base, DataModel) for base in target_type.__bases__ if isinstance(base, type)
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