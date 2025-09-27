"""Fast fuzzy-matched enums with aliases and type safety."""

import re
import threading
import warnings
from enum import Enum, auto
from functools import lru_cache
from typing import Any, Dict, List, Optional, Set, Tuple, Union


class alias(auto):
    """Create an alias for AutoEnum members with fuzzy matching support."""

    def __init__(self, *aliases):
        if len(aliases) == 0:
            raise ValueError("Cannot have empty alias() call.")
        for a in aliases:
            if not isinstance(a, str):
                raise ValueError(
                    f"All aliases must be strings; found alias of type {type(a)} having value: {a}"
                )
        self.names = aliases
        self.enum_name = None

    def __repr__(self) -> str:
        return str(self)

    def __str__(self):
        if self.enum_name is not None:
            return self.enum_name
        return self.alias_repr

    @property
    def alias_repr(self) -> str:
        return str(f"alias:{list(self.names)}")

    def __setattr__(self, attr_name: str, attr_value: Any):
        if attr_name == "value":
            # because alias subclasses auto and does not set value, enum.py:143 will try to set value
            self.enum_name = attr_value
        else:
            super(alias, self).__setattr__(attr_name, attr_value)

    def __getattribute__(self, attr_name: str):
        if attr_name == "value":
            if object.__getattribute__(self, "enum_name") is None:
                # Gets _auto_null as alias inherits auto class but does not set `value`
                try:
                    return object.__getattribute__(self, "value")
                except Exception:
                    from enum import _auto_null

                    return _auto_null
            return self
        return object.__getattribute__(self, attr_name)


_DEFAULT_REMOVAL_TABLE = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "abcdefghijklmnopqrstuvwxyz",
    " -_.:;,",  # Will be removed
)


