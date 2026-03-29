"""Comprehensive tests for classproperty descriptor."""

from abc import ABC, abstractmethod
from typing import ClassVar, Dict, List, Optional, Tuple

import pytest

from morphic import Typed, classproperty
from morphic.classproperty import classproperty as classproperty_direct_import
from morphic.registry import Registry

# ============================================================================
# PART 1: CURRENT BEHAVIOR — CONCRETE CLASSPROPERTIES (NO ABC, NO HIERARCHY)
# ============================================================================


class TestClasspropertyImports:
    """Verify classproperty is importable from all expected locations."""

    def test_import_from_morphic(self) -> None:
        from morphic import classproperty as cp

        assert cp is classproperty

    def test_import_from_morphic_classproperty(self) -> None:
        assert classproperty_direct_import is classproperty

    def test_import_from_morphic_typed(self) -> None:
        from morphic.typed import classproperty as cp

        assert cp is classproperty

    def test_is_subclass_of_property(self) -> None:
        assert issubclass(classproperty, property)

    def test_isinstance_of_property(self) -> None:
        @classproperty
        def dummy(cls) -> int:
            return 42

        assert isinstance(dummy, property)
        assert isinstance(dummy, classproperty)


class TestClasspropertyPlainClass:
    """Test classproperty on plain (non-Typed) classes."""

    def test_class_level_access(self) -> None:
        class MyClass:
            @classproperty
            def value(cls) -> int:
                return 42

        assert MyClass.value == 42

    def test_instance_level_access(self) -> None:
        class MyClass:
            @classproperty
            def value(cls) -> int:
                return 42

        instance = MyClass()
        assert instance.value == 42

    def test_class_and_instance_return_same_value(self) -> None:
        class MyClass:
            @classproperty
            def value(cls) -> int:
                return 42

        instance = MyClass()
        assert MyClass.value == instance.value == 42

    def test_returns_class_not_instance(self) -> None:
        class MyClass:
            @classproperty
            def who(cls) -> str:
                return cls.__name__

        assert MyClass.who == "MyClass"
        assert MyClass().who == "MyClass"

    def test_reads_class_attribute(self) -> None:
        class MyClass:
            _data: str = "hello"

            @classproperty
            def data(cls) -> str:
                return cls._data

        assert MyClass.data == "hello"

    def test_different_subclasses_get_own_cls(self) -> None:
        class Base:
            @classproperty
            def who(cls) -> str:
                return cls.__name__

        class ChildA(Base):
            pass

        class ChildB(Base):
            pass

        assert Base.who == "Base"
        assert ChildA.who == "ChildA"
        assert ChildB.who == "ChildB"
        assert Base().who == "Base"
        assert ChildA().who == "ChildA"
        assert ChildB().who == "ChildB"

    def test_subclass_overrides_classproperty(self) -> None:
        class Base:
            @classproperty
            def value(cls) -> int:
                return 10

        class Child(Base):
            @classproperty
            def value(cls) -> int:
                return 20

        assert Base.value == 10
        assert Child.value == 20
        assert Base().value == 10
        assert Child().value == 20

    def test_subclass_inherits_classproperty(self) -> None:
        class Base:
            _factor: int = 2

            @classproperty
            def doubled(cls) -> int:
                return cls._factor * 2

        class Child(Base):
            _factor: int = 5

        assert Base.doubled == 4
        assert Child.doubled == 10
        assert Base().doubled == 4
        assert Child().doubled == 10

    def test_returns_complex_types(self) -> None:
        class MyClass:
            @classproperty
            def score_range(cls) -> Tuple[float, float]:
                return (0.0, 1.0)

            @classproperty
            def tags(cls) -> List[str]:
                return ["a", "b", "c"]

            @classproperty
            def config(cls) -> Dict[str, int]:
                return {"x": 1, "y": 2}

        instance = MyClass()
        assert MyClass.score_range == (0.0, 1.0)
        assert instance.score_range == (0.0, 1.0)
        assert MyClass.tags == ["a", "b", "c"]
        assert instance.tags == ["a", "b", "c"]
        assert MyClass.config == {"x": 1, "y": 2}
        assert instance.config == {"x": 1, "y": 2}

    def test_returns_none(self) -> None:
        class MyClass:
            @classproperty
            def nothing(cls) -> None:
                return None

        assert MyClass.nothing is None
        assert MyClass().nothing is None

    def test_returns_class_itself(self) -> None:
        class MyClass:
            @classproperty
            def constructor(cls):
                return cls

        assert MyClass.constructor is MyClass
        assert MyClass().constructor is MyClass

    def test_multiple_classproperties(self) -> None:
        class MyClass:
            @classproperty
            def a(cls) -> int:
                return 1

            @classproperty
            def b(cls) -> str:
                return "two"

            @classproperty
            def c(cls) -> float:
                return 3.0

        instance = MyClass()
        assert MyClass.a == 1
        assert MyClass.b == "two"
        assert MyClass.c == 3.0
        assert instance.a == 1
        assert instance.b == "two"
        assert instance.c == 3.0

    def test_classproperty_with_classvar(self) -> None:
        class MyClass:
            _items: ClassVar[List[str]] = ["x", "y"]

            @classproperty
            def items(cls) -> List[str]:
                return cls._items

        assert MyClass.items == ["x", "y"]

    def test_classproperty_raises_exception(self) -> None:
        class MyClass:
            @classproperty
            def explodes(cls) -> int:
                raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            _ = MyClass.explodes

    def test_classproperty_on_instance_raises_exception(self) -> None:
        class MyClass:
            @classproperty
            def explodes(cls) -> int:
                raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            _ = MyClass().explodes


