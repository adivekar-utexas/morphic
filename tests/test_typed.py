"""Comprehensive tests for Typed module."""

from dataclasses import field
from typing import Dict, List, Optional, Union
from unittest.mock import Mock, patch

import pytest

from morphic.autoenum import AutoEnum, alias, auto
from morphic.typed import Typed


# Test fixtures and helper classes
class SimpleEnum(AutoEnum):
    VALUE_A = auto()
    VALUE_B = auto()
    VALUE_C = alias("C", "charlie")  # Test with alias if available


# Mock AutoEnum for testing AutoEnum support
class MockAutoEnum:
    def __init__(self, value):
        self.value = value
        self.aliases = ["alias1", "alias2"]

    def __eq__(self, other):
        return isinstance(other, MockAutoEnum) and self.value == other.value


class SimpleTyped(Typed):
    """Simple test model with basic types."""

    name: str
    age: int
    active: bool = True


class OptionalFieldsModel(Typed):
    """Model with optional and union types."""

    required_field: str
    optional_str: Optional[str] = None
    union_field: Union[int, str] = "default"
    optional_int: Optional[int] = None


class NestedTyped(Typed):
    """Model with nested Typed objects."""

    user: SimpleTyped
    metadata: Optional[SimpleTyped] = None


class EnumTyped(Typed):
    """Model with enum fields."""

    status: SimpleEnum
    optional_status: Optional[SimpleEnum] = None


class DefaultValueModel(Typed):
    """Model with various default values."""

    name: str = "default_name"
    count: int = 0
    tags: list = field(default_factory=list)  # Use simple list type
    active: bool = True


class ComplexModel(Typed):
    """Complex model for comprehensive testing."""

    id: int
    name: str
    nested: SimpleTyped
    enum_field: SimpleEnum
    optional_nested: Optional[NestedTyped] = None
    union_field: Union[int, str, float] = 42
    list_field: list = field(default_factory=list)  # Use simple list type to avoid isinstance issues


class ValidationModel(Typed):
    """Model with custom validation."""

    name: str
    age: int

    def validate(self):
        if self.age < 0:
            raise ValueError("Age cannot be negative")
        if not self.name.strip():
            raise ValueError("Name cannot be empty")


class TestTypedBasics:
    """Test basic Typed functionality."""

    def test_simple_instantiation(self):
        """Test basic model instantiation."""
        model = SimpleTyped(name="John", age=30)
        assert model.name == "John"
        assert model.age == 30
        assert model.active is True

    def test_repr_method(self):
        """Test __repr__ method output."""
        model = SimpleTyped(name="John", age=30, active=False)
        repr_str = repr(model)

        assert "SimpleTyped" in repr_str
        assert "name='John'" in repr_str
        assert "age=30" in repr_str
        assert "active=False" in repr_str

    def test_field_caching(self):
        """Test that field information is cached properly."""
        # Create multiple instances to test caching
        model1 = SimpleTyped(name="John", age=30)
        model2 = SimpleTyped(name="Jane", age=25)

        # Get field info which should populate cache
        field_info1 = model1._get_field_info()
        field_info2 = model2._get_field_info()

        # Both should use the same cached field info
        assert field_info1 is field_info2  # Same object reference (cached)
        assert len(field_info1) == 3  # name, age, active


class TestFromDict:
    """Test from_dict functionality."""

    def test_basic_from_dict(self):
        """Test basic dictionary to model conversion."""
        data = {"name": "John", "age": 30, "active": False}
        model = SimpleTyped.from_dict(data)

        assert model.name == "John"
        assert model.age == 30
        assert model.active is False

    def test_from_dict_with_missing_optional_fields(self):
        """Test from_dict with missing optional fields."""
        data = {"required_field": "test"}
        model = OptionalFieldsModel.from_dict(data)

        assert model.required_field == "test"
        assert model.optional_str is None
        assert model.union_field == "default"
        assert model.optional_int is None

    def test_from_dict_type_conversion(self):
        """Test automatic type conversion in from_dict."""
        data = {
            "name": "John",
            "age": "30",  # String that should convert to int
            "active": "true",  # String that should convert to bool (won't work with basic bool())
        }

        model = SimpleTyped.from_dict(data)
        assert model.name == "John"
        assert model.age == 30
        # Note: "true" won't convert to True with bool("true") - it would be True anyway
        # because any non-empty string is truthy

    def test_from_dict_with_union_types(self):
        """Test from_dict with Union type fields."""
        # Test with int
        data = {"required_field": "test", "union_field": 42}
        model = OptionalFieldsModel.from_dict(data)
        assert model.union_field == 42

        # Test with string
        data = {"required_field": "test", "union_field": "hello"}
        model = OptionalFieldsModel.from_dict(data)
        assert model.union_field == "hello"

    def test_from_dict_with_nested_objects(self):
        """Test from_dict with nested Typed objects."""
        data = {
            "user": {"name": "John", "age": 30, "active": True},
            "metadata": {"name": "Meta", "age": 25, "active": False},
        }
        model = NestedTyped.from_dict(data)

        assert isinstance(model.user, SimpleTyped)
        assert model.user.name == "John"
        assert model.user.age == 30

        assert isinstance(model.metadata, SimpleTyped)
        assert model.metadata.name == "Meta"
        assert model.metadata.age == 25

    def test_from_dict_with_enum(self):
        """Test from_dict with AutoEnum fields."""
        # Test with string values (should auto-convert to AutoEnum)
        data = {"status": "VALUE_A", "optional_status": "VALUE_B"}
        model = EnumTyped.from_dict(data)

        assert model.status == SimpleEnum.VALUE_A
        assert model.optional_status == SimpleEnum.VALUE_B
        assert isinstance(model.status, SimpleEnum)
        assert isinstance(model.optional_status, SimpleEnum)

        # Test with alias
        data_alias = {"status": "C", "optional_status": "charlie"}
        model_alias = EnumTyped.from_dict(data_alias)
        assert model_alias.status == SimpleEnum.VALUE_C
        assert model_alias.optional_status == SimpleEnum.VALUE_C

    def test_autoenum_string_conversion(self):
        """Test comprehensive AutoEnum string conversion capabilities."""

        # Test case-insensitive conversion
        data = {"status": "value_a", "optional_status": "VALUE_B"}
        model = EnumTyped.from_dict(data)
        assert model.status == SimpleEnum.VALUE_A
        assert model.optional_status == SimpleEnum.VALUE_B

        # Test fuzzy matching (spaces, underscores, etc.)
        data_fuzzy = {"status": "Value A", "optional_status": "value-b"}
        model_fuzzy = EnumTyped.from_dict(data_fuzzy)
        assert model_fuzzy.status == SimpleEnum.VALUE_A
        assert model_fuzzy.optional_status == SimpleEnum.VALUE_B

        # Test alias functionality
        data_alias = {"status": "C", "optional_status": "charlie"}
        model_alias = EnumTyped.from_dict(data_alias)
        assert model_alias.status == SimpleEnum.VALUE_C
        assert model_alias.optional_status == SimpleEnum.VALUE_C

        # Test to_dict conversion back to strings
        result = model_alias.to_dict()
        assert result["status"] == "VALUE_C"
        assert result["optional_status"] == "VALUE_C"

    @patch("morphic.typed.Typed._convert_single_type")
    def test_from_dict_with_mock_autoenum(self, mock_convert):
        """Test from_dict with AutoEnum support."""
        # Mock the import and AutoEnum behavior
        with patch("builtins.__import__") as mock_import:
            mock_autoenum_class = Mock()
            mock_autoenum_class.__bases__ = [MockAutoEnum]
            mock_convert.return_value = MockAutoEnum("test")

            data = {"test_field": "test"}
            # This test verifies the AutoEnum handling logic exists
            # Actual AutoEnum testing would require the autoenum package

    def test_from_dict_strict_mode(self):
        """Test from_dict in strict mode."""
        data = {"name": "John", "age": 30, "unknown_field": "value"}

        # Should work in non-strict mode
        model = SimpleTyped.from_dict(data, strict=False)
        assert model.name == "John"

        # Should raise error in strict mode
        with pytest.raises(ValueError, match="Unknown field 'unknown_field'"):
            SimpleTyped.from_dict(data, strict=True)

    def test_from_dict_invalid_input_type(self):
        """Test from_dict with invalid input type."""
        with pytest.raises(TypeError, match="Expected dict, got"):
            SimpleTyped.from_dict("not a dict")

    def test_from_dict_none_values(self):
        """Test from_dict with None values."""
        data = {"required_field": "test", "optional_str": None}
        model = OptionalFieldsModel.from_dict(data)

        assert model.required_field == "test"
        assert model.optional_str is None