class AutoEnum(str, Enum):
    """
    Ultra-fast AutoEnum with fuzzy matching, aliases, and collection conversion.

    AutoEnum provides powerful string-to-enum conversion with case-insensitive matching,
    automatic normalization, and comprehensive alias support. Optimized for performance
    with O(1) lookups and thread-safe initialization.

    Features:
    - **Ultra-fast lookups**: O(1) performance with cached normalization
    - **Fuzzy matching**: Case-insensitive with space/dash/underscore normalization
    - **Rich aliases**: Multiple aliases per enum member with fuzzy matching
    - **Collection conversion**: Convert lists, dicts, and sets between strings and enums
    - **Display names**: Human-readable formatting for UI display
    - **Thread-safe**: Safe concurrent access and initialization
    - **Type safety**: Full typing support with IDE integration

    Basic Usage:
        ```python
        from morphic import AutoEnum, alias, auto

        class Priority(AutoEnum):
            HIGH = alias("urgent", "critical", "high_priority")
            MEDIUM = alias("normal", "standard", "medium_priority")
            LOW = alias("minor", "low_priority")

        # Direct string conversion with fuzzy matching
        p1 = Priority("high")           # HIGH
        p2 = Priority("URGENT")         # HIGH (alias, case insensitive)
        p3 = Priority("high-priority")  # HIGH (fuzzy matching)
        p4 = Priority("Normal")         # MEDIUM (alias, case insensitive)

        # Safe conversion with error handling
        p5 = Priority.from_str("invalid", raise_error=False)  # None
        p6 = Priority.from_str("critical")                    # HIGH

        # Check membership and matching
        assert Priority.matches_any("urgent")         # True
        assert Priority.HIGH.matches("CRITICAL")      # True
        assert not Priority.matches_any("invalid")    # False
        ```

    Advanced Features:
        ```python
        # Collection conversion methods
        status_strings = ["high", "normal", "urgent", "minor"]
        statuses = Priority.convert_list(status_strings)
        # Result: [Priority.HIGH, Priority.MEDIUM, Priority.HIGH, Priority.LOW]

        # Dictionary key/value conversion
        counts = {"high": 10, "normal": 25, "low": 5}
        enum_counts = Priority.convert_keys(counts)
        # Result: {Priority.HIGH: 10, Priority.MEDIUM: 25, Priority.LOW: 5}

        # Display names for UI
        for priority in Priority:
            print(f"{priority}: {priority.display_name()}")
        # Output:
        # HIGH: High
        # MEDIUM: Medium
        # LOW: Low

        # Custom display formatting
        print(Priority.HIGH.display_name(sep="-"))  # "High"
        print(Priority.display_names())             # ["High", "Medium", "Low"]

        # Dynamic enum creation
        Color = AutoEnum.create("Color", ["red", "green grass", "Blue33"])
        red = Color("red")            # Color.Red
        green = Color("green grass")  # Color.Green_Grass
        blue = Color("Blue33")        # Color.Blue33

        # Performance characteristics
        # - 1M+ lookups per second with warm cache
        # - Thread-safe initialization and access
        # - Consistent O(1) performance regardless of enum size
        ```

    String Normalization:
        AutoEnum automatically normalizes strings by:
        - Converting to lowercase
        - Removing spaces, dashes, underscores, dots, colons, semicolons, commas
        - Handling various naming conventions automatically

        ```python
        class Protocol(AutoEnum):
            HTTP_SECURE = alias("HTTPS", "http-secure", "HTTP Secure")

        # All variations work due to normalization
        p1 = Protocol("HTTP-SECURE")    # HTTP_SECURE
        p2 = Protocol("http_secure")    # HTTP_SECURE
        p3 = Protocol("HTTP Secure")    # HTTP_SECURE
        p4 = Protocol("httpsecure")     # HTTP_SECURE (spaces removed)
        ```

    Error Handling:
        ```python
        try:
            status = Priority("invalid_priority")
        except ValueError as e:
            print(f"Error: {e}")
            # Output: Could not find enum with value 'invalid_priority';
            #         available: ['HIGH', 'MEDIUM', 'LOW']

        # Safe conversion patterns
        def safe_priority(value: str) -> Optional[Priority]:
            return Priority.from_str(value, raise_error=False)

        priority = safe_priority("maybe_valid")  # Returns None if invalid
        if priority:
            print(f"Valid priority: {priority}")
        ```
    """

    __slots__ = ()  # no per-instance attrs beyond those in Enum/str

    def __init__(self, value: Union[str, alias]):
        # store aliases tuple for each member
        object.__setattr__(self, "aliases", tuple(value.names) if isinstance(value, alias) else ())

    def _generate_next_value_(name, start, count, last_values):
        # keep the enum member's *name* as its value
        return name

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        setattr(cls, "_lookup_lock", threading.Lock())
        cls._initialize_lookup()

    @classmethod
    def _initialize_lookup(cls):
        # quick check to avoid locking if already built
        if "_value2member_map_normalized_" in cls.__dict__:
            return
        with cls._lookup_lock:
            if "_value2member_map_normalized_" in cls.__dict__:
                return

            mapping: Dict[str, "AutoEnum"] = {}

            def _register(e: "AutoEnum", norm: str):
                if norm in mapping:
                    raise ValueError(
                        f'Cannot register enum "{e.name}"; normalized name "{norm}" already exists.'
                    )
                mapping[norm] = e

            # walk every member exactly once
            for e in cls:
                # register its own name
                _register(e, cls._normalize(e.name))
                # register alias repr
                if e.aliases:
                    # inline alias_repr
                    alias_repr = f"alias:{list(e.aliases)}"
                    _register(e, cls._normalize(alias_repr))
                    # register each plain alias
                    for a in e.aliases:
                        _register(e, cls._normalize(a))

            # stash it on the class
            setattr(cls, "_value2member_map_normalized_", mapping)

    @classmethod
    @lru_cache(maxsize=None)
    def _normalize(cls, x: str) -> str:
        # C-level translate is very fast; caching makes repeated lookups O(1)
        return str(x).translate(_DEFAULT_REMOVAL_TABLE)

    @classmethod
    def _missing_(cls, enum_value: Any):
        # invoked by Enum machinery when auto-casting fails
        return cls.from_str(enum_value, raise_error=True)

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.name

    def __hash__(self) -> int:
        return hash(self.__class__.__name__ + "." + self.name)

    def __eq__(self, other: Any) -> bool:
        # identity check is fastest and correct for singletons
        return self is other

    def __ne__(self, other: Any) -> bool:
        return self is not other

    @classmethod
    def from_str(cls, enum_value: Any, raise_error: bool = True) -> Optional["AutoEnum"]:
        """Convert string to AutoEnum with fuzzy matching."""
        # short‐circuit if it's already the right type
        if isinstance(enum_value, cls):
            return enum_value
        # None tolerated?
        if enum_value is None:
            if raise_error:
                raise ValueError("Cannot convert None to enum")
            return None
        # wrong type?
        if not isinstance(enum_value, str):
            if raise_error:
                raise ValueError(f"Input must be str or {cls.__name__}; got {type(enum_value)}")
            return None
        # one normalized dict lookup
        norm = cls._normalize(enum_value)
        e = cls._value2member_map_normalized_.get(norm)
        if e is None and raise_error:
            raise ValueError(f"Could not find enum with value {enum_value!r}; available: {list(cls)}")
        return e

    def matches(self, enum_value: str) -> bool:
        """Check if this enum matches the given string value."""
        return self is self.from_str(enum_value, raise_error=False)

    @classmethod
    def matches_any(cls, enum_value: str) -> bool:
        """Check if any enum member matches the given string value."""
        return cls.from_str(enum_value, raise_error=False) is not None

    @classmethod
    def does_not_match_any(cls, enum_value: str) -> bool:
        """Check if no enum member matches the given string value."""
        return not cls.matches_any(enum_value)

    @classmethod
    def display_names(cls, **kwargs) -> str:
        """Get display names of all enum members."""
        return str([e.display_name(**kwargs) for e in cls])

    def display_name(self, *, sep: str = " ") -> str:
        """Get human-readable display name for this enum member."""
        return sep.join(
            word.lower() if word.lower() in ("of", "in", "the") else word.capitalize()
            for word in self.name.split("_")
        )

    # -------------- conversion utilities --------------

    @classmethod
    def convert_keys(cls, d: Dict) -> Dict:
        """Convert string dictionary keys to enum values where possible."""
        out = {}
        for k, v in d.items():
            if isinstance(k, str):
                e = cls.from_str(k, raise_error=False)
                out[e if e else k] = v
            else:
                out[k] = v
        return out

    @classmethod
    def convert_keys_to_str(cls, d: Dict) -> Dict:
        """Convert enum dictionary keys to strings."""
        return {(str(k) if isinstance(k, cls) else k): v for k, v in d.items()}

    @classmethod
    def convert_values(
        cls, d: Union[Dict, Set, List, Tuple], raise_error: bool = False
    ) -> Union[Dict, Set, List, Tuple]:
        """Convert string values to enum values where possible."""
        if isinstance(d, dict):
            return cls.convert_dict_values(d)
        if isinstance(d, list):
            return cls.convert_list(d)
        if isinstance(d, tuple):
            return tuple(cls.convert_list(list(d)))
        if isinstance(d, set):
            return cls.convert_set(d)
        if raise_error:
            raise ValueError(f"Unsupported type: {type(d)}")
        return d

    @classmethod
    def convert_dict_values(cls, d: Dict) -> Dict:
        """Convert string dictionary values to enum values where possible."""
        return {k: (cls.from_str(v, raise_error=False) if isinstance(v, str) else v) for k, v in d.items()}

    @classmethod
    def convert_list(cls, l: List) -> List:
        """Convert string list items to enum values where possible."""
        return [
            (cls.from_str(item) if isinstance(item, str) and cls.matches_any(item) else item) for item in l
        ]

    @classmethod
    def convert_set(cls, s: Set) -> Set:
        """Convert string set items to enum values where possible."""
        out = set()
        for item in s:
            if isinstance(item, str) and cls.matches_any(item):
                out.add(cls.from_str(item))
            else:
                out.add(item)
        return out

    @classmethod
    def convert_values_to_str(cls, d: Dict) -> Dict:
        """Convert enum dictionary values to strings."""
        return {k: (str(v) if isinstance(v, cls) else v) for k, v in d.items()}

    @staticmethod
    def create(name: str, values: List[str]) -> type["AutoEnum"]:
        """
        Dynamically creates an AutoEnum subclass named `name` from a list of strings.

        Args:
            name: The name for the new enum class
            values: List of string values to become enum members

        Returns:
            A new AutoEnum subclass

        Example:
            Status = AutoEnum.create('Status', ['pending', 'running', 'complete'])
        """

        # sanitize Python identifiers: letters, digits and underscores only
        def to_identifier(s: str) -> str:
            # replace non-word chars with underscore, strip leading digits
            ident: str = re.sub(r"\W+", "_", s).lstrip("0123456789").lstrip("_").rstrip("_")
            ident_capitalize: str = "_".join([x.capitalize() for x in ident.split("_")])
            if s != ident:
                warnings.warn(
                    f"We have converted '{s}' to '{ident_capitalize}' to make it a valid Python identifier"
                )
            return ident_capitalize

        members = {to_identifier(v): auto() for v in values}
        # Enum functional constructor:
        return AutoEnum(name, members)
