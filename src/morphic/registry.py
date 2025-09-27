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
    A registry for subclasses. When a base class extends Registry, its subclasses will automatically be registered.

    This pattern allows maintaining the Dependency Inversion Principle - the base class doesn't depend on
    subclass implementations. Instead, retrieve subclasses using keys and interact via base class methods.

    Example:
        ```python
        from morphic import Registry
        from abc import ABC, abstractmethod

        class Animal(Registry, ABC):
            @abstractmethod
            def speak(self) -> str:
                pass

        class Dog(Animal):
            def speak(self) -> str:
                return "Woof!"

        class Cat(Animal):
            aliases = ["feline", "kitty"]
            def speak(self) -> str:
                return "Meow!"

        # Retrieve registered classes
        DogClass = Animal.get_subclass("Dog")
        CatClass = Animal.get_subclass("feline")  # Works with aliases

        dog = DogClass()
        cat = CatClass()
        ```
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
        Get registered subclass(es) by key.

        Args:
            key: Key to look up subclass (class name, alias, etc.)
            raise_error: Whether to raise error if key not found

        Returns:
            Single subclass type if only one registered, list if multiple, None if not found
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
        """Get all registered subclasses."""
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
                    if _str_normalize(class_key) == _str_normalize(registry_key) if isinstance(registry_key, str) else False:
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
                _str_normalize(key_part) if isinstance(key_part, str) else key_part for key_part in registry_key
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
        """Override in subclasses to provide additional registry keys."""
        return None

    @classmethod
    def of(cls, registry_key: Any = None, *args, **kwargs):
        """
        Hierarchical factory method to create instances of registered subclasses.

        This method works hierarchically:
        1. If called on a concrete (non-abstract) class without a registry_key, it instantiates that class directly
        2. If called on a concrete class with a registry_key that matches the class, it instantiates that class
        3. If called on an abstract class, it searches only within its subclass hierarchy
        4. If called on any class with a registry_key, it performs hierarchical lookup within the class's subtree

        Args:
            registry_key: Optional key to look up subclass (class name, alias, tuple key, etc.).
                         If None and the class is concrete, instantiates the class directly.
            *args: Positional arguments to pass to the subclass constructor
            **kwargs: Keyword arguments to pass to the subclass constructor

        Returns:
            Instance of the found subclass or the class itself

        Raises:
            TypeError: If called directly on Registry class, or if registry_key is required but not provided
            KeyError: If the registry_key is not found in the class hierarchy

        Examples:
            ```python
            class Animal(Registry, ABC):
                @abstractmethod
                def speak(self) -> str:
                    pass

            class Cat(Animal, ABC):  # Abstract intermediate class
                pass

            class TabbyCat(Cat):
                def __init__(self, name="Tabby"):
                    self.name = name
                def speak(self) -> str:
                    return f"{self.name} the tabby says Meow!"

            class OrangeCat(Cat):
                def __init__(self, name="Orange"):
                    self.name = name
                def speak(self) -> str:
                    return f"{self.name} the orange cat says Meow!"

            class Dog(Animal):  # Concrete class
                def __init__(self, name="Buddy"):
                    self.name = name
                def speak(self) -> str:
                    return f"{self.name} says Woof!"

            # Hierarchical usage:
            dog = Dog.of()  # Direct instantiation of concrete class
            dog = Dog.of("Dog")  # Also works with key matching class name

            tabby = Cat.of("TabbyCat")  # Abstract class looks only in its subclasses
            orange = Cat.of("OrangeCat")  # Only TabbyCat and OrangeCat are accessible

            # This would fail - Cat.of("Dog") because Dog is not a subclass of Cat
            ```
        """
        # Prevent calling 'of' directly on Registry class
        if cls is Registry:
            raise TypeError("The 'of' factory method cannot be called directly on Registry class. "
                          "It must be called on a subclass of Registry.")

        # Ensure this is called on a Registry subclass
        if not issubclass(cls, Registry):
            raise TypeError(f"The 'of' method can only be called on Registry subclasses, "
                          f"but {cls.__name__} is not a Registry subclass.")

        # Handle case where no registry_key is provided
        if registry_key is None:
            if not _is_abstract(cls):
                # Concrete class without registry_key - instantiate directly
                return cls(*args, **kwargs)
            else:
                # Abstract class without registry_key - cannot instantiate
                raise TypeError(f"Cannot instantiate abstract class '{cls.__name__}' without specifying "
                              f"a registry_key to identify which subclass to create.")

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
                if hasattr(sub, 'aliases'):
                    available_classes.update(_as_list(sub.aliases))

            available_keys = sorted(available_classes)
            raise KeyError(f'Could not find subclass of {cls.__name__} using registry_key: "{registry_key}" (type={type(registry_key)}). '
                          f"Available keys in this hierarchy are: {available_keys}")

        # Handle case where multiple subclasses are registered to the same registry_key
        if isinstance(subclass, list):
            if len(subclass) == 1:
                subclass = subclass[0]
            else:
                raise TypeError(f"Cannot instantiate using registry_key '{registry_key}' because multiple subclasses "
                              f"are registered: {[sc.__name__ for sc in subclass]}. "
                              f"Use a more specific registry_key to select a single subclass.")

        # Create and return instance
        return subclass(*args, **kwargs)