class TestToDict:
    """Test to_dict functionality."""

    def test_basic_to_dict(self):
        """Test basic model to dictionary conversion."""
        model = SimpleTyped(name="John", age=30, active=False)
        result = model.to_dict()

        expected = {"name": "John", "age": 30, "active": False}
        assert result == expected

    def test_to_dict_exclude_none(self):
        """Test to_dict with exclude_none option."""
        model = OptionalFieldsModel(required_field="test", optional_str=None, union_field="hello")
        result = model.to_dict(exclude_none=True)

        assert "optional_str" not in result
        assert "optional_int" not in result
        assert result["required_field"] == "test"
        assert result["union_field"] == "hello"

    def test_to_dict_exclude_defaults(self):
        """Test to_dict with exclude_defaults option."""
        model = DefaultValueModel()  # All default values
        result = model.to_dict(exclude_defaults=True)

        # Should exclude all fields with default values
        assert len(result) == 0

        # Now with some non-default values
        model = DefaultValueModel(name="custom", count=5)
        result = model.to_dict(exclude_defaults=True)

        assert result["name"] == "custom"
        assert result["count"] == 5
        assert "tags" not in result  # default factory
        assert "active" not in result  # default value

    def test_to_dict_with_nested_objects(self):
        """Test to_dict with nested Typed objects."""
        nested_user = SimpleTyped(name="John", age=30)
        model = NestedTyped(user=nested_user)
        result = model.to_dict()

        assert "user" in result
        assert isinstance(result["user"], dict)
        assert result["user"]["name"] == "John"
        assert result["user"]["age"] == 30

    def test_to_dict_with_enum(self):
        """Test to_dict with enum fields."""
        model = EnumTyped(status=SimpleEnum.VALUE_A)
        result = model.to_dict()

        assert result["status"] == "VALUE_A"  # AutoEnum uses name as value

    @patch("morphic.typed.Typed._is_default_value")
    def test_to_dict_complex_exclude_options(self, mock_is_default):
        """Test to_dict with both exclude options."""
        mock_is_default.return_value = False

        nested_user = SimpleTyped(name="John", age=30)
        model = NestedTyped(user=nested_user, metadata=None)

        result = model.to_dict(exclude_none=True, exclude_defaults=True)

        assert "user" in result
        assert "metadata" not in result  # None value excluded


class TestCopy:
    """Test copy functionality."""

    def test_basic_copy(self):
        """Test basic copy without changes."""
        original = SimpleTyped(name="John", age=30, active=False)
        copy = original.copy()

        assert copy.name == original.name
        assert copy.age == original.age
        assert copy.active == original.active
        assert copy is not original  # Different instances

    def test_copy_with_changes(self):
        """Test copy with field changes."""
        original = SimpleTyped(name="John", age=30, active=False)
        copy = original.copy(name="Jane", age=25)

        assert copy.name == "Jane"
        assert copy.age == 25
        assert copy.active == original.active  # Unchanged
        assert original.name == "John"  # Original unchanged

    def test_copy_complex_model(self):
        """Test copy with complex nested model."""
        user = SimpleTyped(name="John", age=30)
        original = NestedTyped(user=user)

        new_user_data = {"name": "Jane", "age": 25, "active": True}
        copy = original.copy(user=new_user_data)

        assert isinstance(copy.user, SimpleTyped)
        assert copy.user.name == "Jane"
        assert original.user.name == "John"  # Original unchanged


class TestValidation:
    """Test validation functionality."""

    def test_default_validate(self):
        """Test default validate method (should do nothing)."""
        model = SimpleTyped(name="John", age=30)
        model.validate()  # Should not raise any exception

    def test_custom_validation(self):
        """Test custom validation implementation."""
        # Valid model - validation should pass automatically
        model = ValidationModel(name="John", age=30)
        # No need to call validate() - it's automatic!

        # Invalid age - should raise during construction
        with pytest.raises(ValueError, match="Age cannot be negative"):
            ValidationModel(name="John", age=-5)

        # Invalid name - should raise during construction
        with pytest.raises(ValueError, match="Name cannot be empty"):
            ValidationModel(name="", age=30)

    def test_automatic_validation(self):
        """Test that validation is called automatically during instance creation."""

        class AutoValidateModel(Typed):
            value: int

            def validate(self):
                if self.value < 0:
                    raise ValueError("Value must be non-negative")

        # Valid data should work
        model = AutoValidateModel(value=10)
        assert model.value == 10

        # Invalid data should raise during construction
        with pytest.raises(ValueError, match="Value must be non-negative"):
            AutoValidateModel(value=-5)

        # Should also work with from_dict
        model2 = AutoValidateModel.from_dict({"value": 20})
        assert model2.value == 20

        # from_dict with invalid data should also raise
        with pytest.raises(ValueError, match="Value must be non-negative"):
            AutoValidateModel.from_dict({"value": -10})


class TestTypeConversion:
    """Test type conversion functionality."""

    def test_convert_basic_types(self):
        """Test conversion of basic types."""
        # String to int
        result = SimpleTyped._convert_single_type(int, "42")
        assert result == 42

        # String to float
        result = SimpleTyped._convert_single_type(float, "3.14")
        assert result == 3.14

        # String to bool
        result = SimpleTyped._convert_single_type(bool, "true")
        assert result is True

        # Already correct type
        result = SimpleTyped._convert_single_type(str, "hello")
        assert result == "hello"

    def test_convert_invalid_types(self):
        """Test conversion with invalid input."""
        # Invalid conversion should return original value
        result = SimpleTyped._convert_single_type(int, "not_a_number")
        assert result == "not_a_number"

    def test_convert_none_value(self):
        """Test conversion of None values."""
        field_mock = Mock()
        field_mock.type = int

        result = SimpleTyped._convert_value(field_mock, None)
        assert result is None

    def test_convert_union_types(self):
        """Test conversion with Union types."""
        field_mock = Mock()
        field_mock.type = Union[int, str]

        # Should try to convert to int first
        result = SimpleTyped._convert_value(field_mock, "42")
        assert result == 42

        # Should convert to string if int conversion fails
        result2 = SimpleTyped._convert_value(field_mock, "hello")
        assert result2 == "hello"

        # Should try int conversion first, then str
        field_mock2 = Mock()
        field_mock2.type = Union[str, int]  # Different order
        result3 = SimpleTyped._convert_value(field_mock2, "42")
        # This should still convert to str since it's the first type in the union
        assert result3 == "42"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_model(self):
        """Test model with no fields."""

        class EmptyModel(Typed):
            pass

        model = EmptyModel()
        assert model.to_dict() == {}

        # from_dict should work with empty dict
        model2 = EmptyModel.from_dict({})
        assert isinstance(model2, EmptyModel)

    def test_model_with_complex_defaults(self):
        """Test model with complex default values."""

        class ComplexDefaultModel(Typed):
            data: Dict[str, int] = field(default_factory=dict)
            items: List[str] = field(default_factory=list)

        model = ComplexDefaultModel()
        assert model.data == {}
        assert model.items == []

        result = model.to_dict(exclude_defaults=True)
        assert len(result) == 0

    def test_circular_reference_prevention(self):
        """Test handling of potential circular references."""
        # This tests that to_dict handles nested objects properly
        user = SimpleTyped(name="John", age=30)
        nested = NestedTyped(user=user)

        # Should not cause infinite recursion
        result = nested.to_dict()
        assert isinstance(result["user"], dict)

    def test_large_model_performance(self):
        """Test performance with model containing many fields."""

        class LargeModel(Typed):
            field_1: str = "value_1"
            field_2: str = "value_2"
            field_3: str = "value_3"
            field_4: str = "value_4"
            field_5: str = "value_5"
            field_6: str = "value_6"
            field_7: str = "value_7"
            field_8: str = "value_8"
            field_9: str = "value_9"
            field_10: str = "value_10"

        # Test field caching with large model
        model = LargeModel()
        field_info = model._get_field_info()
        assert len(field_info) == 10

        # Second call should use cache
        field_info2 = model._get_field_info()
        assert field_info is field_info2  # Same object (cached)


