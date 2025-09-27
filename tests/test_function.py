"""Tests for morphic.function module."""

import functools

import pytest

from morphic.function import (
    FunctionSpec,
    call_str_to_params,
    filter_kwargs,
    fn_str,
    get_current_fn_name,
    get_fn_args,
    get_fn_spec,
    is_function,
    params_to_call_str,
    parsed_fn_source,
    wrap_fn_output,
)


class TestIsFunction:
    """Tests for is_function."""

    def test_regular_function(self):
        def regular_func():
            pass

        assert is_function(regular_func) is True

    def test_lambda_function(self):
        lambda_func = lambda x: x
        assert is_function(lambda_func) is True

    def test_method(self):
        class TestClass:
            def method(self):
                pass

        obj = TestClass()
        assert is_function(obj.method) is True

    def test_builtin_function(self):
        assert is_function(len) is True
        assert is_function(str.upper) is True

    def test_partial_function(self):
        def func(a, b):
            return a + b

        partial_func = functools.partial(func, 1)
        assert is_function(partial_func) is True

    def test_non_function_objects(self):
        assert is_function("string") is False
        assert is_function(42) is False
        assert is_function([1, 2, 3]) is False
        assert is_function(object()) is False


class TestFnStr:
    """Tests for fn_str."""

    def test_simple_function(self):
        def test_func():
            pass

        result = fn_str(test_func)
        expected = f"{test_func.__module__}.{test_func.__qualname__}"
        assert result == expected

    def test_class_method(self):
        class TestClass:
            def method(self):
                pass

        obj = TestClass()
        result = fn_str(obj.method)
        expected = f"{obj.method.__module__}.{obj.method.__qualname__}"
        assert result == expected


class TestGetCurrentFnName:
    """Tests for get_current_fn_name."""

    def test_current_function_name(self):
        def test_function():
            return get_current_fn_name()

        assert test_function() == "test_function"

    def test_with_offset(self):
        def outer_function():
            def inner_function():
                return get_current_fn_name(1)  # Get outer function name

            return inner_function()

        assert outer_function() == "outer_function"


class TestCallStrToParams:
    """Tests for call_str_to_params."""

    def test_simple_function_call(self):
        call_str = "func()"
        args, kwargs = call_str_to_params(call_str)
        assert args == []
        assert kwargs == {"name": "func"}

    def test_function_with_positional_args(self):
        call_str = "func(1, 2, 'hello')"
        args, kwargs = call_str_to_params(call_str)
        assert args == [1, 2, "hello"]
        assert kwargs == {"name": "func"}

    def test_function_with_keyword_args(self):
        call_str = "func(a=1, b=2)"
        args, kwargs = call_str_to_params(call_str)
        assert args == []
        assert kwargs == {"name": "func", "a": 1, "b": 2}

    def test_function_with_mixed_args(self):
        call_str = "func(1, 'hello', a=2, b='world')"
        args, kwargs = call_str_to_params(call_str)
        assert args == [1, "hello"]
        assert kwargs == {"name": "func", "a": 2, "b": "world"}

    def test_custom_callable_name_key(self):
        call_str = "func()"
        args, kwargs = call_str_to_params(call_str, callable_name_key="function_name")
        assert args == []
        assert kwargs == {"function_name": "func"}

    def test_invalid_call_string_no_parens(self):
        with pytest.raises(ValueError, match="must end with a closing paren"):
            call_str_to_params("func")

    def test_invalid_call_string_no_closing_paren(self):
        with pytest.raises(ValueError, match="must end with a closing paren"):
            call_str_to_params("func(")

    def test_invalid_arg_value_pair(self):
        with pytest.raises(ValueError, match="Found invalid arg-value pair"):
            call_str_to_params("func(a=b=1)")

    def test_arg_name_overlaps_with_function_name(self):
        with pytest.raises(ValueError, match="Argument name and callable name overlap"):
            call_str_to_params("func(func=1)")

    def test_max_length_exceeded(self):
        long_call_str = "func(" + "a" * 1000 + ")"
        with pytest.raises(ValueError, match="cannot parse `call_str` beyond"):
            call_str_to_params(long_call_str, max_len=100)


class TestParamsToCallStr:
    """Tests for params_to_call_str."""

    def test_no_args_or_kwargs(self):
        result = params_to_call_str("func", [], {})
        assert result == "func()"

    def test_only_positional_args(self):
        result = params_to_call_str("func", [1, 2, "hello"], {})
        assert result == "func(1, 2, 'hello')"

    def test_only_keyword_args(self):
        result = params_to_call_str("func", [], {"a": 1, "b": 2})
        assert result == "func(a=1, b=2)"

    def test_mixed_args(self):
        result = params_to_call_str("func", [1, "hello"], {"a": 2, "b": "world"})
        assert result == "func(1, 'hello', a=2, b='world')"

    def test_kwargs_sorted(self):
        result = params_to_call_str("func", [], {"z": 1, "a": 2, "m": 3})
        assert result == "func(a=2, m=3, z=1)"