class TestClasspropertyTyped:
    """Test classproperty on Typed classes (no hierarchy)."""

    def test_typed_builtin_class_name(self) -> None:
        class User(Typed):
            name: str

        assert User.class_name == "User"
        user: User = User(name="John")
        assert user.class_name == "User"

    def test_typed_builtin_class_name_on_subclass(self) -> None:
        class Base(Typed):
            name: str

        class Child(Base):
            pass

        assert Base.class_name == "Base"
        assert Child.class_name == "Child"
        assert Base(name="b").class_name == "Base"
        assert Child(name="c").class_name == "Child"

    def test_typed_builtin_param_names(self) -> None:
        class User(Typed):
            name: str
            age: int
            email: Optional[str] = None

        assert User.param_names == {"name", "age", "email"}
        user: User = User(name="John", age=30)
        assert user.param_names == {"name", "age", "email"}

    def test_typed_builtin_param_names_on_instance(self) -> None:
        class User(Typed):
            name: str
            age: int

        user: User = User(name="John", age=30)
        assert user.param_names == {"name", "age"}

    def test_typed_builtin_param_default_values(self) -> None:
        class Config(Typed):
            name: str
            retries: int = 3
            active: bool = True

        defaults: Dict = Config.param_default_values
        assert defaults == {"retries": 3, "active": True}
        assert "name" not in defaults
        instance_defaults: Dict = Config(name="x").param_default_values
        assert instance_defaults == {"retries": 3, "active": True}

    def test_typed_builtin_constructor(self) -> None:
        class User(Typed):
            name: str

        assert User._constructor is User
        assert User(name="x")._constructor is User

    def test_custom_classproperty_on_typed(self) -> None:
        class Metric(Typed):
            value: float

            @classproperty
            def display_range(cls) -> Tuple[float, float]:
                return (0.0, 1.0)

        assert Metric.display_range == (0.0, 1.0)
        m: Metric = Metric(value=0.5)
        assert m.display_range == (0.0, 1.0)

    def test_custom_classproperty_sees_subclass(self) -> None:
        class Base(Typed):
            name: str

            @classproperty
            def who(cls) -> str:
                return cls.__name__

        class Child(Base):
            pass

        assert Base.who == "Base"
        assert Child.who == "Child"
        assert Child(name="x").who == "Child"

    def test_subclass_overrides_custom_classproperty(self) -> None:
        class Base(Typed):
            name: str

            @classproperty
            def score_range(cls) -> Tuple[float, float]:
                return (0.0, 1.0)

        class Child(Base):
            @classproperty
            def score_range(cls) -> Tuple[float, float]:
                return (0.0, float("inf"))

        assert Base.score_range == (0.0, 1.0)
        assert Child.score_range == (0.0, float("inf"))
        assert Base(name="b").score_range == (0.0, 1.0)
        assert Child(name="c").score_range == (0.0, float("inf"))

    def test_classproperty_uses_subclass_classvar(self) -> None:
        class Base(Typed):
            name: str
            _decimals: ClassVar[int] = 3

            @classproperty
            def decimals(cls) -> int:
                return cls._decimals

        class Child(Base):
            _decimals: ClassVar[int] = 1

        assert Base.decimals == 3
        assert Child.decimals == 1
        assert Base(name="b").decimals == 3
        assert Child(name="c").decimals == 1


class TestClasspropertyTypedRegistry:
    """Test classproperty on Typed + Registry classes."""

    def test_classproperty_with_registry(self) -> None:
        class Animal(Typed, Registry):
            name: str

            @classproperty
            def species(cls) -> str:
                return "unknown"

        class Dog(Animal):
            aliases: ClassVar[List[str]] = ["dog"]

            @classproperty
            def species(cls) -> str:
                return "canine"

        assert Dog.species == "canine"
        d: Dog = Dog(name="Rex")
        assert d.species == "canine"

    def test_classproperty_via_registry_lookup(self) -> None:
        class Shape(Typed, Registry):
            @classproperty
            def sides(cls) -> int:
                return 0

        class Triangle(Shape):
            aliases: ClassVar[List[str]] = ["tri"]

            @classproperty
            def sides(cls) -> int:
                return 3

        t: Shape = Shape.of("tri")
        assert t.sides == 3
        assert Triangle.sides == 3


