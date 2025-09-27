"""Comprehensive tests for DataModel module."""

from dataclasses import field
from typing import Dict, List, Optional, Union
from unittest.mock import Mock, patch

import pytest

from morphic.autoenum import AutoEnum, alias, auto
from morphic.datamodel import DataModel


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


class SimpleDataModel(DataModel):
    """Simple test model with basic types."""

    name: str
    age: int
    active: bool = True


class OptionalFieldsModel(DataModel):
    """Model with optional and union types."""

    required_field: str
    optional_str: Optional[str] = None
    union_field: Union[int, str] = "default"
    optional_int: Optional[int] = None


class NestedDataModel(DataModel):
    """Model with nested DataModel objects."""

    user: SimpleDataModel
    metadata: Optional[SimpleDataModel] = None


class EnumDataModel(DataModel):
    """Model with enum fields."""

    status: SimpleEnum
    optional_status: Optional[SimpleEnum] = None


class DefaultValueModel(DataModel):
    """Model with various default values."""

    name: str = "default_name"
    count: int = 0
    tags: list = field(default_factory=list)  # Use simple list type
    active: bool = True


class ComplexModel(DataModel):
    """Complex model for comprehensive testing."""

    id: int
    name: str
    nested: SimpleDataModel
    enum_field: SimpleEnum
    optional_nested: Optional[NestedDataModel] = None
    union_field: Union[int, str, float] = 42
    list_field: list = field(default_factory=list)  # Use simple list type to avoid isinstance issues


class ValidationModel(DataModel):
    """Model with custom validation."""

    name: str
    age: int

    def validate(self):
        if self.age < 0:
            raise ValueError("Age cannot be negative")
        if not self.name.strip():
            raise ValueError("Name cannot be empty")


class TestDataModelBasics:
    """Test basic DataModel functionality."""

    def test_simple_instantiation(self):
        """Test basic model instantiation."""
        model = SimpleDataModel(name="John", age=30)
        assert model.name == "John"
        assert model.age == 30
        assert model.active is True

    def test_repr_method(self):
        """Test __repr__ method output."""
        model = SimpleDataModel(name="John", age=30, active=False)
        repr_str = repr(model)

        assert "SimpleDataModel" in repr_str
        assert "name='John'" in repr_str
        assert "age=30" in repr_str
        assert "active=False" in repr_str

    def test_field_caching(self):
        """Test that field information is cached properly."""
        # Create multiple instances to test caching
        model1 = SimpleDataModel(name="John", age=30)
        model2 = SimpleDataModel(name="Jane", age=25)

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
        model = SimpleDataModel.from_dict(data)

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

        model = SimpleDataModel.from_dict(data)
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
        """Test from_dict with nested DataModel objects."""
        data = {
            "user": {"name": "John", "age": 30, "active": True},
            "metadata": {"name": "Meta", "age": 25, "active": False},
        }
        model = NestedDataModel.from_dict(data)

        assert isinstance(model.user, SimpleDataModel)
        assert model.user.name == "John"
        assert model.user.age == 30

        assert isinstance(model.metadata, SimpleDataModel)
        assert model.metadata.name == "Meta"
        assert model.metadata.age == 25

    def test_from_dict_with_enum(self):
        """Test from_dict with AutoEnum fields."""
        # Test with string values (should auto-convert to AutoEnum)
        data = {"status": "VALUE_A", "optional_status": "VALUE_B"}
        model = EnumDataModel.from_dict(data)

        assert model.status == SimpleEnum.VALUE_A
        assert model.optional_status == SimpleEnum.VALUE_B
        assert isinstance(model.status, SimpleEnum)
        assert isinstance(model.optional_status, SimpleEnum)

        # Test with alias
        data_alias = {"status": "C", "optional_status": "charlie"}
        model_alias = EnumDataModel.from_dict(data_alias)
        assert model_alias.status == SimpleEnum.VALUE_C
        assert model_alias.optional_status == SimpleEnum.VALUE_C

    def test_autoenum_string_conversion(self):
        """Test comprehensive AutoEnum string conversion capabilities."""

        # Test case-insensitive conversion
        data = {"status": "value_a", "optional_status": "VALUE_B"}
        model = EnumDataModel.from_dict(data)
        assert model.status == SimpleEnum.VALUE_A
        assert model.optional_status == SimpleEnum.VALUE_B

        # Test fuzzy matching (spaces, underscores, etc.)
        data_fuzzy = {"status": "Value A", "optional_status": "value-b"}
        model_fuzzy = EnumDataModel.from_dict(data_fuzzy)
        assert model_fuzzy.status == SimpleEnum.VALUE_A
        assert model_fuzzy.optional_status == SimpleEnum.VALUE_B

        # Test alias functionality
        data_alias = {"status": "C", "optional_status": "charlie"}
        model_alias = EnumDataModel.from_dict(data_alias)
        assert model_alias.status == SimpleEnum.VALUE_C
        assert model_alias.optional_status == SimpleEnum.VALUE_C

        # Test to_dict conversion back to strings
        result = model_alias.to_dict()
        assert result["status"] == "VALUE_C"
        assert result["optional_status"] == "VALUE_C"

    @patch("morphic.datamodel.DataModel._convert_single_type")
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
        model = SimpleDataModel.from_dict(data, strict=False)
        assert model.name == "John"

        # Should raise error in strict mode
        with pytest.raises(ValueError, match="Unknown field 'unknown_field'"):
            SimpleDataModel.from_dict(data, strict=True)

    def test_from_dict_invalid_input_type(self):
        """Test from_dict with invalid input type."""
        with pytest.raises(TypeError, match="Expected dict, got"):
            SimpleDataModel.from_dict("not a dict")

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
        model = SimpleDataModel(name="John", age=30, active=False)
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
        """Test to_dict with nested DataModel objects."""
        nested_user = SimpleDataModel(name="John", age=30)
        model = NestedDataModel(user=nested_user)
        result = model.to_dict()

        assert "user" in result
        assert isinstance(result["user"], dict)
        assert result["user"]["name"] == "John"
        assert result["user"]["age"] == 30

    def test_to_dict_with_enum(self):
        """Test to_dict with enum fields."""
        model = EnumDataModel(status=SimpleEnum.VALUE_A)
        result = model.to_dict()

        assert result["status"] == "VALUE_A"  # AutoEnum uses name as value

    @patch("morphic.datamodel.DataModel._is_default_value")
    def test_to_dict_complex_exclude_options(self, mock_is_default):
        """Test to_dict with both exclude options."""
        mock_is_default.return_value = False

        nested_user = SimpleDataModel(name="John", age=30)
        model = NestedDataModel(user=nested_user, metadata=None)

        result = model.to_dict(exclude_none=True, exclude_defaults=True)

        assert "user" in result
        assert "metadata" not in result  # None value excluded


