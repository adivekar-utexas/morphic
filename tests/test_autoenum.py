import json
import sys
import time
from typing import List

import pytest

from morphic.autoenum import AutoEnum, alias, auto

# Try importing pydantic, if not available, we'll skip those tests
try:
    from pydantic import BaseModel, conint, constr

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False


# Test enums
class Animal(AutoEnum):
    Antelope = auto()
    Bandicoot = auto()
    Cat = alias("Feline")
    Dog = auto()


class City(AutoEnum):
    Atlanta = auto()
    Boston = auto()
    Chicago = auto()
    Denver = auto()
    El_Paso = auto()
    Fresno = auto()
    Greensboro = auto()
    Houston = auto()
    Indianapolis = auto()
    Jacksonville = auto()
    Kansas_City = auto()
    Los_Angeles = auto()
    Miami = auto()
    New_York_City = alias("New York", "NYC")
    Orlando = auto()
    Philadelphia = auto()
    Quincy = auto()
    Reno = auto()
    San_Francisco = auto()
    Tucson = auto()
    Union_City = auto()
    Virginia_Beach = auto()
    Washington = alias("Washington D.C.")
    Xenia = auto()
    Yonkers = auto()
    Zion = auto()


# Only define Pydantic model if Pydantic is available
if PYDANTIC_AVAILABLE:

    class Company(BaseModel):
        name: constr(min_length=1)
        headquarters: City
        num_employees: conint(ge=1)


def test_basic_enum_access():
    """Test basic enum access and comparison"""
    assert Animal.Antelope == Animal("Antelope")
    assert Animal.Bandicoot == Animal("Bandicoot")
    assert Animal.Cat == Animal("Cat")
    assert Animal.Dog == Animal("Dog")


def test_is_operator():
    """Test 'is' operator functionality"""
    assert Animal.Cat is Animal("Cat")
    assert City.Los_Angeles is City("Los_Angeles")
    assert City.Boston is City("Boston")


def test_naming_conventions():
    """Test different naming conventions are handled correctly"""
    assert (
        City.Los_Angeles
        == City("Los_Angeles")
        == City("LosAngeles")
        == City("LOS_ANGELES")
        == City("losAngeles")
    )
    assert City.New_York_City == City("NewYorkCity") == City("NEW_YORK_CITY") == City("newYorkCity")


def test_fuzzy_matching():
    """Test fuzzy matching with various input formats"""
    assert (
        City.Los_Angeles
        == City("Los Angeles")
        == City("Los__Angeles")
        == City(" _Los_Angeles   ")
        == City("LOS-Angeles")
    )
    assert City.New_York_City == City("New York") == City("New.York") == City("New-York")

    # Test invalid fuzzy matches
    with pytest.raises(ValueError):
        City("Lozz Angeles")
    with pytest.raises(ValueError):
        City("New Yorkk")


def test_aliases():
    """Test alias functionality"""
    assert Animal("Cat") == Animal("Feline")
    assert City("Washington") == City("Washington DC") == City("Washington D.C.")
    assert City("New York") == City("NYC") == City.New_York_City


def test_custom_normalize():
    """Test custom normalization logic"""

    class ExactMatchAnimal(AutoEnum):
        Antelope = auto()
        Bandicoot = auto()
        Cat = alias("Feline")
        Dog = auto()

        @classmethod
        def _normalize(cls, x: str) -> str:
            return str(x)  # Exact matching

    assert ExactMatchAnimal("Antelope") == ExactMatchAnimal.Antelope
    with pytest.raises(ValueError):
        ExactMatchAnimal("antelope")  # Should fail with exact matching


def test_json_compatibility():
    """Test JSON serialization and deserialization"""
    # Test basic JSON serialization
    json_str = json.dumps([Animal.Cat, Animal.Dog])
    assert json_str == '["Cat", "Dog"]'

    # Test JSON deserialization
    animals: List[Animal] = Animal.convert_values(json.loads(json_str))
    assert animals == [Animal.Cat, Animal.Dog]
    assert isinstance(animals[0], Animal) and isinstance(animals[1], Animal)


@pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic is not installed")
def test_pydantic_integration():
    """Test Pydantic model integration"""
    # Test with string input
    netflix = Company(name="Netflix", headquarters="Los Angeles", num_employees=12_000)
    assert netflix.headquarters == City.Los_Angeles
    assert netflix.headquarters is City.Los_Angeles

    # Test JSON serialization
    json_str = netflix.model_dump_json()
    assert json.loads(json_str)["headquarters"] == "Los_Angeles"

    # Test JSON deserialization
    loaded_company = Company.model_validate_json(json_str)
    assert loaded_company.headquarters == City.Los_Angeles
    assert loaded_company.headquarters is City.Los_Angeles