# ============================================================================
# PART 2: ABSTRACT CLASSPROPERTY WITH ABC
# ============================================================================


class TestAbstractClasspropertyPlainClass:
    """Test @abstractmethod + @classproperty on plain (non-Typed) ABC classes."""

    def test_abstract_classproperty_prevents_instantiation(self) -> None:
        class Base(ABC):
            @abstractmethod
            @classproperty
            def value(cls) -> int:
                pass

        with pytest.raises(TypeError, match="abstract"):
            Base()

    def test_bad_child_cannot_be_instantiated(self) -> None:
        class Base(ABC):
            @abstractmethod
            @classproperty
            def value(cls) -> int:
                pass

        class BadChild(Base):
            pass

        with pytest.raises(TypeError, match="abstract"):
            BadChild()

    def test_good_child_can_be_instantiated(self) -> None:
        class Base(ABC):
            @abstractmethod
            @classproperty
            def value(cls) -> int:
                pass

        class GoodChild(Base):
            @classproperty
            def value(cls) -> int:
                return 42

        child: GoodChild = GoodChild()
        assert GoodChild.value == 42
        assert child.value == 42

    def test_abstract_classproperty_class_access_on_good_child(self) -> None:
        class Base(ABC):
            @abstractmethod
            @classproperty
            def score_range(cls) -> Tuple[float, float]:
                pass

        class Concrete(Base):
            @classproperty
            def score_range(cls) -> Tuple[float, float]:
                return (0.0, 1.0)

        assert Concrete.score_range == (0.0, 1.0)
        assert Concrete().score_range == (0.0, 1.0)

    def test_accessing_abstract_classproperty_on_base_returns_descriptor(self) -> None:
        class Base(ABC):
            @abstractmethod
            @classproperty
            def value(cls) -> int:
                pass

        result = Base.value
        assert isinstance(result, classproperty)

    def test_accessing_abstract_classproperty_on_bad_child_returns_descriptor(self) -> None:
        class Base(ABC):
            @abstractmethod
            @classproperty
            def value(cls) -> int:
                pass

        class BadChild(Base):
            pass

        result = BadChild.value
        assert isinstance(result, classproperty)

    def test_multiple_abstract_classproperties(self) -> None:
        class Base(ABC):
            @abstractmethod
            @classproperty
            def a(cls) -> int:
                pass

            @abstractmethod
            @classproperty
            def b(cls) -> str:
                pass

        class PartialChild(Base):
            @classproperty
            def a(cls) -> int:
                return 1

        with pytest.raises(TypeError, match="abstract"):
            PartialChild()

        class FullChild(Base):
            @classproperty
            def a(cls) -> int:
                return 1

            @classproperty
            def b(cls) -> str:
                return "two"

        child: FullChild = FullChild()
        assert child.a == 1
        assert child.b == "two"
        assert FullChild.a == 1
        assert FullChild.b == "two"

    def test_mix_abstract_classproperty_and_abstract_method(self) -> None:
        class Base(ABC):
            @abstractmethod
            @classproperty
            def range(cls) -> Tuple[float, float]:
                pass

            @abstractmethod
            def compute(self) -> float:
                pass

        class OnlyProp(Base):
            @classproperty
            def range(cls) -> Tuple[float, float]:
                return (0.0, 1.0)

        with pytest.raises(TypeError, match="abstract"):
            OnlyProp()

        class OnlyMethod(Base):
            def compute(self) -> float:
                return 0.5

        with pytest.raises(TypeError, match="abstract"):
            OnlyMethod()

        class Complete(Base):
            @classproperty
            def range(cls) -> Tuple[float, float]:
                return (0.0, 1.0)

            def compute(self) -> float:
                return 0.5

        c: Complete = Complete()
        assert Complete.range == (0.0, 1.0)
        assert c.range == (0.0, 1.0)
        assert c.compute() == 0.5

    def test_grandchild_inherits_override(self) -> None:
        class Base(ABC):
            @abstractmethod
            @classproperty
            def value(cls) -> int:
                pass

        class Middle(Base):
            @classproperty
            def value(cls) -> int:
                return 10

        class GrandChild(Middle):
            pass

        assert GrandChild.value == 10
        gc: GrandChild = GrandChild()
        assert gc.value == 10

    def test_grandchild_re_overrides(self) -> None:
        class Base(ABC):
            @abstractmethod
            @classproperty
            def value(cls) -> int:
                pass

        class Middle(Base):
            @classproperty
            def value(cls) -> int:
                return 10

        class GrandChild(Middle):
            @classproperty
            def value(cls) -> int:
                return 99

        assert Middle.value == 10
        assert Middle().value == 10
        assert GrandChild.value == 99
        assert GrandChild().value == 99

    def test_intermediate_abstract_class(self) -> None:
        class Base(ABC):
            @abstractmethod
            @classproperty
            def value(cls) -> int:
                pass

        class MiddleABC(Base, ABC):
            @abstractmethod
            def compute(self) -> float:
                pass

        with pytest.raises(TypeError, match="abstract"):
            MiddleABC()

        class Concrete(MiddleABC):
            @classproperty
            def value(cls) -> int:
                return 42

            def compute(self) -> float:
                return 3.14

        c: Concrete = Concrete()
        assert c.value == 42
        assert Concrete.value == 42
        assert c.compute() == 3.14

    def test_deep_hierarchy(self) -> None:
        class L0(ABC):
            @abstractmethod
            @classproperty
            def tag(cls) -> str:
                pass

        class L1(L0, ABC):
            @abstractmethod
            @classproperty
            def priority(cls) -> int:
                pass

        class L2(L1):
            @classproperty
            def tag(cls) -> str:
                return "l2"

            @classproperty
            def priority(cls) -> int:
                return 1

        class L3(L2):
            pass

        assert L2.tag == "l2"
        assert L2.priority == 1
        assert L3.tag == "l2"
        assert L3.priority == 1
        l2: L2 = L2()
        l3: L3 = L3()
        assert l2.tag == "l2"
        assert l2.priority == 1
        assert l3.tag == "l2"
        assert l3.priority == 1

        with pytest.raises(TypeError, match="abstract"):
            L1()

    def test_abstract_classproperties_tracked_in_dunder(self) -> None:
        class Base(ABC):
            @abstractmethod
            @classproperty
            def value(cls) -> int:
                pass

        assert "value" in Base.__abstractmethods__

        class BadChild(Base):
            pass

        assert "value" in BadChild.__abstractmethods__

        class GoodChild(Base):
            @classproperty
            def value(cls) -> int:
                return 1

        assert len(GoodChild.__abstractmethods__) == 0