class TestWrapFnOutput:
    """Tests for wrap_fn_output."""

    def test_simple_wrapper(self):
        def original_func(x):
            return x * 2

        def wrapper_func(result):
            return result + 1

        wrapped = wrap_fn_output(original_func, wrapper_func)
        assert wrapped(5) == 11  # (5 * 2) + 1

    def test_wrapper_preserves_args_kwargs(self):
        def original_func(a, b, c=3):
            return a + b + c

        def wrapper_func(result):
            return str(result)

        wrapped = wrap_fn_output(original_func, wrapper_func)
        assert wrapped(1, 2) == "6"
        assert wrapped(1, 2, c=5) == "8"


class TestParsedFnSource:
    """Tests for parsed_fn_source."""

    def test_simple_function(self):
        def test_func():
            return 42

        source, body = parsed_fn_source(test_func)
        assert "def test_func():" in source
        assert "return 42" in body

    def test_function_with_multiple_statements(self):
        def test_func():
            x = 1
            y = 2
            return x + y

        source, body = parsed_fn_source(test_func)
        assert "def test_func():" in source
        assert "x = 1" in body
        assert "y = 2" in body
        assert "return x + y" in body


class TestFunctionSpec:
    """Tests for FunctionSpec class."""

    def test_simple_function_properties(self):
        spec = FunctionSpec(
            name="test_func",
            qualname="test_func",
            resolved_name="test_module.test_func",
            args=("a", "b"),
            kwargs=("c",),
            default_args={"b": 2},
            default_kwargs={"c": 3},
        )

        assert spec.args_and_kwargs == ("a", "b", "c")
        assert spec.default_args_and_kwargs == {"b": 2, "c": 3}
        assert spec.required_args_and_kwargs == ("a",)
        assert spec.num_args == 2
        assert spec.num_kwargs == 1
        assert spec.num_args_and_kwargs == 3
        assert spec.num_default_args == 1
        assert spec.num_default_kwargs == 1
        assert spec.num_default_args_and_kwargs == 2
        assert spec.num_required_args_and_kwargs == 1


class TestGetFnSpec:
    """Tests for get_fn_spec."""

    def test_simple_function(self):
        def test_func(a, b=2):
            pass

        spec = get_fn_spec(test_func)
        assert spec.name == "test_func"
        assert spec.args == ("a", "b")
        assert spec.kwargs == ()
        assert spec.default_args == {"b": 2}
        assert spec.default_kwargs == {}

    def test_function_with_keyword_only_args(self):
        def test_func(a, *, b=2, c):
            pass

        spec = get_fn_spec(test_func)
        assert spec.args == ("a",)
        assert spec.kwargs == ("b", "c")
        assert spec.default_args == {}
        assert spec.default_kwargs == {"b": 2}

    def test_function_with_varargs_and_varkwargs(self):
        def test_func(a, *args, b=2, **kwargs):
            pass

        spec = get_fn_spec(test_func)
        assert spec.args == ("a",)
        assert spec.varargs_name == "args"
        assert spec.kwargs == ("b",)
        assert spec.varkwargs_name == "kwargs"

    def test_ignore_self_and_cls(self):
        class TestClass:
            def instance_method(self, a, b=2):
                pass

            @classmethod
            def class_method(cls, a, b=2):
                pass

        obj = TestClass()

        spec = get_fn_spec(obj.instance_method)
        assert "self" not in spec.args
        assert spec.args == ("a", "b")

        spec = get_fn_spec(TestClass.class_method)
        assert "cls" not in spec.args
        assert spec.args == ("a", "b")

    def test_custom_ignored_args(self):
        def test_func(ignored_arg, a, b=2):
            pass

        spec = get_fn_spec(test_func, ignored_args=("ignored_arg",))
        assert spec.args == ("a", "b")
        assert spec.ignored_args == ("ignored_arg",)

    def test_wrapped_function(self):
        def original_func(a, b=2):
            pass

        @functools.wraps(original_func)
        def wrapper(*args, **kwargs):
            return original_func(*args, **kwargs)

        wrapper.__wrapped__ = original_func
        spec = get_fn_spec(wrapper)
        assert spec.args == ("a", "b")
        assert spec.default_args == {"b": 2}

    def test_parse_source_flag(self):
        def test_func():
            return 42

        spec = get_fn_spec(test_func, parse_source=True)
        assert spec.source is not None
        assert spec.source_body is not None
        assert "def test_func():" in spec.source
        assert "return 42" in spec.source_body