def test_string_representation():
    """Test string and repr representation"""
    assert str(City.Boston) == "Boston"
    assert repr(City.Boston) == "Boston"
    assert str(Animal.Cat) == "Cat"
    assert repr(Animal.Cat) == "Cat"


def test_error_handling():
    """Test error handling for invalid inputs"""
    with pytest.raises(ValueError):
        Animal("InvalidAnimal")

    with pytest.raises(ValueError):
        City("InvalidCity")

    # Test error suppression
    assert Animal.from_str("InvalidAnimal", raise_error=False) is None
    assert City.from_str("InvalidCity", raise_error=False) is None


def test_enum_iteration():
    """Test enum iteration and membership"""
    # Test length of enums
    assert len(list(Animal)) == 4
    assert len(list(City)) == 26

    # Test membership of enum values
    assert Animal.Cat in Animal
    assert City.Los_Angeles in City

    # For Python 3.12+, test string membership with fuzzy matching
    if sys.version_info >= (3, 12):
        # Test membership using fuzzy matching
        assert "Cat" in Animal
        assert "Los Angeles" in City
        assert "cat" in Animal  # Case insensitive
        assert "los_angeles" in City  # Case insensitive

        # Test membership of aliases
        assert "Feline" in Animal
        assert "NYC" in City
        assert "New York" in City

        # Test membership of invalid values
        assert "InvalidAnimal" not in Animal
        assert "InvalidCity" not in City

        # Test membership with non-string, non-enum values
        assert 123 not in Animal
        assert None not in City
        assert [] not in Animal
        assert {} not in City
    else:
        # For Python < 3.12, verify that string membership raises TypeError
        with pytest.raises(TypeError, match="unsupported operand type\\(s\\) for 'in': 'str' and 'EnumType'"):
            "Cat" in Animal
        with pytest.raises(TypeError, match="unsupported operand type\\(s\\) for 'in': 'str' and 'EnumType'"):
            "Los Angeles" in City


def test_autoenum_create():
    """Test AutoEnum.create static method"""

    with pytest.warns(
        UserWarning, match="We have converted 'Value 1' to 'Value_1' to make it a valid Python identifier"
    ):
        TestEnum = AutoEnum.create("TestEnum", ["Value 1", "Value2", "Value3"])
        assert TestEnum.Value_1 == TestEnum("Value1")
        assert TestEnum.Value2 == TestEnum("Value2")
        assert TestEnum.Value3 == TestEnum("Value3")

    Color = AutoEnum.create("Color", ["red", "green   grass", "Blue33", "Yellow!!!!!!!!!!!!3"])
    assert Color.Red == Color("Red")
    assert Color.Green_Grass == Color("Green-Grass")
    assert Color.Blue33 == Color("Blue33")
    assert Color.Yellow_3 == Color("yellow_3")
    assert Color.Yellow_3 == Color("Yellow3")


def measure_lookup_speed(enum_class, test_values, iterations=100_000):
    """Measure lookup speed for a given enum class and test values."""
    ## Warmup cache:
    for value in test_values:
        _ = enum_class(value)
    ## Measure lookup speed:
    start_time = time.perf_counter()
    for _ in range(iterations):
        for value in test_values:
            _ = enum_class(value)

    end_time = time.perf_counter()
    total_time = end_time - start_time
    lookups_per_second = (iterations * len(test_values)) / total_time

    return lookups_per_second


def test_enum_size_impact():
    """Test if enum size impacts lookup speed."""
    animal_speed = measure_lookup_speed(Animal, ["Cat", "Dog"])
    city_speed = measure_lookup_speed(City, ["Los_Angeles", "New_York_City"])

    # Calculate speed ratio
    speed_ratio = city_speed / animal_speed

    print(f"\nSpeed ratio (City/Animal) for same number of lookups: {speed_ratio:.4f}x")

    # Ensure the larger enum is at least 50% as fast as the smaller one
    assert speed_ratio > 0.5, f"Larger enum too slow: {speed_ratio:.2f}x speed ratio"


@pytest.mark.parametrize(
    "n,threshold",
    [
        (1_000_000, 1000),  # 1M lookups in <1000 ms
    ],
)
def test_from_str_lookup_speed(n, threshold):
    """Test from_str lookup speed with cache warmup."""
    # warm up cache
    Animal.from_str("Cat")
    start = time.perf_counter()
    for _ in range(n):
        Animal.from_str("Cat")
    duration = 1000 * (time.perf_counter() - start)
    print(
        f"[from_str_lookup] {n:,} iterations took {duration:.2f}ms (avg {1000 * duration / n:.2f}us per from_str lookup)"
    )
    assert duration < threshold, f"{n:,} lookups took {duration:.2f}ms, over {threshold}ms"