class TestConcreteClasspropertyOnABC:
    """Test non-abstract @classproperty on ABC classes.

    An ABC can have concrete (non-abstract) classproperties alongside abstract
    methods.  These should work from both class-level and instance-level access
    on the ABC's concrete subclasses.
    """

    def test_concrete_classproperty_on_plain_abc(self) -> None:
        class Base(ABC):
            @classproperty
            def version(cls) -> str:
                return "1.0"

            @abstractmethod
            def compute(self) -> float:
                pass

        class Child(Base):
            def compute(self) -> float:
                return 42.0

        assert Child.version == "1.0"
        child: Child = Child()
        assert child.version == "1.0"

    def test_concrete_classproperty_inherited_through_abc_chain(self) -> None:
        class Base(ABC):
            @classproperty
            def tag(cls) -> str:
                return cls.__name__.lower()

            @abstractmethod
            def run(self) -> None:
                pass

        class Middle(Base, ABC):
            @abstractmethod
            def extra(self) -> int:
                pass

        class Leaf(Middle):
            def run(self) -> None:
                pass

            def extra(self) -> int:
                return 1

        assert Base.tag == "base"
        assert Middle.tag == "middle"
        assert Leaf.tag == "leaf"
        leaf: Leaf = Leaf()
        assert leaf.tag == "leaf"

    def test_concrete_classproperty_overridden_in_child_of_abc(self) -> None:
        class Base(ABC):
            @classproperty
            def mode(cls) -> str:
                return "default"

            @abstractmethod
            def go(self) -> None:
                pass

        class Child(Base):
            @classproperty
            def mode(cls) -> str:
                return "fast"

            def go(self) -> None:
                pass

        assert Base.mode == "default"
        assert Child.mode == "fast"
        assert Child().mode == "fast"

    def test_mix_abstract_and_concrete_classproperties_on_abc(self) -> None:
        class Base(ABC):
            @abstractmethod
            @classproperty
            def must_override(cls) -> int:
                pass

            @classproperty
            def free_for_all(cls) -> str:
                return f"from-{cls.__name__}"

        class Child(Base):
            @classproperty
            def must_override(cls) -> int:
                return 99

        assert Child.must_override == 99
        assert Child.free_for_all == "from-Child"
        child: Child = Child()
        assert child.must_override == 99
        assert child.free_for_all == "from-Child"

    def test_concrete_classproperty_on_typed_abc(self) -> None:
        class Base(Typed, ABC):
            name: str

            @classproperty
            def version(cls) -> str:
                return "2.0"

            @abstractmethod
            @classproperty
            def kind(cls) -> str:
                pass

        class Child(Base):
            @classproperty
            def kind(cls) -> str:
                return "child"

        assert Child.version == "2.0"
        assert Child.kind == "child"
        child: Child = Child(name="c")
        assert child.version == "2.0"
        assert child.kind == "child"
        assert child.class_name == "Child"

    def test_concrete_classproperty_on_typed_registry_abc(self) -> None:
        class Handler(Typed, Registry, ABC):
            @classproperty
            def api_version(cls) -> int:
                return 3

            @abstractmethod
            @classproperty
            def handler_name(cls) -> str:
                pass

        class WebHandler(Handler):
            aliases: ClassVar[List[str]] = ["web"]

            @classproperty
            def handler_name(cls) -> str:
                return "web"

        assert WebHandler.api_version == 3
        assert WebHandler.handler_name == "web"
        wh: Handler = Handler.of("web")
        assert wh.api_version == 3
        assert wh.handler_name == "web"

    def test_grandchild_inherits_concrete_classproperty_from_abc(self) -> None:
        class Base(ABC):
            @classproperty
            def label(cls) -> str:
                return cls.__name__

            @abstractmethod
            def work(self) -> None:
                pass

        class Middle(Base):
            def work(self) -> None:
                pass

        class GrandChild(Middle):
            pass

        assert GrandChild.label == "GrandChild"
        assert GrandChild().label == "GrandChild"
        assert Middle.label == "Middle"
        assert Middle().label == "Middle"


