"""Collection and data structure utilities."""

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