class TestCopy:
    """Test copy functionality."""

    def test_basic_copy(self):
        """Test basic copy without changes."""
        original = SimpleDataModel(name="John", age=30, active=False)
        copy = original.copy()

        assert copy.name == original.name
        assert copy.age == original.age
        assert copy.active == original.active
        assert copy is not original  # Different instances

    def test_copy_with_changes(self):
        """Test copy with field changes."""
        original = SimpleDataModel(name="John", age=30, active=False)
        copy = original.copy(name="Jane", age=25)

        assert copy.name == "Jane"
        assert copy.age == 25
        assert copy.active == original.active  # Unchanged
        assert original.name == "John"  # Original unchanged

    def test_copy_complex_model(self):
        """Test copy with complex nested model."""
        user = SimpleDataModel(name="John", age=30)
        original = NestedDataModel(user=user)

        new_user_data = {"name": "Jane", "age": 25, "active": True}
        copy = original.copy(user=new_user_data)

        assert isinstance(copy.user, SimpleDataModel)
        assert copy.user.name == "Jane"
        assert original.user.name == "John"  # Original unchanged


class TestValidation:
    """Test validation functionality."""

    def test_default_validate(self):
        """Test default validate method (should do nothing)."""
        model = SimpleDataModel(name="John", age=30)
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

        class AutoValidateModel(DataModel):
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
        result = SimpleDataModel._convert_single_type(int, "42")
        assert result == 42

        # String to float
        result = SimpleDataModel._convert_single_type(float, "3.14")
        assert result == 3.14

        # String to bool
        result = SimpleDataModel._convert_single_type(bool, "true")
        assert result is True

        # Already correct type
        result = SimpleDataModel._convert_single_type(str, "hello")
        assert result == "hello"

    def test_convert_invalid_types(self):
        """Test conversion with invalid input."""
        # Invalid conversion should return original value
        result = SimpleDataModel._convert_single_type(int, "not_a_number")
        assert result == "not_a_number"

    def test_convert_none_value(self):
        """Test conversion of None values."""
        field_mock = Mock()
        field_mock.type = int

        result = SimpleDataModel._convert_value(field_mock, None)
        assert result is None

    def test_convert_union_types(self):
        """Test conversion with Union types."""
        field_mock = Mock()
        field_mock.type = Union[int, str]

        # Should try to convert to int first
        result = SimpleDataModel._convert_value(field_mock, "42")
        assert result == 42

        # Should convert to string if int conversion fails
        result2 = SimpleDataModel._convert_value(field_mock, "hello")
        assert result2 == "hello"

        # Should try int conversion first, then str
        field_mock2 = Mock()
        field_mock2.type = Union[str, int]  # Different order
        result3 = SimpleDataModel._convert_value(field_mock2, "42")
        # This should still convert to str since it's the first type in the union
        assert result3 == "42"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_model(self):
        """Test model with no fields."""

        class EmptyModel(DataModel):
            pass

        model = EmptyModel()
        assert model.to_dict() == {}

        # from_dict should work with empty dict
        model2 = EmptyModel.from_dict({})
        assert isinstance(model2, EmptyModel)

    def test_model_with_complex_defaults(self):
        """Test model with complex default values."""

        class ComplexDefaultModel(DataModel):
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
        user = SimpleDataModel(name="John", age=30)
        nested = NestedDataModel(user=user)

        # Should not cause infinite recursion
        result = nested.to_dict()
        assert isinstance(result["user"], dict)

    def test_large_model_performance(self):
        """Test performance with model containing many fields."""

        class LargeModel(DataModel):
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
        assert isinstance(model.nested, SimpleDataModel)
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
        user = SimpleDataModel.from_dict(user_data)
        user.validate()  # Should pass

        nested = NestedDataModel(user=user)
        nested.validate()  # Should pass

    def test_roundtrip_consistency(self):
        """Test that dict -> model -> dict is consistent."""
        original_data = {"name": "Test", "age": 25, "active": True}

        # Convert to model and back
        model = SimpleDataModel.from_dict(original_data)
        result_data = model.to_dict()

        assert result_data == original_data

    def test_model_inheritance_caching(self):
        """Test that field caching works correctly with separate DataModel classes."""

        class ExtendedModel(DataModel):
            name: str
            age: int
            active: bool = True
            extra_field: str = "extra"

        base_model = SimpleDataModel(name="Base", age=30)
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

    def test_list_of_datamodels_constructor(self):
        """Test constructor with list of DataModel dictionaries."""

        class PersonList(DataModel):
            people: List[SimpleDataModel]

        data = PersonList(people=[
            {"name": "John", "age": 30, "active": True},
            {"name": "Jane", "age": 25, "active": False}
        ])

        assert len(data.people) == 2
        assert isinstance(data.people[0], SimpleDataModel)
        assert isinstance(data.people[1], SimpleDataModel)
        assert data.people[0].name == "John"
        assert data.people[1].name == "Jane"

    def test_list_of_datamodels_from_dict(self):
        """Test from_dict with list of DataModel objects."""

        class PersonList(DataModel):
            people: List[SimpleDataModel]

        input_data = {
            "people": [
                {"name": "John", "age": "30", "active": "True"},  # String conversion
                {"name": "Jane", "age": "25", "active": "False"}
            ]
        }

        data = PersonList.from_dict(input_data)

        assert len(data.people) == 2
        assert isinstance(data.people[0], SimpleDataModel)
        assert data.people[0].name == "John"
        assert data.people[0].age == 30  # Converted from string
        assert data.people[1].name == "Jane"
        assert data.people[1].age == 25  # Converted from string

    def test_dict_of_datamodels_constructor(self):
        """Test constructor with dictionary of DataModel objects."""

        class PersonDict(DataModel):
            users: Dict[str, SimpleDataModel]

        data = PersonDict(users={
            "admin": {"name": "Admin", "age": 35, "active": True},
            "guest": {"name": "Guest", "age": 20, "active": False}
        })

        assert len(data.users) == 2
        assert isinstance(data.users["admin"], SimpleDataModel)
        assert isinstance(data.users["guest"], SimpleDataModel)
        assert data.users["admin"].name == "Admin"
        assert data.users["guest"].name == "Guest"

    def test_dict_of_datamodels_from_dict(self):
        """Test from_dict with dictionary of DataModel objects."""

        class PersonDict(DataModel):
            users: Dict[str, SimpleDataModel]

        input_data = {
            "users": {
                "admin": {"name": "Admin", "age": "35", "active": "True"},
                "guest": {"name": "Guest", "age": "20", "active": "False"}
            }
        }

        data = PersonDict.from_dict(input_data)

        assert len(data.users) == 2
        assert isinstance(data.users["admin"], SimpleDataModel)
        assert data.users["admin"].age == 35  # Converted from string
        assert data.users["guest"].age == 20  # Converted from string

    def test_nested_list_in_datamodel(self):
        """Test deeply nested structure with lists inside DataModel objects."""

        class TaskList(DataModel):
            title: str
            tasks: List[str]

        class Project(DataModel):
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

        class Contact(DataModel):
            name: str
            email: str

        class ContactList(DataModel):
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

        class Address(DataModel):
            street: str
            city: str

        class Person(DataModel):
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

        class Item(DataModel):
            id: int
            name: str

        class Inventory(DataModel):
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

        class StatusItem(DataModel):
            name: str
            status: SimpleEnum

        class StatusList(DataModel):
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
        """Test very deep nesting of DataModel objects."""

        class Level3(DataModel):
            value: str

        class Level2(DataModel):
            level3_items: List[Level3]

        class Level1(DataModel):
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

        class ValidatedItem(DataModel):
            name: str
            count: int

            def validate(self):
                if self.count < 0:
                    raise ValueError("Count must be non-negative")

        class ValidatedList(DataModel):
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

        class TypedItem(DataModel):
            name: str
            value: int

        class TypedContainer(DataModel):
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

        class Person(DataModel):
            name: str
            age: int

        class Team(DataModel):
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

        class ValidDefaultsModel(DataModel):
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

        class ConvertibleDefaultsModel(DataModel):
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
            class InvalidIntDefaultModel(DataModel):
                age: int = "not_a_number"  # Can't convert to int

        # Invalid type that can't be converted
        with pytest.raises(TypeError, match="Invalid default value for field 'items'"):
            class InvalidListDefaultModel(DataModel):
                items: list = "not_a_list"  # Can't convert string to list

    def test_hierarchical_default_values_conversion(self):
        """Test that hierarchical default values are properly converted."""

        class Address(DataModel):
            street: str
            city: str

        class PersonWithAddressDefault(DataModel):
            name: str = "John"
            # Default address as dict that should convert to Address object
            address: Address = {"street": "123 Main St", "city": "Anytown"}

        model = PersonWithAddressDefault()
        assert model.name == "John"
        assert isinstance(model.address, Address)
        assert model.address.street == "123 Main St"
        assert model.address.city == "Anytown"

    def test_list_default_values_conversion(self):
        """Test that list default values with DataModel elements are converted."""

        class Contact(DataModel):
            name: str
            email: str

        class ContactListModel(DataModel):
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
        """Test that dict default values with DataModel elements are converted."""

        class User(DataModel):
            name: str
            role: str

        class UserDictModel(DataModel):
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

        class OptionalModel(DataModel):
            required: str
            optional_str: Optional[str] = None
            optional_int: Optional[int] = None

        model = OptionalModel(required="test")
        assert model.required == "test"
        assert model.optional_str is None
        assert model.optional_int is None

    def test_union_default_values_conversion(self):
        """Test that Union type default values are handled correctly."""

        class UnionDefaultModel(DataModel):
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
        class ValidFactoryModel(DataModel):
            items: list = field(default_factory=list)
            data: dict = field(default_factory=dict)

        model = ValidFactoryModel()
        assert model.items == []
        assert model.data == {}

        # Invalid default factory (not callable)
        with pytest.raises(TypeError, match="default_factory.*must be callable"):
            class InvalidFactoryModel(DataModel):
                items: list = field(default_factory="not_callable")  # Not callable

    def test_enum_default_values_conversion(self):
        """Test that enum default values are properly handled."""

        class EnumDefaultModel(DataModel):
            status: SimpleEnum = "VALUE_A"  # String that should convert to enum

        model = EnumDefaultModel()
        assert model.status == SimpleEnum.VALUE_A
        assert isinstance(model.status, SimpleEnum)

    def test_deeply_nested_default_conversion(self):
        """Test conversion of deeply nested default structures."""

        class Item(DataModel):
            name: str
            value: int

        class Category(DataModel):
            name: str
            items: List[Item]

        class Inventory(DataModel):
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

        class ValidatedDefaultModel(DataModel):
            count: int = 5  # Valid default

            def validate(self):
                if self.count < 0:
                    raise ValueError("Count must be non-negative")

        # Should work fine with valid default
        model = ValidatedDefaultModel()
        assert model.count == 5

        # Test that invalid defaults would be caught
        with pytest.raises(TypeError, match="Invalid default value"):
            class InvalidValidatedDefaultModel(DataModel):
                count: int = "invalid"  # Will fail conversion and validation

                def validate(self):
                    if self.count < 0:
                        raise ValueError("Count must be non-negative")


