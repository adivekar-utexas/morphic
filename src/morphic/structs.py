"""Collection and data structure utilities."""

from collections.abc import MutableMapping
from typing import Any, List, Literal, Optional, Set, Tuple, Union

from .imports import optional_dependency


def is_scalar(x: Optional[Any], method: Literal["numpy", "pandas"] = "pandas") -> bool:
    if x is None:
        return True
    if method == "pandas":
        with optional_dependency("pandas", error="ignore"):
            from pandas.api.types import is_scalar as pd_is_scalar

            ## Ref: https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.api.types.is_scalar.html
            ## Actual code: github.com/pandas-dev/pandas/blob/0402367c8342564538999a559e057e6af074e5e4/pandas/_libs/lib.pyx#L162
            return bool(pd_is_scalar(x))
        # Fallback to basic Python scalar check if pandas not available
        return isinstance(x, (str, bytes, int, float, complex, bool)) or x is None

    if method == "numpy":
        with optional_dependency("numpy", error="ignore"):
            import numpy as np

            ## Ref: https://numpy.org/doc/stable/reference/arrays.scalars.html#built-in-scalar-types
            return bool(np.isscalar(x))
        # Fallback to numpy-compatible behavior if numpy not available
        # numpy.isscalar returns False for None
        return isinstance(x, (str, bytes, int, float, complex, bool))

    raise NotImplementedError(f'Unsupported method: "{method}"')


def is_null(z: Any) -> bool:
    if is_scalar(z):
        with optional_dependency("pandas", error="ignore"):
            import pandas as pd

            return pd.isnull(z)
        # Fallback to basic None check if pandas not available
        return z is None
    return z is None


def default(*vals) -> Optional[Any]:
    """Return the first non-null value from the arguments, or None if all are null."""
    for x in vals:
        if not is_null(x):
            return x
    return None


# ======================== None utilities ======================== #


def any_are_none(*args) -> bool:
    """Return True if any of the arguments are None."""
    for x in args:
        if x is None:
            return True
    return False


def all_are_not_none(*args) -> bool:
    """Return True if all of the arguments are not None."""
    return not any_are_none(*args)


def all_are_none(*args) -> bool:
    """Return True if all of the arguments are None."""
    for x in args:
        if x is not None:
            return False
    return True


def any_are_not_none(*args) -> bool:
    """Return True if any of the arguments are not None."""
    return not all_are_none(*args)


def all_are_true(*args) -> bool:
    """Return True if all of the arguments are True."""
    for x in args:
        if not x:
            return False
    return True


def all_are_false(*args) -> bool:
    """Return True if all of the arguments are False."""
    for x in args:
        if x:
            return False
    return True


def none_count(*args) -> int:
    """Count the number of None values in the arguments."""
    count = 0
    for x in args:
        if x is None:
            count += 1
    return count


def not_none_count(*args) -> int:
    """Count the number of non-None values in the arguments."""
    return len(args) - none_count(*args)


def multiple_are_none(*args) -> bool:
    """Return True if two or more arguments are None."""
    return none_count(*args) >= 2


def multiple_are_not_none(*args) -> bool:
    """Return True if two or more arguments are not None."""
    return not_none_count(*args) >= 2


def not_impl(
    param_name: str,
    param_val: Any,
    supported: Optional[Union[List, Set, Tuple, Any]] = None,
) -> Exception:
    """Generate a NotImplementedError for unsupported parameter values."""
    if not isinstance(param_name, str):
        raise ValueError("First value `param_name` must be a string.")
    param_val_str: str = str(param_val)
    if len(param_val_str) > 100:
        param_val_str: str = "\n" + param_val_str
    if supported is not None:
        supported_list = list(supported) if not isinstance(supported, list) else supported
        return NotImplementedError(
            f"Unsupported value for param `{param_name}`. Valid values are: {supported_list}; "
            f"found {type(param_val)} having value: {param_val_str}"
        )

    return NotImplementedError(
        f"Unsupported value for param `{param_name}`; found {type(param_val)} having value: {param_val_str}"
    )


# ======================== Collection conversion utilities ======================== #


def as_list(item) -> List:
    """Convert item to list."""
    if isinstance(item, (list, tuple, set)):
        return list(item)
    return [item]


def as_tuple(item) -> Tuple:
    """Convert item to tuple."""
    if isinstance(item, (list, tuple, set)):
        return tuple(item)
    return (item,)


def as_set(item) -> Set:
    """Convert item to set."""
    if isinstance(item, set):
        return item
    if isinstance(item, (list, tuple)):
        return set(item)
    return {item}


# ======================== Type checking utilities ======================== #


