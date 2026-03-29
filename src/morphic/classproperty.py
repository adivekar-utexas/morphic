"""Descriptor that allows properties to be accessed at the class level.

Supports ``@abstractmethod`` stacking: when ``@abstractmethod`` wraps a
``@classproperty``, ABC enforcement works exactly as it does for regular
abstract methods — subclasses that fail to override the classproperty cannot
be instantiated.

Usage::

    from abc import ABC, abstractmethod
    from morphic import classproperty

    class Base(ABC):
        @abstractmethod
        @classproperty
        def my_value(cls) -> int:
            pass

    class Concrete(Base):
        @classproperty
        def my_value(cls) -> int:
            return 42
"""


class classproperty(property):
    """Descriptor that allows properties to be accessed at the class level.

    A ``classproperty`` is the class-level analogue of Python's built-in
    ``@property``.  Where ``@property`` computes a value from an *instance*
    (``self``), ``@classproperty`` computes a value from the *class* (``cls``).
    The decorated function receives the class as its first argument — not an
    instance — and the result is available both on the class itself and on any
    instance of that class.

    ``classproperty`` inherits from the built-in ``property`` type.  The key
    difference is in ``__get__``: when Python resolves attribute access,
    ``property.__get__(obj=None, objtype=cls)`` returns the descriptor object
    itself (because there is no instance to pass to ``fget``), whereas
    ``classproperty.__get__`` passes the *class* to ``fget`` and returns the
    computed value.  This is what makes class-level access work.

    Basic usage::

        class Circle:
            _pi = 3.14159

            @classproperty
            def pi(cls) -> float:
                return cls._pi

        Circle.pi        # 3.14159  (class-level access)
        Circle().pi      # 3.14159  (instance-level access — same result)

    Class-level and instance-level access
    ======================================

    A ``classproperty`` is accessible from both the class and any instance of
    that class.  In both cases the decorated function receives the **class**
    (not the instance) as its first argument, so the return value is always
    the same regardless of which instance you access it through::

        class Config:
            _mode = "fast"

            @classproperty
            def mode(cls) -> str:
                return cls._mode

        # All three return the same value:
        Config.mode          # "fast"  (class-level)
        Config().mode        # "fast"  (instance-level)
        Config().mode        # "fast"  (different instance, same result)

    This holds true for all class types — plain classes, ``Typed``, ``Typed +
    Registry``, and ABC subclasses::

        from morphic import Typed

        class Metric(Typed):
            value: float

            @classproperty
            def display_range(cls) -> tuple:
                return (0.0, 1.0)

        Metric.display_range             # (0.0, 1.0)
        Metric(value=0.5).display_range  # (0.0, 1.0)

    When a subclass overrides a ``classproperty``, each class and its instances
    see their own version::

        class Accuracy(Metric):
            @classproperty
            def display_range(cls) -> tuple:
                return (0.0, 100.0)

        Metric.display_range                 # (0.0, 1.0)
        Metric(value=0.5).display_range      # (0.0, 1.0)
        Accuracy.display_range               # (0.0, 100.0)
        Accuracy(value=95.0).display_range   # (0.0, 100.0)

    Subclass polymorphism::

        class Base:
            @classproperty
            def tag(cls) -> str:
                return cls.__name__.lower()

        class Child(Base):
            pass

        Base.tag    # "base"
        Child.tag   # "child"  (cls is Child, not Base)

    Because the function receives the actual class through the MRO, subclasses
    automatically get their own ``cls`` without overriding anything.

    Overriding in subclasses::

        class Metric:
            @classproperty
            def display_range(cls) -> tuple:
                return (0.0, 1.0)

        class Perplexity(Metric):
            @classproperty
            def display_range(cls) -> tuple:
                return (0.0, float("inf"))

        Metric.display_range       # (0.0, 1.0)
        Perplexity.display_range   # (0.0, inf)

    Abstract classproperties
    ========================

    ``classproperty`` supports the standard ``@abstractmethod`` decorator from
    ``abc``.  The correct stacking order places ``@abstractmethod`` on the
    outside::

        from abc import ABC, abstractmethod

        class Base(ABC):
            @abstractmethod          # outer — marks the descriptor as abstract
            @classproperty           # inner — creates the descriptor
            def value(cls) -> int:
                pass

    With this stacking:

    - ``Base()`` raises ``TypeError`` ("Can't instantiate abstract class …").
    - A subclass that does **not** override ``value`` with a concrete
      ``@classproperty`` also raises ``TypeError`` on instantiation.
    - A subclass that overrides ``value`` with a concrete ``@classproperty``
      can be instantiated normally.

    This works identically for plain classes, ``Typed`` classes, and
    ``Typed + Registry`` classes::

        from morphic import Typed, Registry

        class Metric(Typed, Registry, ABC):
            value: float

            @abstractmethod
            @classproperty
            def display_range(cls) -> tuple:
                pass

        class Accuracy(Metric):
            aliases = ["acc"]

            @classproperty
            def display_range(cls) -> tuple:
                return (0.0, 1.0)

        Accuracy(value=0.95)                 # works
        Metric.of("acc", value=0.95)         # works via Registry

    Intermediate abstract classes can add more abstract classproperties
    without overriding existing ones::

        class Metric(ABC):
            @abstractmethod
            @classproperty
            def display_range(cls) -> tuple:
                pass

        class RankedMetric(Metric, ABC):
            @abstractmethod
            @classproperty
            def optimization_direction(cls) -> str:
                pass

        class Accuracy(RankedMetric):
            @classproperty
            def display_range(cls) -> tuple:
                return (0.0, 1.0)

            @classproperty
            def optimization_direction(cls) -> str:
                return "maximize"

    Grandchild classes that inherit from a concrete parent do **not** need to
    re-override the classproperty::

        class BinaryAccuracy(Accuracy):
            pass

        BinaryAccuracy.display_range  # (0.0, 1.0) — inherited

    Concrete classproperties on ABC classes
    =======================================

    An ABC can have **both** abstract and concrete classproperties.  A concrete
    ``@classproperty`` (without ``@abstractmethod``) on an ABC works exactly
    like a classproperty on any other class: it is inherited by all subclasses
    and is accessible from both the class and any instance.  Only the abstract
    classproperties require overriding::

        class Metric(ABC):
            @classproperty
            def api_version(cls) -> int:
                return 3                     # concrete — inherited as-is

            @abstractmethod
            @classproperty
            def display_range(cls) -> tuple:
                pass                         # abstract — must override

        class Accuracy(Metric):
            @classproperty
            def display_range(cls) -> tuple:
                return (0.0, 1.0)

        Accuracy.api_version               # 3      (inherited, class-level)
        Accuracy(value=0.95).api_version   # 3      (inherited, instance-level)
        Accuracy.display_range             # (0.0, 1.0)
        Accuracy(value=0.95).display_range # (0.0, 1.0)

    Concrete classproperties on ABCs participate in normal MRO-based
    polymorphism.  A classproperty that reads ``cls.__name__`` will return the
    actual subclass name when accessed on a child class or its instances::

        class Base(ABC):
            @classproperty
            def label(cls) -> str:
                return cls.__name__.lower()

            @abstractmethod
            def run(self) -> None:
                pass

        class Worker(Base):
            def run(self) -> None:
                pass

        Worker.label      # "worker"    (class-level)
        Worker().label    # "worker"    (instance-level)
        Base.label        # "base"      (class-level on the ABC itself)

    Subclasses can also override a concrete classproperty from an ABC parent::

        class FastWorker(Worker):
            @classproperty
            def label(cls) -> str:
                return "fast-" + cls.__name__.lower()

        FastWorker.label      # "fast-fastworker"
        FastWorker().label    # "fast-fastworker"
        Worker.label          # "worker" (unchanged)

    Decorator stacking order
    ========================

    Only one stacking order is correct::

        @abstractmethod          # outer
        @classproperty           # inner
        def value(cls) -> int:
            pass

    The reverse order (``@classproperty`` wrapping ``@abstractmethod``) does
    not raise an error, but silently defeats ABC enforcement: the
    ``classproperty`` executes ``fget`` on every ``getattr``, returning
    ``None`` from the abstract body, and ABCMeta sees a concrete value.
    Subclasses that forget to override will not be caught.

    Note:
        ``classproperty`` is used internally by ``Typed`` for built-in
        class-level properties: ``class_name``, ``param_names``,
        ``param_default_values``, and ``_constructor``.

    Reference:
        Original ``classproperty`` pattern:
        https://stackoverflow.com/a/13624858/4900327
    """

    # ======================
    # Implementation details
    # ======================

    # Two problems prevent naive ``@abstractmethod`` + ``@classproperty``
    # stacking from working with CPython's ``property``:

    # **Problem 1 — read-only ``__isabstractmethod__``:**
    # ``@abstractmethod`` stamps ``funcobj.__isabstractmethod__ = True`` on the
    # object it wraps.  CPython's ``property`` exposes ``__isabstractmethod__``
    # as a read-only C-level descriptor (delegating to ``fget.__isabstractmethod__``).
    # Writing to it raises ``AttributeError: attribute '__isabstractmethod__' of
    # 'property' objects is not writable``.

    # **Solution:** ``classproperty`` shadows the inherited C-level descriptor
    # with a Python-level ``@property``/``@setter`` pair backed by the instance
    # attribute ``_is_abstract``.  This makes ``__isabstractmethod__`` writable,
    # so ``@abstractmethod`` can set it.

    # **Problem 2 — ``__get__`` defeats ABCMeta enforcement:**
    # ABCMeta checks whether abstract methods are overridden by doing
    # ``value = getattr(cls, name)`` followed by
    # ``getattr(value, "__isabstractmethod__", False)``.  For a regular
    # ``property``, ``getattr(cls, name)`` with no instance returns the
    # descriptor object itself (because ``property.__get__(obj=None)`` returns
    # ``self``).  ABCMeta then sees ``descriptor.__isabstractmethod__ == True``
    # and knows the method is still abstract.

    # But ``classproperty.__get__`` is designed to execute ``fget(cls)`` even
    # when accessed on the class — that is its raison d'être.  So
    # ``getattr(SubClass, name)`` calls ``fget(SubClass)`` and returns a
    # concrete value (e.g. ``None`` from the abstract body).  ABCMeta sees a
    # plain value with no ``__isabstractmethod__`` attribute, concludes the
    # method is overridden, and allows instantiation.  The abstract contract
    # is silently broken.

    # **Solution:** ``__get__`` checks ``self._is_abstract``.  When ``True``,
    # it returns ``self`` (the descriptor) instead of executing ``fget``.  This
    # gives ABCMeta the descriptor it needs to see the abstract flag.  When a
    # subclass provides a concrete ``@classproperty`` (which has
    # ``_is_abstract = False``), ``__get__`` executes ``fget`` normally and
    # returns the computed value.

    # Instance-level storage for __isabstractmethod__.
    # CPython's property exposes __isabstractmethod__ as a read-only C-level
    # descriptor that delegates to fget.__isabstractmethod__.  We shadow it
    # with an instance attribute so that @abstractmethod (which does
    # ``funcobj.__isabstractmethod__ = True``) can write to it.
    _is_abstract: bool = False

    @property  # type: ignore[override]
    def __isabstractmethod__(self) -> bool:
        return self._is_abstract

    @__isabstractmethod__.setter
    def __isabstractmethod__(self, value: bool) -> None:
        self._is_abstract = value

    def __get__(self, obj, objtype=None):
        # When the classproperty is abstract, return the descriptor itself
        # rather than executing fget.  This is required so that ABCMeta's
        # enforcement loop (which does ``getattr(cls, name)`` and then checks
        # ``value.__isabstractmethod__``) can see the flag and correctly track
        # the method as unimplemented.
        #
        # For concrete (non-abstract) classproperties, execute fget as usual.
        if self._is_abstract:
            return self
        return super(classproperty, self).__get__(objtype)

    def __set__(self, obj, value):
        super(classproperty, self).__set__(type(obj), value)

    def __delete__(self, obj):
        super(classproperty, self).__delete__(type(obj))