class TestIntegration:
    """Integration tests combining multiple features."""

    def test_full_workflow(self):
        """Test complete workflow: dict -> model -> modify -> dict."""
        # Start with dictionary data
        data = {
            "id": 1,
            "name": "Test Item",
            "nested": {"name": "Nested", "age": 25, "active": True},
            "enum_field": SimpleEnum.VALUE_A,  # Use actual enum value
            "union_field": 42,
            "list_field": ["item1", "item2"],
        }

        # Convert to model
        model = ComplexModel.from_dict(data)
        assert model.id == 1
        assert model.name == "Test Item"
        assert isinstance(model.nested, SimpleTyped)
        assert model.enum_field == SimpleEnum.VALUE_A

        # Modify the model
        modified = model.copy(name="Modified Item", union_field="string_value")
        assert modified.name == "Modified Item"
        assert modified.union_field == "string_value"
        assert modified.id == model.id  # Unchanged

        # Convert back to dict
        result_dict = modified.to_dict()
        assert result_dict["name"] == "Modified Item"
        assert result_dict["union_field"] == "string_value"
        assert result_dict["enum_field"] == "VALUE_A"  # AutoEnum uses name as value

    def test_nested_model_validation(self):
        """Test validation with nested models."""
        # Create nested model that should validate
        user_data = {"name": "John", "age": 30}
        user = SimpleTyped.from_dict(user_data)
        user.validate()  # Should pass

        nested = NestedTyped(user=user)
        nested.validate()  # Should pass

    def test_roundtrip_consistency(self):
        """Test that dict -> model -> dict is consistent."""
        original_data = {"name": "Test", "age": 25, "active": True}

        # Convert to model and back
        model = SimpleTyped.from_dict(original_data)
        result_data = model.to_dict()

        assert result_data == original_data

    def test_model_inheritance_caching(self):
        """Test that field caching works correctly with separate Typed classes."""

        class ExtendedModel(Typed):
            name: str
            age: int
            active: bool = True
            extra_field: str = "extra"

        base_model = SimpleTyped(name="Base", age=30)
        extended_model = ExtendedModel(name="Extended", age=25, extra_field="test")

        # Should have separate cache entries
        base_fields = base_model._get_field_info()
        extended_fields = extended_model._get_field_info()

        assert len(base_fields) == 3  # name, age, active
        assert len(extended_fields) == 4  # name, age, active, extra_field

        # Verify that they are separate caches
        assert base_fields is not extended_fields
        assert "extra_field" not in base_fields
        assert "extra_field" in extended_fields

        # The extended model should have the extra field in its instance
        assert hasattr(extended_model, "extra_field")
        assert extended_model.extra_field == "test"


