"""Registry pattern for automatic class registration and retrieval."""

from abc import ABC
from typing import Any, ClassVar, Dict, List, Optional, Set, Tuple, Type, Union


def _is_abstract(cls: Type) -> bool:
    """Check if a class is abstract."""
    return ABC in cls.__bases__


def _str_normalize(x: str, remove: Optional[Union[str, Tuple, List, Set]] = (" ", "-", "_")) -> str:
    """Normalize string by removing specified characters and converting to lowercase."""
    if remove is None:
        remove = set()
    if isinstance(remove, str):
        remove = set(remove)

    out = str(x)
    if remove:
        for rem in set(remove).intersection(set(out)):
            out = out.replace(rem, "")
    return out.lower()


def _as_list(item) -> List:
    """Convert item to list."""
    if isinstance(item, (list, tuple, set)):
        return list(item)
    return [item]


def _as_set(item) -> Set:
    """Convert item to set."""
    if isinstance(item, set):
        return item
    if isinstance(item, (list, tuple)):
        return set(item)
    return {item}


class Registry(ABC):
    """
    Inheritance-based class registration system with hierarchical factory pattern.

    Registry automatically registers classes through inheritance and provides sophisticated factory methods
    for instance creation. Classes automatically register themselves when they inherit from Registry subclasses,
    and the system provides hierarchical factory methods that respect class inheritance relationships.

    Features:
        - **Automatic Registration**: Classes auto-register when inheriting from Registry
        - **Hierarchical Factory Pattern**: Three-tier intelligent instantiation
        - **Scoped Lookups**: Each class can only instantiate its own subclasses
        - **Class Aliases**: Multiple names for the same class
        - **Custom Registry Keys**: Flexible key systems including tuples
        - **String Normalization**: Case-insensitive, flexible key matching
        - **Registry Inspection**: Query available classes and hierarchies

    Hierarchical Factory Pattern:
        The Registry provides three intelligent instantiation modes:

        1. **Direct Instantiation (Concrete Classes)**:
           Concrete classes can be instantiated directly without registry keys
           ```python
           dog = Dog.of()  # No key needed for concrete classes
           ```

        2. **Factory Method (Abstract Classes)**:
           Abstract classes require registry keys and search within their hierarchy
           ```python
           animal = Animal.of("Dog", name="Buddy")  # Key required for abstract classes
           ```

        3. **Hierarchical Scoping**:
           Classes can only instantiate their own subclasses, enforcing hierarchy
           ```python
           cat = Cat.of("TabbyCat")  # ✅ TabbyCat is subclass of Cat
           # dog = Cat.of("Dog")     # ❌ Dog is not subclass of Cat
           ```

    Basic Usage:
        ```python
        from morphic.registry import Registry
        from abc import ABC, abstractmethod

        # Base registry class
        class Animal(Registry, ABC):
            @abstractmethod
            def speak(self) -> str:
                pass

        # Classes automatically register when inheriting
        class Dog(Animal):
            aliases = ["canine", "pup"]  # Multiple aliases supported

            def __init__(self, name: str = "Buddy"):
                self.name = name

            def speak(self) -> str:
                return f"{self.name} says Woof!"

        class Cat(Animal):
            aliases = ["feline", "kitty"]

            def __init__(self, name: str = "Whiskers"):
                self.name = name

            def speak(self) -> str:
                return f"{self.name} says Meow!"

        # Hierarchical factory usage examples
        dog = Dog.of(name="Rex")                     # Direct concrete instantiation
        cat = Animal.of("Cat", name="Fluffy")        # Factory with class name
        feline = Animal.of("feline", name="Shadow")  # Using alias
        pup = Animal.of("pup", name="Buddy")         # Case-insensitive fuzzy matching

        # String normalization works automatically
        canine = Animal.of("CANINE", name="Max")     # Case insensitive
        dog2 = Animal.of("ca-nine", name="Rex")      # Handles dashes/spaces

        print(dog.speak())    # "Rex says Woof!"
        print(cat.speak())    # "Fluffy says Meow!"
        ```

    Advanced Features:
        ```python
        # Class aliases for flexible naming
        class DatabaseConnection(Registry):
            aliases = ["db", "database", "connection"]

        # Multiple ways to create the same object
        db1 = DatabaseConnection.of()                    # Direct concrete instantiation
        db2 = DatabaseConnection.of("db", host="remote") # Using alias
        db3 = DatabaseConnection.of("DATABASE")          # Case insensitive

        # Custom registry keys with _registry_keys method
        class HTTPSService(Registry):
            @classmethod
            def _registry_keys(cls):
                return [
                    ("protocol", "https"),          # Tuple key
                    ("service", "web"),             # Another tuple key
                    8443,                          # Numeric key
                    "secure_web"                   # String key
                ]

        # Create using different key types
        service1 = HTTPSService.of(("protocol", "https"))  # Tuple key
        service2 = HTTPSService.of(8443)                   # Numeric key
        service3 = HTTPSService.of("secure_web")           # String key

        # Registry inspection for discovery
        available_classes = DatabaseConnection.subclasses()      # Get all concrete subclasses
        class_by_key = DatabaseConnection.get_subclass("db")     # Get class by key
        all_keys = list(DatabaseConnection._registry.keys())     # All registered keys

        # Error handling with hierarchical scoping
        try:
            service = WrongHierarchy.of("SomeClass")  # KeyError with available options
        except KeyError as e:
            print(f"Available in hierarchy: {e}")
        ```

    Hierarchical Architecture:
        ```python
        class Service(Registry, ABC):
            pass

        class DataService(Service, ABC):
            pass

        class NotificationService(Service, ABC):
            pass

        class FileService(DataService):
            pass

        class EmailService(NotificationService):
            pass

        # Hierarchical scoping enforced
        file_svc = DataService.of("FileService")        # ✅ Works
        email_svc = NotificationService.of("EmailService") # ✅ Works
        any_svc = Service.of("EmailService")            # ✅ Works (common base)
        # email_svc = DataService.of("EmailService")    # ❌ Wrong hierarchy
        ```

    Configuration Options:
        Control registration behavior with class attributes:

        - `aliases`: List of alternative names for the class
        - `_allow_multiple_subclasses`: Allow multiple classes per key (default: False)
        - `_allow_subclass_override`: Allow overriding existing registrations (default: False)
        - `_dont_register`: Skip automatic registration (default: False)

        ```python
        class FlexibleService(Registry, ABC):
            _allow_multiple_subclasses = True
            _allow_subclass_override = True

        class SkippedService(Registry):
            _dont_register = True  # Won't register itself
        ```

    Registry Inspection:
        Query and explore the registry:

        ```python
        # Get all subclasses
        animal_types = Animal.subclasses()              # Concrete classes only
        all_animals = Animal.subclasses(keep_abstract=True) # Include abstract

        # Get specific class by key
        dog_class = Animal.get_subclass("Dog")          # Returns Dog class
        cat_class = Animal.get_subclass("feline")       # Using alias

        # Check what's available
        available_keys = list(Animal._registry.keys())
        ```

    Error Handling:
        The Registry provides clear error messages for common issues:

        - `TypeError`: Calling Registry.of() directly or abstract class without key
        - `KeyError`: Registry key not found in hierarchy
        - `TypeError`: Multiple subclasses registered to same key (when not allowed)

        ```python
        try:
            # Abstract class without key
            animal = Animal.of()
        except TypeError as e:
            print(f"Need registry key: {e}")

        try:
            # Key not in hierarchy
            dog = Cat.of("Dog")
        except KeyError as e:
            print(f"Wrong hierarchy: {e}")
        ```

    Performance Notes:
        - Key lookups are O(1) hash table operations
        - String normalization happens once during registration
        - Hierarchical filtering is optimized for inheritance chains
        - Each registry hierarchy maintains its own lookup table
        - Minimal memory overhead per registered class

    See Also:
        - `of()`: Hierarchical factory method for instance creation
        - `get_subclass()`: Get class by key without creating instance
        - `subclasses()`: Get all registered subclasses
        - `remove_subclass()`: Remove class from registry
    """

    _registry: ClassVar[Dict[Any, Dict[str, Type]]] = {}
    _registry_base_class: ClassVar[Optional[Type]] = None
    _allow_multiple_subclasses: ClassVar[bool] = False
    _allow_subclass_override: ClassVar[bool] = False
    _dont_register: ClassVar[bool] = False
    aliases: ClassVar[Tuple[str, ...]] = tuple()

    def __init_subclass__(cls, **kwargs):
        """Register any subclass with the base class."""
        super().__init_subclass__(**kwargs)

        if cls in Registry.__subclasses__():
            # Current class is a direct subclass of Registry (base class of hierarchy)
            cls._registry = {}
            cls._registry_base_class = cls
        else:
            # Current class is a subclass of a Registry-subclass
            if not _is_abstract(cls) and not cls._dont_register:
                cls._register_subclass()

    @classmethod
    def _register_subclass(cls):
        """Register this subclass in the registry."""
        keys_to_register = []

        # Add class name and aliases
        for key in [cls.__name__] + _as_list(cls.aliases) + _as_list(cls._registry_keys()):
            if key is None:
                continue
            elif isinstance(key, str):
                # Case-insensitive matching
                key = _str_normalize(key)
            elif isinstance(key, tuple):
                key = tuple(
                    _str_normalize(key_part) if isinstance(key_part, str) else key_part for key_part in key
                )
            keys_to_register.append(key)

        cls._add_to_registry(keys_to_register, cls)

    @classmethod
    def _add_to_registry(cls, keys_to_register: List[Any], subclass: Type):
        """Add subclass to registry under specified keys."""
        subclass_name = subclass.__name__

        for k in _as_set(keys_to_register):  # Drop duplicates
            if k not in cls._registry:
                cls._registry[k] = {subclass_name: subclass}
                continue

            # Key already exists in registry
            registered = cls._registry[k]
            registered_names = set(registered.keys())

            if subclass_name in registered_names and not cls._allow_subclass_override:
                raise KeyError(
                    f"A subclass with name '{subclass_name}' is already registered "
                    f"against key '{k}' for registry under '{cls._registry_base_class}'; "
                    f"overriding subclasses is not permitted."
                )
            elif subclass_name not in registered_names and not cls._allow_multiple_subclasses:
                if len(registered_names) == 0:
                    raise ValueError(f"Invalid state: key '{k}' is registered to an empty dict")
                if len(registered_names) > 1:
                    raise ValueError(
                        f"Invalid state: _allow_multiple_subclasses is False but multiple subclasses "
                        f"are registered against key {k}"
                    )
                existing_subclass = next(iter(registered_names))
                raise KeyError(
                    f"Key {k} is already registered to subclass {existing_subclass}; "
                    f"registering multiple subclasses to the same key is not permitted."
                )

            cls._registry[k] = {
                **registered,
                subclass_name: subclass,
            }

    @classmethod
    def get_subclass(
        cls,
        key: Any,
        raise_error: bool = True,
    ) -> Optional[Union[Type, List[Type]]]:
        """
        Get registered subclass(es) by key without creating instances.

        This method performs a global registry lookup (not hierarchical) to find all subclasses
        registered under the given key. Unlike the hierarchical `of()` method, this searches
        the entire registry without scoping restrictions.

        Args:
            key (Any): Key to look up subclass. Can be:
                - str: Class name or alias (case-insensitive, normalized)
                - tuple: Custom composite key from _registry_keys()
                - Any: Custom key type from _registry_keys()
            raise_error (bool): Whether to raise KeyError if key not found.
                Defaults to True.

        Returns:
            - **Type**: Single subclass if only one is registered under the key
            - **List[Type]**: List of subclasses if multiple are registered (when _allow_multiple_subclasses=True)
            - **None**: If key not found and raise_error=False

        Raises:
            KeyError: If key not found and raise_error=True

        Examples:
            ```python
            class Animal(Registry, ABC):
                pass

            class Dog(Animal):
                aliases = ["canine", "pup"]

            class Cat(Animal):
                aliases = ["feline"]

            # Get class by name
            DogClass = Animal.get_subclass("Dog")
            assert DogClass is Dog

            # Get class by alias
            CanineClass = Animal.get_subclass("canine")
            assert CanineClass is Dog

            # Case insensitive
            CatClass = Animal.get_subclass("FELINE")
            assert CatClass is Cat

            # Handle missing keys
            UnknownClass = Animal.get_subclass("Robot", raise_error=False)
            assert UnknownClass is None

            try:
                Animal.get_subclass("Robot")  # raise_error=True by default
            except KeyError:
                print("Robot not found")
            ```

        Note:
            This method searches the entire registry and does not enforce hierarchical
            scoping like the `of()` method. Use `of()` for hierarchy-aware instantiation.
        """
        if isinstance(key, str):
            subclasses = cls._registry.get(_str_normalize(key))
        elif isinstance(key, tuple):
            # Normalize tuple keys the same way as during registration
            normalized_key = tuple(
                _str_normalize(key_part) if isinstance(key_part, str) else key_part for key_part in key
            )
            subclasses = cls._registry.get(normalized_key)
        else:
            subclasses = cls._registry.get(key)

        if subclasses is None:
            if raise_error:
                available_keys = "\n".join(sorted(str(k) for k in cls._registry.keys()))
                raise KeyError(
                    f'Could not find subclass of {cls} using key: "{key}" (type={type(key)}). '
                    f"Available keys are:\n{available_keys}"
                )
            return None

        if len(subclasses) == 1:
            return next(iter(subclasses.values()))
        return list(subclasses.values())

    @classmethod
    def subclasses(cls, keep_abstract: bool = False) -> Set[Type]:
        """
        Get all registered subclasses of this Registry class.

        Returns all classes that have been registered as subclasses of the calling class.
        This provides a way to discover what implementations are available without needing
        to know their keys in advance.

        Args:
            keep_abstract (bool): Whether to include abstract classes in the result.
                Defaults to False (only concrete classes returned).

        Returns:
            Set[Type]: Set of registered subclass types. Abstract classes are excluded
            unless keep_abstract=True.

        Examples:
            ```python
            class Animal(Registry, ABC):
                pass

            class Mammal(Animal, ABC):  # Abstract intermediate
                pass

            class Dog(Mammal):
                pass

            class Cat(Mammal):
                pass

            class Bird(Animal, ABC):  # Abstract intermediate
                pass

            class Parrot(Bird):
                pass

            # Get concrete subclasses only (default)
            concrete_animals = Animal.subclasses()
            assert Dog in concrete_animals
            assert Cat in concrete_animals
            assert Parrot in concrete_animals
            assert Mammal not in concrete_animals  # Abstract
            assert Bird not in concrete_animals    # Abstract

            # Include abstract classes
            all_animals = Animal.subclasses(keep_abstract=True)
            assert Mammal in all_animals
            assert Bird in all_animals
            assert Dog in all_animals

            # Hierarchical subclasses
            mammals = Mammal.subclasses()  # Only mammal subclasses
            assert Dog in mammals
            assert Cat in mammals
            assert Parrot not in mammals  # Not a mammal
            ```

        Use Cases:
            - **Plugin Discovery**: Find all available plugin implementations
            - **Validation**: Check what implementations are registered
            - **Dynamic UI**: Build menus or lists of available options
            - **Testing**: Verify all expected subclasses are registered
            - **Documentation**: Generate lists of available classes

            ```python
            # Plugin discovery example
            available_processors = DataProcessor.subclasses()
            for processor_cls in available_processors:
                print(f"Available: {processor_cls.__name__}")
                if hasattr(processor_cls, 'aliases'):
                    print(f"  Aliases: {processor_cls.aliases}")

            # Dynamic factory with validation
            def create_safe_processor(processor_type: str, **kwargs):
                available = {cls.__name__.lower(): cls for cls in DataProcessor.subclasses()}
                if processor_type.lower() not in available:
                    raise ValueError(f"Unknown processor: {processor_type}. "
                                   f"Available: {list(available.keys())}")
                return available[processor_type.lower()](**kwargs)
            ```

        Note:
            This method respects the registry hierarchy - it only returns subclasses of the
            calling class, not subclasses of sibling classes.
        """
        available_subclasses = set()

        for registered_dict in cls._registry.values():
            for subclass in registered_dict.values():
                if subclass == cls._registry_base_class:
                    continue
                if _is_abstract(subclass) and not keep_abstract:
                    continue
                if isinstance(subclass, type) and issubclass(subclass, cls):
                    available_subclasses.add(subclass)

        return available_subclasses

    @classmethod
    def _get_hierarchical_subclass(cls, registry_key: Any) -> Optional[Union[Type, List[Type]]]:
        """
        Get subclass by registry_key, but only search within the hierarchy of the calling class.

        For concrete classes, this can return the class itself if the registry_key matches.
        For abstract classes, this searches only within direct and indirect subclasses.
        """
        # If the class is concrete (not abstract) and registry_key matches the class name or aliases
        if not _is_abstract(cls):
            # Check if registry_key matches this concrete class
            class_keys = [cls.__name__] + _as_list(cls.aliases) + _as_list(cls._registry_keys())

            for class_key in class_keys:
                if class_key is None:
                    continue
                elif isinstance(class_key, str):
                    if (
                        _str_normalize(class_key) == _str_normalize(registry_key)
                        if isinstance(registry_key, str)
                        else False
                    ):
                        return cls
                elif isinstance(class_key, tuple) and isinstance(registry_key, tuple):
                    normalized_class_key = tuple(
                        _str_normalize(k) if isinstance(k, str) else k for k in class_key
                    )
                    normalized_registry_key = tuple(
                        _str_normalize(k) if isinstance(k, str) else k for k in registry_key
                    )
                    if normalized_class_key == normalized_registry_key:
                        return cls
                elif class_key == registry_key:
                    return cls

        # Search in registry but filter to only subclasses of cls
        matching_subclasses = {}

        # Normalize the search key
        if isinstance(registry_key, str):
            search_key = _str_normalize(registry_key)
        elif isinstance(registry_key, tuple):
            search_key = tuple(
                _str_normalize(key_part) if isinstance(key_part, str) else key_part
                for key_part in registry_key
            )
        else:
            search_key = registry_key

        # Look through registry for matching keys
        registry_entry = cls._registry.get(search_key)
        if registry_entry:
            # Filter to only include subclasses of cls
            for subclass_name, subclass in registry_entry.items():
                if isinstance(subclass, type) and issubclass(subclass, cls) and subclass != cls:
                    matching_subclasses[subclass_name] = subclass

        if not matching_subclasses:
            return None

        if len(matching_subclasses) == 1:
            return next(iter(matching_subclasses.values()))
        return list(matching_subclasses.values())

    @classmethod
    def remove_subclass(cls, subclass: Union[Type, str]):
        """Remove a subclass from the registry."""
        name = subclass if isinstance(subclass, str) else subclass.__name__

        # Remove from all registry entries and clean up empty dictionaries
        keys_to_remove = []
        for key, registered_dict in cls._registry.items():
            for subclass_name in list(registered_dict.keys()):
                if _str_normalize(subclass_name) == _str_normalize(name):
                    registered_dict.pop(subclass_name, None)
            # Mark empty dictionaries for removal
            if not registered_dict:
                keys_to_remove.append(key)

        # Remove empty registry entries
        for key in keys_to_remove:
            cls._registry.pop(key, None)

    @classmethod
    def _registry_keys(cls) -> Optional[Union[List[Any], Any]]:
        """
        Override in subclasses to provide additional registry keys.

        This method allows classes to register themselves under custom keys beyond their
        class name and aliases. Useful for creating semantic keys, composite keys, or
        domain-specific identifiers.

        Returns:
            - **None**: No additional keys (default)
            - **Any**: Single additional key of any type
            - **List[Any]**: Multiple additional keys of any type

        Key Types:
            - **str**: Additional string identifiers
            - **tuple**: Composite keys for hierarchical or multi-dimensional lookups
            - **int/float**: Numeric identifiers
            - **Any**: Custom types for domain-specific keys

        Examples:
            ```python
            # String-based semantic keys
            class EmailService(Service):
                @classmethod
                def _registry_keys(cls):
                    return ["mail", "smtp", "email-sender"]

            # Tuple-based composite keys
            class HTTPSService(Service):
                @classmethod
                def _registry_keys(cls):
                    return [
                        ("protocol", "https"),
                        ("service", "web"),
                        ("port", 443)
                    ]

            # Mixed key types
            class DatabaseService(Service):
                @classmethod
                def _registry_keys(cls):
                    return [
                        "database",                    # String key
                        ("type", "database"),          # Tuple key
                        5432,                          # Port number key
                        ("database", "postgresql")     # Specific database type
                    ]

            # Dynamic key generation
            class APIService(Service):
                version = "v2"
                endpoint = "users"

                @classmethod
                def _registry_keys(cls):
                    return [
                        f"api-{cls.version}",
                        f"{cls.endpoint}-service",
                        ("api", cls.version, cls.endpoint)
                    ]

            # Usage with different key types
            email = Service.of("smtp")                      # String key
            https = Service.of(("protocol", "https"))       # Tuple key
            db = Service.of(5432)                          # Numeric key
            api = Service.of(("api", "v2", "users"))       # Complex tuple key
            ```

        Best Practices:
            ```python
            # Use semantic, domain-appropriate keys
            class PaymentProcessor(Registry):
                @classmethod
                def _registry_keys(cls):
                    return [
                        "payment",
                        ("service", "financial"),
                        ("type", "processor")
                    ]

            # Avoid conflicts with likely aliases
            class LoggingService(Registry):
                aliases = ["logger", "log"]  # Common aliases

                @classmethod
                def _registry_keys(cls):
                    # Avoid "log" here as it's already in aliases
                    return [
                        ("service", "logging"),
                        ("type", "audit"),
                        "audit-logger"  # Specific, unlikely to conflict
                    ]

            # Use tuples for hierarchical organization
            class DatabaseConnection(Registry):
                @classmethod
                def _registry_keys(cls):
                    return [
                        ("database", "connection"),
                        ("storage", "persistent"),
                        ("type", "relational")
                    ]
            ```

        Note:
            - Keys are automatically normalized for strings (case-insensitive, flexible spacing)
            - Tuple keys have their string elements normalized individually
            - All keys must be hashable (usable as dictionary keys)
            - Keys are registered in addition to class name and aliases
            - Duplicate keys across classes will trigger registration conflicts unless
              `_allow_multiple_subclasses` is True
        """
        return None

    @classmethod
    def of(cls, registry_key: Any = None, *args, **kwargs):
        """
        Hierarchical factory method for creating instances of registered subclasses.

        This is the core factory method that provides intelligent, hierarchy-aware instance creation.
        The behavior depends on whether the calling class is abstract or concrete, and whether a
        registry_key is provided. The method enforces hierarchical scoping - classes can only
        instantiate their own subclasses.

        Hierarchical Factory Modes:

            **1. Direct Instantiation (Concrete Classes):**
            Concrete classes can create instances directly without registry keys:
            ```python
            class Dog(Animal):  # Concrete class
                def __init__(self, name="Buddy"):
                    self.name = name

            dog = Dog.of()                    # ✅ Direct instantiation
            dog = Dog.of(name="Rex")          # ✅ With constructor args
            dog = Dog.of("Dog", name="Max")   # ✅ Also works with matching key
            ```

            **2. Factory Method (Abstract Classes):**
            Abstract classes require registry keys to specify which subclass to create:
            ```python
            class Animal(Registry, ABC):  # Abstract base
                pass

            dog = Animal.of("Dog", name="Buddy")    # ✅ Key required
            cat = Animal.of("Cat", name="Whiskers") # ✅ Key required
            # animal = Animal.of()                  # ❌ TypeError: key required
            ```

            **3. Hierarchical Scoping:**
            Classes can only instantiate their own subclasses, enforcing architecture:
            ```python
            class Mammal(Animal, ABC):
                pass

            class Cat(Mammal, ABC):
                pass

            class Dog(Mammal):
                pass

            class TabbyCat(Cat):
                pass

            # Hierarchical restrictions enforced
            tabby = Cat.of("TabbyCat")         # ✅ TabbyCat is Cat subclass
            dog = Mammal.of("Dog")             # ✅ Dog is Mammal subclass
            any_animal = Animal.of("Dog")      # ✅ Dog is Animal subclass

            # dog = Cat.of("Dog")              # ❌ KeyError: Dog not Cat subclass
            ```

        Args:
            registry_key (Any, optional): Key to look up subclass. Can be:
                - **None**: For concrete classes, instantiates the class directly
                - **str**: Class name or alias (case-insensitive, normalized)
                - **tuple**: Custom composite key from _registry_keys()
                - **Any**: Custom key type from _registry_keys()

                If None and the class is concrete, instantiates that class directly.
                If None and the class is abstract, raises TypeError.

            *args: Positional arguments passed to the subclass constructor
            **kwargs: Keyword arguments passed to the subclass constructor

        Returns:
            Instance of the found subclass or the class itself (for direct instantiation)

        Raises:
            TypeError: If called on Registry base class directly, or if abstract class
                      called without registry_key, or multiple subclasses match key
            KeyError: If registry_key not found in the class's hierarchy

        Registry Key Types:
            ```python
            # String keys (normalized: case-insensitive, space/dash/underscore flexible)
            service = Service.of("EmailService")
            service = Service.of("email-service")      # Same as above
            service = Service.of("EMAIL_SERVICE")      # Same as above

            # Alias keys
            class EmailService(Service):
                aliases = ["email", "mail", "smtp"]

            service = Service.of("email")              # Using alias

            # Tuple keys from _registry_keys()
            class HTTPService(Service):
                @classmethod
                def _registry_keys(cls):
                    return [("protocol", "http"), ("service", "web")]

            service = Service.of(("protocol", "http"))
            service = Service.of(("service", "web"))

            # Direct instantiation (concrete classes only)
            service = EmailService.of()                # No key needed
            ```

        Hierarchical Architecture Example:
            ```python
            class Service(Registry, ABC):
                @abstractmethod
                def process(self, data): pass

            class DataService(Service, ABC):
                '''Base for data processing services'''
                pass

            class NotificationService(Service, ABC):
                '''Base for notification services'''
                pass

            class FileService(DataService):
                def process(self, data):
                    return f"Processing file: {data}"

            class EmailService(NotificationService):
                aliases = ["email", "mail"]

                def process(self, data):
                    return f"Sending email: {data}"

            class SMSService(NotificationService):
                def process(self, data):
                    return f"Sending SMS: {data}"

            # Hierarchical scoping in action
            file_svc = DataService.of("FileService")           # ✅ FileService ∈ DataService
            email_svc = NotificationService.of("EmailService") # ✅ EmailService ∈ NotificationService
            mail_svc = NotificationService.of("mail")          # ✅ Using alias
            any_svc = Service.of("SMSService")                 # ✅ SMSService ∈ Service

            # These fail due to hierarchical restrictions
            # email_svc = DataService.of("EmailService")       # ❌ EmailService ∉ DataService
            # file_svc = NotificationService.of("FileService") # ❌ FileService ∉ NotificationService

            # Direct instantiation for concrete classes
            file_svc = FileService.of()                        # ✅ Direct concrete instantiation
            email_svc = EmailService.of(smtp_host="smtp.com")  # ✅ With constructor args
            ```

        Error Handling:
            ```python
            # Registry base class usage
            try:
                Registry.of("SomeClass")
            except TypeError as e:
                # "The 'of' factory method cannot be called directly on Registry class"

            # Abstract class without key
            try:
                Service.of()  # Abstract class, no key
            except TypeError as e:
                # "Cannot instantiate abstract class 'Service' without specifying a registry_key"

            # Key not found in hierarchy
            try:
                DataService.of("EmailService")  # EmailService not in DataService hierarchy
            except KeyError as e:
                # "Could not find subclass of DataService using registry_key: 'EmailService'"
                # Shows available keys in DataService hierarchy

            # Multiple subclasses (when _allow_multiple_subclasses=True)
            try:
                Service.of("shared_alias")  # Multiple classes have same alias
            except TypeError as e:
                # "Cannot instantiate using registry_key 'shared_alias' because multiple subclasses"
            ```

        Performance Notes:
            - Registry lookups are O(1) hash table operations
            - Hierarchical filtering is optimized for inheritance chains
            - String normalization is cached during registration
            - Direct instantiation (concrete classes) bypasses registry lookup entirely

        See Also:
            get_subclass(): Get class by key without creating instance
            subclasses(): Get all registered subclasses in hierarchy
            _get_hierarchical_subclass(): Internal hierarchical lookup method
        """
        # Prevent calling 'of' directly on Registry class
        if cls is Registry:
            raise TypeError(
                "The 'of' factory method cannot be called directly on Registry class. "
                "It must be called on a subclass of Registry."
            )

        # Ensure this is called on a Registry subclass
        if not issubclass(cls, Registry):
            raise TypeError(
                f"The 'of' method can only be called on Registry subclasses, "
                f"but {cls.__name__} is not a Registry subclass."
            )

        # Handle case where no registry_key is provided
        if registry_key is None:
            if not _is_abstract(cls):
                # Concrete class without registry_key - instantiate directly
                return cls(*args, **kwargs)
            else:
                # Abstract class without registry_key - cannot instantiate
                raise TypeError(
                    f"Cannot instantiate abstract class '{cls.__name__}' without specifying "
                    f"a registry_key to identify which subclass to create."
                )

        # Use hierarchical lookup to find the subclass
        subclass = cls._get_hierarchical_subclass(registry_key)

        if subclass is None:
            # Build error message showing available keys in this hierarchy
            available_classes = set()

            # If concrete, the class itself is available
            if not _is_abstract(cls):
                available_classes.add(cls.__name__)

            # Add subclasses
            for sub in cls.subclasses(keep_abstract=True):
                available_classes.add(sub.__name__)
                if hasattr(sub, "aliases"):
                    available_classes.update(_as_list(sub.aliases))

            available_keys = sorted(available_classes)
            raise KeyError(
                f'Could not find subclass of {cls.__name__} using registry_key: "{registry_key}" (type={type(registry_key)}). '
                f"Available keys in this hierarchy are: {available_keys}"
            )

        # Handle case where multiple subclasses are registered to the same registry_key
        if isinstance(subclass, list):
            if len(subclass) == 1:
                subclass = subclass[0]
            else:
                raise TypeError(
                    f"Cannot instantiate using registry_key '{registry_key}' because multiple subclasses "
                    f"are registered: {[sc.__name__ for sc in subclass]}. "
                    f"Use a more specific registry_key to select a single subclass."
                )

        # Create and return instance
        return subclass(*args, **kwargs)