def is_list_like(obj: Any) -> bool:
    """Check if object is list-like (list, tuple)."""
    return isinstance(obj, (list, tuple))


def is_set_like(obj: Any) -> bool:
    """Check if object is set-like (set, frozenset)."""
    return isinstance(obj, (set, frozenset))


def is_list_or_set_like(obj: Any) -> bool:
    """Check if object is list-like or set-like."""
    return is_list_like(obj) or is_set_like(obj)


def is_not_empty_list_like(obj: Union[List, Tuple]) -> bool:
    """Check if object is list-like and not empty."""
    return is_list_like(obj) and len(obj) > 0


def is_empty_list_like(obj: Union[List, Tuple]) -> bool:
    """Check if object is list-like and empty."""
    return is_list_like(obj) and len(obj) == 0


def is_not_empty_list(obj: List) -> bool:
    """Check if object is a non-empty list."""
    return isinstance(obj, list) and len(obj) > 0


def is_empty_list(obj: List) -> bool:
    """Check if object is an empty list."""
    return isinstance(obj, list) and len(obj) == 0


# ======================== Set operations ======================== #


def set_union(*args) -> Set:
    """Return the union of all input collections."""
    union_set: Set = set()
    for s in args:
        if isinstance(s, (list, tuple)):
            s = list(s)
        s = set(s)
        union_set = union_set.union(s)
    return union_set


def set_intersection(*args) -> Set:
    """Return the intersection of all input collections."""
    intersection_set: Optional[Set] = None
    for s in args:
        if isinstance(s, (list, tuple)):
            s = list(s)
        s = set(s)
        if intersection_set is None:
            intersection_set = s
        else:
            intersection_set = intersection_set.intersection(s)
    return intersection_set if intersection_set is not None else set()


# ======================== Collection filtering utilities ======================== #


def keep_values(
    collection: Union[List, Tuple, Set, dict],
    values: Any,
) -> Union[List, Tuple, Set, dict]:
    """Keep only specified values in a collection."""
    values_set: Set = as_set(values)
    if isinstance(collection, list):
        return [x for x in collection if x in values_set]
    elif isinstance(collection, tuple):
        return tuple(x for x in collection if x in values_set)
    elif isinstance(collection, set):
        return {x for x in collection if x in values_set}
    elif isinstance(collection, dict):
        return {k: v for k, v in collection.items() if v in values_set}
    raise NotImplementedError(f"Unsupported data structure: {type(collection)}")


def remove_values(
    collection: Union[List, Tuple, Set, dict],
    values: Any,
) -> Union[List, Tuple, Set, dict]:
    """Remove specified values from a collection."""
    values_set: Set = as_set(values)
    if isinstance(collection, list):
        return [x for x in collection if x not in values_set]
    elif isinstance(collection, tuple):
        return tuple(x for x in collection if x not in values_set)
    elif isinstance(collection, set):
        return {x for x in collection if x not in values_set}
    elif isinstance(collection, dict):
        return {k: v for k, v in collection.items() if v not in values_set}
    raise NotImplementedError(f"Unsupported data structure: {type(collection)}")


def remove_nulls(
    collection: Union[List, Tuple, Set, dict],
) -> Union[List, Tuple, Set, dict]:
    """Remove None values from a collection."""
    if isinstance(collection, list):
        return [x for x in collection if x is not None]
    elif isinstance(collection, tuple):
        return tuple(x for x in collection if x is not None)
    elif isinstance(collection, set):
        return {x for x in collection if x is not None}
    elif isinstance(collection, dict):
        return {k: v for k, v in collection.items() if v is not None}
    raise NotImplementedError(f"Unsupported data structure: {type(collection)}")


# ======================== Single item extraction utilities ======================== #


def only_item(
    collection: Union[dict, List, Tuple, Set],
    raise_error: bool = True,
) -> Any:
    """Extract the only item from a collection, or raise error if not exactly one item."""
    if not (is_list_or_set_like(collection) or isinstance(collection, dict)):
        return collection
    if len(collection) == 1:
        if isinstance(collection, dict):
            return next(iter(collection.items()))
        return next(iter(collection))
    if raise_error:
        raise ValueError(
            f"Expected input {type(collection)} to have only one item; found {len(collection)} elements."
        )
    return collection


def only_key(collection: dict, raise_error: bool = True) -> Any:
    """Extract the only key from a dict, or raise error if not exactly one key."""
    if not isinstance(collection, dict):
        return collection
    if len(collection) == 1:
        return next(iter(collection.keys()))
    if raise_error:
        raise ValueError(
            f"Expected input {type(collection)} to have only one item; found {len(collection)} elements."
        )
    return collection


