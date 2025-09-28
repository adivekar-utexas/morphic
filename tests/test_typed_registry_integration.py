"""Tests for integration between Typed and Registry patterns."""

from abc import ABC, abstractmethod
from typing import List, Optional

import pytest

from morphic.registry import Registry
from morphic.typed import Typed


class TestTypedRegistryIntegration:
    """Test suite for integration between Typed and Registry classes."""

    def test_basic_typed_registry_inheritance(self):
        """Test basic inheritance with proper method resolution order."""

        class Animal(Typed, Registry, ABC):
            name: str
            species: str

            @abstractmethod
            def speak(self) -> str:
                pass

        class Dog(Animal):
            aliases = ["canine", "puppy"]

            def speak(self) -> str:
                return f"{self.name} says Woof!"

        class Cat(Animal):
            aliases = ["feline", "kitty"]

            def speak(self) -> str:
                return f"{self.name} says Meow!"

        # Test Registry factory patterns work with Pydantic validation
        dog = Animal.of("Dog", name="Rex", species="Canis lupus")
        assert isinstance(dog, Dog)
        assert dog.name == "Rex"  # Pydantic validated field
        assert dog.species == "Canis lupus"  # Pydantic validated field
        assert dog.speak() == "Rex says Woof!"

        # Test alias support
        cat = Animal.of("feline", name="Shadow", species="Felis catus")
        assert isinstance(cat, Cat)
        assert cat.name == "Shadow"
        assert cat.species == "Felis catus"
        assert cat.speak() == "Shadow says Meow!"

    def test_direct_concrete_instantiation(self):
        """Test direct instantiation of concrete Typed+Registry classes."""

        class Vehicle(Typed, Registry, ABC):
            brand: str
            year: int = 2023
            doors: int = 4

        class Car(Vehicle):
            pass

        # Direct concrete instantiation without registry key
        car = Car.of(brand="Toyota", year=2022, doors=4)
        assert isinstance(car, Car)
        assert car.brand == "Toyota"
        assert car.year == 2022
        assert car.doors == 4

        # Direct concrete instantiation with matching registry key
        car2 = Car.of("Car", brand="Honda", year=2021)
        assert isinstance(car2, Car)
        assert car2.brand == "Honda"
        assert car2.year == 2021
        assert car2.doors == 4  # Default value

    def test_type_conversion_and_validation(self):
        """Test that Pydantic type conversion works in Registry context."""

        class DatabaseConnection(Typed, Registry, ABC):
            host: str = "localhost"
            port: int = 5432
            ssl: bool = False
            database: str = "mydb"

            @abstractmethod
            def connect(self) -> str:
                pass

        class PostgreSQL(DatabaseConnection):
            aliases = ["postgres", "pg"]

            def connect(self) -> str:
                return f"postgresql://{self.host}:{self.port}/{self.database}"

        # Test type conversion during Registry factory
        db = DatabaseConnection.of(
            "postgres",
            host="remote.db",
            port="5433",  # String converted to int
            ssl="true",  # String converted to bool
            database="production",
        )
        assert isinstance(db, PostgreSQL)
        assert db.host == "remote.db"
        assert db.port == 5433  # Converted from string
        assert isinstance(db.port, int)
        assert db.ssl is True  # Converted from string
        assert isinstance(db.ssl, bool)
        assert db.database == "production"

    def test_hierarchical_scoping_preserved(self):
        """Test that Registry's hierarchical scoping is preserved."""

        class Transport(Typed, Registry, ABC):
            name: str

        class LandTransport(Transport, ABC):
            wheels: int = 4

        class WaterTransport(Transport, ABC):
            draft: float = 1.0

        class Car(LandTransport):
            pass

        class Boat(WaterTransport):
            pass

        # LandTransport should only access Car, not Boat
        car = LandTransport.of("Car", name="Sedan", wheels=4)
        assert isinstance(car, Car)
        assert car.name == "Sedan"
        assert car.wheels == 4

        # Should fail to access Boat from LandTransport hierarchy
        with pytest.raises(KeyError, match="Could not find subclass of LandTransport"):
            LandTransport.of("Boat", name="test")

        # WaterTransport should only access Boat, not Car
        boat = WaterTransport.of("Boat", name="Yacht", draft=2.5)
        assert isinstance(boat, Boat)
        assert boat.name == "Yacht"
        assert boat.draft == 2.5

        # Should fail to access Car from WaterTransport hierarchy
        with pytest.raises(KeyError, match="Could not find subclass of WaterTransport"):
            WaterTransport.of("Car", name="test")

    def test_validation_errors_preserved(self):
        """Test that Pydantic validation errors are properly propagated."""

        class ConfiguredService(Typed, Registry, ABC):
            name: str
            port: int
            timeout: float = 30.0

        class WebService(ConfiguredService):
            pass

        # Test validation error for invalid port
        with pytest.raises(ValueError) as exc_info:
            ConfiguredService.of("WebService", name="api", port="invalid", timeout=15.0)

        error_msg = str(exc_info.value)
        assert "ValidationError" in error_msg
        assert "port" in error_msg  # Field that failed validation
        assert "invalid" in error_msg  # Invalid input value

    def test_registry_errors_preserved(self):
        """Test that Registry errors are properly propagated."""

        class Service(Typed, Registry, ABC):
            name: str

        class EmailService(Service):
            pass

        # Test Registry KeyError for unknown service
        with pytest.raises(KeyError) as exc_info:
            Service.of("UnknownService", name="test")

        error_msg = str(exc_info.value)
        assert "Could not find subclass" in error_msg
        assert "UnknownService" in error_msg
        assert "Available keys" in error_msg

    def test_pure_typed_classes_raise_error(self):
        """Test that pure Typed classes continue to work as before."""

        class User(Typed):
            name: str
            age: int
            active: bool = True

        # Pure Typed factory method should work normally
        user = User.of(name="John", age=30)
        assert isinstance(user, User)
        assert user.name == "John"
        assert user.age == 30
        assert user.active is True

        # Should ignore registry_key parameter if provided (API compatibility)
        with pytest.raises(TypeError) as exc_info:
            user2 = User.of("some_key", name="Jane", age=25, active=False)

    def test_complex_nested_validation(self):
        """Test complex validation scenarios with nested Typed models."""

        class Address(Typed):
            street: str
            city: str
            zipcode: str

        class Person(Typed, Registry, ABC):
            name: str
            age: int
            address: Address

        class Employee(Person):
            aliases = ["worker", "staff"]
            department: str = "general"

        # Test nested model validation through Registry factory
        employee = Person.of(
            "Employee",
            name="Alice",
            age="30",  # String converted to int
            address={  # Dict converted to Address
                "street": "123 Main St",
                "city": "Springfield",
                "zipcode": "12345",
            },
            department="engineering",
        )

        assert isinstance(employee, Employee)
        assert employee.name == "Alice"
        assert employee.age == 30  # Converted from string
        assert isinstance(employee.address, Address)
        assert employee.address.street == "123 Main St"
        assert employee.department == "engineering"

    def test_multiple_inheritance_scenarios(self):
        """Test various multiple inheritance scenarios."""

        class Mixin:
            def common_method(self):
                return "common"

        class Base(Typed, Registry, ABC):
            id: str

            @abstractmethod
            def process(self):
                pass

        class Concrete(Base, Mixin):
            extra_data: str = "none"

            def process(self):
                return f"Processing {self.id}"

        # Test factory with multiple inheritance
        instance = Base.of("Concrete", id="test123", extra_data="important")
        assert isinstance(instance, Concrete)
        assert instance.id == "test123"  # Pydantic validated
        assert instance.extra_data == "important"  # Pydantic validated
        assert instance.common_method() == "common"  # From mixin
        assert instance.process() == "Processing test123"

    def test_autoenum_integration(self):
        """Test integration with AutoEnum for registry keys."""
        from morphic.autoenum import AutoEnum, auto

        class ServiceType(AutoEnum):
            WEB = auto()
            DATABASE = auto()
            CACHE = auto()

        class Service(Typed, Registry, ABC):
            name: str
            version: str = "1.0"

        class WebService(Service):
            aliases = [ServiceType.WEB]
            port: int = 80

        class DatabaseService(Service):
            aliases = [ServiceType.DATABASE]
            host: str = "localhost"

        # Test AutoEnum as registry key
        web = Service.of(ServiceType.WEB, name="api", version="2.0", port=8080)
        assert isinstance(web, WebService)
        assert web.name == "api"
        assert web.version == "2.0"
        assert web.port == 8080

        db = Service.of(ServiceType.DATABASE, name="primary", host="db.example.com")
        assert isinstance(db, DatabaseService)
        assert db.name == "primary"
        assert db.host == "db.example.com"

    def test_field_validation_with_constraints(self):
        """Test field validation with Pydantic constraints."""
        from pydantic import Field

        class Product(Typed, Registry, ABC):
            name: str = Field(..., min_length=1, max_length=100)
            price: float = Field(..., gt=0)
            quantity: int = Field(default=1, ge=0)

        class Electronics(Product):
            warranty_months: int = 12

        # Valid product
        laptop = Product.of(
            "Electronics",
            name="Laptop",
            price="999.99",  # String converted to float
            quantity="5",  # String converted to int
            warranty_months=24,
        )
        assert isinstance(laptop, Electronics)
        assert laptop.name == "Laptop"
        assert laptop.price == 999.99
        assert laptop.quantity == 5
        assert laptop.warranty_months == 24

        # Test constraint violation - negative price
        with pytest.raises(ValueError) as exc_info:
            Product.of("Electronics", name="Laptop", price="-100")
        assert "ValidationError" in str(exc_info.value)

        # Test constraint violation - empty name
        with pytest.raises(ValueError) as exc_info:
            Product.of("Electronics", name="", price="100")
        assert "ValidationError" in str(exc_info.value)

    def test_optional_fields_and_defaults(self):
        """Test handling of optional fields and default values."""

        class Configuration(Typed, Registry, ABC):
            name: str
            enabled: bool = True
            max_connections: Optional[int] = None
            tags: List[str] = []

        class DatabaseConfig(Configuration):
            connection_string: Optional[str] = None

        # Test with minimal required fields
        config = Configuration.of("DatabaseConfig", name="prod_db")
        assert isinstance(config, DatabaseConfig)
        assert config.name == "prod_db"
        assert config.enabled is True  # Default value
        assert config.max_connections is None  # Default value
        assert config.tags == []  # Default value
        assert config.connection_string is None  # Default value

        # Test with all fields specified
        config2 = Configuration.of(
            "DatabaseConfig",
            name="dev_db",
            enabled="false",  # String converted to bool
            max_connections="100",  # String converted to int
            tags=["development", "testing"],
            connection_string="postgresql://localhost/dev",
        )
        assert config2.enabled is False
        assert config2.max_connections == 100
        assert config2.tags == ["development", "testing"]
        assert config2.connection_string == "postgresql://localhost/dev"

    def test_error_messages_quality(self):
        """Test that error messages are helpful and informative."""

        class Service(Typed, Registry, ABC):
            name: str
            port: int

        class WebService(Service):
            pass

        # Test Registry error message shows available options
        try:
            Service.of("NonExistentService", name="test", port=80)
            assert False, "Should have raised KeyError"
        except KeyError as e:
            error_msg = str(e)
            assert "Could not find subclass of Service" in error_msg
            assert "NonExistentService" in error_msg
            assert "Available keys" in error_msg
            assert "WebService" in error_msg  # Should show available option

        # Test Pydantic validation error message is detailed
        try:
            Service.of("WebService", name="test", port="invalid_port")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            error_msg = str(e)
            assert "ValidationError" in error_msg
            assert "port" in error_msg
            assert "invalid_port" in error_msg

    def test_backward_compatibility(self):
        """Test that existing code patterns continue to work."""

        # Test old-style inheritance (Registry first) - should still work
        class OldStyleBase(Registry, ABC):
            pass

        class OldStyleConcrete(OldStyleBase):
            def __init__(self, value="default"):
                self.value = value

        # Old style should still work
        instance = OldStyleBase.of("OldStyleConcrete", value="test")
        assert isinstance(instance, OldStyleConcrete)
        assert instance.value == "test"

        # Test new-style inheritance (Typed first) - enhanced with validation
        class NewStyleBase(Typed, Registry, ABC):
            name: str

        class NewStyleConcrete(NewStyleBase):
            extra: str = "none"

        # New style should work with validation
        instance2 = NewStyleBase.of("NewStyleConcrete", name="test", extra="value")
        assert isinstance(instance2, NewStyleConcrete)
        assert instance2.name == "test"  # Pydantic validated
        assert instance2.extra == "value"

    def test_performance_characteristics(self):
        """Test that performance characteristics are reasonable."""

        class BaseService(Typed, Registry, ABC):
            name: str

        # Create many subclasses to test scalability
        subclasses = []
        for i in range(20):  # Smaller number for faster test
            class_name = f"Service{i}"
            cls = type(
                class_name,
                (BaseService,),
                {
                    "aliases": [f"svc{i}", f"service_{i}"],
                },
            )
            subclasses.append(cls)

        # Test that lookups are still fast with many registered classes
        import time

        start_time = time.time()
        for i in range(5):  # Multiple lookups
            service = BaseService.of(f"Service{i}", name=f"test_service_{i}")
            assert service.name == f"test_service_{i}"
        end_time = time.time()

        # Should complete quickly (less than 1 second for 5 lookups with 20 registered classes)
        assert (end_time - start_time) < 1.0