class TestGetFnArgs:
    """Tests for get_fn_args."""

    def test_function_spec_input(self):
        spec = FunctionSpec(
            name="test_func",
            qualname="test_func",
            resolved_name="test_module.test_func",
            args=("a", "b"),
            kwargs=("c", "d"),
            default_args={"b": 2},
            default_kwargs={"d": 4},
        )

        args = get_fn_args(spec)
        assert args == ("a", "b", "c", "d")

    def test_function_input(self):
        def test_func(a, b=2, *, c, d=4):
            pass

        args = get_fn_args(test_func)
        assert "a" in args
        assert "b" in args
        assert "c" in args
        assert "d" in args

    def test_include_args_only(self):
        def test_func(a, b=2, *, c, d=4):
            pass

        args = get_fn_args(test_func, include_args=True, include_kwargs=False)
        assert "a" in args
        assert "b" in args
        assert "c" not in args
        assert "d" not in args

    def test_include_kwargs_only(self):
        def test_func(a, b=2, *, c, d=4):
            pass

        args = get_fn_args(test_func, include_args=False, include_kwargs=True)
        assert "a" not in args
        assert "b" not in args
        assert "c" in args
        assert "d" in args

    def test_exclude_default_args(self):
        def test_func(a, b=2, *, c, d=4):
            pass

        args = get_fn_args(test_func, include_default=False)
        assert "a" in args
        assert "b" not in args  # has default
        assert "c" in args
        assert "d" not in args  # has default

    def test_ignore_specific_args(self):
        def test_func(self, a, b, kwargs):
            pass

        args = get_fn_args(test_func, ignore=("self", "kwargs"))
        assert "self" not in args
        assert "kwargs" not in args
        assert "a" in args
        assert "b" in args


class TestFilterKwargs:
    """Tests for filter_kwargs."""

    def test_single_function(self):
        def test_func(a, b, c):
            pass

        kwargs = {"a": 1, "b": 2, "c": 3, "d": 4}
        filtered = filter_kwargs(test_func, **kwargs)
        assert filtered == {"a": 1, "b": 2, "c": 3}

    def test_multiple_functions(self):
        def func1(a, b):
            pass

        def func2(b, c):
            pass

        kwargs = {"a": 1, "b": 2, "c": 3, "d": 4}
        filtered = filter_kwargs([func1, func2], **kwargs)
        assert filtered == {"a": 1, "b": 2, "c": 3}

    def test_no_matching_kwargs(self):
        def test_func(a, b):
            pass

        kwargs = {"c": 3, "d": 4}
        filtered = filter_kwargs(test_func, **kwargs)
        assert filtered == {}

    def test_tuple_of_functions(self):
        def func1(a):
            pass

        def func2(b):
            pass

        kwargs = {"a": 1, "b": 2, "c": 3}
        filtered = filter_kwargs((func1, func2), **kwargs)
        assert filtered == {"a": 1, "b": 2}

    def test_set_of_functions(self):
        def func1(a):
            pass

        def func2(b):
            pass

        kwargs = {"a": 1, "b": 2, "c": 3}
        filtered = filter_kwargs({func1, func2}, **kwargs)
        assert filtered == {"a": 1, "b": 2}


class TestIntegrationScenarios:
    """Integration tests combining multiple functions."""

    def test_roundtrip_call_str_conversion(self):
        """Test converting call string to params and back."""
        original_call = "my_func(1, 'hello', a=2, b='world')"
        args, kwargs = call_str_to_params(original_call)

        # Remove the 'name' key that was added
        callable_name = kwargs.pop("name")
        reconstructed = params_to_call_str(callable_name, args, kwargs)

        # Parse both to compare normalized forms
        orig_args, orig_kwargs = call_str_to_params(original_call)
        recon_args, recon_kwargs = call_str_to_params(reconstructed)

        assert orig_args == recon_args
        assert orig_kwargs == recon_kwargs

    def test_function_spec_with_complex_function(self):
        """Test get_fn_spec with a complex function signature."""

        def complex_func(a, b=2, *args, c, d=4, **kwargs):
            return sum([a, b, c, d])

        spec = get_fn_spec(complex_func, parse_source=True)

        assert spec.args == ("a", "b")
        assert spec.kwargs == ("c", "d")
        assert spec.default_args == {"b": 2}
        assert spec.default_kwargs == {"d": 4}
        assert spec.varargs_name == "args"
        assert spec.varkwargs_name == "kwargs"
        assert spec.source is not None
        assert spec.source_body is not None

    def test_filter_kwargs_with_function_spec(self):
        """Test filter_kwargs using function obtained from spec."""

        def test_func(a, b, c=3):
            pass

        spec = get_fn_spec(test_func)
        args = get_fn_args(spec)

        kwargs = {"a": 1, "b": 2, "c": 3, "d": 4}

        # Create a mock function that accepts the args from spec
        def mock_func(**kw):
            pass

        # Manually set up the mock to accept the right args
        mock_func.__name__ = "mock_func"
        mock_func.__qualname__ = "mock_func"

        # Use the original function for filtering
        filtered = filter_kwargs(test_func, **kwargs)
        assert filtered == {"a": 1, "b": 2, "c": 3}