def only_value(collection: dict, raise_error: bool = True) -> Any:
    """Extract the only value from a dict, or raise error if not exactly one value."""
    if not isinstance(collection, dict):
        return collection
    if len(collection) == 1:
        return next(iter(collection.values()))
    if raise_error:
        raise ValueError(
            f"Expected input {type(collection)} to have only one item; found {len(collection)} elements."
        )
    return collection


# ======================== Collection mapping utilities ======================== #
INBUILT_COLLECTIONS = (list, tuple, set, frozenset, dict)


def is_inbuilt_collection(obj: Any) -> bool:
    """Check if object is a collection."""
    return isinstance(obj, INBUILT_COLLECTIONS)


def map_collection(obj: Any, func: callable, *, recurse: bool = False) -> Any:
    """
    Apply a function to all values in a nested collection structure.

    This utility recursively traverses collections (list, tuple, set, frozenset, dict)
    and applies the given function to each value. For dictionaries, the function is
    applied only to values, not keys.

    Args:
        obj: The object to map over. Can be a scalar value or any nested collection.
        func: A callable that takes a single argument and returns a transformed value.
        recurse: If True, recursively apply to nested collections.
                 If False (default), only apply to the immediate values.

    Returns:
        A new structure of the same type with the function applied to values:
        - For scalars (non-collections): Returns `func(obj)`
        - For lists: Returns `[func(item) for item in obj]` (or recursive equivalent)
        - For tuples: Returns `tuple(func(item) for item in obj)` (or recursive equivalent)
        - For sets: Returns `{func(item) for item in obj}` (or recursive equivalent)
        - For frozensets: Returns `frozenset(func(item) for item in obj)` (or recursive equivalent)
        - For dicts: Returns `{k: func(v) for k, v in obj.items()}` (or recursive equivalent)

    Examples:
        Basic scalar transformation:
        >>> map_collection(5, lambda x: x * 2)
        10

        List transformation:
        >>> map_collection([1, 2, 3], lambda x: x * 2)
        [2, 4, 6]

        Nested list transformation:
        >>> map_collection([[1, 2], [3, 4]], lambda x: x * 2)
        [[2, 4], [6, 8]]

        Dict transformation (only values):
        >>> map_collection({"a": 1, "b": 2}, lambda x: x * 2)
        {'a': 2, 'b': 4}

        Nested dict transformation:
        >>> map_collection({"x": {"a": 1, "b": 2}}, lambda x: x * 2)
        {'x': {'a': 2, 'b': 4}}

        Mixed nested structures:
        >>> map_collection({"nums": [1, 2], "data": {"val": 3}}, lambda x: x * 2)
        {'nums': [2, 4], 'data': {'val': 6}}

        Tuple preservation:
        >>> result = map_collection((1, 2, 3), lambda x: x * 2)
        >>> assert isinstance(result, tuple)
        >>> assert result == (2, 4, 6)

        Set transformation:
        >>> result = map_collection({1, 2, 3}, lambda x: x * 2)
        >>> assert isinstance(result, set)
        >>> assert result == {2, 4, 6}

        Non-recursive mode:
        >>> map_collection([[1, 2], [3, 4]], lambda x: x if isinstance(x, list) else x * 2, recurse=False)
        [[1, 2], [3, 4]]

        Type conversion example:
        >>> def to_str(x): return str(x) if not isinstance(x, (list, dict, tuple, set, frozenset)) else x
        >>> map_collection([1, 2, {"a": 3}], to_str)
        ['1', '2', {'a': '3'}]

    Note:
        - The function is applied to leaf values (non-collection items)
        - Collections are reconstructed with the same type
        - For dicts, keys are never transformed, only values
        - Order is preserved for ordered collections (list, tuple)
        - When `recurse=True`, the function is applied after recursing into subcollections
    """
    # Handle None
    if obj is None:
        return func(obj)

    # For non-collections (scalars), apply the function directly
    if not is_inbuilt_collection(obj):
        return func(obj)

    # Handle dict
    if isinstance(obj, dict):
        if recurse:
            return {k: map_collection(v, func, recurse=True) for k, v in obj.items()}
        else:
            return {k: func(v) for k, v in obj.items()}

    # Handle list
    if isinstance(obj, list):
        if recurse:
            return [map_collection(item, func, recurse=True) for item in obj]
        else:
            return [func(item) for item in obj]

    # Handle tuple
    if isinstance(obj, tuple):
        if recurse:
            return tuple(map_collection(item, func, recurse=True) for item in obj)
        else:
            return tuple(func(item) for item in obj)

    # Handle set
    if isinstance(obj, set):
        if recurse:
            return {map_collection(item, func, recurse=True) for item in obj}
        else:
            return {func(item) for item in obj}

    # Handle frozenset
    if isinstance(obj, frozenset):
        if recurse:
            return frozenset(map_collection(item, func, recurse=True) for item in obj)
        else:
            return frozenset(func(item) for item in obj)

    raise NotImplementedError(f"Unsupported data structure: {type(obj)}")


