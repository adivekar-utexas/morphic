"""Function utilities for introspection and manipulation."""

import ast
import functools
import inspect
import re
import sys
import textwrap
import types
from ast import literal_eval
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from .structs import default
from .typed import Typed


def fn_str(fn: Callable) -> str:
    """Get a string representation of a function."""
    return f"{get_fn_spec(fn).resolved_name}"


def get_current_fn_name(n: int = 0) -> str:
    """Get the name of the current function."""
    return sys._getframe(n + 1).f_code.co_name


def is_function(fn: Any) -> bool:
    """Check if an object is a function."""
    return isinstance(
        fn,
        (
            types.FunctionType,
            types.MethodType,
            types.MethodDescriptorType,
            types.BuiltinFunctionType,
            types.BuiltinMethodType,
            types.LambdaType,
            functools.partial,
        ),
    )


def call_str_to_params(
    call_str: str,
    callable_name_key: str = "name",
    max_len: int = 1024,
) -> Tuple[List, Dict]:
    """Parse a call string into args and kwargs."""
    if len(call_str) > max_len:
        raise ValueError(f"We cannot parse `call_str` beyond {max_len} chars; found {len(call_str)} chars")
    call_str = call_str.strip()
    if not call_str.endswith(")"):
        raise ValueError(f'`call_str` must end with a closing paren; found: `call_str`="{call_str}"')
    if not (call_str.find("(") < call_str.find(")")):
        raise ValueError(
            f"`call_str` must have one opening paren, followed by one closing paren; "
            f'found: `call_str`="{call_str}"'
        )

    name: str = call_str.split("(")[0]
    args: List = []
    kwargs: Dict = {callable_name_key: name}

    if call_str != f"{name}()":
        # We have some params
        params_str: str = call_str.replace(f"{name}(", "")
        assert params_str.endswith(")")
        params_str = params_str[:-1]

        for param_str in params_str.split(","):
            param_str = param_str.strip()
            if "=" not in param_str:
                # Not an arg-value pair, instead just arg
                args.append(literal_eval(param_str))
            elif len(param_str.split("=")) != 2:
                # Cannot resolve arg-value pair
                raise ValueError(f'Found invalid arg-value pair "{param_str}" in `call_str`="{call_str}"')
            else:
                k, v = param_str.split("=")
                if k == name:
                    raise ValueError(f'Argument name and callable name overlap: "{name}"')
                kwargs[k] = literal_eval(v)

    return args, kwargs


def params_to_call_str(callable_name: str, args: List, kwargs: Dict) -> str:
    """Convert args and kwargs to a call string."""
    sep: str = ", "
    stringified = []

    if len(args) > 0:
        stringified.append(sep.join(repr(arg) for arg in args))

    if len(kwargs) > 0:
        stringified.append(
            sep.join([f"{k}={repr(v)}" for k, v in sorted(list(kwargs.items()), key=lambda x: x[0])])
        )

    return f"{callable_name}({sep.join(stringified)})"


def wrap_fn_output(fn: Callable, wrapper_fn: Callable) -> Callable:
    """
    Wrap a function's output with another function.

    Args:
        fn: Original function to invoke
        wrapper_fn: Function that takes the original function's output and transforms it

    Returns:
        Wrapped function
    """

    def wrapper(*args, **kwargs):
        return wrapper_fn(fn(*args, **kwargs))

    return wrapper


def parsed_fn_source(function: Callable) -> Tuple[str, str]:
    """Parse a function's source code into full source and body."""
    # Get the source code of the function and dedent it to handle nested functions
    source_code = textwrap.dedent(inspect.getsource(function))
    # Parse it into an AST
    parsed_source = ast.parse(source_code)

    # The first element of the body should be the FunctionDef node for the function
    function_node: Any = parsed_source.body[0]

    # Extract the full function source
    fn_source: str = ast.unparse(function_node)

    # Extract just the function body
    fn_body: str = "\n".join([ast.unparse(stmt) for stmt in function_node.body])

    return fn_source, fn_body


