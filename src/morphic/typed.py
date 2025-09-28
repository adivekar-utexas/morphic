"""Enhanced base configuration class with Pydantic-like functionality."""

import functools
import textwrap
from abc import ABC
from pprint import pformat
from typing import (
    Any,
    ClassVar,
    Dict,
    Optional,
    Set,
    Tuple,
    TypeVar,
)

from pydantic import BaseModel, ConfigDict, ValidationError, validate_call


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

        # Create and validate instances
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
                error_msg: str = textwrap.indent(error.get("msg", ""), "    ").strip()
                errors_str += f"\n[Error#{error_i + 1}] ValidationError in {error['loc']}: {error_msg}"
                if isinstance(error["input"], dict):
                    errors_str += (
                        f"\n[Error#{error_i + 1}] Input keys: {_Typed_pformat(error['input'].keys())}"
                    )
                    errors_str += f"\n[Error#{error_i + 1}] Input values: {_Typed_pformat(error['input'])}"
                else:
                    errors_str += f"\n[Error#{error_i + 1}] Input: {_Typed_pformat(error['input'])}"
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
    def of(cls, /, **data: Dict[str, Any]) -> T:
        """
        Factory method for creating instances with keyword arguments.

        This is a convenience factory method that provides an alternative way to create
        instances of Typed models. It's functionally equivalent to calling the constructor
        directly but offers a more fluent interface that can be useful in factory patterns
        and method chaining scenarios.

        Args:
            **kwargs (Any): Keyword arguments passed directly to the class constructor.
                These are the same field values that would be passed to `__init__`.

        Returns:
            T: A new instance of the Typed subclass with validated field values.

        Raises:
            ValueError: If validation fails, same as the constructor. See `__init__`
                documentation for details on validation behavior and error messages.

        Examples:
            ```python
            class User(Typed):
                name: str
                age: int
                active: bool = True

            # These are equivalent
            user1 = User(name="John", age=30)
            user2 = User.of(name="John", age=30)

            assert user1.model_dump() == user2.model_dump()

            # Useful in factory patterns
            def create_user_from_dict(data: dict) -> User:
                return User.of(**data)

            # Method chaining style
            users = [
                User.of(name="Alice", age=25),
                User.of(name="Bob", age=30),
                User.of(name="Carol", age=35),
            ]
            ```

        Integration with Registry:
            When used with morphic.Registry, this method provides consistency with the
            Registry factory pattern:

            ```python
            from morphic.registry import Registry
            from morphic.typed import Typed

            class DataModel(Registry, Typed):
                name: str

            class UserModel(DataModel):
                age: int

            # Both work consistently
            user1 = UserModel.of(name="John", age=30)        # Typed factory
            user2 = DataModel.of("UserModel", name="John", age=30)  # Registry factory
            ```

        Note:
            This method is purely a convenience wrapper around the constructor and
            provides no additional functionality beyond improved ergonomics.
        """
        return cls(**data)

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