# ======================== Dictionary utilities ======================== #


class AttrDict(MutableMapping):
    """A dictionary that supports both attribute and item access.

    `AttrDict` provides a convenient way to access dictionary keys as attributes,
    allowing for cleaner syntax while maintaining full dictionary functionality.

    Attributes and dictionary keys are synchronized bidirectionally:
    - Setting an attribute updates the dictionary: `obj.key = value` → `obj['key'] = value`
    - Setting a dictionary item makes it accessible as an attribute: `obj['key'] = value` → `obj.key`
    - Deleting works both ways: `del obj.key` ↔ `del obj['key']`

    This class fully implements the `MutableMapping` interface, so it behaves like a
    regular dictionary for all standard operations (iteration, len, containment checks, etc.).

    Private attributes (starting with '_') are stored as real object attributes and are
    not accessible via dictionary syntax.

    Examples:
        Basic usage with attribute and item access:

        >>> cfg = AttrDict({"a": 1, "b": 2})
        >>> cfg.a                    # Access via attribute
        1
        >>> cfg["b"]                 # Access via item
        2
        >>> cfg.c = 3                # Set via attribute
        >>> cfg["c"]                 # Available via item access
        3
        >>> cfg["d"] = 4             # Set via item
        >>> cfg.d                    # Available via attribute access
        4

        Initialization with keyword arguments:

        >>> config = AttrDict(x=10, y=20)
        >>> config.x
        10
        >>> config["y"]
        20

        Mixed initialization:

        >>> params = AttrDict({"learning_rate": 0.01}, batch_size=32, epochs=10)
        >>> params.learning_rate
        0.01
        >>> params.batch_size
        32

        Dictionary operations:

        >>> cfg = AttrDict({"a": 1, "b": 2})
        >>> len(cfg)
        2
        >>> "a" in cfg
        True
        >>> list(cfg.keys())
        ['a', 'b']
        >>> cfg.update({"c": 3})
        >>> cfg.c
        3

        Deletion:

        >>> cfg = AttrDict({"a": 1, "b": 2})
        >>> del cfg.a                # Delete via attribute
        >>> "a" in cfg
        False
        >>> del cfg["b"]             # Delete via item
        >>> "b" in cfg
        False

        Converting to regular dict:

        >>> cfg = AttrDict({"a": 1, "b": 2})
        >>> cfg.to_dict()
        {'a': 1, 'b': 2}

    Note:
        Keys starting with '_' can be stored in the dictionary and accessed like any
        other key. However, due to the use of `__slots__`, you cannot dynamically create
        private attributes on the object itself (they must be stored in the dict).

        >>> cfg = AttrDict({"a": 1})
        >>> cfg["_private"] = "internal"  # Stored in dictionary
        >>> "_private" in cfg              # In the dictionary
        True
        >>> cfg._private                   # Accessible as attribute
        'internal'

        The internal `_data` attribute is stored separately and is not accessible
        via dictionary operations.

    Args:
        data: Initial data as a dictionary or mapping object (optional).
        **kwargs: Additional key-value pairs to initialize the dictionary.

    Raises:
        AttributeError: When accessing a non-existent attribute.
        KeyError: When accessing a non-existent dictionary key.
    """

    __slots__ = ("_data",)

    def __init__(self, data=None, /, **kwargs):
        # store the real dict in a private slot to avoid recursion in __setattr__
        object.__setattr__(self, "_data", dict(data or {}))
        if kwargs:
            self._data.update(kwargs)

    # ---- Mapping protocol (so it behaves like a real dict) ----
    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    # ---- Attribute <-> item bridge ----
    def __getattr__(self, name):
        # Called only if normal attribute lookup fails; map to dict read
        try:
            return self._data[name]
        except KeyError as e:
            raise AttributeError(name) from e

    def __setattr__(self, name, value):
        # Keep private/dunder names as real attributes; everything else into dict
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            self._data[name] = value

    def __delattr__(self, name):
        if name.startswith("_"):
            object.__delattr__(self, name)
        else:
            try:
                del self._data[name]
            except KeyError as e:
                raise AttributeError(name) from e

    def __repr__(self):
        return f"{self.__class__.__name__}({self._data!r})"

    def to_dict(self):
        return dict(self._data)
