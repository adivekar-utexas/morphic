"""Enhanced base configuration class with Pydantic-like functionality."""

import functools
import textwrap
import typing
from abc import ABC
from pprint import pformat
from typing import (
    Any,
    ClassVar,
    Dict,
    NoReturn,
    Optional,
    Set,
    Tuple,
    TypeVar,
    get_args,
    get_origin,
)

from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError, model_validator, validate_call
from pydantic.errors import PydanticSchemaGenerationError
from pydantic_core import PydanticUndefined

from .autoenum import AutoEnum
from .registry import Registry
from .structs import INBUILT_COLLECTIONS, map_collection


def format_exception_msg(ex: Exception, short: bool = False, prefix: Optional[str] = None) -> str:
    """
    Format exception messages with optional traceback information.

    Provides a utility for formatting exception messages with configurable detail levels
    and optional prefixes. Used internally by Typed for enhanced error reporting.

    Args:
        ex (Exception): The exception to format.
        short (bool, optional): Whether to use short format for traceback.
            Defaults to False (full traceback).
        prefix (Optional[str], optional): Optional prefix to add to the message.
            Defaults to None.

    Returns:
        str: Formatted exception message with traceback information.

    Examples:
        ```python
        try:
            raise ValueError("Something went wrong")
        except Exception as e:
            # Short format
            short_msg = format_exception_msg(e, short=True)
            print(short_msg)
            # "ValueError: 'Something went wrong'\\nTrace: file.py#123; "

            # Full format with prefix
            full_msg = format_exception_msg(e, prefix="Validation Error")
            print(full_msg)
            # "Validation Error: ValueError: 'Something went wrong'\\nTraceback:\\n\\tfile.py line 123, in function..."
        ```

    Note:
        This is primarily an internal utility function used by Typed's error handling.
        Reference: https://stackoverflow.com/a/64212552
    """
    ## Ref: https://stackoverflow.com/a/64212552
    tb = ex.__traceback__
    trace = []
    while tb is not None:
        trace.append(
            {
                "filename": tb.tb_frame.f_code.co_filename,
                "function_name": tb.tb_frame.f_code.co_name,
                "lineno": tb.tb_lineno,
            }
        )
        tb = tb.tb_next
    if prefix is not None:
        out = f'{prefix}: {type(ex).__name__}: "{str(ex)}"'
    else:
        out = f'{type(ex).__name__}: "{str(ex)}"'
    if short:
        out += "\nTrace: "
        for trace_line in trace:
            out += f"{trace_line['filename']}#{trace_line['lineno']}; "
    else:
        out += "\nTraceback:"
        for trace_line in trace:
            out += f"\n\t{trace_line['filename']} line {trace_line['lineno']}, in {trace_line['function_name']}..."
    return out.strip()


class classproperty(property):
    """
    Descriptor that allows properties to be accessed at the class level.

    Similar to the built-in `property` decorator, but works on classes rather than instances.
    This allows defining computed properties that can be accessed directly on the class
    without requiring an instance.

    Examples:
        ```python
        class MyClass:
            _name = "Example"

            @classproperty
            def name(cls):
                return cls._name

        # Access directly on class
        print(MyClass.name)  # "Example"

        # Also works on instances
        instance = MyClass()
        print(instance.name)  # "Example"
        ```

    Note:
        This is used internally by Typed for class-level properties like `class_name`
        and `param_names`. Reference: https://stackoverflow.com/a/13624858/4900327
    """

    def __get__(self, obj, objtype=None):
        return super(classproperty, self).__get__(objtype)

    def __set__(self, obj, value):
        super(classproperty, self).__set__(type(obj), value)

    def __delete__(self, obj):
        super(classproperty, self).__delete__(type(obj))


def _Typed_pformat(data: Any) -> str:
    """
    Pretty-format data structures for enhanced error messages.

    Internal utility function that provides consistent, readable formatting for
    data structures in error messages and debugging output.

    Args:
        data (Any): The data structure to format.

    Returns:
        str: Pretty-formatted string representation of the data.

    Configuration:
        Uses the following pprint settings for optimal readability:
        - width=100: Maximum line width
        - indent=2: Indentation level for nested structures
        - depth=None: No depth limit for nested structures
        - compact=False: Prioritize readability over compactness
        - sort_dicts=False: Preserve original dict ordering
        - underscore_numbers=True: Use underscores in large numbers

    Note:
        This is an internal utility function used by Typed's error handling
        to provide readable representations of input data in error messages.
    """
    return pformat(
        data, width=100, indent=2, depth=None, compact=False, sort_dicts=False, underscore_numbers=True
    )


T = TypeVar("T", bound="Typed")