class TestAbstractClasspropertyTyped:
    """Test @abstractmethod + @classproperty on Typed ABC classes."""

    def test_typed_abstract_classproperty_prevents_instantiation(self) -> None:
        class Base(Typed, ABC):
            name: str

            @abstractmethod
            @classproperty
            def display_range(cls) -> Tuple[float, float]:
                pass

        with pytest.raises(TypeError, match="abstract"):
            Base(name="x")

    def test_typed_bad_child_cannot_be_instantiated(self) -> None:
        class Base(Typed, ABC):
            name: str

            @abstractmethod
            @classproperty
            def display_range(cls) -> Tuple[float, float]:
                pass

        class BadChild(Base):
            pass

        with pytest.raises(TypeError, match="abstract"):
            BadChild(name="x")

    def test_typed_good_child_works(self) -> None:
        class Base(Typed, ABC):
            name: str

            @abstractmethod
            @classproperty
            def display_range(cls) -> Tuple[float, float]:
                pass

        class GoodChild(Base):
            @classproperty
            def display_range(cls) -> Tuple[float, float]:
                return (0.0, 1.0)

        child: GoodChild = GoodChild(name="test")
        assert GoodChild.display_range == (0.0, 1.0)
        assert child.display_range == (0.0, 1.0)

    def test_typed_builtin_classproperties_still_work(self) -> None:
        class Base(Typed, ABC):
            name: str

            @abstractmethod
            @classproperty
            def display_range(cls) -> Tuple[float, float]:
                pass

        class Child(Base):
            @classproperty
            def display_range(cls) -> Tuple[float, float]:
                return (0.0, 100.0)

        assert Child.class_name == "Child"
        assert "name" in Child.param_names
        child: Child = Child(name="test")
        assert child.class_name == "Child"
        assert child.param_names == {"name"}

    def test_typed_grandchild_inherits(self) -> None:
        class Base(Typed, ABC):
            name: str

            @abstractmethod
            @classproperty
            def display_range(cls) -> Tuple[float, float]:
                pass

        class Middle(Base):
            @classproperty
            def display_range(cls) -> Tuple[float, float]:
                return (0.0, 1.0)

        class GrandChild(Middle):
            pass

        gc: GrandChild = GrandChild(name="gc")
        assert gc.display_range == (0.0, 1.0)
        assert GrandChild.display_range == (0.0, 1.0)

    def test_typed_multiple_abstract_classproperties(self) -> None:
        class Metric(Typed, ABC):
            value: float

            @abstractmethod
            @classproperty
            def display_range(cls) -> Tuple[float, float]:
                pass

            @abstractmethod
            @classproperty
            def optimization_direction(cls) -> str:
                pass

        class Accuracy(Metric):
            @classproperty
            def display_range(cls) -> Tuple[float, float]:
                return (0.0, 1.0)

            @classproperty
            def optimization_direction(cls) -> str:
                return "maximize"

        a: Accuracy = Accuracy(value=0.95)
        assert a.display_range == (0.0, 1.0)
        assert a.optimization_direction == "maximize"
        assert Accuracy.display_range == (0.0, 1.0)
        assert Accuracy.optimization_direction == "maximize"

    def test_typed_partial_override_still_abstract(self) -> None:
        class Metric(Typed, ABC):
            value: float

            @abstractmethod
            @classproperty
            def display_range(cls) -> Tuple[float, float]:
                pass

            @abstractmethod
            @classproperty
            def direction(cls) -> str:
                pass

        class Partial(Metric):
            @classproperty
            def display_range(cls) -> Tuple[float, float]:
                return (0.0, 1.0)

        with pytest.raises(TypeError, match="abstract"):
            Partial(value=0.5)

    def test_typed_intermediate_abc(self) -> None:
        class Base(Typed, ABC):
            name: str

            @abstractmethod
            @classproperty
            def tag(cls) -> str:
                pass

        class MiddleABC(Base, ABC):
            @abstractmethod
            @classproperty
            def priority(cls) -> int:
                pass

        with pytest.raises(TypeError, match="abstract"):
            MiddleABC(name="m")

        class Leaf(MiddleABC):
            @classproperty
            def tag(cls) -> str:
                return "leaf"

            @classproperty
            def priority(cls) -> int:
                return 1

        leaf: Leaf = Leaf(name="test")
        assert leaf.tag == "leaf"
        assert leaf.priority == 1


