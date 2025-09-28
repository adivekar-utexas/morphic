"""Enhanced base configuration class with Pydantic-like functionality."""

import functools
import textwrap
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
)

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator, validate_call


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
                errors_str += "\n"
                errors_str += textwrap.indent(f"[Error#{error_i + 1}] ValidationError:\n{error_msg}", "  ")
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
        from morphic.registry import Registry

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

    @classmethod
    def _set_default_param_values(cls, params: Dict):
        assert isinstance(params, dict)
        ## Apply default values for fields not present in the input
        for field_name, field in cls.model_fields.items():
            if field_name not in params:
                if field.default is not None:
                    params[field_name] = field.default
                elif field.default_factory is not None:
                    params[field_name] = field.default_factory()

    @model_validator(mode="before")
    @classmethod
    def _validate_inputs(cls, data: Dict) -> Dict:
        cls._set_default_param_values(data)
        cls.validate_inputs(data)
        return data

    @classmethod
    def validate_inputs(cls, data: Dict) -> NoReturn:
        """
        Hook method for custom input validation and mutation before Pydantic model creation.

        This method is called during the Pydantic validation process (via `@model_validator(mode="before")`)
        and allows subclasses to perform custom validation and mutation of input data before the 
        Pydantic model is instantiated. Since it's called before model creation, the data dictionary
        can be freely modified, and these changes will be reflected in the final model instance.

        Key Features:
            - **Pre-validation Hook**: Called before Pydantic's field validation
            - **Mutable Data**: Can modify the input dictionary directly
            - **Early Validation**: Allows custom validation logic before type conversion
            - **Data Enrichment**: Can add computed fields or transform existing ones
            - **Error Handling**: Can raise custom validation errors with detailed messages

        Execution Order:
            1. `_set_default_param_values()` - Apply default values for missing fields
            2. `validate_inputs()` - Custom validation and mutation (this method)
            3. Pydantic field validation - Type conversion and constraint validation
            4. Pydantic model validators - Any `@model_validator(mode="after")` methods

        Args:
            data (Dict): The input data dictionary passed to the model constructor or
                `model_validate()`. This dictionary is mutable and can be modified in-place.
                Keys represent field names and values represent the raw input values.

        Returns:
            NoReturn: This method should not return anything. All modifications should be
                made to the `data` dictionary in-place.

        Raises:
            ValueError: Should raise ValueError (or subclasses) for validation failures.
                The error message will be wrapped by Typed's enhanced error handling.
            Any other exception: Will be caught and wrapped by Typed's error handling system.

        Examples:
            Basic Input Validation:
                ```python
                class User(Typed):
                    name: str
                    email: str
                    age: int

                    @classmethod
                    def validate_inputs(cls, data: Dict) -> NoReturn:
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
                    def validate_inputs(cls, data: Dict) -> NoReturn:
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
                    def validate_inputs(cls, data: Dict) -> NoReturn:
                        from datetime import datetime
                        
                        # Parse and validate dates
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
                    def validate_inputs(cls, data: Dict) -> NoReturn:
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
                    def validate_inputs(cls, data: Dict) -> NoReturn:
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
                def validate_inputs(cls, data: Dict) -> NoReturn:
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
            - `_set_default_param_values()`: Applies default values before validation
            - `@model_validator(mode="after")`: Pydantic post-creation validation
            - `@field_validator`: Field-level validation for specific fields
            - `model_validate()`: Entry point for dictionary-to-model conversion
        """
        pass


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