class FunctionSpec(Typed):
    """Specification of a function's signature and metadata."""

    name: str
    qualname: str
    resolved_name: str
    args: Tuple[str, ...]
    kwargs: Tuple[str, ...]
    default_args: Dict[str, Any]
    default_kwargs: Dict[str, Any]
    source: Optional[str] = None
    source_body: Optional[str] = None
    varargs_name: Optional[str] = None
    varkwargs_name: Optional[str] = None
    ignored_args: Tuple[str, ...] = ("self", "cls")

    @property
    def args_and_kwargs(self) -> Tuple[str, ...]:
        """Get all arguments and keyword arguments."""
        return self.args + self.kwargs

    @property
    def default_args_and_kwargs(self) -> Dict[str, Any]:
        """Get all default arguments and keyword arguments."""
        return {**self.default_args, **self.default_kwargs}

    @property
    def required_args_and_kwargs(self) -> Tuple[str, ...]:
        """Get required arguments (those without defaults)."""
        default_args_and_kwargs = self.default_args_and_kwargs
        return tuple(arg for arg in self.args_and_kwargs if arg not in default_args_and_kwargs)

    @property
    def num_args(self) -> int:
        """Number of positional arguments."""
        return len(self.args)

    @property
    def num_kwargs(self) -> int:
        """Number of keyword-only arguments."""
        return len(self.kwargs)

    @property
    def num_args_and_kwargs(self) -> int:
        """Total number of arguments."""
        return self.num_args + self.num_kwargs

    @property
    def num_default_args(self) -> int:
        """Number of positional arguments with defaults."""
        return len(self.default_args)

    @property
    def num_default_kwargs(self) -> int:
        """Number of keyword arguments with defaults."""
        return len(self.default_kwargs)

    @property
    def num_default_args_and_kwargs(self) -> int:
        """Total number of arguments with defaults."""
        return self.num_default_args + self.num_default_kwargs

    @property
    def num_required_args_and_kwargs(self) -> int:
        """Number of required arguments (without defaults)."""
        return self.num_args_and_kwargs - self.num_default_args_and_kwargs


def get_fn_spec(
    fn: Callable, *, parse_source: bool = False, ignored_args: Tuple[str, ...] = ("self", "cls")
) -> FunctionSpec:
    """Get detailed specification of a function's signature."""
    if hasattr(fn, "__wrapped__"):
        # If function is wrapped with decorators, unwrap and get all args
        return get_fn_spec(fn.__wrapped__, parse_source=parse_source, ignored_args=ignored_args)

    argspec: inspect.FullArgSpec = inspect.getfullargspec(fn)

    args_raw: Tuple[str, ...] = tuple(default(argspec.args, []))
    varargs_name: Optional[str] = argspec.varargs

    kwargs_raw: Tuple[str, ...] = tuple(default(argspec.kwonlyargs, []))
    varkwargs_name: Optional[str] = argspec.varkw

    default_args_tuple: Tuple[Any, ...] = default(argspec.defaults, tuple())
    default_args_raw: Dict[str, Any] = dict(
        zip(
            argspec.args[-len(default_args_tuple) :] if default_args_tuple else [],
            default_args_tuple,
        )
    )
    default_kwargs_raw: Dict[str, Any] = default(argspec.kwonlydefaults, dict())

    # Filter out ignored args
    args = tuple(arg for arg in args_raw if arg not in ignored_args)
    kwargs = tuple(arg for arg in kwargs_raw if arg not in ignored_args)
    default_args = {k: v for k, v in default_args_raw.items() if k not in ignored_args}
    default_kwargs = {k: v for k, v in default_kwargs_raw.items() if k not in ignored_args}

    source: Optional[str] = None
    source_body: Optional[str] = None
    if parse_source:
        try:
            source, source_body = parsed_fn_source(fn)
        except (IndentationError, OSError):
            try:
                source = inspect.getsource(fn)
                source_args_and_body = re.sub(
                    r"^\s*(def\s+\w+\()", "", source, count=1, flags=re.MULTILINE
                ).strip()
                source_body = source_args_and_body  # Better than nothing
            except OSError:
                # Built-in functions don't have source
                pass

    return FunctionSpec(
        name=fn.__name__,
        qualname=fn.__qualname__,
        resolved_name=f"{fn.__module__}.{fn.__qualname__}",
        source=source,
        source_body=source_body,
        args=args,
        varargs_name=varargs_name,
        kwargs=kwargs,
        varkwargs_name=varkwargs_name,
        default_args=default_args,
        default_kwargs=default_kwargs,
        ignored_args=ignored_args,
    )


def get_fn_args(
    fn: Union[Callable, FunctionSpec],
    *,
    ignore: Tuple[str, ...] = ("self", "cls", "kwargs"),
    include_args: bool = True,
    include_kwargs: bool = True,
    include_default: bool = True,
) -> Tuple[str, ...]:
    """Get the argument names of a function."""
    if isinstance(fn, FunctionSpec):
        fn_spec = fn
    else:
        fn_spec = get_fn_spec(fn)

    arg_names: List[str] = []

    if include_args:
        arg_names.extend(fn_spec.args)
    if include_kwargs:
        arg_names.extend(fn_spec.kwargs)

    if not include_default:
        ignore = tuple(list(ignore) + list(fn_spec.default_args.keys()) + list(fn_spec.default_kwargs.keys()))

    ignore_set: Set[str] = set(ignore)
    arg_names = tuple(a for a in arg_names if a not in ignore_set)

    return arg_names


def filter_kwargs(fns: Union[Callable, List[Callable], Tuple[Callable, ...]], **kwargs) -> Dict[str, Any]:
    """Filter kwargs to only include those accepted by the given functions."""
    to_keep: Set = set()

    if isinstance(fns, (list, set, tuple)):
        fns = list(fns)
    else:
        fns = [fns]

    for fn in fns:
        fn_args = get_fn_args(fn)
        to_keep.update(set(fn_args))

    filtered_kwargs = {k: kwargs[k] for k in kwargs if k in to_keep}
    return filtered_kwargs