class TestAbstractClasspropertyTypedRegistry:
    """Test @abstractmethod + @classproperty on Typed + Registry ABC classes."""

    def test_registry_abstract_classproperty(self) -> None:
        class Metric(Typed, Registry, ABC):
            value: float

            @abstractmethod
            @classproperty
            def display_range(cls) -> Tuple[float, float]:
                pass

        class Accuracy(Metric):
            aliases: ClassVar[List[str]] = ["acc"]

            @classproperty
            def display_range(cls) -> Tuple[float, float]:
                return (0.0, 1.0)

        a: Accuracy = Accuracy(value=0.95)
        assert a.display_range == (0.0, 1.0)
        assert Accuracy.display_range == (0.0, 1.0)

    def test_registry_lookup_with_abstract_classproperty(self) -> None:
        class Scorer(Typed, Registry, ABC):
            @abstractmethod
            @classproperty
            def max_score(cls) -> float:
                pass

        class PercentScorer(Scorer):
            aliases: ClassVar[List[str]] = ["percent"]

            @classproperty
            def max_score(cls) -> float:
                return 100.0

        s: Scorer = Scorer.of("percent")
        assert s.max_score == 100.0

    def test_registry_bad_child_cannot_instantiate(self) -> None:
        class Scorer2(Typed, Registry, ABC):
            @abstractmethod
            @classproperty
            def max_score(cls) -> float:
                pass

        class BadScorer(Scorer2):
            aliases: ClassVar[List[str]] = ["bad"]

        with pytest.raises(TypeError, match="abstract"):
            BadScorer()


# ============================================================================
# PART 3: EDGE CASES AND INTERACTION PATTERNS
# ============================================================================


class TestClasspropertyEdgeCases:
    """Edge cases and unusual patterns."""

    def test_classproperty_returns_mutable_object(self) -> None:
        class MyClass:
            @classproperty
            def items(cls) -> List[int]:
                return [1, 2, 3]

        a: List[int] = MyClass.items
        b: List[int] = MyClass.items
        assert a == b
        assert a is not b

    def test_classproperty_with_no_return_annotation(self) -> None:
        class MyClass:
            @classproperty
            def value(cls):
                return "no annotation"

        assert MyClass.value == "no annotation"

    def test_classproperty_fget_attribute(self) -> None:
        class MyClass:
            @classproperty
            def value(cls) -> int:
                return 42

        descriptor = MyClass.__dict__["value"]
        assert isinstance(descriptor, classproperty)
        assert descriptor.fget is not None
        assert callable(descriptor.fget)

    def test_non_abstract_classproperty_does_not_have_isabstractmethod(self) -> None:
        @classproperty
        def value(cls) -> int:
            return 42

        assert not getattr(value, "__isabstractmethod__", False)

    def test_abstract_classproperty_has_isabstractmethod(self) -> None:
        @abstractmethod
        @classproperty
        def value(cls) -> int:
            pass

        assert getattr(value, "__isabstractmethod__", False) is True

    def test_classproperty_on_diamond_inheritance(self) -> None:
        class A:
            @classproperty
            def val(cls) -> str:
                return f"A({cls.__name__})"

        class B(A):
            pass

        class C(A):
            @classproperty
            def val(cls) -> str:
                return f"C({cls.__name__})"

        class D(B, C):
            pass

        # D's MRO: D -> B -> C -> A. First classproperty found is C's.
        assert D.val == "C(D)"
        # B's MRO: B -> A. B doesn't know about C.
        assert B.val == "A(B)"
        assert C.val == "C(C)"
        assert A.val == "A(A)"

    def test_abstract_classproperty_diamond_inheritance(self) -> None:
        class A(ABC):
            @abstractmethod
            @classproperty
            def val(cls) -> int:
                pass

        class B(A):
            @classproperty
            def val(cls) -> int:
                return 10

        class C(A):
            @classproperty
            def val(cls) -> int:
                return 20

        class D(B, C):
            pass

        d: D = D()
        assert D.val == 10
        assert d.val == 10