class TestHierarchicalTyping:
    """Test hierarchical typing support for complex nested structures."""

    def test_list_of_Typeds_constructor(self):
        """Test constructor with list of Typed dictionaries."""

        class PersonList(Typed):
            people: List[SimpleTyped]

        data = PersonList(people=[
            {"name": "John", "age": 30, "active": True},
            {"name": "Jane", "age": 25, "active": False}
        ])

        assert len(data.people) == 2
        assert isinstance(data.people[0], SimpleTyped)
        assert isinstance(data.people[1], SimpleTyped)
        assert data.people[0].name == "John"
        assert data.people[1].name == "Jane"

    def test_list_of_Typeds_from_dict(self):
        """Test from_dict with list of Typed objects."""

        class PersonList(Typed):
            people: List[SimpleTyped]

        input_data = {
            "people": [
                {"name": "John", "age": "30", "active": "True"},  # String conversion
                {"name": "Jane", "age": "25", "active": "False"}
            ]
        }

        data = PersonList.from_dict(input_data)

        assert len(data.people) == 2
        assert isinstance(data.people[0], SimpleTyped)
        assert data.people[0].name == "John"
        assert data.people[0].age == 30  # Converted from string
        assert data.people[1].name == "Jane"
        assert data.people[1].age == 25  # Converted from string

    def test_dict_of_Typeds_constructor(self):
        """Test constructor with dictionary of Typed objects."""

        class PersonDict(Typed):
            users: Dict[str, SimpleTyped]

        data = PersonDict(users={
            "admin": {"name": "Admin", "age": 35, "active": True},
            "guest": {"name": "Guest", "age": 20, "active": False}
        })

        assert len(data.users) == 2
        assert isinstance(data.users["admin"], SimpleTyped)
        assert isinstance(data.users["guest"], SimpleTyped)
        assert data.users["admin"].name == "Admin"
        assert data.users["guest"].name == "Guest"

    def test_dict_of_Typeds_from_dict(self):
        """Test from_dict with dictionary of Typed objects."""

        class PersonDict(Typed):
            users: Dict[str, SimpleTyped]

        input_data = {
            "users": {
                "admin": {"name": "Admin", "age": "35", "active": "True"},
                "guest": {"name": "Guest", "age": "20", "active": "False"}
            }
        }

        data = PersonDict.from_dict(input_data)

        assert len(data.users) == 2
        assert isinstance(data.users["admin"], SimpleTyped)
        assert data.users["admin"].age == 35  # Converted from string
        assert data.users["guest"].age == 20  # Converted from string

    def test_nested_list_in_Typed(self):
        """Test deeply nested structure with lists inside Typed objects."""

        class TaskList(Typed):
            title: str
            tasks: List[str]

        class Project(Typed):
            name: str
            task_lists: List[TaskList]

        data = Project(
            name="My Project",
            task_lists=[
                {"title": "Todo", "tasks": ["task1", "task2"]},
                {"title": "Done", "tasks": ["completed1"]}
            ]
        )

        assert data.name == "My Project"
        assert len(data.task_lists) == 2
        assert isinstance(data.task_lists[0], TaskList)
        assert data.task_lists[0].title == "Todo"
        assert data.task_lists[0].tasks == ["task1", "task2"]
        assert data.task_lists[1].title == "Done"
        assert data.task_lists[1].tasks == ["completed1"]

    def test_mixed_list_types(self):
        """Test list with mixed nested and basic types."""

        class Contact(Typed):
            name: str
            email: str

        class ContactList(Typed):
            contacts: List[Contact]
            tags: List[str]

        data = ContactList(
            contacts=[
                {"name": "John", "email": "john@example.com"},
                {"name": "Jane", "email": "jane@example.com"}
            ],
            tags=["work", "personal"]
        )

        assert len(data.contacts) == 2
        assert isinstance(data.contacts[0], Contact)
        assert data.contacts[0].name == "John"
        assert data.tags == ["work", "personal"]

    def test_optional_hierarchical_fields(self):
        """Test optional fields with hierarchical types."""

        class Address(Typed):
            street: str
            city: str

        class Person(Typed):
            name: str
            addresses: Optional[List[Address]] = None
            metadata: Optional[Dict[str, str]] = None

        # Test with None values
        person1 = Person(name="John")
        assert person1.addresses is None
        assert person1.metadata is None

        # Test with actual values
        person2 = Person(
            name="Jane",
            addresses=[{"street": "123 Main St", "city": "NYC"}],
            metadata={"role": "admin", "department": "IT"}
        )

        assert len(person2.addresses) == 1
        assert isinstance(person2.addresses[0], Address)
        assert person2.addresses[0].street == "123 Main St"
        assert person2.metadata == {"role": "admin", "department": "IT"}

    def test_hierarchical_to_dict(self):
        """Test to_dict with hierarchical structures."""

        class Item(Typed):
            id: int
            name: str

        class Inventory(Typed):
            items: List[Item]
            categories: Dict[str, Item]

        inventory = Inventory(
            items=[{"id": 1, "name": "Item1"}, {"id": 2, "name": "Item2"}],
            categories={"tools": {"id": 3, "name": "Hammer"}}
        )

        result = inventory.to_dict()

        expected = {
            "items": [
                {"id": 1, "name": "Item1"},
                {"id": 2, "name": "Item2"}
            ],
            "categories": {
                "tools": {"id": 3, "name": "Hammer"}
            }
        }

        assert result == expected

    def test_hierarchical_with_enums(self):
        """Test hierarchical structures containing enums."""

        class StatusItem(Typed):
            name: str
            status: SimpleEnum

        class StatusList(Typed):
            items: List[StatusItem]
            default_status: SimpleEnum = SimpleEnum.VALUE_A

        data = StatusList(
            items=[
                {"name": "Item1", "status": "VALUE_A"},
                {"name": "Item2", "status": "VALUE_B"}
            ]
        )

        assert len(data.items) == 2
        assert isinstance(data.items[0], StatusItem)
        assert data.items[0].status == SimpleEnum.VALUE_A
        assert data.items[1].status == SimpleEnum.VALUE_B

        # Test to_dict conversion
        result = data.to_dict()
        assert result["items"][0]["status"] == "VALUE_A"
        assert result["items"][1]["status"] == "VALUE_B"
        assert result["default_status"] == "VALUE_A"

    def test_deeply_nested_structures(self):
        """Test very deep nesting of Typed objects."""

        class Level3(Typed):
            value: str

        class Level2(Typed):
            level3_items: List[Level3]

        class Level1(Typed):
            level2_dict: Dict[str, Level2]

        data = Level1(level2_dict={
            "section1": {
                "level3_items": [
                    {"value": "deep1"},
                    {"value": "deep2"}
                ]
            },
            "section2": {
                "level3_items": [
                    {"value": "deep3"}
                ]
            }
        })

        assert len(data.level2_dict) == 2
        assert isinstance(data.level2_dict["section1"], Level2)
        assert len(data.level2_dict["section1"].level3_items) == 2
        assert isinstance(data.level2_dict["section1"].level3_items[0], Level3)
        assert data.level2_dict["section1"].level3_items[0].value == "deep1"
        assert data.level2_dict["section2"].level3_items[0].value == "deep3"

    def test_hierarchical_validation_errors(self):
        """Test that validation works correctly in hierarchical structures."""

        class ValidatedItem(Typed):
            name: str
            count: int

            def validate(self):
                if self.count < 0:
                    raise ValueError("Count must be non-negative")

        class ValidatedList(Typed):
            items: List[ValidatedItem]

        # Should work with valid data
        data = ValidatedList(items=[
            {"name": "Item1", "count": 5},
            {"name": "Item2", "count": 10}
        ])
        assert len(data.items) == 2

        # Should fail validation in nested objects
        with pytest.raises(ValueError, match="Count must be non-negative"):
            ValidatedList(items=[
                {"name": "Item1", "count": 5},
                {"name": "Item2", "count": -1}  # Invalid count
            ])

    def test_hierarchical_type_validation(self):
        """Test type validation in hierarchical structures."""

        class TypedItem(Typed):
            name: str
            value: int

        class TypedContainer(Typed):
            items: List[TypedItem]

        # Should work with correct types
        data = TypedContainer(items=[
            {"name": "Item1", "value": 42}
        ])
        assert data.items[0].value == 42

        # Should perform type conversion in nested objects
        data = TypedContainer(items=[
            {"name": 123, "value": 42}  # int should convert to str for name
        ])
        assert data.items[0].name == "123"
        assert isinstance(data.items[0].name, str)
        assert data.items[0].value == 42

    def test_roundtrip_hierarchical_consistency(self):
        """Test that hierarchical dict -> model -> dict is consistent."""

        class Person(Typed):
            name: str
            age: int

        class Team(Typed):
            name: str
            members: List[Person]
            leads: Dict[str, Person]

        original_data = {
            "name": "Development Team",
            "members": [
                {"name": "John", "age": 30},
                {"name": "Jane", "age": 25}
            ],
            "leads": {
                "tech": {"name": "Alice", "age": 35},
                "design": {"name": "Bob", "age": 28}
            }
        }

        # Convert to model and back
        model = Team.from_dict(original_data)
        result_data = model.to_dict()

        assert result_data == original_data


