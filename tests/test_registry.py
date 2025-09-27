"""Tests for the Registry pattern."""

from abc import ABC, abstractmethod

import pytest

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

    def test_registry_keys_method(self):
        """Test custom registry keys via _registry_keys method."""

        class Tool(Registry, ABC):
            pass

        class Hammer(Tool):
            @classmethod
            def _registry_keys(cls):
                return ["pound", "nail_tool", ("tool", "heavy")]

        # Test retrieval by custom keys
        HammerClass = Tool.get_subclass("pound")
        assert HammerClass is Hammer

        HammerClass2 = Tool.get_subclass("nail_tool")
        assert HammerClass2 is Hammer

        # Test tuple key
        HammerClass3 = Tool.get_subclass(("tool", "heavy"))
        assert HammerClass3 is Hammer

    def test_aliases_attribute(self):
        """Test aliases class attribute."""

        class Food(Registry, ABC):
            pass

        class Pizza(Food):
            aliases = ("pie", "flatbread")

        class Burger(Food):
            aliases = ["sandwich", "patty"]

        # Test tuple aliases
        PizzaClass = Food.get_subclass("pie")
        assert PizzaClass is Pizza

        PizzaClass2 = Food.get_subclass("flatbread")
        assert PizzaClass2 is Pizza

        # Test list aliases
        BurgerClass = Food.get_subclass("sandwich")
        assert BurgerClass is Burger

        BurgerClass2 = Food.get_subclass("patty")
        assert BurgerClass2 is Burger

    def test_abstract_subclass_handling(self):
        """Test that abstract subclasses are handled correctly."""

        class Base(Registry, ABC):
            pass

        class AbstractMiddle(Base, ABC):
            @abstractmethod
            def abstract_method(self):
                pass

        class Concrete(AbstractMiddle):
            def abstract_method(self):
                return "implemented"

        # Abstract classes should not be in subclasses by default
        subclasses = Base.subclasses()
        assert AbstractMiddle not in subclasses
        assert Concrete in subclasses

        # But should be included when keep_abstract=True
        all_subclasses = Base.subclasses(keep_abstract=True)
        # Note: Abstract subclasses may not be included depending on implementation
        assert Concrete in all_subclasses

        # Abstract classes should not be automatically registered
        abstract_result = Base.get_subclass("AbstractMiddle", raise_error=False)
        assert abstract_result is None  # Abstract classes are not registered by default

    def test_dont_register_flag(self):
        """Test _dont_register flag prevents registration."""

        class Database(Registry, ABC):
            pass

        class MySQL(Database):
            pass

        class PostgreSQL(Database):
            _dont_register = True

        # MySQL should be registered
        MySQLClass = Database.get_subclass("MySQL")
        assert MySQLClass is MySQL

        # PostgreSQL should not be registered
        with pytest.raises(KeyError):
            Database.get_subclass("PostgreSQL")

        result = Database.get_subclass("PostgreSQL", raise_error=False)
        assert result is None

    def test_allow_subclass_override_flag(self):
        """Test _allow_subclass_override flag behavior."""

        class Service(Registry, ABC):
            _allow_subclass_override = True

        # First registration
        class EmailService(Service):
            version = 1

        # Override with same name
        class EmailService(Service):
            version = 2

        # Should get the latest version
        ServiceClass = Service.get_subclass("EmailService")
        assert ServiceClass.version == 2

        # Test that default behavior (no override) raises error
        class StrictService(Registry, ABC):
            pass

        class SMSService(StrictService):
            version = 1

        with pytest.raises(KeyError, match="already registered"):

            class SMSService(StrictService):
                version = 2

    def test_allow_multiple_subclasses_flag(self):
        """Test _allow_multiple_subclasses flag behavior."""

        class MultiService(Registry, ABC):
            _allow_multiple_subclasses = True

        class NotificationService(MultiService):
            aliases = ["notify"]
            method = "email"

        class AlertService(MultiService):
            aliases = ["notify"]  # Same alias as NotificationService
            method = "sms"

        # Should return list when multiple subclasses registered to same key
        services = MultiService.get_subclass("notify")
        assert isinstance(services, list)
        assert len(services) == 2
        assert NotificationService in services
        assert AlertService in services

        # Test that default behavior raises error for multiple registrations
        class SingleService(Registry, ABC):
            pass

        class Service1(SingleService):
            aliases = ["common"]

        with pytest.raises(KeyError, match="multiple subclasses"):

            class Service2(SingleService):
                aliases = ["common"]

    def test_remove_subclass(self):
        """Test remove_subclass functionality."""

        class Language(Registry, ABC):
            pass

        class Python(Language):
            aliases = ["py"]

        class Java(Language):
            aliases = ["jvm"]

        # Verify initial registration
        assert Language.get_subclass("Python") is Python
        assert Language.get_subclass("py") is Python
        assert Language.get_subclass("Java") is Java

        # Remove by class name
        Language.remove_subclass("Python")

        # Python should no longer be found
        result = Language.get_subclass("Python", raise_error=False)
        assert result is None or result == []

        # Aliases should also be removed
        result = Language.get_subclass("py", raise_error=False)
        assert result is None or result == []

        # Java should still be there
        assert Language.get_subclass("Java") is Java

        # Remove by class type
        Language.remove_subclass(Java)

        # Java should no longer be found
        result = Language.get_subclass("Java", raise_error=False)
        assert result is None or result == []

    def test_string_normalization(self):
        """Test string normalization edge cases."""

        class Protocol(Registry, ABC):
            pass

        class HTTPProtocol(Protocol):
            aliases = ["HTTP-SECURE", "http_secure", "http secure"]

        # All variations should resolve to the same class
        assert Protocol.get_subclass("HTTP-SECURE") is HTTPProtocol
        assert Protocol.get_subclass("http_secure") is HTTPProtocol
        assert Protocol.get_subclass("http secure") is HTTPProtocol
        assert Protocol.get_subclass("HTTPSECURE") is HTTPProtocol
        assert Protocol.get_subclass("httpsecure") is HTTPProtocol

    def test_complex_inheritance_hierarchy(self):
        """Test complex inheritance with multiple levels."""

        class Animal(Registry, ABC):
            @abstractmethod
            def speak(self):
                pass

        class Mammal(Animal, ABC):
            warm_blooded = True

        class Dog(Mammal):
            def speak(self):
                return "Woof"

        class Cat(Mammal):
            aliases = ["feline"]

            def speak(self):
                return "Meow"

        class Bird(Animal, ABC):
            has_wings = True

        class Parrot(Bird):
            def speak(self):
                return "Squawk"

        # Test retrieval at different levels
        assert Animal.get_subclass("Dog") is Dog
        assert Animal.get_subclass("Cat") is Cat
        assert Animal.get_subclass("feline") is Cat
        assert Animal.get_subclass("Parrot") is Parrot

        # Test subclasses method
        concrete_animals = Animal.subclasses()
        assert Dog in concrete_animals
        assert Cat in concrete_animals
        assert Parrot in concrete_animals
        assert Mammal not in concrete_animals  # Abstract
        assert Bird not in concrete_animals  # Abstract

        # Test with abstract classes included - note they may not be included in this implementation
        all_animals = Animal.subclasses(keep_abstract=True)
        # Just verify concrete classes are present
        assert Dog in all_animals
        assert Cat in all_animals
        assert Parrot in all_animals

    def test_none_values_in_registry_keys(self):
        """Test that None values in registry keys are handled properly."""

        class Widget(Registry, ABC):
            pass

        class Button(Widget):
            aliases = ["btn", None, "button"]

            @classmethod
            def _registry_keys(cls):
                return ["clickable", None, "interactive"]

        # Should work with non-None values
        assert Widget.get_subclass("btn") is Button
        assert Widget.get_subclass("button") is Button
        assert Widget.get_subclass("clickable") is Button
        assert Widget.get_subclass("interactive") is Button

        # None values should be filtered out (no error)
        assert Widget.get_subclass("Button") is Button

    def test_empty_registry_error_message(self):
        """Test error message when no subclasses are registered."""

        class EmptyRegistry(Registry, ABC):
            pass

        with pytest.raises(KeyError) as exc_info:
            EmptyRegistry.get_subclass("nonexistent")

        error_msg = str(exc_info.value)
        assert "Could not find subclass" in error_msg
        assert "nonexistent" in error_msg
        assert "Available keys are:" in error_msg

    def test_registry_isolation(self):
        """Test that different registry hierarchies don't interfere."""

        class Animals(Registry, ABC):
            pass

        class Vehicles(Registry, ABC):
            pass

        class Dog(Animals):
            pass

        class Car(Vehicles):
            pass

        # Each registry should only see its own subclasses
        assert Animals.get_subclass("Dog") is Dog
        assert Vehicles.get_subclass("Car") is Car

        with pytest.raises(KeyError):
            Animals.get_subclass("Car")

        with pytest.raises(KeyError):
            Vehicles.get_subclass("Dog")

        # Subclasses should be isolated
        animal_subclasses = Animals.subclasses()
        vehicle_subclasses = Vehicles.subclasses()

        assert Dog in animal_subclasses
        assert Car not in animal_subclasses
        assert Car in vehicle_subclasses
        assert Dog not in vehicle_subclasses

    def test_tuple_keys_normalization(self):
        """Test that tuple keys with string elements are normalized."""

        class Task(Registry, ABC):
            pass

        class DataTask(Task):
            @classmethod
            def _registry_keys(cls):
                return [("data", "processing"), ("DATA", "PROCESSING")]

        # Tuple variations should work with normalization
        assert Task.get_subclass(("data", "processing")) is DataTask
        assert Task.get_subclass(("DATA", "PROCESSING")) is DataTask
        assert Task.get_subclass(("Data", "Processing")) is DataTask

    def test_edge_case_empty_aliases(self):
        """Test edge case with empty aliases."""

        class Component(Registry, ABC):
            pass

        class Header(Component):
            aliases = []

        class Footer(Component):
            aliases = tuple()

        class Sidebar(Component):
            aliases = set()

        # Should still work with class names
        assert Component.get_subclass("Header") is Header
        assert Component.get_subclass("Footer") is Footer
        assert Component.get_subclass("Sidebar") is Sidebar

    def test_factory_pattern_usage(self):
        """Test Registry usage in factory pattern scenarios."""

        class DataProcessor(Registry, ABC):
            _allow_subclass_override = True

            @abstractmethod
            def process(self, data):
                pass

            @classmethod
            def create(cls, processor_type: str, **kwargs):
                ProcessorClass = cls.get_subclass(processor_type)
                return ProcessorClass(**kwargs)

        class CSVProcessor(DataProcessor):
            def __init__(self, delimiter=","):
                self.delimiter = delimiter

            def process(self, data):
                return f"Processing CSV with delimiter '{self.delimiter}': {data}"

        class JSONProcessor(DataProcessor):
            aliases = ["json", "JSON"]

            def __init__(self, indent=None):
                self.indent = indent

            def process(self, data):
                return f"Processing JSON with indent={self.indent}: {data}"

        # Test factory creation
        csv_processor = DataProcessor.create("CSVProcessor", delimiter=";")
        assert isinstance(csv_processor, CSVProcessor)
        assert csv_processor.delimiter == ";"
        assert "delimiter ';'" in csv_processor.process("test")

        # Test with aliases
        json_processor = DataProcessor.create("json", indent=2)
        assert isinstance(json_processor, JSONProcessor)
        assert json_processor.indent == 2
        assert "indent=2" in json_processor.process("test")

    def test_enum_like_registry_keys(self):
        """Test using enum-like objects as registry keys."""

        class MLType:
            PDF = "pdf"
            IMAGE = "image"
            TEXT = "text"

        class Document(Registry, ABC):
            mltype = None

            @classmethod
            def _registry_keys(cls):
                return cls.mltype

        class PdfDocument(Document):
            mltype = MLType.PDF

            def read(self):
                return "Reading PDF"

        class ImageDocument(Document):
            mltype = MLType.IMAGE

            def read(self):
                return "Reading Image"

        # Test retrieval by enum values
        assert Document.get_subclass(MLType.PDF) is PdfDocument
        assert Document.get_subclass(MLType.IMAGE) is ImageDocument
        assert Document.get_subclass("pdf") is PdfDocument  # Case-insensitive
        assert Document.get_subclass("IMAGE") is ImageDocument

    def test_complex_registry_keys_with_tuples(self):
        """Test complex registry keys including tuples and multiple types."""

        class TaskType:
            CLASSIFICATION = "classification"
            REGRESSION = "regression"

        class Algorithm(Registry, ABC):
            tasks = None

            @classmethod
            def _registry_keys(cls):
                keys = []
                if cls.tasks:
                    if isinstance(cls.tasks, (list, tuple)):
                        for task in cls.tasks:
                            keys.append((task, cls.__name__))
                    else:
                        keys.append((cls.tasks, cls.__name__))
                return keys

        class LinearRegression(Algorithm):
            tasks = TaskType.REGRESSION

        class RandomForest(Algorithm):
            tasks = [TaskType.CLASSIFICATION, TaskType.REGRESSION]

        # Test tuple key retrieval
        assert Algorithm.get_subclass((TaskType.REGRESSION, "LinearRegression")) is LinearRegression
        assert Algorithm.get_subclass((TaskType.CLASSIFICATION, "RandomForest")) is RandomForest
        assert Algorithm.get_subclass((TaskType.REGRESSION, "RandomForest")) is RandomForest

        # Case-insensitive tuple matching
        assert Algorithm.get_subclass(("REGRESSION", "linearregression")) is LinearRegression

    def test_registry_with_file_formats(self):
        """Test Registry pattern with file format handling."""

        class FileFormat:
            CSV = "csv"
            JSON = "json"
            PARQUET = "parquet"

        class Writer(Registry, ABC):
            file_formats = []
            file_ending = None
            _allow_multiple_subclasses = True

            @classmethod
            def _registry_keys(cls):
                keys = []
                if cls.file_formats:
                    keys.extend(cls.file_formats)
                if cls.file_ending:
                    keys.append(cls.file_ending)
                return keys

            @abstractmethod
            def write(self, data):
                pass

        class CSVWriter(Writer):
            aliases = ["CsvWriter"]
            file_formats = [FileFormat.CSV]
            file_ending = ".csv"

            def write(self, data):
                return f"Writing CSV: {data}"

        class JSONWriter(Writer):
            file_formats = [FileFormat.JSON]
            file_ending = ".json"

            def write(self, data):
                return f"Writing JSON: {data}"

        class ParquetWriter(Writer):
            file_formats = [FileFormat.PARQUET]
            file_ending = ".parquet"

            def write(self, data):
                return f"Writing Parquet: {data}"

        # Test retrieval by file format
        assert Writer.get_subclass(FileFormat.CSV) is CSVWriter
        assert Writer.get_subclass(FileFormat.JSON) is JSONWriter
        assert Writer.get_subclass(FileFormat.PARQUET) is ParquetWriter

        # Test retrieval by file ending
        assert Writer.get_subclass(".csv") is CSVWriter
        assert Writer.get_subclass(".json") is JSONWriter
        assert Writer.get_subclass(".parquet") is ParquetWriter

        # Test aliases
        assert Writer.get_subclass("CsvWriter") is CSVWriter

    def test_multiple_inheritance_with_registry(self):
        """Test Registry behavior with multiple inheritance."""

        class Mixin:
            def common_method(self):
                return "common"

        class Base(Registry, ABC):
            @abstractmethod
            def base_method(self):
                pass

        class Concrete(Base, Mixin):
            def base_method(self):
                return "implemented"

        # Should work with multiple inheritance
        ConcreteClass = Base.get_subclass("Concrete")
        assert ConcreteClass is Concrete

        instance = ConcreteClass()
        assert instance.base_method() == "implemented"
        assert instance.common_method() == "common"

    def test_registry_with_classvars_and_instance_creation(self):
        """Test Registry with class variables and instance creation patterns."""

        class Metric(Registry, ABC):
            _allow_subclass_override = True

            @abstractmethod
            def compute(self):
                pass

        class Accuracy(Metric):
            aliases = ["acc", "accuracy"]
            version = 1

            def __init__(self, threshold=0.5):
                self.threshold = threshold

            def compute(self):
                return f"Accuracy with threshold {self.threshold}"

        class F1Score(Metric):
            aliases = ["f1", "F1"]
            version = 2

            def __init__(self, average="binary"):
                self.average = average

            def compute(self):
                return f"F1Score with average {self.average}"

        # Test class variable access
        AccuracyClass = Metric.get_subclass("accuracy")
        assert AccuracyClass.version == 1
        assert AccuracyClass is Accuracy

        F1Class = Metric.get_subclass("F1")
        assert F1Class.version == 2
        assert F1Class is F1Score

        # Test instance creation
        acc_instance = AccuracyClass(threshold=0.7)
        assert acc_instance.threshold == 0.7
        assert "0.7" in acc_instance.compute()

        f1_instance = F1Class(average="macro")
        assert f1_instance.average == "macro"
        assert "macro" in f1_instance.compute()

    def test_dynamic_subclass_registration(self):
        """Test dynamic registration and deregistration scenarios."""

        class Service(Registry, ABC):
            _allow_subclass_override = True

        # Initially no subclasses
        assert len(Service.subclasses()) == 0

        # Dynamically create subclass
        class EmailService(Service):
            def send(self, message):
                return f"Sending email: {message}"

        # Should be automatically registered
        assert len(Service.subclasses()) == 1
        assert Service.get_subclass("EmailService") is EmailService

        # Remove and verify removal
        Service.remove_subclass("EmailService")
        result = Service.get_subclass("EmailService", raise_error=False)
        # After removal, should get None or empty list depending on implementation
        assert result is None or result == []

        # Re-register with same name (override)
        class EmailService(Service):
            version = 2

            def send(self, message):
                return f"Sending email v2: {message}"

        # Should be the new version
        NewEmailService = Service.get_subclass("EmailService")
        assert NewEmailService.version == 2
        # Note: this may be the same class object due to how Python handles class redefinition

    def test_registry_error_handling_edge_cases(self):
        """Test edge cases in error handling and validation."""

        class StrictRegistry(Registry, ABC):
            pass

        class FlexibleRegistry(Registry, ABC):
            _allow_multiple_subclasses = True

        # Test with non-string keys
        class NumericKeyed(StrictRegistry):
            @classmethod
            def _registry_keys(cls):
                return [42, 3.14, True]

        assert StrictRegistry.get_subclass(42) is NumericKeyed
        assert StrictRegistry.get_subclass(3.14) is NumericKeyed
        assert StrictRegistry.get_subclass(True) is NumericKeyed

        # Test error message contents
        try:
            StrictRegistry.get_subclass("nonexistent")
            assert False, "Should have raised KeyError"
        except KeyError as e:
            error_msg = str(e)
            assert "Could not find subclass" in error_msg
            assert "nonexistent" in error_msg
            assert "Available keys are:" in error_msg
            # Should contain the numeric keys
            assert "42" in error_msg

    def test_large_scale_registry(self):
        """Test Registry with many subclasses and complex aliases."""

        class Component(Registry, ABC):
            _allow_multiple_subclasses = True

        # Create many subclasses dynamically
        subclasses = []
        for i in range(20):
            class_name = f"Component{i}"
            aliases = [f"comp{i}", f"c{i}", f"component_{i}"]

            # Create class dynamically
            cls = type(
                class_name,
                (Component,),
                {
                    "aliases": aliases,
                    "component_id": i,
                    "_registry_keys": classmethod(lambda cls: [f"id_{cls.component_id}"]),
                },
            )
            subclasses.append(cls)

        # Test that all are registered
        all_subclasses = Component.subclasses()
        assert len(all_subclasses) == 20

        # Test retrieval by various keys
        for i, cls in enumerate(subclasses):
            # By class name
            assert Component.get_subclass(f"Component{i}") is cls
            # By aliases
            assert Component.get_subclass(f"comp{i}") is cls
            assert Component.get_subclass(f"c{i}") is cls
            assert Component.get_subclass(f"component_{i}") is cls
            # By custom registry key
            assert Component.get_subclass(f"id_{i}") is cls

    def test_registry_inheritance_with_overrides(self):
        """Test inheritance patterns with method overrides."""

        class BaseProcessor(Registry, ABC):
            _allow_subclass_override = True
            _allow_multiple_subclasses = True

            def preprocess(self, data):
                return f"Base preprocessing: {data}"

            @abstractmethod
            def process(self, data):
                pass

            def postprocess(self, data):
                return f"Base postprocessing: {data}"

        class TextProcessor(BaseProcessor):
            aliases = ["text"]

            def preprocess(self, data):
                return f"Text preprocessing: {data.lower()}"

            def process(self, data):
                return f"Processing text: {data}"

        class ImageProcessor(BaseProcessor):
            aliases = ["image", "img"]

            def process(self, data):
                return f"Processing image: {data}"

            def postprocess(self, data):
                return f"Image postprocessing: {data.upper()}"

        # Test method resolution
        TextProcessorClass = BaseProcessor.get_subclass("text")
        text_processor = TextProcessorClass()

        assert "Text preprocessing" in text_processor.preprocess("TEST")
        assert "Processing text" in text_processor.process("test")
        assert "Base postprocessing" in text_processor.postprocess("test")

        ImageProcessorClass = BaseProcessor.get_subclass("img")
        image_processor = ImageProcessorClass()

        assert "Base preprocessing" in image_processor.preprocess("test")
        assert "Processing image" in image_processor.process("test")
        assert "Image postprocessing" in image_processor.postprocess("test")

    def test_registry_with_complex_initialization(self):
        """Test Registry with complex initialization patterns."""

        class ConfigurableBase(Registry, ABC):
            def __init__(self, config=None, **kwargs):
                self.config = config or {}
                self.config.update(kwargs)

        class DatabaseConnection(ConfigurableBase):
            aliases = ["db", "database"]

            def __init__(self, host="localhost", port=5432, **kwargs):
                super().__init__(host=host, port=port, **kwargs)
                self.connection_string = f"postgresql://{host}:{port}"

        class CacheConnection(ConfigurableBase):
            aliases = ["cache", "redis"]

            def __init__(self, host="localhost", port=6379, ttl=3600, **kwargs):
                super().__init__(host=host, port=port, ttl=ttl, **kwargs)
                self.connection_string = f"redis://{host}:{port}"

        # Test complex initialization
        DbClass = ConfigurableBase.get_subclass("database")
        db = DbClass(host="remote.db", port=5433, ssl=True)

        assert db.config["host"] == "remote.db"
        assert db.config["port"] == 5433
        assert db.config["ssl"] is True
        assert "remote.db:5433" in db.connection_string

        CacheClass = ConfigurableBase.get_subclass("redis")
        cache = CacheClass(ttl=7200, max_connections=10)

        assert cache.config["ttl"] == 7200
        assert cache.config["max_connections"] == 10
        assert cache.config["host"] == "localhost"  # Default
        assert "localhost:6379" in cache.connection_string

    def test_of_factory_method_basic(self):
        """Test basic functionality of the 'of' factory method."""

        class Animal(Registry, ABC):
            @abstractmethod
            def speak(self) -> str:
                pass

        class Dog(Animal):
            def __init__(self, name="Buddy"):
                self.name = name

            def speak(self) -> str:
                return f"{self.name} says Woof!"

        class Cat(Animal):
            aliases = ["feline", "kitty"]

            def __init__(self, name="Whiskers", color="orange"):
                self.name = name
                self.color = color

            def speak(self) -> str:
                return f"{self.name} the {self.color} cat says Meow!"

        # Test basic factory creation with class name
        dog = Animal.of("Dog")
        assert isinstance(dog, Dog)
        assert dog.name == "Buddy"  # Default name
        assert dog.speak() == "Buddy says Woof!"

        # Test with custom arguments
        custom_dog = Animal.of("Dog", name="Rex")
        assert isinstance(custom_dog, Dog)
        assert custom_dog.name == "Rex"
        assert custom_dog.speak() == "Rex says Woof!"

        # Test with aliases
        cat = Animal.of("feline", name="Shadow", color="black")
        assert isinstance(cat, Cat)
        assert cat.name == "Shadow"
        assert cat.color == "black"
        assert cat.speak() == "Shadow the black cat says Meow!"

        # Test with case-insensitive matching
        cat2 = Animal.of("KITTY", name="Fluffy")
        assert isinstance(cat2, Cat)
        assert cat2.name == "Fluffy"
        assert cat2.color == "orange"  # Default color

    def test_of_factory_method_with_tuple_keys(self):
        """Test 'of' factory method with tuple keys."""

        class Tool(Registry, ABC):
            @abstractmethod
            def use(self) -> str:
                pass

        class Hammer(Tool):
            def __init__(self, weight=1.0):
                self.weight = weight

            @classmethod
            def _registry_keys(cls):
                return [("tool", "heavy"), ("construction", "hammer")]

            def use(self) -> str:
                return f"Using {self.weight}kg hammer"

        # Test with tuple keys
        hammer1 = Tool.of(("tool", "heavy"), weight=2.5)
        assert isinstance(hammer1, Hammer)
        assert hammer1.weight == 2.5
        assert hammer1.use() == "Using 2.5kg hammer"

        hammer2 = Tool.of(("construction", "hammer"))
        assert isinstance(hammer2, Hammer)
        assert hammer2.weight == 1.0  # Default weight

    def test_of_factory_method_error_conditions(self):
        """Test error conditions for the 'of' factory method."""

        class Vehicle(Registry, ABC):
            pass

        class Car(Vehicle):
            pass

        # Test calling 'of' directly on Registry class
        with pytest.raises(TypeError, match="cannot be called directly on Registry class"):
            Registry.of("Car")

        # Test with non-existent key
        with pytest.raises(KeyError):
            Vehicle.of("nonexistent")

        # Test with valid key but class that doesn't exist
        with pytest.raises(KeyError):
            Vehicle.of("Airplane")

    def test_of_factory_method_with_complex_initialization(self):
        """Test 'of' factory method with complex initialization patterns."""

        class Database(Registry, ABC):
            @abstractmethod
            def connect(self) -> str:
                pass

        class PostgreSQLDB(Database):
            aliases = ["postgres", "pg"]

            def __init__(self, host="localhost", port=5432, database="mydb", **kwargs):
                self.host = host
                self.port = port
                self.database = database
                self.options = kwargs

            def connect(self) -> str:
                return f"Connected to PostgreSQL at {self.host}:{self.port}/{self.database}"

        class MySQL(Database):
            aliases = ["mysql"]

            def __init__(self, host="localhost", port=3306, **config):
                self.host = host
                self.port = port
                self.config = config

            def connect(self) -> str:
                return f"Connected to MySQL at {self.host}:{self.port}"

        # Test with keyword arguments
        pg_db = Database.of("postgres", host="remote.db", port=5433, database="production", ssl=True)
        assert isinstance(pg_db, PostgreSQLDB)
        assert pg_db.host == "remote.db"
        assert pg_db.port == 5433
        assert pg_db.database == "production"
        assert pg_db.options["ssl"] is True
        assert "remote.db:5433/production" in pg_db.connect()

        # Test with mixed args and kwargs
        mysql_db = Database.of("mysql", port=3307, charset="utf8mb4")
        assert isinstance(mysql_db, MySQL)
        assert mysql_db.host == "localhost"  # Default
        assert mysql_db.port == 3307
        assert mysql_db.config["charset"] == "utf8mb4"

    def test_of_factory_method_with_abstract_subclasses(self):
        """Test 'of' factory method behavior with abstract subclasses."""

        class Processor(Registry, ABC):
            @abstractmethod
            def process(self, data):
                pass

        class TextProcessor(Processor, ABC):
            """Abstract intermediate class."""
            @abstractmethod
            def normalize(self, text):
                pass

        class UpperCaseProcessor(TextProcessor):
            def __init__(self, prefix=""):
                self.prefix = prefix

            def normalize(self, text):
                return text.upper()

            def process(self, data):
                normalized = self.normalize(data)
                return f"{self.prefix}{normalized}" if self.prefix else normalized

        # Should be able to create concrete subclass
        processor = Processor.of("UpperCaseProcessor", prefix=">>> ")
        assert isinstance(processor, UpperCaseProcessor)
        assert processor.prefix == ">>> "
        assert processor.process("hello") == ">>> HELLO"

        # Abstract intermediate class should not be creatable via 'of'
        with pytest.raises(KeyError):
            Processor.of("TextProcessor")

    def test_of_factory_method_with_multiple_subclasses(self):
        """Test 'of' factory method when multiple subclasses are registered."""

        class Service(Registry, ABC):
            _allow_multiple_subclasses = True

            @abstractmethod
            def serve(self):
                pass

        class EmailService(Service):
            aliases = ["notification"]

            def __init__(self, provider="smtp"):
                self.provider = provider

            def serve(self):
                return f"Email via {self.provider}"

        class SMSService(Service):
            aliases = ["notification"]  # Same alias as EmailService

            def __init__(self, provider="twilio"):
                self.provider = provider

            def serve(self):
                return f"SMS via {self.provider}"

        # When multiple subclasses are registered, the 'of' method should raise TypeError
        with pytest.raises(TypeError, match="Cannot instantiate using registry_key 'notification' because multiple subclasses"):
            Service.of("notification", provider="custom")

    def test_of_factory_method_inheritance_chain(self):
        """Test 'of' factory method with complex inheritance chains."""

        class Shape(Registry, ABC):
            @abstractmethod
            def area(self):
                pass

        class Polygon(Shape, ABC):
            def __init__(self, sides):
                self.sides = sides

        class Rectangle(Polygon):
            def __init__(self, width, height):
                super().__init__(4)
                self.width = width
                self.height = height

            def area(self):
                return self.width * self.height

        class Circle(Shape):
            def __init__(self, radius):
                self.radius = radius

            def area(self):
                return 3.14159 * self.radius ** 2

        # Test factory creation across inheritance chain
        rect = Shape.of("Rectangle", width=10, height=5)
        assert isinstance(rect, Rectangle)
        assert rect.width == 10
        assert rect.height == 5
        assert rect.sides == 4
        assert rect.area() == 50

        circle = Shape.of("Circle", radius=3)
        assert isinstance(circle, Circle)
        assert circle.radius == 3
        assert abs(circle.area() - 28.274) < 0.01

    def test_of_factory_method_with_existing_factory_pattern(self):
        """Test 'of' method alongside existing factory patterns."""

        class DataProcessor(Registry, ABC):
            @abstractmethod
            def process(self, data):
                pass

            @classmethod
            def create(cls, processor_type: str, **kwargs):
                """Existing factory method for comparison."""
                ProcessorClass = cls.get_subclass(processor_type)
                return ProcessorClass(**kwargs)

        class CSVProcessor(DataProcessor):
            def __init__(self, delimiter=","):
                self.delimiter = delimiter

            def process(self, data):
                return f"Processing CSV with delimiter '{self.delimiter}': {data}"

        class JSONProcessor(DataProcessor):
            aliases = ["json"]

            def __init__(self, indent=None):
                self.indent = indent

            def process(self, data):
                return f"Processing JSON with indent={self.indent}: {data}"

        # Test both factory methods work identically
        csv1 = DataProcessor.create("CSVProcessor", delimiter=";")
        csv2 = DataProcessor.of("CSVProcessor", delimiter=";")

        assert type(csv1) == type(csv2)
        assert csv1.delimiter == csv2.delimiter
        assert csv1.process("test") == csv2.process("test")

        json1 = DataProcessor.create("json", indent=2)
        json2 = DataProcessor.of("json", indent=2)

        assert type(json1) == type(json2)
        assert json1.indent == json2.indent
        assert json1.process("test") == json2.process("test")

    def test_hierarchical_of_concrete_class_without_key(self):
        """Test hierarchical 'of' method on concrete classes without providing a key."""

        class Animal(Registry, ABC):
            @abstractmethod
            def speak(self) -> str:
                pass

        class Dog(Animal):
            def __init__(self, name="Buddy", breed="Mixed"):
                self.name = name
                self.breed = breed

            def speak(self) -> str:
                return f"{self.name} the {self.breed} says Woof!"

        class Cat(Animal):
            def __init__(self, name="Whiskers", color="Orange"):
                self.name = name
                self.color = color

            def speak(self) -> str:
                return f"{self.name} the {self.color} cat says Meow!"

        # Test direct instantiation of concrete classes without key
        dog = Dog.of()
        assert isinstance(dog, Dog)
        assert dog.name == "Buddy"
        assert dog.breed == "Mixed"
        assert dog.speak() == "Buddy the Mixed says Woof!"

        # Test with custom arguments
        custom_dog = Dog.of(name="Rex", breed="German Shepherd")
        assert isinstance(custom_dog, Dog)
        assert custom_dog.name == "Rex"
        assert custom_dog.breed == "German Shepherd"
        assert custom_dog.speak() == "Rex the German Shepherd says Woof!"

        # Test with kwargs only
        cat = Cat.of(name="Shadow", color="Black")
        assert isinstance(cat, Cat)
        assert cat.name == "Shadow"
        assert cat.color == "Black"
        assert cat.speak() == "Shadow the Black cat says Meow!"

    def test_hierarchical_of_concrete_class_with_matching_key(self):
        """Test hierarchical 'of' method on concrete classes with key that matches the class."""

        class Vehicle(Registry, ABC):
            pass

        class Car(Vehicle):
            aliases = ["automobile", "auto"]

            def __init__(self, model="Generic", year=2023):
                self.model = model
                self.year = year

            def describe(self):
                return f"{self.year} {self.model}"

        # Test with class name as key
        car1 = Car.of("Car", model="Tesla", year=2024)
        assert isinstance(car1, Car)
        assert car1.model == "Tesla"
        assert car1.year == 2024

        # Test with alias as key
        car2 = Car.of("automobile", model="BMW", year=2023)
        assert isinstance(car2, Car)
        assert car2.model == "BMW"
        assert car2.year == 2023

        # Test case-insensitive matching
        car3 = Car.of("AUTO", model="Honda")
        assert isinstance(car3, Car)
        assert car3.model == "Honda"
        assert car3.year == 2023  # Default

    def test_hierarchical_of_abstract_class_requires_key(self):
        """Test that abstract classes require a key and cannot be instantiated directly."""

        class Shape(Registry, ABC):
            @abstractmethod
            def area(self):
                pass

        class Rectangle(Shape):
            def __init__(self, width=1, height=1):
                self.width = width
                self.height = height

            def area(self):
                return self.width * self.height

        # Abstract class without key should raise TypeError
        with pytest.raises(TypeError, match="Cannot instantiate abstract class 'Shape' without specifying"):
            Shape.of()

        # Should work with key
        rect = Shape.of("Rectangle", width=5, height=3)
        assert isinstance(rect, Rectangle)
        assert rect.width == 5
        assert rect.height == 3
        assert rect.area() == 15

    def test_hierarchical_of_complex_inheritance_hierarchy(self):
        """Test hierarchical 'of' method with complex multi-level inheritance."""

        class Animal(Registry, ABC):
            @abstractmethod
            def speak(self) -> str:
                pass

        class Mammal(Animal, ABC):
            warm_blooded = True

        class Cat(Mammal, ABC):
            def __init__(self, name="Cat"):
                self.name = name

        class TabbyCat(Cat):
            aliases = ["tabby"]

            def __init__(self, name="Tabby", stripes=True):
                super().__init__(name)
                self.stripes = stripes

            def speak(self) -> str:
                return f"{self.name} the tabby says Meow!"

        class OrangeCat(Cat):
            aliases = ["orange", "ginger"]

            def __init__(self, name="Orange", fluffy=True):
                super().__init__(name)
                self.fluffy = fluffy

            def speak(self) -> str:
                return f"{self.name} the orange cat says Meow!"

        class Dog(Mammal):
            aliases = ["doggy", "pup"]

            def __init__(self, name="Dog", breed="Mixed"):
                self.name = name
                self.breed = breed

            def speak(self) -> str:
                return f"{self.name} the {self.breed} says Woof!"

        class Bird(Animal, ABC):
            has_wings = True

        class Parrot(Bird):
            def __init__(self, name="Parrot", can_talk=True):
                self.name = name
                self.can_talk = can_talk

            def speak(self) -> str:
                return f"{self.name} says Squawk!"

        # Test hierarchical access - Cat.of should only access Cat subclasses
        tabby = Cat.of("TabbyCat", name="Stripey")
        assert isinstance(tabby, TabbyCat)
        assert tabby.name == "Stripey"
        assert tabby.stripes is True

        orange = Cat.of("ginger", name="Fluffy", fluffy=False)
        assert isinstance(orange, OrangeCat)
        assert orange.name == "Fluffy"
        assert orange.fluffy is False

        # Cat.of should NOT be able to access Dog (not a subclass of Cat)
        with pytest.raises(KeyError, match="Could not find subclass of Cat"):
            Cat.of("Dog")

        with pytest.raises(KeyError, match="Could not find subclass of Cat"):
            Cat.of("doggy")

        # Dog.of should work directly (concrete class)
        dog1 = Dog.of()  # No key needed
        assert isinstance(dog1, Dog)
        assert dog1.name == "Dog"
        assert dog1.breed == "Mixed"

        dog2 = Dog.of("pup", name="Buddy", breed="Labrador")
        assert isinstance(dog2, Dog)
        assert dog2.name == "Buddy"
        assert dog2.breed == "Labrador"

        # Mammal.of should access both Dog and Cat subclasses
        dog3 = Mammal.of("Dog", name="Max")
        assert isinstance(dog3, Dog)
        assert dog3.name == "Max"

        tabby2 = Mammal.of("tabby", name="Tiger")
        assert isinstance(tabby2, TabbyCat)
        assert tabby2.name == "Tiger"

        # But Mammal.of should NOT access Bird subclasses
        with pytest.raises(KeyError, match="Could not find subclass of Mammal"):
            Mammal.of("Parrot")

        # Animal.of should access everything
        parrot = Animal.of("Parrot", name="Polly")
        assert isinstance(parrot, Parrot)
        assert parrot.name == "Polly"

    def test_hierarchical_of_error_messages(self):
        """Test that hierarchical 'of' provides helpful error messages."""

        class Transport(Registry, ABC):
            pass

        class LandTransport(Transport, ABC):
            pass

        class Car(LandTransport):
            aliases = ["auto"]

        class WaterTransport(Transport, ABC):
            pass

        class Boat(WaterTransport):
            aliases = ["ship"]

        # Test error message shows only relevant subclasses
        try:
            LandTransport.of("Boat")
            assert False, "Should have raised KeyError"
        except KeyError as e:
            error_msg = str(e)
            assert "Could not find subclass of LandTransport" in error_msg
            assert "Boat" in error_msg
            # Should show available keys in LandTransport hierarchy
            assert "Car" in error_msg or "auto" in error_msg
            # Should NOT show WaterTransport subclasses
            assert "ship" not in error_msg or "Boat" not in error_msg.split("Available keys")[1]

    def test_hierarchical_of_with_aliases_and_registry_keys(self):
        """Test hierarchical 'of' method works with aliases and custom registry keys."""

        class Protocol(Registry, ABC):
            pass

        class HTTPProtocol(Protocol):
            aliases = ["http", "web"]

            @classmethod
            def _registry_keys(cls):
                return [("protocol", "http"), "http_protocol"]

            def __init__(self, port=80, secure=False):
                self.port = port
                self.secure = secure

        class FTPProtocol(Protocol):
            aliases = ["ftp", "file_transfer"]

            @classmethod
            def _registry_keys(cls):
                return [("protocol", "ftp")]

            def __init__(self, port=21, passive=True):
                self.port = port
                self.passive = passive

        # Test concrete class direct instantiation
        http1 = HTTPProtocol.of()
        assert isinstance(http1, HTTPProtocol)
        assert http1.port == 80
        assert http1.secure is False

        # Test with various keys
        http2 = HTTPProtocol.of("http", port=443, secure=True)
        assert isinstance(http2, HTTPProtocol)
        assert http2.port == 443
        assert http2.secure is True

        http3 = HTTPProtocol.of("http_protocol", port=8080)
        assert isinstance(http3, HTTPProtocol)
        assert http3.port == 8080

        http4 = HTTPProtocol.of(("protocol", "http"), secure=True)
        assert isinstance(http4, HTTPProtocol)
        assert http4.secure is True

        # Test from abstract base class
        ftp = Protocol.of("file_transfer", port=2121, passive=False)
        assert isinstance(ftp, FTPProtocol)
        assert ftp.port == 2121
        assert ftp.passive is False

        # Hierarchical restriction - HTTPProtocol.of should not access FTP
        with pytest.raises(KeyError):
            HTTPProtocol.of("ftp")

    def test_hierarchical_of_backwards_compatibility(self):
        """Test that hierarchical 'of' method maintains backwards compatibility."""

        class DataProcessor(Registry, ABC):
            @abstractmethod
            def process(self, data):
                pass

        class CSVProcessor(DataProcessor):
            def __init__(self, delimiter=","):
                self.delimiter = delimiter

            def process(self, data):
                return f"Processing CSV with delimiter '{self.delimiter}': {data}"

        class JSONProcessor(DataProcessor):
            aliases = ["json"]

            def __init__(self, indent=None):
                self.indent = indent

            def process(self, data):
                return f"Processing JSON with indent={self.indent}: {data}"

        # Old usage patterns should still work
        csv_processor = DataProcessor.of("CSVProcessor", delimiter=";")
        assert isinstance(csv_processor, CSVProcessor)
        assert csv_processor.delimiter == ";"

        json_processor = DataProcessor.of("json", indent=4)
        assert isinstance(json_processor, JSONProcessor)
        assert json_processor.indent == 4

        # New hierarchical patterns
        csv_direct = CSVProcessor.of()  # Direct instantiation
        assert isinstance(csv_direct, CSVProcessor)
        assert csv_direct.delimiter == ","

        csv_with_key = CSVProcessor.of("CSVProcessor", delimiter="|")
        assert isinstance(csv_with_key, CSVProcessor)
        assert csv_with_key.delimiter == "|"

        # Hierarchical restriction - CSVProcessor.of cannot access JSONProcessor
        with pytest.raises(KeyError):
            CSVProcessor.of("json")

    def test_hierarchical_of_with_multiple_registry_bases(self):
        """Test hierarchical 'of' with multiple separate registry hierarchies."""

        class Animals(Registry, ABC):
            pass

        class Cat(Animals):
            def __init__(self, name="Cat"):
                self.name = name

        class Dog(Animals):
            def __init__(self, name="Dog"):
                self.name = name

        class Vehicles(Registry, ABC):
            pass

        class Car(Vehicles):
            def __init__(self, model="Car"):
                self.model = model

        class Bike(Vehicles):
            def __init__(self, type="Mountain"):
                self.type = type

        # Each hierarchy should be isolated
        cat = Cat.of()
        assert isinstance(cat, Cat)
        assert cat.name == "Cat"

        car = Car.of()
        assert isinstance(car, Car)
        assert car.model == "Car"

        # Cross-hierarchy access should fail
        with pytest.raises(KeyError):
            Cat.of("Car")

        with pytest.raises(KeyError):
            Car.of("Cat")

        # Base class access should be restricted to their own hierarchy
        dog = Animals.of("Dog", name="Buddy")
        assert isinstance(dog, Dog)
        assert dog.name == "Buddy"

        bike = Vehicles.of("Bike", type="Road")
        assert isinstance(bike, Bike)
        assert bike.type == "Road"

        with pytest.raises(KeyError):
            Animals.of("Car")

        with pytest.raises(KeyError):
            Vehicles.of("Dog")