@pytest.mark.parametrize(
    "n,threshold",
    [
        (10_000, 1000),  # 10k lookups in <1000 ms
    ],
)
def test_no_cache_from_str_lookup_speed(n, threshold):
    """Test from_str lookup speed without cache warmup."""
    loop_times = []
    for _ in range(5):  # Run 5 times to get average
        start = time.perf_counter()
        for _ in range(n):
            Animal.from_str("Cat")
        duration = 1000 * (time.perf_counter() - start)
        loop_times.append(duration)

    avg_duration = sum(loop_times) / len(loop_times)
    print(
        f"[no_cache_from_str_lookup] {n:,} iterations took avg {avg_duration:.2f}ms (avg {1000 * avg_duration / n:.2f}us per from_str lookup)"
    )
    assert avg_duration < threshold, f"{n:,} lookups took avg {avg_duration:.2f}ms, over {threshold}ms"


@pytest.mark.parametrize(
    "n,threshold",
    [
        (1_000_000, 1000),  # 1M lookups in <1000 ms
    ],
)
def test_matches_any_lookup_speed(n, threshold):
    """Test matches_any lookup speed with cache warmup."""
    # warm up cache
    Animal.matches_any("Cat")
    start = time.perf_counter()
    for _ in range(n):
        Animal.matches_any("Cat")
    duration = 1000 * (time.perf_counter() - start)
    print(
        f"[matches_any_lookup] {n:,} iterations took {duration:.2f}ms (avg {1000 * duration / n:.2f}us per matches_any lookup)"
    )
    assert duration < threshold, f"{n:,} lookups took {duration:.2f}ms, over {threshold}ms"


@pytest.mark.parametrize(
    "n,threshold",
    [
        (10_000, 1000),  # 10k lookups in <1000 ms
    ],
)
def test_no_cache_matches_any_lookup_speed(n, threshold):
    """Test matches_any lookup speed without cache warmup."""
    loop_times = []
    for _ in range(5):  # Run 5 times to get average
        start = time.perf_counter()
        for _ in range(n):
            Animal.matches_any("Cat")
        duration = 1000 * (time.perf_counter() - start)
        loop_times.append(duration)

    avg_duration = sum(loop_times) / len(loop_times)
    print(
        f"[no_cache_matches_any_lookup] {n:,} iterations took avg {avg_duration:.2f}ms (avg {1000 * avg_duration / n:.2f}us per matches_any lookup)"
    )
    assert avg_duration < threshold, f"{n:,} lookups took avg {avg_duration:.2f}ms, over {threshold}ms"


@pytest.mark.parametrize(
    "n,threshold",
    [
        (1_000_000, 10_000),  # 1M iterations in <10,000 ms
    ],
)
def test_enum_iteration_speed(n, threshold):
    """Test enum iteration speed."""
    # warm up
    list(Animal)
    start = time.perf_counter()
    for _ in range(n):
        list(Animal)
    duration = 1000 * (time.perf_counter() - start)
    print(
        f"[enum_iteration] {n:,} iterations took {duration:.2f}ms (avg {1000 * duration / n:.2f}us per iteration)"
    )
    assert duration < threshold, f"{n:,} iterations took {duration:.2f}ms, over {threshold}ms"


@pytest.mark.parametrize(
    "n,threshold",
    [
        (1_000_000, 10_000),  # 1M conversions in <10,000 ms
    ],
)
def test_convert_list_speed(n, threshold):
    """Test list conversion speed."""
    test_list = ["Cat", "Dog", "Antelope", "Bandicoot"]
    # warm up
    Animal.convert_list(test_list)
    start = time.perf_counter()
    for _ in range(n):
        Animal.convert_list(test_list)
    duration = 1000 * (time.perf_counter() - start)
    print(
        f"[convert_list] {n:,} conversions took {duration:.2f}ms (avg {1000 * duration / n:.2f}us per conversion)"
    )
    assert duration < threshold, f"{n:,} conversions took {duration:.2f}ms, over {threshold}ms"