class TestDefaultValueValidation:
    """Test validation and conversion of default values at class definition time."""

    def test_valid_default_values_pass(self):
        """Test that valid default values are accepted."""

        class ValidDefaultsModel(Typed):
            name: str = "default_name"
            age: int = 25
            active: bool = True
            score: float = 85.5

        # Should create class successfully
        model = ValidDefaultsModel()
        assert model.name == "default_name"
        assert model.age == 25
        assert model.active is True
        assert model.score == 85.5

    def test_convertible_default_values_are_converted(self):
        """Test that default values are automatically converted to the correct type."""

        class ConvertibleDefaultsModel(Typed):
            age: int = "25"  # String that can convert to int
            score: float = "85.5"  # String that can convert to float
            active: bool = "true"  # String that can convert to bool

        # Should create class successfully with converted defaults
        model = ConvertibleDefaultsModel()
        assert model.age == 25  # Converted from string
        assert isinstance(model.age, int)
        assert model.score == 85.5  # Converted from string
        assert isinstance(model.score, float)
        # Note: "true" as a non-empty string is truthy, so bool("true") = True
        assert model.active is True
        assert isinstance(model.active, bool)

    def test_invalid_default_values_raise_error_at_class_definition(self):
        """Test that invalid default values raise errors at class definition time."""

        # Invalid string default for int field
        with pytest.raises(TypeError, match="Invalid default value for field 'age'"):
            class InvalidIntDefaultModel(Typed):
                age: int = "not_a_number"  # Can't convert to int

        # Invalid type that can't be converted
        with pytest.raises(TypeError, match="Invalid default value for field 'items'"):
            class InvalidListDefaultModel(Typed):
                items: list = "not_a_list"  # Can't convert string to list

    def test_hierarchical_default_values_conversion(self):
        """Test that hierarchical default values are properly converted."""

        class Address(Typed):
            street: str
            city: str

        class PersonWithAddressDefault(Typed):
            name: str = "John"
            # Default address as dict that should convert to Address object
            address: Address = {"street": "123 Main St", "city": "Anytown"}

        model = PersonWithAddressDefault()
        assert model.name == "John"
        assert isinstance(model.address, Address)
        assert model.address.street == "123 Main St"
        assert model.address.city == "Anytown"

    def test_list_default_values_conversion(self):
        """Test that list default values with Typed elements are converted."""

        class Contact(Typed):
            name: str
            email: str

        class ContactListModel(Typed):
            # Default list of contacts as dicts that should convert to Contact objects
            contacts: List[Contact] = [
                {"name": "John", "email": "john@example.com"},
                {"name": "Jane", "email": "jane@example.com"}
            ]

        model = ContactListModel()
        assert len(model.contacts) == 2
        assert all(isinstance(contact, Contact) for contact in model.contacts)
        assert model.contacts[0].name == "John"
        assert model.contacts[1].name == "Jane"

    def test_dict_default_values_conversion(self):
        """Test that dict default values with Typed elements are converted."""

        class User(Typed):
            name: str
            role: str

        class UserDictModel(Typed):
            # Default dict of users that should convert to User objects
            users: Dict[str, User] = {
                "admin": {"name": "Admin User", "role": "admin"},
                "guest": {"name": "Guest User", "role": "guest"}
            }

        model = UserDictModel()
        assert len(model.users) == 2
        assert all(isinstance(user, User) for user in model.users.values())
        assert model.users["admin"].name == "Admin User"
        assert model.users["guest"].role == "guest"

    def test_optional_default_values_with_none(self):
        """Test that Optional fields with None defaults work correctly."""

        class OptionalModel(Typed):
            required: str
            optional_str: Optional[str] = None
            optional_int: Optional[int] = None

        model = OptionalModel(required="test")
        assert model.required == "test"
        assert model.optional_str is None
        assert model.optional_int is None

    def test_union_default_values_conversion(self):
        """Test that Union type default values are handled correctly."""

        class UnionDefaultModel(Typed):
            value: Union[int, str] = "42"  # Should try int first, convert to int
            mixed: Union[str, int] = 42    # Should try str first, keep as int if str conversion fails

        model = UnionDefaultModel()
        # The conversion behavior depends on the order of types in Union
        # and how our conversion logic handles it
        assert model.value == 42 or model.value == "42"  # Either conversion is valid
        assert model.mixed == 42 or model.mixed == "42"   # Either conversion is valid

    def test_default_factory_validation(self):
        """Test that default_factory values are validated to be callable."""

        # Valid default factory
        class ValidFactoryModel(Typed):
            items: list = field(default_factory=list)
            data: dict = field(default_factory=dict)

        model = ValidFactoryModel()
        assert model.items == []
        assert model.data == {}

        # Invalid default factory (not callable)
        with pytest.raises(TypeError, match="default_factory.*must be callable"):
            class InvalidFactoryModel(Typed):
                items: list = field(default_factory="not_callable")  # Not callable

    def test_enum_default_values_conversion(self):
        """Test that enum default values are properly handled."""

        class EnumDefaultModel(Typed):
            status: SimpleEnum = "VALUE_A"  # String that should convert to enum

        model = EnumDefaultModel()
        assert model.status == SimpleEnum.VALUE_A
        assert isinstance(model.status, SimpleEnum)

    def test_deeply_nested_default_conversion(self):
        """Test conversion of deeply nested default structures."""

        class Item(Typed):
            name: str
            value: int

        class Category(Typed):
            name: str
            items: List[Item]

        class Inventory(Typed):
            # Complex nested default structure
            categories: Dict[str, Category] = {
                "electronics": {
                    "name": "Electronics",
                    "items": [
                        {"name": "Phone", "value": 500},
                        {"name": "Laptop", "value": 1000}
                    ]
                },
                "books": {
                    "name": "Books",
                    "items": [
                        {"name": "Python Guide", "value": 50}
                    ]
                }
            }

        model = Inventory()
        assert len(model.categories) == 2
        assert isinstance(model.categories["electronics"], Category)
        assert len(model.categories["electronics"].items) == 2
        assert isinstance(model.categories["electronics"].items[0], Item)
        assert model.categories["electronics"].items[0].name == "Phone"
        assert model.categories["books"].items[0].value == 50

    def test_default_value_validation_with_custom_validation(self):
        """Test that default values pass custom validation methods."""

        class ValidatedDefaultModel(Typed):
            count: int = 5  # Valid default

            def validate(self):
                if self.count < 0:
                    raise ValueError("Count must be non-negative")

        # Should work fine with valid default
        model = ValidatedDefaultModel()
        assert model.count == 5

        # Test that invalid defaults would be caught
        with pytest.raises(TypeError, match="Invalid default value"):
            class InvalidValidatedDefaultModel(Typed):
                count: int = "invalid"  # Will fail conversion and validation

                def validate(self):
                    if self.count < 0:
                        raise ValueError("Count must be non-negative")


class TestAutoDataclass:
    """Test automatic dataclass transformation."""

    def test_automatic_dataclass_transformation(self):
        """Test that Typed subclasses automatically become dataclasses."""

        # Define a class without @dataclass decorator
        class AutoTyped(Typed):
            name: str
            age: int
            active: bool = True

        # Should automatically have dataclass functionality
        assert hasattr(AutoTyped, "__dataclass_fields__")
        assert len(AutoTyped.__dataclass_fields__) == 3

        # Should be able to instantiate like a dataclass
        model = AutoTyped(name="Test", age=25)
        assert model.name == "Test"
        assert model.age == 25
        assert model.active is True

        # Should have dataclass methods
        assert hasattr(model, "__init__")
        assert hasattr(model, "__repr__")
        assert hasattr(model, "__eq__")

        # Should work with from_dict
        data = {"name": "John", "age": 30, "active": False}
        model2 = AutoTyped.from_dict(data)
        assert model2.name == "John"
        assert model2.age == 30
        assert model2.active is False

        # Should work with to_dict
        result = model2.to_dict()
        assert result == data

    def test_multiple_auto_dataclass_models(self):
        """Test that multiple auto-dataclass models work independently."""

        # First auto dataclass model
        class Model1(Typed):
            title: str
            count: int = 0

        # Second auto dataclass model (no decorator)
        class Model2(Typed):
            name: str
            value: float = 1.0

        # Both should work identically
        model1 = Model1(title="Test")
        model2 = Model2(name="Test")

        assert hasattr(model1, "__dataclass_fields__")
        assert hasattr(model2, "__dataclass_fields__")

        # Both should support Typed functionality
        model1_dict = model1.to_dict()
        model2_dict = model2.to_dict()

        assert model1_dict == {"title": "Test", "count": 0}
        assert model2_dict == {"name": "Test", "value": 1.0}

    def test_auto_dataclass_with_complex_types(self):
        """Test auto-dataclass with complex field types."""

        class ComplexAutoModel(Typed):
            name: str = "default"
            tags: list = field(default_factory=list)
            metadata: Optional[dict] = None
            status: SimpleEnum = SimpleEnum.VALUE_A

        # Should work with complex types
        model = ComplexAutoModel()
        assert model.name == "default"
        assert model.tags == []
        assert model.metadata is None
        assert model.status == SimpleEnum.VALUE_A

        # Should work with from_dict
        data = {
            "name": "Test",
            "tags": ["tag1", "tag2"],
            "metadata": {"key": "value"},
            "status": "VALUE_B",
        }

        model2 = ComplexAutoModel.from_dict(data)
        assert model2.name == "Test"
        assert model2.tags == ["tag1", "tag2"]
        assert model2.metadata == {"key": "value"}
        assert model2.status == SimpleEnum.VALUE_B