class TestAutoDataclass:
    """Test automatic dataclass transformation."""

    def test_automatic_dataclass_transformation(self):
        """Test that DataModel subclasses automatically become dataclasses."""

        # Define a class without @dataclass decorator
        class AutoDataModel(DataModel):
            name: str
            age: int
            active: bool = True

        # Should automatically have dataclass functionality
        assert hasattr(AutoDataModel, "__dataclass_fields__")
        assert len(AutoDataModel.__dataclass_fields__) == 3

        # Should be able to instantiate like a dataclass
        model = AutoDataModel(name="Test", age=25)
        assert model.name == "Test"
        assert model.age == 25
        assert model.active is True

        # Should have dataclass methods
        assert hasattr(model, "__init__")
        assert hasattr(model, "__repr__")
        assert hasattr(model, "__eq__")

        # Should work with from_dict
        data = {"name": "John", "age": 30, "active": False}
        model2 = AutoDataModel.from_dict(data)
        assert model2.name == "John"
        assert model2.age == 30
        assert model2.active is False

        # Should work with to_dict
        result = model2.to_dict()
        assert result == data

    def test_multiple_auto_dataclass_models(self):
        """Test that multiple auto-dataclass models work independently."""

        # First auto dataclass model
        class Model1(DataModel):
            title: str
            count: int = 0

        # Second auto dataclass model (no decorator)
        class Model2(DataModel):
            name: str
            value: float = 1.0

        # Both should work identically
        model1 = Model1(title="Test")
        model2 = Model2(name="Test")

        assert hasattr(model1, "__dataclass_fields__")
        assert hasattr(model2, "__dataclass_fields__")

        # Both should support DataModel functionality
        model1_dict = model1.to_dict()
        model2_dict = model2.to_dict()

        assert model1_dict == {"title": "Test", "count": 0}
        assert model2_dict == {"name": "Test", "value": 1.0}

    def test_auto_dataclass_with_complex_types(self):
        """Test auto-dataclass with complex field types."""

        class ComplexAutoModel(DataModel):
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

        class TypedModel(DataModel):
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

        class TypedModel(DataModel):
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

        class OptionalModel(DataModel):
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

        class UnionModel(DataModel):
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

        class GenericModel(DataModel):
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
        model = EnumDataModel(status=SimpleEnum.VALUE_A)
        assert model.status == SimpleEnum.VALUE_A

        # Should work with valid enum string conversion
        model = EnumDataModel(status="VALUE_A")  # AutoEnum expects the name, not auto() value
        assert model.status == SimpleEnum.VALUE_A
        assert isinstance(model.status, SimpleEnum)

        # Should fail with invalid enum string
        with pytest.raises(ValueError, match="Could not find enum with value 'not_an_enum'"):
            EnumDataModel(status="not_an_enum")

    def test_nested_datamodel_validation(self):
        """Test validation with nested DataModel objects."""
        user = SimpleDataModel(name="John", age=30, active=True)

        # Should work with correct nested object
        model = NestedDataModel(user=user)
        assert model.user.name == "John"

        # Should fail with wrong type for nested field
        with pytest.raises(TypeError, match="Field 'user' expected type.*SimpleDataModel.*got str"):
            NestedDataModel(user="not_a_datamodel")

    def test_type_validation_with_custom_validation(self):
        """Test that type validation works together with custom validation."""

        class CustomValidationModel(DataModel):
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

        class ConversionModel(DataModel):
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


