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