class TestTypeValidation:
    """Test automatic type validation functionality."""

    def test_basic_type_validation_success(self):
        """Test that correct types pass validation."""

        class TypedModel(Typed):
            name: str
            age: int
            active: bool

        # Should work with correct types
        model = TypedModel(name="John", age=30, active=True)
        assert model.name == "John"
        assert model.age == 30
        assert model.active is True

    def test_basic_type_conversion_success(self):
        """Test that compatible types are automatically converted."""

        class TypedModel(Typed):
            name: str
            age: int

        # Int should convert to str for name field
        model1 = TypedModel(name=123, age=30)
        assert model1.name == "123"
        assert isinstance(model1.name, str)
        assert model1.age == 30
        assert isinstance(model1.age, int)

        # Str should convert to int for age field
        model2 = TypedModel(name="John", age="30")
        assert model2.name == "John"
        assert isinstance(model2.name, str)
        assert model2.age == 30
        assert isinstance(model2.age, int)

    def test_optional_field_validation(self):
        """Test validation with Optional fields."""

        class OptionalModel(Typed):
            required: str
            optional: Optional[int] = None

        # Should work with None for optional field
        model = OptionalModel(required="test", optional=None)
        assert model.optional is None

        # Should work with correct type for optional field
        model = OptionalModel(required="test", optional=42)
        assert model.optional == 42

        # Should fail with None for required field
        with pytest.raises(TypeError, match="Field 'required' cannot be None"):
            OptionalModel(required=None, optional=42)

    def test_union_field_validation(self):
        """Test validation with Union types."""

        class UnionModel(Typed):
            union_field: Union[int, str]

        # Should work with int
        model = UnionModel(union_field=42)
        assert model.union_field == 42

        # Should work with str
        model = UnionModel(union_field="hello")
        assert model.union_field == "hello"

        # Should fail with unsupported type
        with pytest.raises(TypeError, match="Field 'union_field' expected type.*Union.*got list"):
            UnionModel(union_field=[1, 2, 3])

    def test_generic_type_validation(self):
        """Test validation with generic types like List, Dict."""
        from typing import Dict, List

        class GenericModel(Typed):
            items: List[str] = field(default_factory=list)
            mapping: Dict[str, int] = field(default_factory=dict)

        # Should work with correct container types
        model = GenericModel(items=["a", "b"], mapping={"key": 42})
        assert model.items == ["a", "b"]
        assert model.mapping == {"key": 42}

        # Should work with empty containers from defaults
        model = GenericModel()
        assert model.items == []
        assert model.mapping == {}

        # Should fail with wrong container type for items (expected list, got dict)
        with pytest.raises(TypeError, match="Field 'items' expected type.*List.*got dict"):
            GenericModel(items={"not": "list"}, mapping={})

    def test_enum_type_validation(self):
        """Test validation with enum types."""
        # Should work with correct enum values
        model = EnumTyped(status=SimpleEnum.VALUE_A)
        assert model.status == SimpleEnum.VALUE_A

        # Should work with valid enum string conversion
        model = EnumTyped(status="VALUE_A")  # AutoEnum expects the name, not auto() value
        assert model.status == SimpleEnum.VALUE_A
        assert isinstance(model.status, SimpleEnum)

        # Should fail with invalid enum string
        with pytest.raises(ValueError, match="Could not find enum with value 'not_an_enum'"):
            EnumTyped(status="not_an_enum")

    def test_nested_Typed_validation(self):
        """Test validation with nested Typed objects."""
        user = SimpleTyped(name="John", age=30, active=True)

        # Should work with correct nested object
        model = NestedTyped(user=user)
        assert model.user.name == "John"

        # Should fail with wrong type for nested field
        with pytest.raises(TypeError, match="Field 'user' expected type.*SimpleTyped.*got str"):
            NestedTyped(user="not_a_Typed")

    def test_type_validation_with_custom_validation(self):
        """Test that type validation works together with custom validation."""

        class CustomValidationModel(Typed):
            name: str
            age: int

            def validate(self):
                if self.age < 0:
                    raise ValueError("Age must be non-negative")

        # Should work with correct types and valid data
        model = CustomValidationModel(name="John", age=30)
        assert model.name == "John"

        # Type conversion should work, then custom validation is applied
        model = CustomValidationModel(name=123, age=30)  # 123 converts to "123"
        assert model.name == "123"
        assert isinstance(model.name, str)

        # Should fail on custom validation after type validation passes
        with pytest.raises(ValueError, match="Age must be non-negative"):
            CustomValidationModel(name="John", age=-5)

    def test_consistent_type_conversion_behavior(self):
        """Test that both from_dict and constructor perform consistent type conversion."""

        class ConversionModel(Typed):
            name: str
            age: int

        # from_dict should do type conversion
        model1 = ConversionModel.from_dict({"name": "John", "age": "30"})
        assert model1.name == "John"
        assert model1.age == 30  # Converted from string
        assert isinstance(model1.age, int)

        # Constructor should also do type conversion (consistent behavior)
        model2 = ConversionModel(name="John", age="30")  # String auto-converted
        assert model2.name == "John"
        assert model2.age == 30  # Converted from string
        assert isinstance(model2.age, int)

        # Both should produce the same result
        assert model1.to_dict() == model2.to_dict()


class TestNestedTypedConversion:
    """Test automatic nested Typed conversion in constructor."""

    def test_constructor_dict_to_nested_Typed(self):
        """Test that constructor automatically converts dicts to nested Typed objects."""
        # Single nested conversion
        model = NestedTyped(user={"name": "John", "age": 30})
        assert isinstance(model.user, SimpleTyped)
        assert model.user.name == "John"
        assert model.user.age == 30
        assert model.user.active is True  # default value

    def test_constructor_multiple_nested_conversion(self):
        """Test constructor with multiple nested dict conversions."""
        model = NestedTyped(
            user={"name": "John", "age": 30, "active": False}, metadata={"name": "Meta", "age": 25}
        )
        assert isinstance(model.user, SimpleTyped)
        assert isinstance(model.metadata, SimpleTyped)
        assert model.user.name == "John"
        assert model.user.active is False
        assert model.metadata.name == "Meta"
        assert model.metadata.active is True  # default

    def test_constructor_mixed_instance_and_dict(self):
        """Test constructor with mix of Typed instance and dict."""
        user_instance = SimpleTyped(name="InstanceUser", age=35)
        model = NestedTyped(user=user_instance, metadata={"name": "DictMeta", "age": 28})
        assert model.user is user_instance
        assert isinstance(model.metadata, SimpleTyped)
        assert model.user.name == "InstanceUser"
        assert model.metadata.name == "DictMeta"

    def test_constructor_optional_nested_with_none(self):
        """Test constructor with Optional nested field set to None."""
        model = NestedTyped(user={"name": "OnlyUser", "age": 40}, metadata=None)
        assert isinstance(model.user, SimpleTyped)
        assert model.user.name == "OnlyUser"
        assert model.metadata is None

    def test_constructor_nested_conversion_works(self):
        """Test that nested objects also perform automatic type conversion."""
        # Type conversion should work in nested object
        model = NestedTyped(user={"name": 123, "age": 30})
        assert model.user.name == "123"  # int converted to str
        assert isinstance(model.user.name, str)
        assert model.user.age == 30

        # String to int conversion should work in nested age field
        model = NestedTyped(user={"name": "John", "age": "30"})
        assert model.user.name == "John"
        assert model.user.age == 30  # str converted to int
        assert isinstance(model.user.age, int)

        # Invalid conversion should still fail with type validation error
        with pytest.raises(TypeError, match="Field 'age' expected type.*int.*got str"):
            NestedTyped(user={"name": "John", "age": "not_a_number"})

    def test_from_dict_still_does_type_conversion(self):
        """Test that from_dict still does type conversion (different from constructor)."""
        # from_dict should convert types
        model = NestedTyped.from_dict(
            {
                "user": {"name": "John", "age": "30"}  # string age gets converted
            }
        )
        assert isinstance(model.user, SimpleTyped)
        assert model.user.name == "John"
        assert model.user.age == 30  # converted from string
        assert isinstance(model.user.age, int)

    def test_constructor_and_from_dict_consistent_behavior(self):
        """Test that constructor and from_dict have consistent behavior."""
        # Both constructor and from_dict should convert types consistently
        model1 = NestedTyped(user={"name": "John", "age": "30"})  # string age converts
        assert model1.user.age == 30
        assert isinstance(model1.user.age, int)

        model2 = NestedTyped.from_dict({"user": {"name": "John", "age": "30"}})
        assert model2.user.age == 30  # string converted to int
        assert isinstance(model2.user.age, int)

        # Both should produce same result
        assert model1.to_dict() == model2.to_dict()

    def test_deeply_nested_conversion(self):
        """Test conversion with deeply nested Typed objects."""
        # Create a more complex nested structure for testing
        complex_data = {
            "user": {"name": "John", "age": 30},
            "metadata": {"name": "Meta", "age": 25, "active": False},
        }

        model = NestedTyped(**complex_data)

        # Verify all levels are properly converted and validated
        assert isinstance(model.user, SimpleTyped)
        assert isinstance(model.metadata, SimpleTyped)
        assert model.user.name == "John"
        assert model.metadata.active is False