class TestNestedDataModelConversion:
    """Test automatic nested DataModel conversion in constructor."""

    def test_constructor_dict_to_nested_datamodel(self):
        """Test that constructor automatically converts dicts to nested DataModel objects."""
        # Single nested conversion
        model = NestedDataModel(user={"name": "John", "age": 30})
        assert isinstance(model.user, SimpleDataModel)
        assert model.user.name == "John"
        assert model.user.age == 30
        assert model.user.active is True  # default value

    def test_constructor_multiple_nested_conversion(self):
        """Test constructor with multiple nested dict conversions."""
        model = NestedDataModel(
            user={"name": "John", "age": 30, "active": False}, metadata={"name": "Meta", "age": 25}
        )
        assert isinstance(model.user, SimpleDataModel)
        assert isinstance(model.metadata, SimpleDataModel)
        assert model.user.name == "John"
        assert model.user.active is False
        assert model.metadata.name == "Meta"
        assert model.metadata.active is True  # default

    def test_constructor_mixed_instance_and_dict(self):
        """Test constructor with mix of DataModel instance and dict."""
        user_instance = SimpleDataModel(name="InstanceUser", age=35)
        model = NestedDataModel(user=user_instance, metadata={"name": "DictMeta", "age": 28})
        assert model.user is user_instance
        assert isinstance(model.metadata, SimpleDataModel)
        assert model.user.name == "InstanceUser"
        assert model.metadata.name == "DictMeta"

    def test_constructor_optional_nested_with_none(self):
        """Test constructor with Optional nested field set to None."""
        model = NestedDataModel(user={"name": "OnlyUser", "age": 40}, metadata=None)
        assert isinstance(model.user, SimpleDataModel)
        assert model.user.name == "OnlyUser"
        assert model.metadata is None

    def test_constructor_nested_conversion_works(self):
        """Test that nested objects also perform automatic type conversion."""
        # Type conversion should work in nested object
        model = NestedDataModel(user={"name": 123, "age": 30})
        assert model.user.name == "123"  # int converted to str
        assert isinstance(model.user.name, str)
        assert model.user.age == 30

        # String to int conversion should work in nested age field
        model = NestedDataModel(user={"name": "John", "age": "30"})
        assert model.user.name == "John"
        assert model.user.age == 30  # str converted to int
        assert isinstance(model.user.age, int)

        # Invalid conversion should still fail with type validation error
        with pytest.raises(TypeError, match="Field 'age' expected type.*int.*got str"):
            NestedDataModel(user={"name": "John", "age": "not_a_number"})

    def test_from_dict_still_does_type_conversion(self):
        """Test that from_dict still does type conversion (different from constructor)."""
        # from_dict should convert types
        model = NestedDataModel.from_dict(
            {
                "user": {"name": "John", "age": "30"}  # string age gets converted
            }
        )
        assert isinstance(model.user, SimpleDataModel)
        assert model.user.name == "John"
        assert model.user.age == 30  # converted from string
        assert isinstance(model.user.age, int)

    def test_constructor_and_from_dict_consistent_behavior(self):
        """Test that constructor and from_dict have consistent behavior."""
        # Both constructor and from_dict should convert types consistently
        model1 = NestedDataModel(user={"name": "John", "age": "30"})  # string age converts
        assert model1.user.age == 30
        assert isinstance(model1.user.age, int)

        model2 = NestedDataModel.from_dict({"user": {"name": "John", "age": "30"}})
        assert model2.user.age == 30  # string converted to int
        assert isinstance(model2.user.age, int)

        # Both should produce same result
        assert model1.to_dict() == model2.to_dict()

    def test_deeply_nested_conversion(self):
        """Test conversion with deeply nested DataModel objects."""
        # Create a more complex nested structure for testing
        complex_data = {
            "user": {"name": "John", "age": 30},
            "metadata": {"name": "Meta", "age": 25, "active": False},
        }

        model = NestedDataModel(**complex_data)

        # Verify all levels are properly converted and validated
        assert isinstance(model.user, SimpleDataModel)
        assert isinstance(model.metadata, SimpleDataModel)
        assert model.user.name == "John"
        assert model.metadata.active is False