def test_lookup_throughput():
    """Test lookup throughput with and without caching for both enums."""
    # Test values that will be used for both enums
    test_values = [
        "value1",  # Exact match
        "value2",  # Exact match
        "Value1",  # Case variation
        "Value2",  # Case variation
        "value 1",  # Spacing variation
        "value 2",  # Spacing variation
    ]

    iterations = 100_000

    # Test with caching (warm cache)
    print("\nTesting with caching (warm cache):")
    print("----------------------------------")

    # Warm up cache for Animal enum
    for value in test_values:
        _ = Animal.from_str(value, raise_error=False)

    # Measure Animal enum with cache
    start_time = time.perf_counter()
    for _ in range(iterations):
        for value in test_values:
            _ = Animal.from_str(value, raise_error=False)
    animal_cached_time = time.perf_counter() - start_time
    animal_cached_throughput = (iterations * len(test_values)) / animal_cached_time

    # Warm up cache for City enum
    for value in test_values:
        _ = City.from_str(value, raise_error=False)

    # Measure City enum with cache
    start_time = time.perf_counter()
    for _ in range(iterations):
        for value in test_values:
            _ = City.from_str(value, raise_error=False)
    city_cached_time = time.perf_counter() - start_time
    city_cached_throughput = (iterations * len(test_values)) / city_cached_time

    print(f"Animal enum ({len(Animal)} members):")
    print(f"  - Throughput: {animal_cached_throughput:,.0f} lookups/second")
    print(f"  - Total time: {animal_cached_time:.3f}s")
    print(f"  - Time per lookup: {animal_cached_time * 1_000_000 / (iterations * len(test_values)):.3f}µs")

    print(f"\nCity enum ({len(City)} members):")
    print(f"  - Throughput: {city_cached_throughput:,.0f} lookups/second")
    print(f"  - Total time: {city_cached_time:.3f}s")
    print(f"  - Time per lookup: {city_cached_time * 1_000_000 / (iterations * len(test_values)):.3f}µs")

    # Test without caching (cold cache)
    print("\nTesting without caching (cold cache):")
    print("------------------------------------")

    # Clear the cache
    Animal._normalize.cache_clear()
    City._normalize.cache_clear()

    # Measure Animal enum without cache
    animal_uncached_time = 0.0
    for _ in range(iterations):
        for value in test_values:
            Animal._normalize.cache_clear()
            start_time = time.perf_counter()
            _ = Animal.from_str(value, raise_error=False)
            animal_uncached_time += time.perf_counter() - start_time
    animal_uncached_throughput = (iterations * len(test_values)) / animal_uncached_time

    # Clear the cache again
    Animal._normalize.cache_clear()
    City._normalize.cache_clear()

    # Measure City enum without cache
    city_uncached_time = 0.0
    for _ in range(iterations):
        for value in test_values:
            City._normalize.cache_clear()
            start_time = time.perf_counter()
            _ = City.from_str(value, raise_error=False)
            city_uncached_time += time.perf_counter() - start_time
    city_uncached_throughput = (iterations * len(test_values)) / city_uncached_time

    print(f"Animal enum ({len(Animal)} members):")
    print(f"  - Throughput: {animal_uncached_throughput:,.0f} lookups/second")
    print(f"  - Total time: {animal_uncached_time:.3f}s")
    print(f"  - Time per lookup: {animal_uncached_time * 1_000_000 / (iterations * len(test_values)):.3f}µs")

    print(f"\nCity enum ({len(City)} members):")
    print(f"  - Throughput: {city_uncached_throughput:,.0f} lookups/second")
    print(f"  - Total time: {city_uncached_time:.3f}s")
    print(f"  - Time per lookup: {city_uncached_time * 1_000_000 / (iterations * len(test_values)):.3f}µs")

    # Calculate speed ratios
    cached_ratio = city_cached_throughput / animal_cached_throughput
    uncached_ratio = city_uncached_throughput / animal_uncached_throughput

    print("\nSpeed ratios:")
    print(f"  - With caching: {cached_ratio:.2f}x (City/Animal)")
    print(f"  - Without caching: {uncached_ratio:.2f}x (City/Animal)")

    # Assertions
    # With caching, both should be very fast
    assert animal_cached_throughput > 100_000, (
        f"Animal enum cached throughput too slow: {animal_cached_throughput:,.0f} lookups/second"
    )
    assert city_cached_throughput > 100_000, (
        f"City enum cached throughput too slow: {city_cached_throughput:,.0f} lookups/second"
    )

    # Without caching, the larger enum should be slower
    assert uncached_ratio < 2.0, f"Larger enum is faster without caching: {uncached_ratio:.2f}x"
    assert uncached_ratio > 0.5, f"Larger enum is too slow without caching: {uncached_ratio:.2f}x"