class Typed(BaseModel, ABC):
    """
    Enhanced Pydantic BaseModel with advanced validation and utility features.

    Typed provides a powerful foundation for creating structured data models with automatic validation,
    type conversion, serialization, and enhanced error handling. Built on top of Pydantic BaseModel,
    it adds additional convenience methods and improved error reporting while maintaining full
    compatibility with Pydantic's ecosystem.

    Features:
        - **Enhanced Error Handling**: Detailed validation error messages with context
        - **Type Validation**: Automatic type conversion and validation using Pydantic
        - **Immutable Models**: Frozen models by default for thread safety
        - **JSON Schema**: Automatic schema generation for API documentation
        - **Serialization**: JSON and dict serialization with customizable options
        - **Class Properties**: Convenient access to model metadata and field information
        - **Registry Integration**: Compatible with morphic.Registry for factory patterns
        - **Lifecycle Hooks**: Four customizable hooks for initialization and validation
            - `pre_initialize`: Set up derived fields before validation
            - `pre_validate`: Validate and normalize input data
            - `post_initialize`: Perform side effects after validation
            - `post_validate`: Validate the completed instance

    Configuration:
        The class uses a pre-configured Pydantic ConfigDict with the following settings:

        - `extra="forbid"`: Prevents extra fields not defined in the model
        - `frozen=True`: Makes instances immutable after creation
        - `validate_default=True`: Validates default values during model creation
        - `arbitrary_types_allowed=True`: Allows custom types that don't have Pydantic validators

    Basic Usage:
        ```python
        from morphic.typed import Typed
        from typing import Optional, List

        class User(Typed):
            name: str
            age: int
            email: Optional[str] = None
            tags: List[str] = []

        # Create and pre_validate instances
        user = User(name="John", age=30, email="john@example.com")
        print(user.name)  # "John"

        # Automatic type conversion
        user2 = User(name="Jane", age="25")  # age converted from string to int
        print(user2.age)  # 25 (int)

        # Validation errors with detailed messages
        try:
            invalid_user = User(name="Bob", age="invalid")
        except ValueError as e:
            print(e)  # Detailed error with field location and input
        ```

    Advanced Usage:
        ```python
        from pydantic import Field, field_validator
        from morphic.typed import Typed

        class Product(Typed):
            name: str = Field(..., description="Product name")
            price: float = Field(..., gt=0, description="Price must be positive")
            category: str = Field(default="general", description="Product category")

            @field_validator('name')
            @classmethod
            def validate_name(cls, v):
                if not v.strip():
                    raise ValueError("Name cannot be empty")
                return v.title()

        # Factory method
        product = Product.of(name="laptop", price=999.99, category="electronics")

        # Serialization
        data = product.model_dump()  # Convert to dict
        json_str = product.model_dump_json()  # Convert to JSON string

        # Schema generation
        schema = Product.model_json_schema()
        ```

        Integration with AutoEnum:
            ```python
            from morphic.autoenum import AutoEnum, auto
            from morphic.typed import Typed

            class Status(AutoEnum):
                ACTIVE = auto()
                INACTIVE = auto()
                PENDING = auto()

            class Task(Typed):
                title: str
                status: Status = Status.PENDING

            # AutoEnum fields work seamlessly
            task = Task(title="Review PR", status="ACTIVE")  # String converted to enum
            assert task.status == Status.ACTIVE
            ```

        Lifecycle Hooks Example:
            ```python
            from morphic.typed import Typed
            from typing import Optional
            from datetime import datetime

            class User(Typed):
                first_name: str
                last_name: str
                email: str

                # Derived fields
                full_name: Optional[str] = None
                email_domain: Optional[str] = None
                created_at: Optional[str] = None

                @classmethod
                def pre_initialize(cls, data: dict) -> None:
                    # Set up derived fields before validation
                    if 'first_name' in data and 'last_name' in data:
                        data['full_name'] = f"{data['first_name']} {data['last_name']}"

                    if 'email' in data:
                        data['email_domain'] = data['email'].split("@")[1]

                    if data.get('created_at') is None:
                        data['created_at'] = datetime.now().isoformat()

                @classmethod
                def pre_validate(cls, data: dict) -> None:
                    # Normalize and validate input data
                    if 'email' in data:
                        data['email'] = data['email'].lower().strip()

                    if 'first_name' in data:
                        data['first_name'] = data['first_name'].strip().title()

                    if 'last_name' in data:
                        data['last_name'] = data['last_name'].strip().title()

                def post_initialize(self) -> None:
                    # Perform side effects after validation
                    print(f"User {self.full_name} created at {self.created_at}")

                def post_validate(self) -> None:
                    # Validate the completed instance
                    if not self.email_domain:
                        raise ValueError("Email domain is required")

            # Usage
            user = User(
                first_name="john",
                last_name="doe",
                email="  JOHN@EXAMPLE.COM  "
            )
            assert user.first_name == "John"
            assert user.last_name == "Doe"
            assert user.email == "john@example.com"
            assert user.full_name == "John Doe"
            assert user.email_domain == "example.com"
            assert user.created_at is not None
            ```

        See Also:
            - `morphic.registry.Registry`: For factory pattern and class registration
            - `morphic.autoenum.AutoEnum`: For fuzzy-matching enumerations
            - `pydantic.BaseModel`: The underlying Pydantic base class
    """

    ## Registry integration support
    aliases: ClassVar[Tuple[str, ...]] = tuple()

    ## Pydantic V2 config schema:
    ## https://docs.pydantic.dev/2.1/blog/pydantic-v2-alpha/#changes-to-config
    model_config = ConfigDict(
        ## Only string literal is needed for extra parameter
        ## https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.extra
        extra="forbid",
        ## https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.frozen
        frozen=True,
        ## https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.validate_default
        validate_default=True,
        ## https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.arbitrary_types_allowed
        arbitrary_types_allowed=True,
        ## Ref: https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.validate_assignment
        validate_assignment=False,  ## Unnecessary since Typed is frozen
        ## Custom setting for private attribute validation
        validate_private_assignment=True,
    )

    def __init__(self, /, **data: Dict[str, Any]):
        """
        Initialize a new Typed instance with validation and enhanced error handling.

        This constructor extends Pydantic's BaseModel initialization with improved error
        messages and detailed validation feedback. It automatically validates all fields
        according to their type annotations and any custom validators defined in the model.

        Args:
            **data (Dict): Keyword arguments representing the field values for the model.
                Each key should correspond to a field name defined in the model, and the
                value will be validated and potentially converted to the correct type.

        Raises:
            ValueError: If validation fails for any field. The error message includes:
                - Detailed breakdown of each validation error
                - Field locations where errors occurred
                - Input values that caused the errors
                - Pretty-formatted representation of all provided data

                This wraps Pydantic's ValidationError to provide more context.

        Examples:
            ```python
            class User(Typed):
                name: str
                age: int
                active: bool = True

            # Valid initialization
            user = User(name="John", age=30)
            print(user.name)  # "John"

            # Type conversion
            user2 = User(name="Jane", age="25", active="false")
            print(user2.age)    # 25 (converted from string)
            print(user2.active) # False (converted from string)

            # Validation error with detailed message
            try:
                User(name="Bob", age="invalid_age")
            except ValueError as e:
                print(e)
                # Output includes:
                # - Error location: ('age',)
                # - Error message: Input should be a valid integer
                # - Input value: 'invalid_age'
                # - All provided data: {'name': 'Bob', 'age': 'invalid_age'}
            ```

        Field Validation:
            The constructor performs validation in the following order:

            1. **Type Validation**: Each field is validated against its type annotation
            2. **Field Validators**: Custom validators decorated with `@field_validator`
            3. **Model Validators**: Model-level validators decorated with `@model_validator`
            4. **Constraint Validation**: Pydantic Field constraints (min, max, regex, etc.)

        Type Conversion:
            Common type conversions that happen automatically:

            - `str` to `int`, `float`, `bool` when the string represents a valid value
            - `int` to `float` when a float field receives an integer
            - `str` to `AutoEnum` when using morphic AutoEnum fields
            - `dict` to nested `Typed` models when properly annotated
            - `list` elements converted according to `List[Type]` annotations

        Note:
            This method wraps Pydantic's native ValidationError in a ValueError with
            enhanced formatting. The original Pydantic behavior is preserved while
            providing more user-friendly error messages.
        """
        try:
            super().__init__(**data)
        except ValidationError as e:
            errors_str = ""
            for error_i, error in enumerate(e.errors()):
                assert isinstance(error, dict)
                # Access 'msg' and 'loc' directly to raise KeyError if missing
                error_msg: str = textwrap.indent(error["msg"], "    ").strip()
                error_loc: tuple = error["loc"]
                error_type: str = error["type"]

                errors_str += "\n"
                errors_str += textwrap.indent(
                    f"[Error#{error_i + 1}] ValidationError at field {error_loc}:\n{error_msg} (type={error_type})",
                    "  ",
                )

                if isinstance(error["input"], dict):
                    errors_str += "\n"
                    errors_str += textwrap.indent(
                        f"[Error#{error_i + 1}] Input keys: {_Typed_pformat(tuple(error['input'].keys()))}",
                        "  ",
                    )
                    errors_str += "\n"
                    errors_str += textwrap.indent(
                        f"[Error#{error_i + 1}] Input values: {_Typed_pformat(error['input'])}", "  "
                    )
                else:
                    errors_str += "\n"
                    errors_str += textwrap.indent(
                        f"[Error#{error_i + 1}] Input: {_Typed_pformat(error['input'])}", "  "
                    )
            raise ValueError(
                f"Cannot create Pydantic instance of type '{self.class_name}' {self.__class__}, "
                f"encountered following validation errors: {errors_str}"
                f"\nInputs to '{self.class_name}' constructor are {tuple(data.keys())}:"
                f"\n{_Typed_pformat(data)}"
            )

        except Exception as e:
            error_msg: str = textwrap.indent(format_exception_msg(e), "    ")
            raise ValueError(
                f"Cannot create Pydantic instance of type '{self.class_name}' {self.__class__}, "
                f"encountered Exception:\n{error_msg}"
                f"\nInputs to '{self.class_name}' constructor are {tuple(data.keys())}:"
                f"\n{_Typed_pformat(data)}"
            )

    @classmethod
    def of(cls, registry_key: Optional[Any] = None, /, **data: Dict[str, Any]) -> T:
        """
        Factory method for creating instances with automatic Registry delegation.

        This factory method intelligently delegates to Registry's hierarchical factory when the class
        inherits from both Typed and Registry, while maintaining the simple Typed factory behavior
        for pure Typed classes. This ensures that Registry's sophisticated factory patterns work
        seamlessly with Typed's validation and modeling capabilities.

        Delegation Logic:
            - **Registry + Typed Classes**: Automatically delegates to Registry.of() for hierarchical
              factory patterns, registry key lookup, and subclass instantiation
            - **Pure Typed Classes**: Uses simple constructor-based factory for direct instantiation
            - **Detection**: Checks if the class inherits from Registry using method resolution order

        Args:
            registry_key (Optional[Any], optional): Registry key for subclass lookup. When provided,
                this triggers Registry-style factory behavior. When None and class inherits from
                Registry, uses Registry's direct instantiation logic. Defaults to None.
            **data (Dict[str, Any]): Field values passed to the class constructor. These undergo
                Pydantic validation and type conversion.

        Returns:
            T: A new instance of the appropriate subclass (for Registry) or the class itself (for Typed).

        Raises:
            ValueError: If validation fails during Typed model creation
            KeyError: If registry_key not found in Registry hierarchy
            TypeError: If Registry constraints are violated (e.g., abstract class without key)

        Registry Integration Examples:
            ```python
            from morphic.registry import Registry
            from morphic.typed import Typed
            from abc import ABC, abstractmethod

            # Proper inheritance order: Typed first, then Registry
            class Animal(Typed, Registry, ABC):
                name: str
                species: str

                @abstractmethod
                def speak(self) -> str:
                    pass

            class Dog(Animal):
                aliases = ["canine", "puppy"]

                def __init__(self, name: str = "Buddy", breed: str = "Mixed", **kwargs):
                    # Extract Typed fields for validation
                    super().__init__(name=name, species="Canis lupus", **kwargs)
                    self.breed = breed

                def speak(self) -> str:
                    return f"{self.name} says Woof!"

            class Cat(Animal):
                aliases = ["feline", "kitty"]

                def __init__(self, name: str = "Whiskers", color: str = "Orange", **kwargs):
                    super().__init__(name=name, species="Felis catus", **kwargs)
                    self.color = color

                def speak(self) -> str:
                    return f"{self.name} says Meow!"

            # Registry factory patterns work seamlessly
            dog = Animal.of("Dog", name="Rex", breed="German Shepherd")
            assert isinstance(dog, Dog)
            assert dog.name == "Rex"           # Pydantic validated
            assert dog.species == "Canis lupus"  # Pydantic validated
            assert dog.breed == "German Shepherd"  # Custom attribute

            # Alias support
            cat = Animal.of("feline", name="Shadow", color="Black")
            assert isinstance(cat, Cat)
            assert cat.speak() == "Shadow says Meow!"

            # Direct concrete instantiation
            dog2 = Dog.of(name="Buddy", breed="Labrador")
            assert isinstance(dog2, Dog)
            assert dog2.name == "Buddy"

            # Hierarchical scoping still enforced
            # Dog.of("Cat") would raise KeyError - not in Dog's hierarchy
            ```

        Pure Typed Usage:
            ```python
            # Pure Typed classes work as before
            class User(Typed):
                name: str
                age: int
                active: bool = True

            # Simple factory method (no registry_key parameter used)
            user = User.of(name="John", age=30)
            assert isinstance(user, User)
            assert user.name == "John"
            ```

        Advanced Registry Patterns:
            ```python
            # Complex hierarchies with validation
            class DatabaseConnection(Typed, Registry, ABC):
                host: str = "localhost"
                port: int = 5432
                ssl: bool = False

                @abstractmethod
                def connect(self) -> str:
                    pass

            class PostgreSQL(DatabaseConnection):
                aliases = ["postgres", "pg"]

                def __init__(self, database: str = "mydb", **kwargs):
                    super().__init__(**kwargs)
                    self.database = database

                def connect(self) -> str:
                    return f"postgresql://{self.host}:{self.port}/{self.database}"

            # Type conversion and validation happen automatically
            db = DatabaseConnection.of(
                "postgres",
                host="remote.db",
                port="5433",      # String converted to int
                ssl="true",       # String converted to bool
                database="production"
            )
            assert db.port == 5433        # Converted and validated
            assert db.ssl is True         # Converted and validated
            assert db.database == "production"
            ```

        Method Resolution:
            When a class inherits from both Typed and Registry, the method resolution follows:

            1. Check if class has Registry in its MRO (method resolution order)
            2. If Registry found: Delegate to Registry.of() with all arguments
            3. If no Registry: Use simple Typed factory (ignore registry_key if provided)

        Error Handling:
            ```python
            # Registry errors are preserved
            try:
                Animal.of("InvalidAnimal")  # KeyError from Registry
            except KeyError as e:
                print(f"Registry error: {e}")

            # Pydantic validation errors are preserved
            try:
                Animal.of("Dog", name="Rex", age="invalid")  # ValueError from Typed
            except ValueError as e:
                print(f"Validation error: {e}")
            ```

        Performance Notes:
            - Registry delegation adds minimal overhead (single MRO check)
            - Pydantic validation occurs in all cases for data integrity
            - Registry hierarchy lookups use O(1) hash table operations

        See Also:
            - `morphic.registry.Registry.of()`: The underlying Registry factory method
            - `morphic.typed.Typed.__init__()`: Pydantic validation and error handling
            - `morphic.autoenum.AutoEnum`: For creating fuzzy-matching registry keys
        """
        # Check if this class inherits from Registry by looking at the method resolution order
        # Check if Registry is in the MRO of this class
        if Registry in cls.__mro__:
            # This class inherits from Registry, so delegate to Registry's of method
            # Call Registry.of as a method on the class, not on Registry directly
            # This ensures proper method resolution and class hierarchy handling
            return super(Typed, cls).of(registry_key, **data)
        else:
            if registry_key is not None:
                raise TypeError(
                    f"Registry key '{registry_key}' provided for pure Typed class {cls.class_name}, but pure Typed classes do not support registry keys."
                )
            # Pure Typed class - use simple constructor-based factory
            # Ignore registry_key parameter if provided (for API compatibility)
            return cls(**data)

    @classmethod
    def _get_private_attr_types(cls) -> Dict[str, Any]:
        """
        Get cached type annotations for private attributes.

        This method walks the MRO once per class and caches the result for fast lookups.
        Child class annotations override parent annotations.

        Returns:
            Dict[str, Any]: Mapping of private attribute names to their type annotations.
        """
        # Check if this specific class has already cached its annotations
        # We store the cache directly on the class (not inherited from parent)
        cache_attr = "_annotations_cache"

        # Use __dict__ to check for attribute on this specific class (not inherited)
        if cache_attr not in cls.__dict__:
            # Build annotations dict from MRO (base to derived, so child overrides parent)
            annotations = {}
            for base_cls in reversed(cls.__mro__):
                if base_cls is object:
                    continue
                annotations.update(getattr(base_cls, "__annotations__", {}))

            # Store directly on this class
            setattr(cls, cache_attr, annotations)

        return getattr(cls, cache_attr)

    @classproperty
    def class_name(cls) -> str:
        """
        Get the name of the class as a string.

        Returns the simple class name (without module path) of the current class.
        This is useful for error messages, logging, and debugging.

        Returns:
            str: The name of the class (e.g., "User" for a User class).

        Examples:
            ```python
            class User(Typed):
                name: str

            print(User.class_name)  # "User"

            user = User(name="John")
            print(user.class_name)  # "User" (same for instances)
            ```
        """
        return str(cls.__name__)  ## Will return the child class name.

    @classproperty
    def param_names(cls) -> Set[str]:
        """
        Get the names of all model fields as a set.

        Extracts field names from the model's JSON schema, providing a convenient
        way to inspect what fields are available on a model without creating an instance.

        Returns:
            Set[str]: Set containing all field names defined in the model.

        Examples:
            ```python
            class User(Typed):
                name: str
                age: int
                email: Optional[str] = None

            field_names = User.param_names
            print(field_names)  # {"name", "age", "email"}

            # Check if a field exists
            if "email" in User.param_names:
                print("User model has email field")
            ```

        Note:
            This property uses the model's JSON schema, so it reflects the actual
            fields that Pydantic recognizes for validation and serialization.
        """
        return set(cls.model_json_schema().get("properties", {}).keys())

    @classproperty
    def param_default_values(cls) -> Dict:
        """
        Get default values for model fields that have defaults defined.

        Extracts default values from the model's JSON schema, providing an easy way
        to inspect which fields have defaults and what those default values are.

        Returns:
            Dict: Dictionary mapping field names to their default values. Only includes
                fields that have explicit defaults defined.

        Examples:
            ```python
            class User(Typed):
                name: str                    # No default
                age: int                     # No default
                active: bool = True          # Has default
                role: str = "user"          # Has default
                email: Optional[str] = None  # Has default

            defaults = User.param_default_values
            print(defaults)  # {"active": True, "role": "user", "email": None}

            # Check if a field has a default
            if "active" in User.param_default_values:
                print(f"Default active value: {User.param_default_values['active']}")
            ```

        Note:
            - Only fields with explicit defaults are included
            - Fields without defaults will not appear in the returned dictionary
            - Values are extracted from JSON schema, so they may be serialized representations
        """
        properties = cls.model_json_schema().get("properties", {})
        return {param: prop.get("default") for param, prop in properties.items() if "default" in prop}

    @classproperty
    def _constructor(cls) -> T:
        """
        Internal property that returns the class constructor.

        This is primarily used internally for consistency with other morphic patterns
        and framework integration. External users should generally use the class
        directly or the `of` factory method.

        Returns:
            Type[T]: The class itself, typed as the generic type parameter.

        Note:
            This is an internal implementation detail and may change in future versions.
            Use `cls` directly or `cls.of()` for public API usage.
        """
        return cls

    def __str__(self) -> str:
        """
        Return a human-readable string representation of the model instance.

        Provides a formatted string showing the class name followed by a JSON
        representation of the model's data with proper indentation for readability.

        Returns:
            str: Formatted string containing class name and JSON representation
                of the model data.

        Examples:
            ```python
            class User(Typed):
                name: str
                age: int
                active: bool = True

            user = User(name="John", age=30, active=False)
            print(str(user))
            # Output:
            # User:
            # {
            #     "name": "John",
            #     "age": 30,
            #     "active": false
            # }

            # Also works with complex nested structures
            class Profile(Typed):
                user: User
                tags: List[str]

            profile = Profile(
                user={"name": "Jane", "age": 25},
                tags=["admin", "developer"]
            )
            print(str(profile))  # Formatted JSON with nested User object
            ```

        Note:
            This method uses `model_dump_json()` for Pydantic v2 compatibility
            to generate the JSON representation with proper formatting.
        """
        params_str: str = self.model_dump_json(indent=4)
        out: str = f"{self.class_name}:\n{params_str}"
        return out

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Override attribute setting to validate private attributes when validate_private_assignment is enabled.

        This method extends Pydantic's frozen model behavior by adding automatic
        validation for private attributes (those starting with '_') when the model has
        `validate_private_assignment=True` in its configuration. While Pydantic allows private
        attributes to be set on frozen models (they bypass the frozen restriction), it
        doesn't validate them by default. This override ensures that private attributes
        are validated against their type annotations when validation is enabled.

        **Validation Rules:**
            - **Public fields**: Use normal Pydantic validation and frozen behavior
            - **Private attributes with type hints** (when validate_private_assignment=True):
              Automatically validated against type annotation
            - **Private attributes without type hints**: Set without validation
            - **Dunder attributes** (`__name__`): Set without validation (internal use)
            - **When validate_private_assignment=False**: All private attributes bypass validation

        **Type Validation:**
            The validation uses Pydantic's type system and supports:
            - Basic types: `int`, `str`, `float`, `bool`, etc.
            - Optional types: `Optional[int]`, `Union[int, None]`
            - Collections: `List[int]`, `Dict[str, int]`, `Set[str]`, etc.
            - Nested Typed models: `MyTypedModel`
            - AutoEnum types: `MyAutoEnum`
            - Union types: `Union[int, str]`
            - Complex nested types: `List[Optional[MyTyped]]`, etc.

        Args:
            name (str): The name of the attribute to set.
            value (Any): The value to assign to the attribute.

        Raises:
            ValidationError: If the value fails validation for a typed private attribute
                when validate_private_assignment=True. The error includes:
                - The attribute name
                - The expected type
                - The actual value and its type
                - Detailed validation error from Pydantic

        Examples:
            Basic Private Attribute Validation (with validate_private_assignment=True):
                ```python
                from pydantic import PrivateAttr
                from morphic.typed import Typed

                class Counter(Typed):
                    # Typed has validate_private_assignment=True by default
                    name: str
                    _count: int = PrivateAttr(default=0)

                    def post_initialize(self) -> None:
                        # Valid: _count is an int
                        self._count = 10

                counter = Counter(name="MyCounter")
                counter._count = 20  # Valid

                try:
                    counter._count = "invalid"  # Invalid: wrong type
                except ValidationError as e:
                    print(e)  # Detailed error about type mismatch
                ```

            Without Validation (validate_private_assignment=False):
                ```python
                from pydantic import ConfigDict, PrivateAttr
                from morphic.typed import Typed

                class NoValidationCounter(Typed):
                    model_config = ConfigDict(
                        extra="forbid",
                        frozen=True,
                        validate_private_assignment=False,  # Disable private attr validation
                    )

                    name: str
                    _count: int = PrivateAttr(default=0)

                counter = NoValidationCounter(name="MyCounter")
                counter._count = "anything"  # No validation occurs
                ```

            Optional Private Attributes:
                ```python
                class Cache(Typed):
                    key: str
                    _cached_value: Optional[str] = PrivateAttr(default=None)

                    def post_initialize(self) -> None:
                        self._cached_value = None  # Valid
                        self._cached_value = "cached"  # Valid

                cache = Cache(key="data")
                cache._cached_value = "new_value"  # Valid
                cache._cached_value = None  # Valid
                try:
                    cache._cached_value = 123  # Invalid: int not str
                except ValidationError as e:
                    print(e)
                ```

            Complex Types:
                ```python
                class DataProcessor(Typed):
                    name: str
                    _buffer: List[int] = PrivateAttr(default_factory=list)
                    _metadata: Dict[str, Any] = PrivateAttr(default_factory=dict)

                    def post_initialize(self) -> None:
                        self._buffer = [1, 2, 3]  # Valid
                        self._metadata = {"key": "value"}  # Valid

                processor = DataProcessor(name="Processor")
                processor._buffer = [4, 5, 6]  # Valid
                try:
                    processor._buffer = "not a list"  # Invalid
                except ValidationError as e:
                    print(e)
                ```

            Nested Typed Models:
                ```python
                class Config(Typed):
                    value: int

                class System(Typed):
                    name: str
                    _config: Optional[Config] = PrivateAttr(default=None)

                    def post_initialize(self) -> None:
                        self._config = Config(value=10)  # Valid

                system = System(name="System1")
                system._config = Config(value=20)  # Valid
                try:
                    system._config = {"value": 30}  # Invalid: dict not Config
                except ValidationError as e:
                    print(e)
                ```

            Without Type Annotations (No Validation):
                ```python
                class FlexibleModel(Typed):
                    name: str

                    def post_initialize(self) -> None:
                        # No type annotation, so no validation
                        self._anything = "string"
                        self._anything = 123  # Also valid

                model = FlexibleModel(name="Test")
                model._untyped = {"any": "value"}  # No validation
                ```

        **Performance Notes:**
            - Type annotation lookup is cached internally by Python
            - Validation only occurs when validate_private_assignment=True
            - Validation only occurs for private attributes with type hints
            - No overhead for public fields or untyped private attributes

        **Integration with Pydantic:**
            This validation works seamlessly with Pydantic's features:
            - Respects Pydantic's type coercion (e.g., `"123"` → `123`)
            - Works with Pydantic validators and custom types
            - Compatible with Pydantic's serialization (private attrs excluded)
            - Honors the validate_private_assignment configuration setting

        **Note on validate_assignment vs validate_private_assignment:**
            - `validate_private_assignment`: Controls validation of private attributes (Typed feature)
            - `validate_assignment`: Controls validation of public fields (Pydantic feature, used in MutableTyped)

        See Also:
            - `post_initialize()`: Common place to set private attributes
            - `pydantic.PrivateAttr`: For defining private attributes with defaults
            - `model_config.validate_private_assignment`: Configuration for private attribute validation
        """
        # Check if private attribute validation is enabled in the model config
        # validate_private_assignment is a Typed-specific setting (separate from Pydantic's validate_assignment)
        validate_private_assignment = self.model_config.get("validate_private_assignment", False)

        # Check if this is a private attribute (starts with _ but not __)
        # and validation is enabled
        if validate_private_assignment and name.startswith("_") and not name.startswith("__"):
            # Get cached type annotations for this class (computed once per class, not per instance)
            annotations = type(self)._get_private_attr_types()

            # If this private attribute has a type annotation, validate it
            if name in annotations:
                expected_type = annotations[name]

                # Try to validate the value against the expected type
                try:
                    # Use cached TypeAdapter for validation to avoid recreating it
                    # This ensures we use the same validation logic as regular fields
                    # Note: ConfigDict is not directly supported in TypeAdapter constructor,
                    # so we handle arbitrary types via exception handling

                    # Get or create TypeAdapter cache on this specific class
                    cls = type(self)
                    cache_attr = "_type_adapter_cache"
                    if cache_attr not in cls.__dict__:
                        setattr(cls, cache_attr, {})

                    cache = getattr(cls, cache_attr)

                    # Use type as cache key (hashable)
                    if expected_type not in cache:
                        try:
                            cache[expected_type] = TypeAdapter(expected_type)
                        except PydanticSchemaGenerationError:
                            # Cache None to indicate this type cannot be validated by TypeAdapter
                            cache[expected_type] = None

                    type_adapter = cache[expected_type]

                    # If cached value is None, it means TypeAdapter creation failed previously
                    if type_adapter is None:
                        raise PydanticSchemaGenerationError("Cached: Cannot create TypeAdapter for this type")

                    validated_value = type_adapter.validate_python(value)
                    # Use the validated value (which may have been coerced)
                    value = validated_value
                except PydanticSchemaGenerationError:
                    # TypeAdapter couldn't create a schema for this type (likely an arbitrary type)
                    # Fall back to isinstance check for concrete types
                    origin = get_origin(expected_type)
                    args = get_args(expected_type)

                    if origin is typing.Union and args:
                        # Handle Union types (including Optional)
                        # Check if value matches any of the union types
                        none_allowed = type(None) in args
                        non_none_types = [t for t in args if t is not type(None) and isinstance(t, type)]

                        if value is None:
                            if not none_allowed:
                                raise ValidationError.from_exception_data(
                                    title=f"{self.class_name}.{name}",
                                    line_errors=[
                                        {
                                            "type": "none_required",
                                            "loc": (name,),
                                            "msg": f"Cannot set private attribute '{name}' on {self.class_name} instance. Expected type: {expected_type}, but got None",
                                            "input": value,
                                            "ctx": {"expected": str(expected_type)},
                                        }
                                    ],
                                )
                        elif non_none_types:
                            # Check if value matches any of the non-None types
                            if not any(isinstance(value, t) for t in non_none_types):
                                type_names = " or ".join(t.__name__ for t in non_none_types)
                                raise ValidationError.from_exception_data(
                                    title=f"{self.class_name}.{name}",
                                    line_errors=[
                                        {
                                            "type": "is_instance_of",
                                            "loc": (name,),
                                            "msg": f"Cannot set private attribute '{name}' on {self.class_name} instance. Expected type: {type_names}, but got value of type {type(value).__name__}",
                                            "input": value,
                                            "ctx": {"class": type_names},
                                        }
                                    ],
                                )
                        # else: Union with no concrete types, skip validation
                    elif origin is not None:
                        # For other generic types (List, Dict, etc.), we can't easily validate
                        # without TypeAdapter, so we skip validation
                        pass
                    elif isinstance(expected_type, type):
                        # For concrete types, perform a simple isinstance check
                        if not isinstance(value, expected_type):
                            raise ValidationError.from_exception_data(
                                title=f"{self.class_name}.{name}",
                                line_errors=[
                                    {
                                        "type": "is_instance_of",
                                        "loc": (name,),
                                        "msg": f"Cannot set private attribute '{name}' on {self.class_name} instance. Expected type: {expected_type.__name__}, but got value of type {type(value).__name__}",
                                        "input": value,
                                        "ctx": {"class": expected_type.__name__},
                                    }
                                ],
                            )
                    # else: For non-type annotations (e.g., type variables), skip validation
                except ValidationError as e:
                    # Re-raise ValidationError directly for consistency with Pydantic
                    raise e
                except Exception:
                    # Catch any other unexpected errors during validation
                    # (e.g., TypeAdapter was created but validation fails for arbitrary types)
                    # In this case, fall back to isinstance check for concrete types
                    origin = get_origin(expected_type)
                    args = get_args(expected_type)

                    if origin is typing.Union and args:
                        # Handle Union types (including Optional)
                        # Check if value matches any of the union types
                        none_allowed = type(None) in args
                        non_none_types = [t for t in args if t is not type(None) and isinstance(t, type)]

                        if value is None:
                            if not none_allowed:
                                raise ValidationError.from_exception_data(
                                    title=f"{self.class_name}.{name}",
                                    line_errors=[
                                        {
                                            "type": "none_required",
                                            "loc": (name,),
                                            "msg": f"Cannot set private attribute '{name}' on {self.class_name} instance. Expected type: {expected_type}, but got None",
                                            "input": value,
                                            "ctx": {"expected": str(expected_type)},
                                        }
                                    ],
                                )
                        elif non_none_types:
                            # Check if value matches any of the non-None types
                            if not any(isinstance(value, t) for t in non_none_types):
                                type_names = " or ".join(t.__name__ for t in non_none_types)
                                raise ValidationError.from_exception_data(
                                    title=f"{self.class_name}.{name}",
                                    line_errors=[
                                        {
                                            "type": "is_instance_of",
                                            "loc": (name,),
                                            "msg": f"Cannot set private attribute '{name}' on {self.class_name} instance. Expected type: {type_names}, but got value of type {type(value).__name__}",
                                            "input": value,
                                            "ctx": {"class": type_names},
                                        }
                                    ],
                                )
                        # else: Union with no concrete types, skip validation
                    elif origin is not None:
                        # For other generic types, we can't validate without TypeAdapter, so skip
                        pass
                    elif isinstance(expected_type, type):
                        # For concrete types, perform a simple isinstance check
                        if not isinstance(value, expected_type):
                            raise ValidationError.from_exception_data(
                                title=f"{self.class_name}.{name}",
                                line_errors=[
                                    {
                                        "type": "is_instance_of",
                                        "loc": (name,),
                                        "msg": f"Cannot set private attribute '{name}' on {self.class_name} instance. Expected type: {expected_type.__name__}, but got value of type {type(value).__name__}",
                                        "input": value,
                                        "ctx": {"class": expected_type.__name__},
                                    }
                                ],
                            )
                    # else: For non-type annotations, skip validation

        # Delegate to parent class (BaseModel's __setattr__)
        super().__setattr__(name, value)

    @classmethod
    def _set_default_values(cls, data: Dict):
        if not isinstance(data, dict):
            raise ValueError(f"data must be a dictionary, got {type(data)}")
        ## Apply default values for fields not present in the input
        for field_name, field in cls.model_fields.items():
            if field_name not in data:
                if field.default is not PydanticUndefined:
                    data[field_name] = field.default
                elif field.default_factory is not None:
                    data[field_name] = field.default_factory()

    @classmethod
    def _convert_nested_typed_fields(cls, data: Dict):
        """
        Convert nested dict fields to BaseModel objects and strings to AutoEnum before pre_initialize.

        This method automatically converts:
        - Dictionary values to their corresponding BaseModel objects
        - String values to their corresponding AutoEnum instances

        This ensures that lifecycle hooks always receive properly instantiated objects,
        not raw dictionaries or strings.

        Supports all Python collections (list, tuple, set, frozenset, dict) with:
            - Direct BaseModel fields: `field: MyTyped`
            - Optional BaseModel fields: `field: Optional[MyTyped]`
            - List of BaseModel: `field: List[MyTyped]`
            - Tuple of BaseModel: `field: Tuple[MyTyped, ...]`
            - Set of BaseModel: `field: Set[MyTyped]`
            - FrozenSet of BaseModel: `field: FrozenSet[MyTyped]`
            - Dict with BaseModel values: `field: Dict[str, MyTyped]`
            - Direct AutoEnum fields: `field: MyEnum`
            - Optional AutoEnum fields: `field: Optional[MyEnum]`
            - Collections of AutoEnum: `field: List[MyEnum]`, `Set[MyEnum]`, etc.
            - Dict with AutoEnum values: `field: Dict[str, MyEnum]`
            - Nested combinations of the above
        """
        if not isinstance(data, dict):
            raise ValueError(f"data must be a dictionary, got {type(data)}")

        for field_name, field in cls.model_fields.items():
            if field_name not in data:
                continue

            value = data[field_name]
            if value is None:
                continue

            # Get the field annotation
            annotation = field.annotation

            # Handle Optional[T] - unwrap to get T
            origin = get_origin(annotation)
            args = get_args(annotation)

            # Unwrap Optional/Union types to find the actual type
            actual_types = []
            if origin is typing.Union:
                # Filter out NoneType from Union to get actual types
                actual_types = [arg for arg in args if arg is not type(None)]
            else:
                actual_types = [annotation]

            for actual_type in actual_types:
                inner_origin = get_origin(actual_type)
                inner_args = get_args(actual_type)

                # Check for BaseModel conversions (dicts -> BaseModel instances)
                if isinstance(actual_type, type) and issubclass(actual_type, BaseModel):
                    # Direct BaseModel field - convert directly without map_collection
                    if isinstance(value, dict):
                        data[field_name] = actual_type(**value)
                        break
                elif inner_origin is dict and len(inner_args) >= 2:
                    # Dict[K, BaseModel] - use map_collection without recursion
                    # Each value dict will be converted to a model, and the model's __init__
                    # will handle its own nested conversions
                    value_type = inner_args[1]
                    if isinstance(value_type, type) and issubclass(value_type, BaseModel):

                        def convert_to_model(obj):
                            if isinstance(obj, dict):
                                return value_type(**obj)
                            return obj

                        data[field_name] = map_collection(value, convert_to_model, recurse=False)
                        break
                # Check if this is a collection containing BaseModel or a direct BaseModel
                elif inner_origin in INBUILT_COLLECTIONS and len(inner_args) > 0:
                    # Collection[BaseModel] - use map_collection without recursion
                    # Each dict will be converted to a model, and the model's __init__
                    # will handle its own nested conversions
                    element_type = inner_args[0]
                    if isinstance(element_type, type) and issubclass(element_type, BaseModel):

                        def convert_to_model(obj):
                            if isinstance(obj, dict):
                                return element_type(**obj)
                            return obj

                        data[field_name] = map_collection(value, convert_to_model, recurse=False)
                        break

                # Check for AutoEnum conversions (strings -> AutoEnum instances)
                if isinstance(actual_type, type) and issubclass(actual_type, AutoEnum):
                    # Direct AutoEnum field - convert string to enum
                    if isinstance(value, str):
                        data[field_name] = actual_type(value)
                        break
                elif inner_origin is dict and len(inner_args) >= 2:
                    # Dict[K, AutoEnum] - use map_collection without recursion
                    value_type = inner_args[1]
                    if isinstance(value_type, type) and issubclass(value_type, AutoEnum):

                        def convert_to_enum(obj):
                            if isinstance(obj, str):
                                return value_type(obj)
                            return obj

                        data[field_name] = map_collection(value, convert_to_enum, recurse=False)
                        break
                # Check if this is a collection containing AutoEnum
                elif inner_origin in INBUILT_COLLECTIONS and len(inner_args) > 0:
                    # Collection[AutoEnum] - use map_collection without recursion
                    element_type = inner_args[0]
                    if isinstance(element_type, type) and issubclass(element_type, AutoEnum):

                        def convert_to_enum(obj):
                            if isinstance(obj, str):
                                return element_type(obj)
                            return obj

                        data[field_name] = map_collection(value, convert_to_enum, recurse=False)
                        break

    @model_validator(mode="before")
    @classmethod
    def _pre_set_validate_inputs(cls, data: Dict) -> Dict:
        if not isinstance(data, dict):
            raise ValueError(f"data must be a dictionary, got {type(data)}")
        ## Proxy method for Pydantic to call
        data = cls.pre_set_validate_inputs(data)
        return data

    @classmethod
    def pre_set_validate_inputs(cls, data: Dict) -> Dict:
        """
        Default implementation of pre_set_validate_inputs, overridable by subclasses.
        """
        ## Set default values
        cls._set_default_values(data)

        ## Convert nested Typed fields from dicts to objects
        ## This ensures hooks always receive instantiated objects, not raw dicts
        cls._convert_nested_typed_fields(data)

        ## Call pre_initialize for each superclass in MRO (base to derived)
        ## Only call methods that are defined directly on each class to avoid duplicates
        ## Pass cls (the actual subclass) as context so class variables are accessible
        for base_cls in reversed(cls.__mro__[:-1]):  # Exclude object
            if "pre_initialize" in base_cls.__dict__ and base_cls is not BaseModel:
                # Get the unbound function and call with cls as the first argument
                base_cls.__dict__["pre_initialize"].__func__(cls, data)

        ## Call pre_validate for each superclass in MRO (base to derived)
        ## Only call methods that are defined directly on each class to avoid duplicates
        ## Pass cls (the actual subclass) as context so class variables are accessible
        for base_cls in reversed(cls.__mro__[:-1]):  # Exclude object
            if "pre_validate" in base_cls.__dict__ and base_cls is not BaseModel:
                # Get the unbound function and call with cls as the first argument
                base_cls.__dict__["pre_validate"].__func__(cls, data)

        return data

    @classmethod
    def pre_initialize(cls, data: Any) -> NoReturn:
        """
        Pre-initialization hook for setting up derived fields before validation.

        This classmethod is called after default values are set but before pre_validate.
        It's designed for initializing fields that depend on multiple input fields
        (e.g., computed or derived fields).

        **Execution Order:**
            1. `_set_default_values()` - Apply default values for missing fields
            2. `pre_initialize()` - Initialize derived fields (this method)
            3. `pre_validate()` - Validate and normalize input data
            4. Pydantic field validation - Type conversion and constraint validation
            5. `post_initialize()` - Post-validation initialization
            6. `post_validate()` - Post-validation validation

        **Key Features:**
            - **Pre-validation Hook**: Called before validation logic
            - **Mutable Data**: Can modify the input dictionary directly
            - **Derived Fields**: Ideal for computing fields based on other fields
            - **Automatic Inheritance**: Parent class hooks are called automatically

        Args:
            data (Dict): The input data dictionary passed to the model constructor.
                This dictionary is mutable and can be modified in-place. Keys represent
                field names and values represent the raw input values (with defaults applied).

        Returns:
            NoReturn: This method should not return anything. All modifications should
                be made to the `data` dictionary in-place.

        Note:
            Parent class `pre_initialize` methods are called automatically in MRO order
            (base to derived), so subclasses don't need to call `super().pre_initialize(data)`.
            Override `pre_set_validate_inputs` if you need custom ordering.

        Examples:
            Basic Derived Field Initialization:
                ```python
                class User(Typed):
                    first_name: str
                    last_name: str
                    full_name: Optional[str] = None  # Will be computed

                    @classmethod
                    def pre_initialize(cls, data: Dict) -> NoReturn:
                        # Compute full_name from first_name and last_name
                        if 'first_name' in data and 'last_name' in data:
                            data['full_name'] = f"{data['first_name']} {data['last_name']}"

                user = User(first_name="John", last_name="Doe")
                assert user.full_name == "John Doe"
                ```

            Multiple Derived Fields:
                ```python
                from datetime import datetime

                class Order(Typed):
                    subtotal: float
                    tax_rate: float = 0.1
                    total: Optional[float] = None
                    order_date: Optional[str] = None

                    @classmethod
                    def pre_initialize(cls, data: Dict) -> NoReturn:
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

        Inheritance Example:
            ```python
            class Parent(Typed):
                name: str
                parent_computed: Optional[str] = None

                @classmethod
                def pre_initialize(cls, data: Dict) -> NoReturn:
                    if 'name' in data:
                        data['parent_computed'] = f"Parent: {data['name']}"

            class Child(Parent):
                age: int
                child_computed: Optional[str] = None

                @classmethod
                def pre_initialize(cls, data: Dict) -> NoReturn:
                    # Parent's hook is called automatically before this
                    if 'name' in data and 'age' in data:
                        data['child_computed'] = f"Child: {data['name']}, {data['age']}"

            # Both hooks run automatically in order
            model = Child(name="john", age=30)
            assert model.parent_computed == "Parent: john"  # From parent
            assert model.child_computed == "Child: john, 30"  # From child
            ```

        Three-Level Inheritance Example:
            ```python
            class Level1(Typed):
                field1: str
                level1_data: Optional[str] = None

                @classmethod
                def pre_initialize(cls, data: Dict) -> NoReturn:
                    if 'field1' in data:
                        data['level1_data'] = f"L1: {data['field1']}"

            class Level2(Level1):
                field2: str
                level2_data: Optional[str] = None

                @classmethod
                def pre_initialize(cls, data: Dict) -> NoReturn:
                    if 'field2' in data:
                        data['level2_data'] = f"L2: {data['field2']}"

            class Level3(Level2):
                field3: str
                level3_data: Optional[str] = None

                @classmethod
                def pre_initialize(cls, data: Dict) -> NoReturn:
                    if 'field3' in data:
                        data['level3_data'] = f"L3: {data['field3']}"

            # All three hooks run in order: Level1 -> Level2 -> Level3
            model = Level3(field1="a", field2="b", field3="c")
            assert model.level1_data == "L1: a"
            assert model.level2_data == "L2: b"
            assert model.level3_data == "L3: c"
            ```

        Working with Nested Typed Objects:
            Nested `Typed` fields are **automatically converted from dicts to objects** before
            `pre_initialize` is called. This means you can directly access nested objects and
            their computed fields without manual conversion.

            ```python
            class Address(Typed):
                street: str
                city: str
                full_address: Optional[str] = None

                @classmethod
                def pre_initialize(cls, data: Dict) -> NoReturn:
                    if 'street' in data and 'city' in data:
                        data['full_address'] = f"{data['street']}, {data['city']}"

            class Person(Typed):
                name: str
                address: Address
                summary: Optional[str] = None

                @classmethod
                def pre_initialize(cls, data: Dict) -> NoReturn:
                    # address is already an Address object (not a dict!)
                    if 'address' in data:
                        addr = data['address']
                        # Can access computed fields directly
                        data['summary'] = f"{data['name']} from {addr.full_address}"

            # Pass nested data as dict - automatic conversion happens
            person = Person(
                name="John",
                address={"street": "123 Main St", "city": "NYC"}
            )
            assert person.summary == "John from 123 Main St, NYC"
            ```

            This works for:
            - Direct fields: `address: Address`
            - Optional fields: `address: Optional[Address]`
            - Lists: `addresses: List[Address]`
            - Dicts: `locations: Dict[str, Address]`

        See Also:
            - `pre_validate()`: For validation and normalization after initialization
            - `post_initialize()`: For post-validation initialization
            - `pre_set_validate_inputs()`: To customize the execution order
        """
        pass

    @classmethod
    def pre_validate(cls, data: Any) -> NoReturn:
        """
        Pre-validation hook for validating and normalizing input data.

        This classmethod is called after pre_initialize and before Pydantic validation.
        It's designed for validating input data and normalizing field values.

        **Execution Order:**
            1. `_set_default_values()` - Apply default values for missing fields
            2. `pre_initialize()` - Initialize derived fields
            3. `pre_validate()` - Validate and normalize input data (this method)
            4. Pydantic field validation - Type conversion and constraint validation
            5. `post_initialize()` - Post-validation initialization
            6. `post_validate()` - Post-validation validation

        **Key Features:**
            - **Pre-validation Hook**: Called before Pydantic's field validation
            - **Mutable Data**: Can modify the input dictionary directly
            - **Early Validation**: Allows custom validation logic before type conversion
            - **Data Normalization**: Can normalize and transform field values
            - **Error Handling**: Can raise custom validation errors with detailed messages
            - **Automatic Inheritance**: Parent class hooks are called automatically

        Args:
            data (Dict): The input data dictionary passed to the model constructor or
                `model_validate()`. This dictionary is mutable and can be modified in-place.
                Keys represent field names and values represent the raw input values (with
                defaults and pre_initialize results applied).

        Returns:
            NoReturn: This method should not return anything. All modifications should be
                made to the `data` dictionary in-place.

        Raises:
            ValueError: Should raise ValueError (or subclasses) for validation failures.
                The error message will be wrapped by Typed's enhanced error handling.
            Any other exception: Will be caught and wrapped by Typed's error handling system.

        Note:
            Parent class `pre_validate` methods are called automatically in MRO order
            (base to derived), so subclasses don't need to call `super().pre_validate(data)`.
            Override `pre_set_validate_inputs` if you need custom ordering.

        Examples:
            Basic Input Validation:
                ```python
                class User(Typed):
                    name: str
                    email: str
                    age: int

                    @classmethod
                    def pre_validate(cls, data: Dict) -> NoReturn:
                        # Normalize email to lowercase
                        if 'email' in data:
                            data['email'] = data['email'].lower()

                        # Validate age range
                        if 'age' in data and isinstance(data['age'], (int, str)):
                            age = int(data['age']) if isinstance(data['age'], str) else data['age']
                            if age < 0 or age > 150:
                                raise ValueError(f"Age must be between 0 and 150, got {age}")

                # Usage - email gets normalized, age gets validated
                user = User(name="John", email="JOHN@EXAMPLE.COM", age=30)
                assert user.email == "john@example.com"

                # Invalid age raises error before model creation
                try:
                    User(name="John", email="john@example.com", age=200)
                except ValueError as e:
                    print(e)  # "Age must be between 0 and 150, got 200"
                ```

            Data Enrichment and Computed Fields:
                ```python
                class Product(Typed):
                    name: str
                    price: float
                    tax_rate: float = 0.1
                    total_price: Optional[float] = None  # Will be computed

                    @classmethod
                    def pre_validate(cls, data: Dict) -> NoReturn:
                        # Compute total price if not provided
                        if 'total_price' not in data and 'price' in data:
                            price = float(data['price'])
                            tax_rate = float(data.get('tax_rate', 0.1))
                            data['total_price'] = price * (1 + tax_rate)

                        # Normalize product name
                        if 'name' in data:
                            data['name'] = data['name'].strip().title()

                # Usage - total_price gets computed automatically
                product = Product(name="  laptop  ", price=1000)
                assert product.name == "Laptop"
                assert product.total_price == 1100.0  # 1000 * 1.1
                ```

            Complex Validation with Multiple Fields:
                ```python
                class DateRange(Typed):
                    start_date: str
                    end_date: str
                    duration_days: Optional[int] = None

                    @classmethod
                    def pre_validate(cls, data: Dict) -> NoReturn:
                        from datetime import datetime

                        # Parse and pre_validate dates
                        if 'start_date' in data and 'end_date' in data:
                            try:
                                start = datetime.fromisoformat(data['start_date'])
                                end = datetime.fromisoformat(data['end_date'])
                            except ValueError as e:
                                raise ValueError(f"Invalid date format: {e}")

                            # Validate date order
                            if start >= end:
                                raise ValueError("start_date must be before end_date")

                            # Compute duration if not provided
                            if 'duration_days' not in data:
                                data['duration_days'] = (end - start).days

                # Usage - dates get validated and duration computed
                date_range = DateRange(
                    start_date="2024-01-01",
                    end_date="2024-01-10"
                )
                assert date_range.duration_days == 9
                ```

            Conditional Field Processing:
                ```python
                class APIRequest(Typed):
                    method: str
                    url: str
                    headers: Optional[Dict[str, str]] = None
                    body: Optional[str] = None

                    @classmethod
                    def pre_validate(cls, data: Dict) -> NoReturn:
                        # Normalize HTTP method
                        if 'method' in data:
                            data['method'] = data['method'].upper()

                        # Add default headers if not provided
                        if 'headers' not in data:
                            data['headers'] = {}

                        # For POST/PUT requests, ensure Content-Type is set
                        method = data.get('method', '').upper()
                        if method in ['POST', 'PUT', 'PATCH'] and 'body' in data:
                            headers = data['headers']
                            if 'Content-Type' not in headers:
                                headers['Content-Type'] = 'application/json'

                        # Validate URL format
                        url = data.get('url', '')
                        if url and not (url.startswith('http://') or url.startswith('https://')):
                            raise ValueError(f"URL must start with http:// or https://, got: {url}")

                # Usage - method normalized, headers added, URL validated
                request = APIRequest(
                    method="post",
                    url="https://api.example.com/users",
                    body='{"name": "John"}'
                )
                assert request.method == "POST"
                assert request.headers["Content-Type"] == "application/json"
                ```

        Advanced Patterns:
            Validation with External Dependencies:
                ```python
                class UserAccount(Typed):
                    username: str
                    email: str
                    role: str = "user"

                    @classmethod
                    def pre_validate(cls, data: Dict) -> NoReturn:
                        # Validate username format
                        username = data.get('username', '')
                        if username and not username.isalnum():
                            raise ValueError("Username must be alphanumeric")

                        # Validate email format (basic check)
                        email = data.get('email', '')
                        if email and '@' not in email:
                            raise ValueError("Invalid email format")

                        # Validate role against allowed values
                        role = data.get('role', 'user')
                        allowed_roles = ['user', 'admin', 'moderator']
                        if role not in allowed_roles:
                            raise ValueError(f"Role must be one of {allowed_roles}, got: {role}")
                ```

        Integration with Registry and AutoEnum:
            ```python
            from morphic.autoenum import AutoEnum, auto
            from morphic.registry import Registry

            class Status(AutoEnum):
                ACTIVE = auto()
                INACTIVE = auto()
                PENDING = auto()

            class Task(Typed, Registry):
                title: str
                status: Status = Status.PENDING
                priority: int = 1

                @classmethod
                def pre_validate(cls, data: Dict) -> NoReturn:
                    # Normalize title
                    if 'title' in data:
                        data['title'] = data['title'].strip()
                        if not data['title']:
                            raise ValueError("Title cannot be empty")

                    # Clamp priority to valid range
                    if 'priority' in data:
                        priority = int(data['priority'])
                        data['priority'] = max(1, min(10, priority))  # Clamp to 1-10

                    # Auto-assign status based on priority
                    if 'status' not in data:
                        priority = int(data.get('priority', 1))
                        if priority >= 8:
                            data['status'] = Status.ACTIVE
                        else:
                            data['status'] = Status.PENDING

            # Usage with Registry factory
            task = Task.of(title="  Important Task  ", priority=15)
            assert task.title == "Important Task"
            assert task.priority == 10  # Clamped from 15
            assert task.status == Status.ACTIVE  # Auto-assigned
            ```

        Error Handling Best Practices:
            - Raise descriptive ValueError messages with context about what failed
            - Include the problematic field name and value in error messages
            - Use early returns or guard clauses for optional field validation
            - Validate field dependencies and relationships
            - Consider using helper methods for complex validation logic

        Performance Considerations:
            - This method is called for every model instantiation
            - Avoid expensive operations like network calls or file I/O
            - Cache validation results or patterns when possible
            - Use lazy evaluation for optional validations

        Thread Safety:
            - This method operates on the input data dictionary, not the class
            - Avoid modifying class-level attributes or shared state
            - Each validation call receives its own data dictionary copy

        See Also:
            - `pre_initialize()`: For setting up derived fields before validation
            - `post_validate()`: For post-validation validation
            - `pre_set_validate_inputs()`: To customize the execution order
            - `@field_validator`: Field-level validation for specific fields
        """
        pass

    @model_validator(mode="after")
    def _post_set_validate_inputs(self) -> T:
        self.post_set_validate_inputs()
        return self

    def post_set_validate_inputs(self) -> NoReturn:
        ## Call post_initialize for each class in MRO (base to derived order)
        ## Only call methods that are defined directly on each class to avoid duplicates
        ## Get the unbound function to ensure proper context
        for base_cls in reversed(self.__class__.__mro__[:-1]):  # Exclude object
            if "post_initialize" in base_cls.__dict__ and base_cls is not BaseModel:
                # Get the unbound function and call with self
                base_cls.__dict__["post_initialize"](self)

        ## Call post_validate for each class in MRO (base to derived order)
        ## Only call methods that are defined directly on each class to avoid duplicates
        ## Get the unbound function to ensure proper context
        for base_cls in reversed(self.__class__.__mro__[:-1]):  # Exclude object
            if "post_validate" in base_cls.__dict__ and base_cls is not BaseModel:
                # Get the unbound function and call with self
                base_cls.__dict__["post_validate"](self)

    def post_initialize(self) -> NoReturn:
        """
        Post-initialization hook for side effects after validation.

        This instance method is called after Pydantic validation is complete and before
        post_validate. It's designed for performing side effects that don't modify the
        instance (e.g., logging, external system integration).

        **Execution Order:**
            1. `_set_default_values()` - Apply default values for missing fields
            2. `pre_initialize()` - Initialize derived fields
            3. `pre_validate()` - Validate and normalize input data
            4. Pydantic field validation - Type conversion and constraint validation
            5. `post_initialize()` - Post-validation initialization (this method)
            6. `post_validate()` - Post-validation validation

        **Key Features:**
            - **Post-Validation Hook**: Called after all field validation and type conversion
            - **Instance Access**: Can access validated field values (read-only)
            - **Side Effects**: Perfect for logging, external system integration, or notifications
            - **Error Handling**: Can handle initialization errors gracefully
            - **Frozen Instance**: Cannot modify instance attributes (instance is frozen)
            - **Automatic Inheritance**: Parent class hooks are called automatically

        **Differences from pre_initialize:**
            - **Timing**: `pre_initialize()` runs before validation, `post_initialize()` runs after
            - **Data Access**: `pre_initialize()` works on raw input dict, `post_initialize()` works on validated instance
            - **Purpose**: `pre_initialize()` for setting derived fields, `post_initialize()` for side effects
            - **Mutability**: `pre_initialize()` can modify data dict, `post_initialize()` cannot modify frozen instance

        Args:
            None: This method takes no parameters. Access validated fields via `self`.

        Returns:
            NoReturn: This method should not return anything. Since the instance is frozen,
                this method is primarily for side effects rather than modifying attributes.

        Raises:
            Any exception: Exceptions raised during initialization will be caught and wrapped
                by Typed's error handling system, similar to validation errors.

        Note:
            Parent class `post_initialize` methods are called automatically in MRO order
            (base to derived), so subclasses don't need to call `super().post_initialize()`.
            Override `post_set_validate_inputs` if you need custom ordering.

        Examples:
            Side Effects and Logging:
                ```python
                class User(Typed):
                    name: str
                    email: str
                    display_name: Optional[str] = None
                    email_domain: Optional[str] = None

                    @classmethod
                    def pre_validate(cls, data: dict) -> None:
                        # Set computed fields during validation
                        if 'name' in data:
                            data['display_name'] = data['name'].title()
                        if 'email' in data:
                            data['email_domain'] = data['email'].split("@")[1]

                    def post_initialize(self) -> None:
                        # Perform side effects after validation
                        print(f"User created: {self.display_name} ({self.email_domain})")
                        # Could also integrate with external systems, logging, etc.

                user = User(name="john doe", email="john@example.com")
                assert user.display_name == "John Doe"
                assert user.email_domain == "example.com"
                ```

            External System Integration:
                ```python
                from datetime import datetime

                class Product(Typed):
                    name: str
                    price: float
                    total_with_tax: Optional[float] = None
                    metadata: Optional[dict] = None

                    @classmethod
                    def pre_validate(cls, data: dict) -> None:
                        # Compute derived values during validation
                        if 'price' in data:
                            data['total_with_tax'] = data['price'] * 1.1
                            data['metadata'] = {
                                "created_at": datetime.now().isoformat(),
                                "price_category": "expensive" if data['price'] > 100 else "affordable"
                            }

                    def post_initialize(self) -> None:
                        # Integrate with external systems after validation
                        # e.g., send to analytics, update cache, etc.
                        print(f"Product {self.name} registered in system")

                product = Product(name="Laptop", price=999.99)
                assert product.total_with_tax == 1099.989
                assert product.metadata["price_category"] == "expensive"
                ```

            Conditional Side Effects:
                ```python
                class Task(Typed):
                    title: str
                    priority: int = 1
                    processing_time: Optional[int] = None
                    error_message: Optional[str] = None

                    @classmethod
                    def pre_validate(cls, data: dict) -> None:
                        # Set processing time and pre_validate during validation
                        if 'priority' in data:
                            data['processing_time'] = data['priority'] * 100
                            if data['priority'] > 10:
                                data['error_message'] = "Priority too high"

                    def post_initialize(self) -> None:
                        # Perform conditional side effects
                        if self.priority > 5:
                            print(f"High priority task created: {self.title}")
                        if self.error_message:
                            print(f"Warning: {self.error_message}")

                task = Task(title="Important Task", priority=5)
                assert task.processing_time == 500
                assert task.error_message is None
                ```

            External Dependencies:
                ```python
                class CacheableModel(Typed):
                    id: str
                    data: str
                    cache_key: Optional[str] = None
                    hash_value: Optional[int] = None

                    @classmethod
                    def pre_validate(cls, data: dict) -> None:
                        # Generate cache key during validation
                        if 'id' in data and 'data' in data:
                            data['cache_key'] = f"cache_{data['id']}_{hash(data['data'])}"
                            data['hash_value'] = hash(data['data'])

                    def post_initialize(self) -> None:
                        # Interact with external systems after validation
                        # e.g., register with cache service, send to analytics, etc.
                        print(f"Model {self.id} registered with cache service")

                model = CacheableModel(id="user123", data="important data")
                assert model.cache_key.startswith("cache_user123_")
                assert model.hash_value is not None
                ```

            Error Handling:
                ```python
                class RobustModel(Typed):
                    value: int
                    processed_value: Optional[int] = None
                    error: Optional[str] = None

                    @classmethod
                    def pre_validate(cls, data: dict) -> None:
                        # Handle processing during validation
                        if 'value' in data:
                            try:
                                if data['value'] < 0:
                                    raise ValueError("Value cannot be negative")
                                data['processed_value'] = data['value'] * 2
                            except Exception as e:
                                data['error'] = str(e)

                    def post_initialize(self) -> None:
                        # Handle side effects after validation
                        if self.error:
                            print(f"Error during processing: {self.error}")
                        else:
                            print(f"Successfully processed value: {self.processed_value}")

                # Successful initialization
                model1 = RobustModel(value=10)
                assert model1.processed_value == 20
                assert model1.error is None

                # Initialization with error
                model2 = RobustModel(value=-5)
                assert model2.processed_value is None
                assert model2.error == "Value cannot be negative"
                ```

            Nested Object Side Effects:
                ```python
                class Address(Typed):
                    street: str
                    city: str
                    full_address: Optional[str] = None

                    @classmethod
                    def pre_validate(cls, data: dict) -> None:
                        if 'street' in data and 'city' in data:
                            data['full_address'] = f"{data['street']}, {data['city']}"

                    def post_initialize(self) -> None:
                        print(f"Address created: {self.full_address}")

                class Person(Typed):
                    name: str
                    address: Address
                    contact_info: Optional[str] = None

                    @classmethod
                    def pre_validate(cls, data: dict) -> None:
                        if 'name' in data and 'address' in data:
                            # Create address to get full_address
                            address = Address(**data['address'])
                            data['contact_info'] = f"{data['name']} at {address.full_address}"

                    def post_initialize(self) -> None:
                        print(f"Person created: {self.contact_info}")

                person = Person(
                    name="John Doe",
                    address={"street": "123 Main St", "city": "Anytown"}
                )
                assert person.address.full_address == "123 Main St, Anytown"
                assert person.contact_info == "John Doe at 123 Main St, Anytown"
                ```

        Advanced Patterns:
            Inheritance and Super Calls:
                ```python
                class BaseModel(Typed):
                    name: str
                    base_info: Optional[str] = None

                    @classmethod
                    def pre_validate(cls, data: dict) -> None:
                        if 'name' in data:
                            data['base_info'] = f"Base: {data['name']}"

                    def post_initialize(self) -> None:
                        print(f"Base model initialized: {self.base_info}")

                class ExtendedModel(BaseModel):
                    age: int
                    extended_info: Optional[str] = None

                    @classmethod
                    def pre_validate(cls, data: dict) -> None:
                        # Call parent validation
                        super().pre_validate(data)
                        # Add extended validation
                        if 'name' in data and 'age' in data:
                            data['extended_info'] = f"Extended: {data['name']} is {data['age']} years old"

                    def post_initialize(self) -> None:
                        # Call parent initialization
                        super().post_initialize()
                        # Add extended initialization
                        print(f"Extended model initialized: {self.extended_info}")

                model = ExtendedModel(name="John", age=30)
                assert model.base_info == "Base: John"
                assert model.extended_info == "Extended: John is 30 years old"
                ```

            Factory Method Integration:
                ```python
                class FactoryModel(Typed):
                    name: str
                    factory_info: Optional[str] = None

                    @classmethod
                    def pre_validate(cls, data: dict) -> None:
                        if 'name' in data:
                            data['factory_info'] = f"Created via factory: {data['name']}"

                    def post_initialize(self) -> None:
                        print(f"Factory model initialized: {self.factory_info}")

                # Works with of() factory method
                model = FactoryModel.of(name="FactoryTest")
                assert model.factory_info == "Created via factory: FactoryTest"
                ```

            Inheritance Example:
                ```python
                class Parent(Typed):
                    name: str

                    def post_initialize(self) -> None:
                        print(f"Parent initialized: {self.name}")

                class Child(Parent):
                    age: int

                    def post_initialize(self) -> None:
                        # Parent's hook is called automatically before this
                        print(f"Child initialized: {self.name}, age {self.age}")

                # Both hooks run automatically in order
                model = Child(name="john", age=30)
                # Output:
                # Parent initialized: john
                # Child initialized: john, age 30
                ```

            Multi-Level Inheritance Example:
                ```python
                class Level1(Typed):
                    field1: str

                    def post_initialize(self) -> None:
                        print(f"Level1: {self.field1}")

                class Level2(Level1):
                    field2: str

                    def post_initialize(self) -> None:
                        print(f"Level2: {self.field2}")

                class Level3(Level2):
                    field3: str

                    def post_initialize(self) -> None:
                        print(f"Level3: {self.field3}")

                # All three hooks run in order: Level1 -> Level2 -> Level3
                model = Level3(field1="a", field2="b", field3="c")
                # Output:
                # Level1: a
                # Level2: b
                # Level3: c
                ```

        Performance Considerations:
            - This method is called for every model instantiation
            - Avoid expensive operations like network calls or file I/O
            - Cache expensive computations when possible
            - Use lazy evaluation for optional initializations

        Thread Safety:
            - This method operates on the model instance, not shared state
            - Avoid modifying class-level attributes
            - Each initialization call receives its own model instance

        Best Practices:
            - Use for side effects like logging, external system integration, or notifications
            - Handle errors gracefully with try-catch blocks
            - Keep initialization logic simple and fast
            - Document any side effects or external dependencies
            - Use `pre_validate()` for input transformation and computed fields instead

        Working with Nested Typed Objects:
            Like in `pre_initialize`, nested `Typed` objects are already instantiated (not dicts).
            By the time `post_initialize` runs, all nested objects are fully validated and their
            hooks have completed.

            ```python
            class Item(Typed):
                name: str
                price: float

                def post_initialize(self) -> NoReturn:
                    print(f"Item {self.name} created")

            class Order(Typed):
                items: List[Item]
                total: float

                def post_initialize(self) -> NoReturn:
                    # All items are fully validated Item instances
                    for item in self.items:
                        assert isinstance(item, Item)
                        print(f"  - {item.name}: ${item.price}")

            # Output when creating:
            # Item Widget created
            # Item Gadget created
            #   - Widget: $10.0
            #   - Gadget: $20.0
            order = Order(
                items=[{"name": "Widget", "price": 10.0}, {"name": "Gadget", "price": 20.0}],
                total=30.0
            )
            ```

            Note: Nested objects are converted before any hooks run, so they're available
            as objects in both pre-hooks and post-hooks.

        See Also:
            - `pre_initialize()`: For setting up derived fields before validation
            - `post_validate()`: For post-validation validation
            - `post_set_validate_inputs()`: To customize the execution order
            - `@model_validator(mode="after")`: Pydantic's post-creation validation hook
        """
        pass

    def post_validate(self) -> NoReturn:
        """
        Post-validation hook for validating the model instance after initialization.

        This instance method is called after post_initialize. It's designed for
        performing validation on the fully constructed and initialized model instance.

        **Execution Order:**
            1. `_set_default_values()` - Apply default values for missing fields
            2. `pre_initialize()` - Initialize derived fields
            3. `pre_validate()` - Validate and normalize input data
            4. Pydantic field validation - Type conversion and constraint validation
            5. `post_initialize()` - Post-validation initialization
            6. `post_validate()` - Post-validation validation (this method)

        **Key Features:**
            - **Post-Validation Hook**: Called after initialization is complete
            - **Instance Access**: Can access all validated and initialized fields (read-only)
            - **Cross-Field Validation**: Perfect for validating relationships between fields
            - **Frozen Instance**: Cannot modify instance attributes (instance is frozen)
            - **Automatic Inheritance**: Parent class hooks are called automatically

        Args:
            None: This method takes no parameters. Access validated fields via `self`.

        Returns:
            NoReturn: This method should not return anything. It's primarily for
                validation that raises exceptions if the instance is invalid.

        Raises:
            ValueError: Should raise ValueError (or subclasses) for validation failures.
            Any other exception: Will be caught and wrapped by Typed's error handling system.

        Note:
            Parent class `post_validate` methods are called automatically in MRO order
            (base to derived), so subclasses don't need to call `super().post_validate()`.
            Override `post_set_validate_inputs` if you need custom ordering.

        Examples:
            Cross-Field Validation:
                ```python
                class DateRange(Typed):
                    start_date: str
                    end_date: str

                    def post_validate(self) -> NoReturn:
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

            Business Logic Validation:
                ```python
                class Order(Typed):
                    items: List[str]
                    subtotal: float
                    discount: float = 0.0
                    total: float

                    def post_validate(self) -> NoReturn:
                        # Validate discount
                        if self.discount < 0 or self.discount > self.subtotal:
                            raise ValueError("Invalid discount amount")

                        # Validate total calculation
                        expected_total = self.subtotal - self.discount
                        if abs(self.total - expected_total) > 0.01:
                            raise ValueError(f"Total mismatch: expected {expected_total}, got {self.total}")

                        # Validate items
                        if not self.items:
                            raise ValueError("Order must have at least one item")
                ```

        See Also:
            - `pre_validate()`: For input validation before model creation
            - `post_initialize()`: For side effects after validation
            - `post_set_validate_inputs()`: To customize the execution order
        """
        pass


class MutableTyped(Typed):
    """
    A mutable variant of Typed that allows field modification after instantiation.

    Unlike the base Typed class which is frozen (immutable), MutableTyped instances
    can have their fields modified after creation. This is useful when you need
    to update model instances during runtime, especially in tight loops or with
    frequent modifications where validation overhead should be minimized.

    Key Features:
    - **Mutable**: Fields can be modified after instantiation
    - **Performance Optimized**: No validation on assignment by default for speed
    - **Type Safe at Creation**: Full validation during instantiation
    - **Pydantic Compatible**: Built on Pydantic's validation system
    - **Optional Validation**: Can enable assignment validation if needed

    Configuration:
    - `frozen=False`: Allows field modification
    - `validate_assignment=False`: Disabled by default for performance (can be enabled)
    - `validate_private_assignment=False`: Private attrs not validated (inherited default)

    Basic Usage:
        ```python
        class User(MutableTyped):
            name: str
            age: int
            active: bool = True

        user = User(name="John", age=30)
        user.name = "Jane"  # This works with MutableTyped
        user.age = 25       # This also works
        print(user.name)    # "Jane"

        # Compare with regular Typed (frozen):
        class FrozenUser(Typed):
            name: str
            age: int

        frozen_user = FrozenUser(name="John", age=30)
        frozen_user.name = "Jane"  # This would raise ValidationError
        ```

    No Validation on Assignment (Default):
        By default, assignments are NOT validated for performance:

        ```python
        user = User(name="John", age=30)
        user.age = "not_a_number"  # Allowed! No validation on assignment
        user.name = 123  # Also allowed for performance

        # This is intentional for high-performance scenarios like tight loops
        for i in range(1000000):
            user.age = i  # Fast - no validation overhead
        ```

    Enabling Validation on Assignment (Optional):
        If you need validation on assignment, enable it explicitly:

        ```python
        from pydantic import ConfigDict

        class ValidatedUser(MutableTyped):
            model_config = ConfigDict(
                frozen=False,
                validate_assignment=True,  # Enable validation
            )

            name: str
            age: int

        user = ValidatedUser(name="John", age=30)
        try:
            user.age = "not_a_number"  # Now raises ValidationError
        except ValidationError:
            print("Validation enforced!")
        ```

    Hooks and Derived Fields:
        **Important**: Use pre-hooks for derived fields, not post-hooks.
        Post-hooks should only perform side effects (logging, notifications, etc.).

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
                # ❌ WRONG: Don't modify instance here
                # self.score = self.age * 10  # Would cause issues

        user = UserWithScore(name="John", age=30)
        print(user.score)  # 300 (set by pre_initialize)

        # Modifying age triggers validation including pre_initialize again
        user.age = 25
        print(user.score)  # 250 (recomputed by pre_initialize!)
        ```

    Performance Considerations:
        By default, MutableTyped prioritizes performance over validation:

        ```python
        class Counter(MutableTyped):
            count: int = 0
            label: str = "counter"

        counter = Counter()

        # Fast - no validation overhead
        for i in range(1000000):
            counter.count = i  # Direct assignment, no validation

        # Validation only happens at creation time
        counter2 = Counter(count="invalid")  # Raises ValidationError
        ```

        When to Enable validate_assignment=True:
        - When data integrity is critical and performance is not
        - When assignments come from untrusted sources
        - When you need to catch type errors during development
        - When assignment frequency is low

        When to Keep validate_assignment=False (default):
        - High-performance scenarios (tight loops, frequent updates)
        - Internal state management where types are controlled
        - When you trust the assignment sources
        - When you want minimal overhead

    See Also:
        - `Typed`: The base frozen (immutable) class
        - `pre_validate()`: For function parameter validation
        - `pre_initialize()`: For setting up derived fields
        - `post_initialize()`: For side effects after creation
        - Pydantic's `ConfigDict`: For advanced configuration options
    """

    model_config = ConfigDict(
        ## Ref: https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.frozen
        frozen=False,
        ## Ref: https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.validate_assignment
        ## Disabled by default for performance in tight loops and frequent modifications
        validate_assignment=False,
        ## Custom setting for private attribute validation
        validate_private_assignment=False,
    )


def validate(*args, **kwargs):
    """
    Function decorator for automatic parameter validation using Pydantic.

    This decorator validates function parameters against their type annotations using Pydantic's
    validation system. It provides automatic type conversion, validation, and helpful error
    messages for function arguments, making it easy to add runtime type checking to any function.

    Features:
        - **Automatic Type Conversion**: Converts compatible types (e.g., string to int)
        - **Type Validation**: Validates all parameters against their type annotations
        - **Default Value Validation**: Validates default parameter values at call time
        - **Detailed Error Messages**: Provides clear validation error messages
        - **Arbitrary Types**: Supports custom types and Typed models as parameters
        - **Return Value Validation**: Optional validation of return values

    Configuration:
        The decorator is pre-configured with the following Pydantic settings:

        - `populate_by_name=True`: Allows both original names and aliases for fields
        - `arbitrary_types_allowed=True`: Supports custom types beyond built-in types
        - `validate_default=True`: Validates default parameter values when used

    Basic Usage:
        ```python
        from morphic.typed import validate

        @validate
        def create_user(name: str, age: int, active: bool = True) -> str:
            return f"User {name}, age {age}, active: {active}"

        # Automatic type conversion
        result = create_user("John", "30", "false")
        print(result)  # "User John, age 30, active: False"

        # Validation errors for invalid types
        try:
            create_user("John", "invalid_age")
        except ValidationError as e:
            print(e)  # Clear error message about invalid integer
        ```

    Advanced Usage:
        ```python
        from typing import List, Optional
        from morphic.typed import validate, Typed

        class User(Typed):
            name: str
            age: int

        @validate
        def process_users(
            users: List[User],
            active_only: bool = True,
            max_age: Optional[int] = None
        ) -> List[str]:
            # users automatically converted from list of dicts to list of User objects
            filtered = [u for u in users if not active_only or u.age <= (max_age or 100)]
            return [u.name for u in filtered]

        # Dict to Typed conversion happens automatically
        result = process_users([
            {"name": "Alice", "age": "25"},  # Dict converted to User
            {"name": "Bob", "age": "30"},
        ], max_age="35")  # String converted to int
        print(result)  # ["Alice", "Bob"]
        ```

    Return Value Validation:
        ```python
        @validate(validate_return=True)
        def get_user_name(user_id: int) -> str:
            if user_id > 0:
                return f"user_{user_id}"
            else:
                return None  # This will raise ValidationError

        name = get_user_name(5)  # "user_5"

        try:
            get_user_name(-1)  # ValidationError: return value not a string
        except ValidationError as e:
            print(e)
        ```

    Type Conversion Examples:
        The decorator handles many common type conversions automatically:

        ```python
        @validate
        def example_conversions(
            number: int,           # "123" -> 123
            decimal: float,        # "3.14" -> 3.14
            flag: bool,           # "true" -> True, "false" -> False
            items: List[int],     # ["1", "2", "3"] -> [1, 2, 3]
            mapping: Dict[str, int],  # {"a": "1"} -> {"a": 1}
            user: User,           # {"name": "John", "age": 30} -> User instance
        ):
            pass
        ```

    Error Handling:
        ```python
        @validate
        def divide(a: int, b: int) -> float:
            return a / b

        try:
            divide("10", "not_a_number")
        except ValidationError as e:
            print(e)
            # Output: Detailed error showing which parameter failed validation
            # and what the invalid input was
        ```

    Integration with Typed Models:
        ```python
        class Config(Typed):
            host: str = "localhost"
            port: int = 8080
            debug: bool = False

        @validate
        def start_server(config: Config) -> str:
            return f"Starting server on {config.host}:{config.port}"

        # Dict automatically converted to Config instance
        result = start_server({
            "host": "example.com",
            "port": "9000",  # String converted to int
            "debug": "true"  # String converted to bool
        })
        ```

    Args:
        validate_return (bool, optional): Whether to validate the return value against
            the function's return type annotation. Defaults to False.
        config (dict, optional): Additional Pydantic configuration options to override
            the default settings.

    Returns:
        Callable: The decorated function with automatic parameter validation.

    Raises:
        ValidationError: If parameter validation fails or if return value validation
            is enabled and the return value doesn't match the annotation.

    Note:
        This is a pre-configured version of Pydantic's `validate_call` decorator with
        sensible defaults for use with morphic types and patterns.

    See Also:
        - `pydantic.validate_call`: The underlying Pydantic decorator
        - `morphic.typed.Typed`: For creating validated data models
        - `morphic.autoenum.AutoEnum`: For creating validated enumerations
    """
    return functools.partial(
        validate_call,
        config=dict(
            ## Allow population of a field by it's original name and alias (if False, only alias is used)
            populate_by_name=True,
            ## Perform type checking of non-BaseModel types (if False, throws an error)
            arbitrary_types_allowed=True,
            ## Validate default values
            validate_default=True,
        ),
    )(*args, **kwargs)
