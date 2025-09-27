"""Tests for the Registry pattern."""

import pytest
from abc import ABC, abstractmethod
from morphic.registry import Registry


class TestRegistry:
    def test_basic_registry_functionality(self):
        """Test basic registry functionality."""

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

        # Test getting subclass by name
        DogClass = Animal.get_subclass("Dog")
        assert DogClass is Dog

        # Test getting subclass by alias
        CatClass = Animal.get_subclass("feline")
        assert CatClass is Cat

        CatClass2 = Animal.get_subclass("kitty")
        assert CatClass2 is Cat

    def test_case_insensitive_matching(self):
        """Test case insensitive matching."""

        class Vehicle(Registry, ABC):
            pass

        class Car(Vehicle):
            pass

        # Should work with different cases
        CarClass = Vehicle.get_subclass("car")
        assert CarClass is Car

        CarClass2 = Vehicle.get_subclass("CAR")
        assert CarClass2 is Car

    def test_key_not_found(self):
        """Test behavior when key is not found."""

        class Fruit(Registry, ABC):
            pass

        class Apple(Fruit):
            pass

        # Should raise KeyError when key not found
        with pytest.raises(KeyError):
            Fruit.get_subclass("banana")

        # Should return None when raise_error=False
        result = Fruit.get_subclass("banana", raise_error=False)
        assert result is None

    def test_subclasses_method(self):
        """Test getting all subclasses."""

        class Shape(Registry, ABC):
            pass

        class Circle(Shape):
            pass

        class Square(Shape):
            pass

        subclasses = Shape.subclasses()
        assert Circle in subclasses
        assert Square in subclasses
        assert len(subclasses) == 2