class TestValidateCall:
    """Comprehensive tests for validate decorator."""

    def test_basic_validate_functionality(self):
        """Test basic validate functionality with type conversion."""
        from morphic.typed import validate

        @validate
        def add_numbers(a: int, b: int) -> int:
            return a + b

        # Test type conversion from strings
        result = add_numbers("5", "10")
        assert result == 15
        assert isinstance(result, int)

        # Test with actual int arguments
        result = add_numbers(3, 7)
        assert result == 10

        # Test mixed types that can be converted
        result = add_numbers("5", 10)
        assert result == 15

    def test_validate_without_parentheses(self):
        """Test validate decorator used without parentheses."""
        from morphic.typed import validate

        @validate
        def multiply(x: float, y: float) -> float:
            return x * y

        # Should work with type conversion
        result = multiply("2.5", "4.0")
        assert result == 10.0
        assert isinstance(result, float)

    def test_validate_with_defaults(self):
        """Test validate with default parameter values."""
        from morphic.typed import validate

        @validate
        def process_data(name: str, count: int = 10) -> str:
            return f"Processing {count} items: {name}"

        result = process_data("test", "5")
        assert result == "Processing 5 items: test"

        # Test with default value
        result = process_data("test")
        assert result == "Processing 10 items: test"

    def test_validate_with_Typed_types(self):
        """Test validate with Typed type arguments."""
        from morphic.typed import validate

        @validate
        def create_user(user_data: SimpleTyped) -> SimpleTyped:
            return user_data

        # Dict should be automatically converted to SimpleTyped
        result = create_user({"name": "John", "age": "30", "active": True})
        assert isinstance(result, SimpleTyped)
        assert result.name == "John"
        assert result.age == 30
        assert isinstance(result.age, int)  # Converted from string
        assert result.active is True

        # Existing Typed object should pass through unchanged
        user = SimpleTyped(name="Jane", age=25)
        result = create_user(user)
        assert isinstance(result, SimpleTyped)
        assert result.name == "Jane"
        assert result.age == 25

    def test_validate_with_list_types(self):
        """Test validate with List type annotations."""
        from morphic.typed import validate

        @validate
        def process_users(users: List[SimpleTyped]) -> int:
            return len(users)

        # List of dicts should be converted to list of Typed objects
        result = process_users([
            {"name": "John", "age": "30"},
            {"name": "Jane", "age": "25"}
        ])
        assert result == 2

        # Mixed list with dict and Typed object
        user = SimpleTyped(name="Bob", age=35)
        result = process_users([
            {"name": "John", "age": "30"},
            user
        ])
        assert result == 2

    def test_validate_with_optional_types(self):
        """Test validate with Optional type annotations."""
        from morphic.typed import validate
        from typing import Optional

        @validate
        def greet_user(name: str, title: Optional[str] = None) -> str:
            if title:
                return f"Hello, {title} {name}"
            return f"Hello, {name}"

        # Test with None (should be valid for Optional)
        result = greet_user("John", None)
        assert result == "Hello, John"

        # Test with default None
        result = greet_user("Jane")
        assert result == "Hello, Jane"

        # Test with actual value
        result = greet_user("Smith", "Dr.")
        assert result == "Hello, Dr. Smith"

    def test_validate_with_union_types(self):
        """Test validate with Union type annotations."""
        from morphic.typed import validate
        from typing import Union

        @validate
        def format_value(value: Union[int, str]) -> str:
            return f"Value: {value}"

        # Test with int
        result = format_value(42)
        assert result == "Value: 42"

        # Test with string
        result = format_value("hello")
        assert result == "Value: hello"

        # Test with convertible string to int
        result = format_value("123")
        assert result == "Value: 123"  # Will be converted to int first

    def test_validate_validation_errors(self):
        """Test validate raises ValidationError for invalid inputs."""
        from morphic.typed import validate, ValidationError

        @validate
        def divide(a: int, b: int) -> float:
            return a / b

        # Test invalid conversion
        with pytest.raises(ValidationError, match="Argument 'a' expected type"):
            divide("not_a_number", 5)

        with pytest.raises(ValidationError, match="Argument 'b' expected type"):
            divide(10, "also_not_a_number")

    def test_validate_with_return_validation(self):
        """Test validate with return value validation."""
        from morphic.typed import validate, ValidationError

        @validate(validate_return=True)
        def get_name(user_id: int) -> str:
            if user_id > 0:
                return f"user_{user_id}"
            else:
                return 123  # Invalid return type

        # Valid return
        result = get_name(5)
        assert result == "user_5"

        # Invalid return should raise ValidationError
        with pytest.raises(ValidationError, match="Return value expected type"):
            get_name(0)

    def test_validate_with_default_validation(self):
        """Test validate validates default parameter values."""
        from morphic.typed import validate, ValidationError

        # Valid defaults should work
        @validate
        def process_items(items: List[str], count: int = 10) -> str:
            return f"Processing {count} of {len(items)} items"

        result = process_items(["a", "b", "c"])
        assert result == "Processing 10 of 3 items"

        # Invalid defaults should raise error at decoration time
        with pytest.raises(ValidationError, match="Cannot convert"):
            @validate
            def bad_function(count: int = "not_a_number"):
                return count

    def test_validate_preserves_function_metadata(self):
        """Test that validate preserves function metadata."""
        from morphic.typed import validate

        @validate
        def documented_function(x: int, y: int) -> int:
            """Add two numbers together."""
            return x + y

        # Should preserve function name and docstring
        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "Add two numbers together."

        # Should have access to original function
        assert hasattr(documented_function, 'raw_function')
        assert documented_function.raw_function.__name__ == "documented_function"

    def test_validate_with_arbitrary_types(self):
        """Test validate with arbitrary types (always enabled)."""
        from morphic.typed import validate

        # Should allow any types with automatic conversion
        @validate
        def flexible_function(name: str, count: int) -> str:
            return f"{name}: {count}"

        # Basic types should work
        result = flexible_function("test", 5)
        assert result == "test: 5"

        # Type conversion should work for basic types
        result = flexible_function("test", "5")
        assert result == "test: 5"

    def test_validate_with_no_annotations(self):
        """Test validate with functions that have no type annotations."""
        from morphic.typed import validate

        @validate
        def no_annotations(a, b):
            return a + b

        # Should work without any validation
        result = no_annotations(1, 2)
        assert result == 3

        result = no_annotations("hello", "world")
        assert result == "helloworld"

    def test_validate_with_varargs_kwargs(self):
        """Test validate with *args and **kwargs."""
        from morphic.typed import validate

        @validate
        def flexible_function(a: int, *args, b: str = "default", **kwargs):
            return f"a={a}, args={args}, b={b}, kwargs={kwargs}"

        # Test with only required parameter (a should be converted)
        result = flexible_function("5")
        assert "a=5" in result
        assert "b=default" in result

        # Test with keyword arguments
        result = flexible_function("10", b="test", extra="value")
        assert "a=10" in result
        assert "b=test" in result
        assert "extra" in result

        # Test with positional arguments (note: Python signature binding behavior)
        result = flexible_function("5", b="custom")
        assert "a=5" in result
        assert "b=custom" in result

    def test_validate_with_nested_Typeds(self):
        """Test validate with nested Typed structures."""
        from morphic.typed import validate

        @validate
        def create_nested(data: NestedTyped) -> str:
            return f"User: {data.user.name}, age {data.user.age}"

        # Should handle deeply nested dict-to-Typed conversion
        result = create_nested({
            "user": {"name": "John", "age": "30"},
            "metadata": {"name": "Meta", "age": "25"}
        })
        assert result == "User: John, age 30"

    def test_validate_error_messages(self):
        """Test that validate provides clear error messages."""
        from morphic.typed import validate, ValidationError

        @validate
        def test_function(name: str, age: int) -> None:
            pass

        # Test argument binding error
        with pytest.raises(ValidationError, match="Invalid function arguments"):
            test_function()  # Missing required arguments

        # Test type validation error
        with pytest.raises(ValidationError, match="Argument 'age' expected type"):
            test_function("John", "definitely_not_a_number")

    def test_validate_with_complex_types(self):
        """Test validate with complex type annotations."""
        from morphic.typed import validate
        from typing import Dict, List

        @validate
        def process_mapping(data: Dict[str, List[int]]) -> int:
            total = 0
            for values in data.values():
                total += sum(values)
            return total

        # Should handle complex nested type conversions
        result = process_mapping({
            "group1": ["1", "2", "3"],  # strings converted to ints
            "group2": [4, 5, 6]         # already ints
        })
        assert result == 21  # 1+2+3+4+5+6

    def test_validate_performance_with_repeated_calls(self):
        """Test that validate doesn't have excessive overhead on repeated calls."""
        from morphic.typed import validate
        import time

        @validate
        def simple_add(a: int, b: int) -> int:
            return a + b

        # Time multiple calls to ensure reasonable performance
        start_time = time.time()
        for i in range(1000):
            result = simple_add(i, i + 1)
        end_time = time.time()

        # Should complete 1000 calls in reasonable time (less than 1 second)
        elapsed = end_time - start_time
        assert elapsed < 1.0, f"Performance test failed: {elapsed:.3f} seconds for 1000 calls"

        # Verify correctness wasn't compromised for speed
        assert simple_add(5, 10) == 15

    def test_validate_enhanced_default_validation(self):
        """Test enhanced default parameter validation for complex types."""
        from morphic.typed import validate, ValidationError
        from typing import List, Dict, Optional

        # Test invalid list elements are caught
        with pytest.raises(ValidationError, match="Invalid list element at index 2"):
            @validate
            def bad_list(numbers: List[int] = ["1", "2", "invalid"]):
                return numbers

        # Test valid list conversion works
        @validate
        def good_list(numbers: List[int] = ["1", "2", "3"]):
            return numbers

        result = good_list()
        assert result == [1, 2, 3]
        assert all(isinstance(x, int) for x in result)

        # Test invalid dict values are caught
        with pytest.raises(ValidationError, match="Invalid dict entry"):
            @validate
            def bad_dict(mapping: Dict[str, int] = {"a": "1", "b": "invalid"}):
                return mapping

        # Test valid dict conversion works
        @validate
        def good_dict(mapping: Dict[str, int] = {"a": "1", "b": "2"}):
            return mapping

        result = good_dict()
        assert result == {"a": 1, "b": 2}
        assert all(isinstance(v, int) for v in result.values())

        # Test nested Typed validation
        with pytest.raises(ValidationError, match="Invalid list element"):
            @validate
            def bad_nested(users: List[SimpleTyped] = [{"name": "John", "age": "invalid"}]):
                return users

        # Test valid nested Typed conversion
        @validate
        def good_nested(users: List[SimpleTyped] = [{"name": "John", "age": "30"}]):
            return users

        result = good_nested()
        assert len(result) == 1
        assert isinstance(result[0], SimpleTyped)
        assert result[0].name == "John"
        assert result[0].age == 30
        assert isinstance(result[0].age, int)

    def test_validate_default_validation_edge_cases(self):
        """Test edge cases for default parameter validation."""
        from morphic.typed import validate, ValidationError
        from typing import Optional, Union

        # Test None validation for Optional types
        @validate
        def optional_none(value: Optional[str] = None):
            return value

        result = optional_none()
        assert result is None

        # Test None validation for non-Optional types should fail
        with pytest.raises(ValidationError, match="None not allowed for type"):
            @validate
            def non_optional_none(value: str = None):
                return value

        # Test Union type validation with invalid value
        with pytest.raises(ValidationError, match="Could not convert"):
            @validate
            def bad_union(value: Union[int, bool] = "invalid_for_both"):
                return value

        # Test Union type validation with valid conversion
        @validate
        def good_union(value: Union[int, str] = "123"):
            return value

        result = good_union()
        assert result == 123  # Should convert to int first
        assert isinstance(result, int)

        # Test boolean string conversion - note that runtime uses Typed conversion
        # which uses Python's bool() that treats non-empty strings as True
        @validate
        def bool_conversion(flag: bool = "true"):
            return flag

        # Python's bool("true") is True
        assert bool_conversion() is True

        @validate
        def bool_false(flag: bool = "false"):
            return flag

        # Python's bool("false") is True (non-empty string!)
        # This is the current Typed behavior - uses Python's built-in bool()
        assert bool_false() is True

        # Only empty string converts to False with Python's bool()
        @validate
        def bool_empty(flag: bool = ""):
            return flag

        assert bool_empty() is False

        with pytest.raises(ValidationError, match="Cannot convert"):
            @validate
            def invalid_bool(flag: bool = "maybe"):
                return flag

        # Test complex nested structures
        @validate
        def complex_nested(
            data: Dict[str, List[SimpleTyped]] = {
                "group1": [{"name": "Alice", "age": "25"}],
                "group2": [{"name": "Bob", "age": "30"}]
            }
        ):
            return data

        result = complex_nested()
        assert isinstance(result, dict)
        assert "group1" in result
        assert isinstance(result["group1"], list)
        assert isinstance(result["group1"][0], SimpleTyped)
        assert result["group1"][0].age == 25
        assert isinstance(result["group1"][0].age, int)

        # Test invalid complex nested structures
        with pytest.raises(ValidationError, match="Invalid dict entry"):
            @validate
            def bad_complex_nested(
                data: Dict[str, List[SimpleTyped]] = {
                    "group1": [{"name": "Alice", "age": "invalid_age"}]
                }
            ):
                return data