# ============================================================================
# PART 4: DEEP MULTI-LEVEL ABC HIERARCHIES
# ============================================================================


class TestDeepABCHierarchies:
    """Test abstract classproperties across deep, multi-level ABC hierarchies.

    These tests verify that enforcement, inheritance, and access all work
    correctly when abstract classproperties are introduced and overridden
    at different levels of a class tree that is 3+ ABCs deep.
    """

    def test_override_split_across_levels(self) -> None:
        """Each abstract classproperty is overridden at a different level."""

        class L0(ABC):
            @abstractmethod
            @classproperty
            def alpha(cls) -> str:
                pass

        class L1(L0, ABC):
            @abstractmethod
            @classproperty
            def beta(cls) -> int:
                pass

        class L2(L1, ABC):
            @abstractmethod
            @classproperty
            def gamma(cls) -> float:
                pass

            @classproperty
            def alpha(cls) -> str:
                return "overridden-at-L2"

        # L2 overrides alpha but not beta or gamma — still abstract
        with pytest.raises(TypeError, match="abstract"):
            L2()

        class L3(L2):
            @classproperty
            def beta(cls) -> int:
                return 42

        # L3 overrides beta but inherits gamma as abstract — still abstract
        with pytest.raises(TypeError, match="abstract"):
            L3()

        class L4(L3):
            @classproperty
            def gamma(cls) -> float:
                return 3.14

        # L4 has all three overridden (alpha from L2, beta from L3, gamma from L4)
        obj: L4 = L4()
        assert L4.alpha == "overridden-at-L2"
        assert L4.beta == 42
        assert L4.gamma == 3.14
        assert obj.alpha == "overridden-at-L2"
        assert obj.beta == 42
        assert obj.gamma == 3.14

    def test_each_abc_level_adds_abstract_and_concrete(self) -> None:
        """Each ABC level adds both an abstract classproperty and a concrete one."""

        class L0(ABC):
            @abstractmethod
            @classproperty
            def abstract_a(cls) -> str:
                pass

            @classproperty
            def concrete_a(cls) -> str:
                return f"concrete_a({cls.__name__})"

        class L1(L0, ABC):
            @abstractmethod
            @classproperty
            def abstract_b(cls) -> str:
                pass

            @classproperty
            def concrete_b(cls) -> str:
                return f"concrete_b({cls.__name__})"

        class L2(L1, ABC):
            @abstractmethod
            @classproperty
            def abstract_c(cls) -> str:
                pass

            @classproperty
            def concrete_c(cls) -> str:
                return f"concrete_c({cls.__name__})"

        # All intermediate ABCs are not instantiable
        with pytest.raises(TypeError, match="abstract"):
            L0()
        with pytest.raises(TypeError, match="abstract"):
            L1()
        with pytest.raises(TypeError, match="abstract"):
            L2()

        # But their concrete classproperties are accessible at class level
        assert L0.concrete_a == "concrete_a(L0)"
        assert L1.concrete_a == "concrete_a(L1)"
        assert L1.concrete_b == "concrete_b(L1)"
        assert L2.concrete_a == "concrete_a(L2)"
        assert L2.concrete_b == "concrete_b(L2)"
        assert L2.concrete_c == "concrete_c(L2)"

        class Leaf(L2):
            @classproperty
            def abstract_a(cls) -> str:
                return "a"

            @classproperty
            def abstract_b(cls) -> str:
                return "b"

            @classproperty
            def abstract_c(cls) -> str:
                return "c"

        leaf: Leaf = Leaf()
        assert leaf.abstract_a == "a"
        assert leaf.abstract_b == "b"
        assert leaf.abstract_c == "c"
        assert leaf.concrete_a == "concrete_a(Leaf)"
        assert leaf.concrete_b == "concrete_b(Leaf)"
        assert leaf.concrete_c == "concrete_c(Leaf)"
        assert Leaf.abstract_a == "a"
        assert Leaf.concrete_a == "concrete_a(Leaf)"

    def test_intermediate_abcs_cannot_instantiate_but_class_access_works(self) -> None:
        """Every intermediate ABC is blocked from instantiation, but its concrete
        classproperties are still accessible at the class level."""

        class A(ABC):
            @abstractmethod
            @classproperty
            def required(cls) -> int:
                pass

            @classproperty
            def version(cls) -> str:
                return "1.0"

        class B(A, ABC):
            @classproperty
            def extra(cls) -> str:
                return "from-B"

        class C(B, ABC):
            pass

        with pytest.raises(TypeError, match="abstract"):
            A()
        with pytest.raises(TypeError, match="abstract"):
            B()
        with pytest.raises(TypeError, match="abstract"):
            C()

        assert A.version == "1.0"
        assert B.version == "1.0"
        assert B.extra == "from-B"
        assert C.version == "1.0"
        assert C.extra == "from-B"

        class D(C):
            @classproperty
            def required(cls) -> int:
                return 99

        d: D = D()
        assert d.required == 99
        assert d.version == "1.0"
        assert d.extra == "from-B"
        assert D.required == 99
        assert D.version == "1.0"
        assert D.extra == "from-B"

    def test_deep_typed_hierarchy(self) -> None:
        """Four-level Typed + ABC hierarchy with abstract classproperties."""

        class L0(Typed, ABC):
            name: str

            @abstractmethod
            @classproperty
            def kind(cls) -> str:
                pass

        class L1(L0, ABC):
            @abstractmethod
            @classproperty
            def priority(cls) -> int:
                pass

        class L2(L1):
            @classproperty
            def kind(cls) -> str:
                return "base-kind"

            @classproperty
            def priority(cls) -> int:
                return 0

        class L3(L2):
            @classproperty
            def priority(cls) -> int:
                return 10

        with pytest.raises(TypeError, match="abstract"):
            L0(name="x")
        with pytest.raises(TypeError, match="abstract"):
            L1(name="x")

        l2: L2 = L2(name="two")
        assert l2.kind == "base-kind"
        assert l2.priority == 0
        assert L2.kind == "base-kind"
        assert L2.priority == 0
        assert l2.class_name == "L2"

        l3: L3 = L3(name="three")
        assert l3.kind == "base-kind"
        assert l3.priority == 10
        assert L3.kind == "base-kind"
        assert L3.priority == 10
        assert l3.class_name == "L3"

    def test_multiple_inheritance_two_abc_branches(self) -> None:
        """Concrete class inherits from two separate ABC branches, each
        contributing an abstract classproperty."""

        class BranchA(ABC):
            @abstractmethod
            @classproperty
            def from_a(cls) -> str:
                pass

        class BranchB(ABC):
            @abstractmethod
            @classproperty
            def from_b(cls) -> int:
                pass

        class Merged(BranchA, BranchB):
            @classproperty
            def from_a(cls) -> str:
                return "a-value"

            @classproperty
            def from_b(cls) -> int:
                return 7

        m: Merged = Merged()
        assert Merged.from_a == "a-value"
        assert Merged.from_b == 7
        assert m.from_a == "a-value"
        assert m.from_b == 7

        # Missing one branch's override
        class PartialMerge(BranchA, BranchB):
            @classproperty
            def from_a(cls) -> str:
                return "ok"

        with pytest.raises(TypeError, match="abstract"):
            PartialMerge()

    def test_five_level_abc_chain_with_typed_registry(self) -> None:
        """Five-level chain: Typed + Registry + ABC with abstract classproperties
        added at different levels, overridden at different levels."""

        class L0_5L(Typed, Registry, ABC):
            name: str

            @abstractmethod
            @classproperty
            def category(cls) -> str:
                pass

        class L1_5L(L0_5L, ABC):
            @abstractmethod
            @classproperty
            def sub_category(cls) -> str:
                pass

            @classproperty
            def category(cls) -> str:
                return "general"

        class L2_5L(L1_5L, ABC):
            @abstractmethod
            @classproperty
            def detail(cls) -> str:
                pass

        class L3_5L(L2_5L):
            aliases: ClassVar[List[str]] = ["five_level_l3"]

            @classproperty
            def sub_category(cls) -> str:
                return "specific"

            @classproperty
            def detail(cls) -> str:
                return "fine-grained"

        class L4_5L(L3_5L):
            aliases: ClassVar[List[str]] = ["five_level_l4"]

            @classproperty
            def detail(cls) -> str:
                return "ultra-fine"

        with pytest.raises(TypeError, match="abstract"):
            L0_5L(name="x")
        with pytest.raises(TypeError, match="abstract"):
            L1_5L(name="x")
        with pytest.raises(TypeError, match="abstract"):
            L2_5L(name="x")

        l3: L3_5L = L3_5L(name="three")
        assert l3.category == "general"
        assert l3.sub_category == "specific"
        assert l3.detail == "fine-grained"
        assert L3_5L.category == "general"
        assert L3_5L.sub_category == "specific"
        assert L3_5L.detail == "fine-grained"

        l4: L4_5L = L4_5L(name="four")
        assert l4.category == "general"
        assert l4.sub_category == "specific"
        assert l4.detail == "ultra-fine"
        assert L4_5L.category == "general"
        assert L4_5L.detail == "ultra-fine"

        via_registry: L0_5L = L0_5L.of("five_level_l3", name="reg")
        assert via_registry.category == "general"
        assert via_registry.sub_category == "specific"
        assert via_registry.detail == "fine-grained"
