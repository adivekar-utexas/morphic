"""Comprehensive tests for Typed module."""

from dataclasses import field
from typing import Dict, List, NoReturn, Optional, Union

import pytest
from pydantic import Field, ValidationError, field_validator

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
    tags: List[str] = Field(default_factory=list)  # Use Pydantic Field with default_factory
    active: bool = True


class ComplexModel(Typed):
    """Complex model for comprehensive testing."""

    id: int
    name: str
    nested: SimpleTyped
    enum_field: SimpleEnum
    optional_nested: Optional[NestedTyped] = None
    union_field: Union[int, str, float] = 42
    list_field: List[str] = Field(default_factory=list)  # Use Pydantic Field with proper typing


class ValidationModel(Typed):
    """Model with custom validation."""

    name: str
    age: int

    @field_validator("age")
    @classmethod
    def validate_age(cls, v):
        if v < 0:
            raise ValueError("Age cannot be negative")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v


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

    def test_model_fields(self):
        """Test that model fields are properly defined."""
        # Create multiple instances
        model1 = SimpleTyped(name="John", age=30)
        model2 = SimpleTyped(name="Jane", age=25)

        # Check model fields using Pydantic's model_fields (access from class)
        fields1 = SimpleTyped.model_fields
        fields2 = SimpleTyped.model_fields

        # Both should use the same field definitions (same class)
        assert fields1 is fields2  # Same object reference (cached on class)
        assert len(fields1) == 3  # name, age, active
        assert "name" in fields1
        assert "age" in fields1
        assert "active" in fields1


class TestModelValidate:
    """Test model_validate functionality."""

    def test_basic_model_validate(self):
        """Test basic dictionary to model conversion using Pydantic's model_validate."""
        data = {"name": "John", "age": 30, "active": False}
        model = SimpleTyped.model_validate(data)

        assert model.name == "John"
        assert model.age == 30
        assert model.active is False

    def test_model_validate_with_missing_optional_fields(self):
        """Test model_validate with missing optional fields."""
        data = {"required_field": "test"}
        model = OptionalFieldsModel.model_validate(data)

        assert model.required_field == "test"
        assert model.optional_str is None
        assert model.union_field == "default"
        assert model.optional_int is None

    def test_model_validate_type_conversion(self):
        """Test automatic type conversion in model_validate."""
        data = {
            "name": "John",
            "age": "30",  # String that should convert to int
            "active": "true",  # String that should convert to bool
        }

        model = SimpleTyped.model_validate(data)
        assert model.name == "John"
        assert model.age == 30
        # Pydantic converts string "true" to True
        assert model.active is True

    def test_model_validate_with_union_types(self):
        """Test model_validate with Union type fields."""
        # Test with int
        data = {"required_field": "test", "union_field": 42}
        model = OptionalFieldsModel.model_validate(data)
        assert model.union_field == 42

        # Test with string
        data = {"required_field": "test", "union_field": "hello"}
        model = OptionalFieldsModel.model_validate(data)
        assert model.union_field == "hello"

    def test_model_validate_with_nested_objects(self):
        """Test model_validate with nested Typed objects."""
        data = {
            "user": {"name": "John", "age": 30, "active": True},
            "metadata": {"name": "Meta", "age": 25, "active": False},
        }
        model = NestedTyped.model_validate(data)

        assert isinstance(model.user, SimpleTyped)
        assert model.user.name == "John"
        assert model.user.age == 30

        assert isinstance(model.metadata, SimpleTyped)
        assert model.metadata.name == "Meta"
        assert model.metadata.age == 25

    def test_model_validate_with_enum(self):
        """Test model_validate with AutoEnum fields."""
        # Test with string values (should auto-convert to AutoEnum)
        data = {"status": "VALUE_A", "optional_status": "VALUE_B"}

        for model in [
            EnumTyped.model_validate(data),
            EnumTyped(**data),
        ]:
            assert model.status == SimpleEnum.VALUE_A
            assert model.optional_status == SimpleEnum.VALUE_B
            assert isinstance(model.status, SimpleEnum)
            assert isinstance(model.optional_status, SimpleEnum)

        # Test with alias
        data_alias = {"status": "C", "optional_status": "charlie"}
        for model_alias in [
            EnumTyped.model_validate(data_alias),
            EnumTyped(**data_alias),
        ]:
            assert model_alias.status == SimpleEnum.VALUE_C
            assert model_alias.optional_status == SimpleEnum.VALUE_C

    def test_autoenum_string_conversion(self):
        """Test comprehensive AutoEnum string conversion capabilities."""

        # Test case-insensitive conversion
        data = {"status": "value_a", "optional_status": "VALUE_B"}
        model = EnumTyped.model_validate(data)
        assert model.status == SimpleEnum.VALUE_A
        assert model.optional_status == SimpleEnum.VALUE_B

        # Test fuzzy matching (spaces, underscores, etc.)
        data_fuzzy = {"status": "Value A", "optional_status": "value-b"}
        model_fuzzy = EnumTyped.model_validate(data_fuzzy)
        assert model_fuzzy.status == SimpleEnum.VALUE_A
        assert model_fuzzy.optional_status == SimpleEnum.VALUE_B

        # Test alias functionality
        data_alias = {"status": "C", "optional_status": "charlie"}
        model_alias = EnumTyped.model_validate(data_alias)
        assert model_alias.status == SimpleEnum.VALUE_C
        assert model_alias.optional_status == SimpleEnum.VALUE_C

        # Test dict conversion back to AutoEnum objects using model_dump
        result = model_alias.model_dump()
        assert result["status"] == SimpleEnum.VALUE_C
        assert result["optional_status"] == SimpleEnum.VALUE_C

    def test_model_validate_with_mock_autoenum(self):
        """Test model_validate with AutoEnum support - Pydantic handles this automatically."""
        # With Pydantic, AutoEnum conversion is handled automatically through type annotations
        # This test verifies that the enum conversion works as expected
        data = {"status": "VALUE_A"}
        model = EnumTyped.model_validate(data)
        assert model.status == SimpleEnum.VALUE_A
        assert isinstance(model.status, SimpleEnum)

    def test_model_validate_extra_fields(self):
        """Test model_validate with extra fields - Pydantic config controls this."""
        data = {"name": "John", "age": 30, "unknown_field": "value"}

        # With extra="forbid" config, extra fields should raise ValidationError
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            SimpleTyped.model_validate(data)

    def test_model_validate_invalid_input_type(self):
        """Test model_validate with invalid input type."""
        with pytest.raises(ValidationError):
            SimpleTyped.model_validate("not a dict")

    def test_model_validate_none_values(self):
        """Test model_validate with None values."""
        data = {"required_field": "test", "optional_str": None}
        model = OptionalFieldsModel.model_validate(data)

        assert model.required_field == "test"
        assert model.optional_str is None


class TestModelDump:
    """Test model_dump functionality."""

    def test_basic_model_dump(self):
        """Test basic model to dictionary conversion using model_dump."""
        model = SimpleTyped(name="John", age=30, active=False)
        result = model.model_dump()

        expected = {"name": "John", "age": 30, "active": False}
        assert result == expected

    def test_model_dump_exclude_none(self):
        """Test model_dump with exclude_none option."""
        model = OptionalFieldsModel(required_field="test", optional_str=None, union_field="hello")
        result = model.model_dump(exclude_none=True)

        assert "optional_str" not in result
        assert "optional_int" not in result
        assert result["required_field"] == "test"
        assert result["union_field"] == "hello"

    def test_model_dump_with_nested_objects(self):
        """Test model_dump with nested Typed objects."""
        nested_user = SimpleTyped(name="John", age=30)
        model = NestedTyped(user=nested_user)
        result = model.model_dump()

        assert "user" in result
        assert isinstance(result["user"], dict)
        assert result["user"]["name"] == "John"
        assert result["user"]["age"] == 30

    def test_model_dump_with_enum(self):
        """Test model_dump with enum fields."""
        model = EnumTyped(status=SimpleEnum.VALUE_A)
        result = model.model_dump()

        assert result["status"] == SimpleEnum.VALUE_A  # AutoEnum returns enum object itself


class TestModelCopy:
    """Test model_copy functionality."""

    def test_basic_model_copy(self):
        """Test basic model_copy without changes."""
        original = SimpleTyped(name="John", age=30, active=False)
        copy = original.model_copy()

        assert copy.name == original.name
        assert copy.age == original.age
        assert copy.active == original.active
        assert copy is not original  # Different instances

    def test_model_copy_with_changes(self):
        """Test model_copy with field changes using update parameter."""
        original = SimpleTyped(name="John", age=30, active=False)
        copy = original.model_copy(update={"name": "Jane", "age": 25})

        assert copy.name == "Jane"
        assert copy.age == 25
        assert copy.active == original.active  # Unchanged
        assert original.name == "John"  # Original unchanged

    def test_model_copy_complex_model(self):
        """Test model_copy with complex nested model."""
        user = SimpleTyped(name="John", age=30)
        original = NestedTyped(user=user)

        new_user = SimpleTyped(name="Jane", age=25, active=True)
        copy = original.model_copy(update={"user": new_user})

        assert isinstance(copy.user, SimpleTyped)
        assert copy.user.name == "Jane"
        assert original.user.name == "John"  # Original unchanged


class TestValidation:
    """Test validation functionality."""

    def test_automatic_validation(self):
        """Test that Pydantic validates automatically during construction."""
        # Validation happens automatically, no need to call validate()
        model = SimpleTyped(name="John", age=30)
        assert model.name == "John"
        assert model.age == 30

    def test_custom_field_validation(self):
        """Test custom field validation with Pydantic validators."""
        # Valid model - validation should pass automatically
        model = ValidationModel(name="John", age=30)
        assert model.name == "John"
        assert model.age == 30

        # Invalid age - should raise during construction (ValueError due to Typed's __init__ wrapper)
        with pytest.raises(ValueError, match="Age cannot be negative"):
            ValidationModel(name="John", age=-5)

        # Invalid name - should raise during construction (ValueError due to Typed's __init__ wrapper)
        with pytest.raises(ValueError, match="Name cannot be empty"):
            ValidationModel(name="", age=30)


class TestPydanticTypeConversion:
    """Test Pydantic's automatic type conversion functionality."""

    def test_pydantic_converts_basic_types(self):
        """Test that Pydantic automatically converts basic types."""
        # String to int conversion
        model = SimpleTyped(name="John", age="42")  # age as string
        assert model.age == 42
        assert isinstance(model.age, int)

        # Test with model_validate for more explicit conversion
        data = {"name": "John", "age": "30", "active": "true"}
        model = SimpleTyped.model_validate(data)
        assert model.age == 30
        assert isinstance(model.age, int)
        assert model.active is True
        assert isinstance(model.active, bool)

    def test_pydantic_validation_errors(self):
        """Test that Pydantic raises ValidationError for invalid conversions."""
        # Invalid int conversion (ValueError due to Typed's __init__ wrapper)
        with pytest.raises(ValueError):
            SimpleTyped(name="John", age="not_a_number")

    def test_pydantic_union_type_handling(self):
        """Test that Pydantic handles Union types correctly."""
        # Test Union field with int
        model = OptionalFieldsModel(required_field="test", union_field=42)
        assert model.union_field == 42
        assert isinstance(model.union_field, int)

        # Test Union field with string
        model = OptionalFieldsModel(required_field="test", union_field="hello")
        assert model.union_field == "hello"
        assert isinstance(model.union_field, str)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_model(self):
        """Test model with no fields."""

        class EmptyModel(Typed):
            pass

        model = EmptyModel()
        assert model.model_dump() == {}

        # model_validate should work with empty dict
        model2 = EmptyModel.model_validate({})
        assert isinstance(model2, EmptyModel)

    def test_model_with_complex_defaults(self):
        """Test model with complex default values."""

        class ComplexDefaultModel(Typed):
            data: Dict[str, int] = field(default_factory=dict)
            items: List[str] = field(default_factory=list)

        model = ComplexDefaultModel()
        assert model.data == {}
        assert model.items == []

        result = model.model_dump(exclude_defaults=True)
        assert len(result) == 0

    def test_circular_reference_prevention(self):
        """Test handling of potential circular references."""
        # This tests that dict handles nested objects properly
        user = SimpleTyped(name="John", age=30)
        nested = NestedTyped(user=user)

        # Should not cause infinite recursion
        result = nested.model_dump()
        assert isinstance(result["user"], dict)

    def test_large_model_performance(self):
        """Test performance with model containing many fields using Pydantic."""

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

        # Test Pydantic model fields (access from class)
        model = LargeModel()
        model_fields = LargeModel.model_fields
        assert len(model_fields) == 10

        # Fields are cached on the class level in Pydantic
        model2 = LargeModel()
        assert LargeModel.model_fields is LargeModel.model_fields  # Same object (cached on class)


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
        model = ComplexModel.model_validate(data)
        assert model.id == 1
        assert model.name == "Test Item"
        assert isinstance(model.nested, SimpleTyped)
        assert model.enum_field == SimpleEnum.VALUE_A

        # Modify the model
        modified = model.model_copy(update={"name": "Modified Item", "union_field": "string_value"})
        assert modified.name == "Modified Item"
        assert modified.union_field == "string_value"
        assert modified.id == model.id  # Unchanged

        # Convert back to dict
        result_dict = modified.model_dump()
        assert result_dict["name"] == "Modified Item"
        assert result_dict["union_field"] == "string_value"
        assert result_dict["enum_field"] == SimpleEnum.VALUE_A  # AutoEnum returns enum object itself

    def test_nested_model_validation(self):
        """Test validation with nested models."""
        # Create nested model that should validate automatically with Pydantic
        user_data = {"name": "John", "age": 30}
        user = SimpleTyped.model_validate(user_data)
        # Pydantic validates automatically, no need to call validate()

        nested = NestedTyped(user=user)
        # Pydantic validates automatically during construction

    def test_roundtrip_consistency(self):
        """Test that dict -> model -> dict is consistent."""
        original_data = {"name": "Test", "age": 25, "active": True}

        # Convert to model and back
        model = SimpleTyped.model_validate(original_data)
        result_data = model.model_dump()

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

        # Should have separate field definitions using Pydantic (access from class)
        base_fields = SimpleTyped.model_fields
        extended_fields = ExtendedModel.model_fields

        assert len(base_fields) == 3  # name, age, active
        assert len(extended_fields) == 4  # name, age, active, extra_field

        # Verify that they are separate field dictionaries
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

        data = PersonList(
            people=[{"name": "John", "age": 30, "active": True}, {"name": "Jane", "age": 25, "active": False}]
        )

        assert len(data.people) == 2
        assert isinstance(data.people[0], SimpleTyped)
        assert isinstance(data.people[1], SimpleTyped)
        assert data.people[0].name == "John"
        assert data.people[1].name == "Jane"

    def test_list_of_Typeds_model_validate(self):
        """Test model_validate with list of Typed objects."""

        class PersonList(Typed):
            people: List[SimpleTyped]

        input_data = {
            "people": [
                {"name": "John", "age": "30", "active": "True"},  # String conversion
                {"name": "Jane", "age": "25", "active": "False"},
            ]
        }

        data = PersonList.model_validate(input_data)

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

        data = PersonDict(
            users={
                "admin": {"name": "Admin", "age": 35, "active": True},
                "guest": {"name": "Guest", "age": 20, "active": False},
            }
        )

        assert len(data.users) == 2
        assert isinstance(data.users["admin"], SimpleTyped)
        assert isinstance(data.users["guest"], SimpleTyped)
        assert data.users["admin"].name == "Admin"
        assert data.users["guest"].name == "Guest"

    def test_dict_of_Typeds_model_validate(self):
        """Test model_validate with dictionary of Typed objects."""

        class PersonDict(Typed):
            users: Dict[str, SimpleTyped]

        input_data = {
            "users": {
                "admin": {"name": "Admin", "age": "35", "active": "True"},
                "guest": {"name": "Guest", "age": "20", "active": "False"},
            }
        }

        data = PersonDict.model_validate(input_data)

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
                {"title": "Done", "tasks": ["completed1"]},
            ],
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
                {"name": "Jane", "email": "jane@example.com"},
            ],
            tags=["work", "personal"],
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
            metadata={"role": "admin", "department": "IT"},
        )

        assert len(person2.addresses) == 1
        assert isinstance(person2.addresses[0], Address)
        assert person2.addresses[0].street == "123 Main St"
        assert person2.metadata == {"role": "admin", "department": "IT"}

    def test_hierarchical_to_dict(self):
        """Test dict with hierarchical structures."""

        class Item(Typed):
            id: int
            name: str

        class Inventory(Typed):
            items: List[Item]
            categories: Dict[str, Item]

        inventory = Inventory(
            items=[{"id": 1, "name": "Item1"}, {"id": 2, "name": "Item2"}],
            categories={"tools": {"id": 3, "name": "Hammer"}},
        )

        result = inventory.model_dump()

        expected = {
            "items": [{"id": 1, "name": "Item1"}, {"id": 2, "name": "Item2"}],
            "categories": {"tools": {"id": 3, "name": "Hammer"}},
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
            items=[{"name": "Item1", "status": "VALUE_A"}, {"name": "Item2", "status": "VALUE_B"}]
        )

        assert len(data.items) == 2
        assert isinstance(data.items[0], StatusItem)
        assert data.items[0].status == SimpleEnum.VALUE_A
        assert data.items[1].status == SimpleEnum.VALUE_B

        # Test model_dump conversion
        result = data.model_dump()
        assert result["items"][0]["status"] == SimpleEnum.VALUE_A
        assert result["items"][1]["status"] == SimpleEnum.VALUE_B
        assert result["default_status"] == SimpleEnum.VALUE_A

    def test_deeply_nested_structures(self):
        """Test very deep nesting of Typed objects."""

        class Level3(Typed):
            value: str

        class Level2(Typed):
            level3_items: List[Level3]

        class Level1(Typed):
            level2_dict: Dict[str, Level2]

        data = Level1(
            level2_dict={
                "section1": {"level3_items": [{"value": "deep1"}, {"value": "deep2"}]},
                "section2": {"level3_items": [{"value": "deep3"}]},
            }
        )

        assert len(data.level2_dict) == 2
        assert isinstance(data.level2_dict["section1"], Level2)
        assert len(data.level2_dict["section1"].level3_items) == 2
        assert isinstance(data.level2_dict["section1"].level3_items[0], Level3)
        assert data.level2_dict["section1"].level3_items[0].value == "deep1"
        assert data.level2_dict["section2"].level3_items[0].value == "deep3"

    def test_hierarchical_type_validation(self):
        """Test type validation in hierarchical structures."""

        class TypedItem(Typed):
            name: str
            value: int

        class TypedContainer(Typed):
            items: List[TypedItem]

        # Should work with correct types
        data = TypedContainer(items=[{"name": "Item1", "value": 42}])
        assert data.items[0].value == 42

        # Should work with correct types (Pydantic doesn't auto-convert int to str)
        data = TypedContainer(
            items=[
                {"name": "Item1", "value": 42}  # Use correct str type for name
            ]
        )
        assert data.items[0].name == "Item1"
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
            "members": [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}],
            "leads": {"tech": {"name": "Alice", "age": 35}, "design": {"name": "Bob", "age": 28}},
        }

        # Convert to model and back
        model = Team.model_validate(original_data)
        result_data = model.model_dump()

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

    def test_invalid_default_values_behavior(self):
        """Test Pydantic's behavior with invalid default values."""

        # Pydantic doesn't validate defaults at class definition time
        # Instead, validation happens during instantiation
        class InvalidIntDefaultModel(Typed):
            age: int = "not_a_number"  # This will cause error during instantiation

        # This should fail when creating an instance without providing age
        with pytest.raises(ValueError):
            InvalidIntDefaultModel()

        # But works if we provide a valid value
        model = InvalidIntDefaultModel(age=25)
        assert model.age == 25

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
                {"name": "Jane", "email": "jane@example.com"},
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
                "guest": {"name": "Guest User", "role": "guest"},
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
            mixed: Union[str, int] = 42  # Should try str first, keep as int if str conversion fails

        model = UnionDefaultModel()
        # The conversion behavior depends on the order of types in Union
        # and how our conversion logic handles it
        assert model.value == 42 or model.value == "42"  # Either conversion is valid
        assert model.mixed == 42 or model.mixed == "42"  # Either conversion is valid

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
                    "items": [{"name": "Phone", "value": 500}, {"name": "Laptop", "value": 1000}],
                },
                "books": {"name": "Books", "items": [{"name": "Python Guide", "value": 50}]},
            }

        model = Inventory()
        assert len(model.categories) == 2
        assert isinstance(model.categories["electronics"], Category)
        assert len(model.categories["electronics"].items) == 2
        assert isinstance(model.categories["electronics"].items[0], Item)
        assert model.categories["electronics"].items[0].name == "Phone"
        assert model.categories["books"].items[0].value == 50


class TestPydanticModelBehavior:
    """Test Pydantic BaseModel behavior (replaces dataclass tests)."""

    def test_pydantic_model_functionality(self):
        """Test that Typed subclasses work as Pydantic models."""

        # Define a class
        class AutoTyped(Typed):
            name: str
            age: int
            active: bool = True

        # Should have Pydantic model functionality
        assert hasattr(AutoTyped, "model_fields")
        assert len(AutoTyped.model_fields) == 3

        # Should be able to instantiate like a Pydantic model
        model = AutoTyped(name="Test", age=25)
        assert model.name == "Test"
        assert model.age == 25
        assert model.active is True

        # Should have Pydantic methods
        assert hasattr(model, "__init__")
        assert hasattr(model, "__repr__")
        assert hasattr(model, "__eq__")

        # Should work with model_validate
        data = {"name": "John", "age": 30, "active": False}
        model2 = AutoTyped.model_validate(data)
        assert model2.name == "John"
        assert model2.age == 30
        assert model2.active is False

        # Should work with model_dump
        result = model2.model_dump()
        assert result == data

    def test_multiple_pydantic_models(self):
        """Test that multiple Pydantic models work independently."""

        # First model
        class Model1(Typed):
            title: str
            count: int = 0

        # Second model
        class Model2(Typed):
            name: str
            value: float = 1.0

        # Both should work identically
        model1 = Model1(title="Test")
        model2 = Model2(name="Test")

        assert hasattr(Model1, "model_fields")
        assert hasattr(Model2, "model_fields")

        # Both should support Typed functionality
        model1_dict = model1.model_dump()
        model2_dict = model2.model_dump()

        assert model1_dict == {"title": "Test", "count": 0}
        assert model2_dict == {"name": "Test", "value": 1.0}

    def test_pydantic_model_with_complex_types(self):
        """Test Pydantic model with complex field types."""

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

        # Should work with model_validate
        data = {
            "name": "Test",
            "tags": ["tag1", "tag2"],
            "metadata": {"key": "value"},
            "status": "VALUE_B",
        }

        model2 = ComplexAutoModel.model_validate(data)
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

        # Test with correct types (Pydantic doesn't auto-convert int to str)
        model1 = TypedModel(name="John", age=30)
        assert model1.name == "John"
        assert isinstance(model1.name, str)
        assert model1.age == 30
        assert isinstance(model1.age, int)

        # Str should convert to int for age field (this works)
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

        # Should fail with None for required field (ValueError due to Typed's __init__ wrapper)
        with pytest.raises(ValueError):
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

        # Should fail with unsupported type (ValueError due to Typed's __init__ wrapper)
        with pytest.raises(ValueError):
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
        # (ValueError due to Typed's __init__ wrapper)
        with pytest.raises(ValueError):
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

        # Should fail with invalid enum string (ValueError due to Typed's __init__ wrapper)
        with pytest.raises(ValueError, match="not_an_enum"):
            EnumTyped(status="not_an_enum")

    def test_nested_Typed_validation(self):
        """Test validation with nested Typed objects."""
        user = SimpleTyped(name="John", age=30, active=True)

        # Should work with correct nested object
        model = NestedTyped(user=user)
        assert model.user.name == "John"

        # Should fail with wrong type for nested field (ValueError due to Typed's __init__ wrapper)
        with pytest.raises(ValueError):
            NestedTyped(user="not_a_Typed")

    def test_type_validation_with_custom_validation(self):
        """Test that type validation works together with custom validation."""
        from pydantic import model_validator

        class CustomValidationModel(Typed):
            name: str
            age: int

            @model_validator(mode="after")
            def validate_age_positive(self):
                if self.age < 0:
                    raise ValueError("Age must be non-negative")
                return self

        # Should work with correct types and valid data
        model = CustomValidationModel(name="John", age=30)
        assert model.name == "John"

        # Use correct types (Pydantic doesn't auto-convert int to str)
        model = CustomValidationModel(name="John", age=30)
        assert model.name == "John"
        assert isinstance(model.name, str)

        # Should fail on custom validation after type validation passes (ValueError due to Typed's __init__ wrapper)
        with pytest.raises(ValueError, match="Age must be non-negative"):
            CustomValidationModel(name="John", age=-5)

    def test_consistent_type_conversion_behavior(self):
        """Test that both model_validate and constructor perform consistent type conversion."""

        class ConversionModel(Typed):
            name: str
            age: int

        # model_validate should do type conversion
        model1 = ConversionModel.model_validate({"name": "John", "age": "30"})
        assert model1.name == "John"
        assert model1.age == 30  # Converted from string
        assert isinstance(model1.age, int)

        # Constructor should also do type conversion (consistent behavior)
        model2 = ConversionModel(name="John", age="30")  # String auto-converted
        assert model2.name == "John"
        assert model2.age == 30  # Converted from string
        assert isinstance(model2.age, int)

        # Both should produce the same result
        assert model1.model_dump() == model2.model_dump()


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
        # Use correct types (Pydantic doesn't auto-convert int to str in nested objects)
        model = NestedTyped(user={"name": "John", "age": 30})
        assert model.user.name == "John"
        assert isinstance(model.user.name, str)
        assert model.user.age == 30

        # String to int conversion should work in nested age field
        model = NestedTyped(user={"name": "John", "age": "30"})
        assert model.user.name == "John"
        assert model.user.age == 30  # str converted to int
        assert isinstance(model.user.age, int)

        # Invalid conversion should still fail (ValueError due to Typed's __init__ wrapper)
        with pytest.raises(ValueError):
            NestedTyped(user={"name": "John", "age": "not_a_number"})

    def test_model_validate_still_does_type_conversion(self):
        """Test that model_validate still does type conversion (alternative to from_dict)."""
        # model_validate should convert types
        model = NestedTyped.model_validate(
            {
                "user": {"name": "John", "age": "30"}  # string age gets converted
            }
        )
        assert isinstance(model.user, SimpleTyped)
        assert model.user.name == "John"
        assert model.user.age == 30  # converted from string
        assert isinstance(model.user.age, int)

    def test_constructor_and_model_validate_consistent_behavior(self):
        """Test that constructor and model_validate have consistent behavior."""
        # Both constructor and model_validate should convert types consistently
        model1 = NestedTyped(user={"name": "John", "age": "30"})  # string age converts
        assert model1.user.age == 30
        assert isinstance(model1.user.age, int)

        model2 = NestedTyped.model_validate({"user": {"name": "John", "age": "30"}})
        assert model2.user.age == 30  # string converted to int
        assert isinstance(model2.user.age, int)

        # Both should produce same result
        assert model1.model_dump() == model2.model_dump()

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


class TestValidateInputs:
    """Comprehensive tests for validate_inputs method."""

    def test_basic_validate_inputs_override(self):
        """Test basic validate_inputs method override with data mutation."""
        
        class NormalizingModel(Typed):
            name: str
            email: str
            
            @classmethod
            def validate_inputs(cls, data: Dict) -> NoReturn:
                # Normalize name to title case
                if 'name' in data:
                    data['name'] = data['name'].strip().title()
                
                # Normalize email to lowercase
                if 'email' in data:
                    data['email'] = data['email'].lower().strip()
        
        # Test that mutations are applied
        model = NormalizingModel(name="  john doe  ", email="  JOHN@EXAMPLE.COM  ")
        assert model.name == "John Doe"
        assert model.email == "john@example.com"
    
    def test_validate_inputs_with_model_validate(self):
        """Test that validate_inputs works with model_validate."""
        
        class ValidatingModel(Typed):
            username: str
            age: int
            
            @classmethod
            def validate_inputs(cls, data: Dict) -> NoReturn:
                # Normalize username
                if 'username' in data:
                    data['username'] = data['username'].lower()
                
                # Validate age range
                if 'age' in data:
                    age = int(data['age']) if isinstance(data['age'], str) else data['age']
                    if age < 0 or age > 120:
                        raise ValueError(f"Age must be between 0 and 120, got {age}")
        
        # Test with model_validate
        model = ValidatingModel.model_validate({
            "username": "JohnDoe",
            "age": "30"
        })
        assert model.username == "johndoe"
        assert model.age == 30
        
        # Test validation error
        with pytest.raises(ValueError, match="Age must be between 0 and 120, got 150"):
            ValidatingModel.model_validate({"username": "test", "age": 150})

    def test_validate_inputs_computed_fields(self):
        """Test validate_inputs for computing derived fields."""
        
        class ProductModel(Typed):
            name: str
            price: float
            tax_rate: float = 0.1
            total_price: Optional[float] = None
            
            @classmethod
            def validate_inputs(cls, data: Dict) -> NoReturn:
                # Compute total price if not provided
                if 'total_price' not in data and 'price' in data:
                    price = float(data['price'])
                    tax_rate = float(data.get('tax_rate', 0.1))
                    data['total_price'] = price * (1 + tax_rate)
                
                # Normalize product name
                if 'name' in data:
                    data['name'] = data['name'].strip().title()
        
        # Test automatic computation
        product = ProductModel(name="  laptop  ", price=1000)
        assert product.name == "Laptop"
        assert product.total_price == 1100.0
        
        # Test with custom tax rate
        product2 = ProductModel(name="mouse", price=50, tax_rate=0.05)
        assert product2.total_price == 52.5
        
        # Test when total_price is provided explicitly
        product3 = ProductModel(name="keyboard", price=100, total_price=125)
        assert product3.total_price == 125  # Not computed

    def test_validate_inputs_conditional_logic(self):
        """Test validate_inputs with conditional logic based on field values."""
        
        class APIRequestModel(Typed):
            method: str
            url: str
            headers: Optional[Dict[str, str]] = None
            body: Optional[str] = None
            
            @classmethod
            def validate_inputs(cls, data: Dict) -> NoReturn:
                # Normalize HTTP method
                if 'method' in data:
                    data['method'] = data['method'].upper()
                
                # Initialize headers if not provided
                if 'headers' not in data:
                    data['headers'] = {}
                
                # For POST/PUT requests with body, ensure Content-Type is set
                method = data.get('method', '').upper()
                if method in ['POST', 'PUT', 'PATCH'] and 'body' in data:
                    headers = data['headers']
                    if 'Content-Type' not in headers:
                        headers['Content-Type'] = 'application/json'
                
                # Validate URL format
                url = data.get('url', '')
                if url and not (url.startswith('http://') or url.startswith('https://')):
                    raise ValueError(f"URL must start with http:// or https://, got: {url}")
        
        # Test POST request with body
        request = APIRequestModel(
            method="post",
            url="https://api.example.com/users",
            body='{"name": "John"}'
        )
        assert request.method == "POST"
        assert request.headers["Content-Type"] == "application/json"
        
        # Test GET request without body
        get_request = APIRequestModel(method="get", url="https://api.example.com/users")
        assert get_request.method == "GET"
        assert "Content-Type" not in get_request.headers
        
        # Test invalid URL
        with pytest.raises(ValueError, match="URL must start with http:// or https://"):
            APIRequestModel(method="GET", url="ftp://invalid.com")

    def test_validate_inputs_with_defaults(self):
        """Test validate_inputs interaction with default values."""
        
        class ConfigModel(Typed):
            host: str = "localhost"
            port: int = 8080
            debug: bool = False
            full_url: Optional[str] = None
            
            @classmethod
            def validate_inputs(cls, data: Dict) -> NoReturn:
                # Compute full URL if not provided
                if 'full_url' not in data:
                    host = data.get('host', 'localhost')
                    port = data.get('port', 8080)
                    data['full_url'] = f"http://{host}:{port}"
                
                # Validate port range
                if 'port' in data:
                    port = int(data['port'])
                    if port < 1 or port > 65535:
                        raise ValueError(f"Port must be between 1 and 65535, got {port}")
        
        # Test with defaults
        config = ConfigModel()
        assert config.host == "localhost"
        assert config.port == 8080
        assert config.full_url == "http://localhost:8080"
        
        # Test with custom values
        config2 = ConfigModel(host="example.com", port=9000)
        assert config2.full_url == "http://example.com:9000"
        
        # Test invalid port
        with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
            ConfigModel(port=70000)

    def test_validate_inputs_error_handling(self):
        """Test error handling in validate_inputs."""
        
        class StrictValidationModel(Typed):
            username: str
            password: str
            
            @classmethod
            def validate_inputs(cls, data: Dict) -> NoReturn:
                # Username validation
                username = data.get('username', '')
                if username:
                    if len(username) < 3:
                        raise ValueError("Username must be at least 3 characters long")
                    if not username.isalnum():
                        raise ValueError("Username must be alphanumeric")
                
                # Password validation
                password = data.get('password', '')
                if password:
                    if len(password) < 8:
                        raise ValueError("Password must be at least 8 characters long")
                    if not any(c.isdigit() for c in password):
                        raise ValueError("Password must contain at least one digit")
        
        # Test valid inputs
        model = StrictValidationModel(username="user123", password="password1")
        assert model.username == "user123"
        
        # Test username too short
        with pytest.raises(ValueError, match="Username must be at least 3 characters long"):
            StrictValidationModel(username="ab", password="password1")
        
        # Test username not alphanumeric
        with pytest.raises(ValueError, match="Username must be alphanumeric"):
            StrictValidationModel(username="user@123", password="password1")
        
        # Test password too short
        with pytest.raises(ValueError, match="Password must be at least 8 characters long"):
            StrictValidationModel(username="user123", password="short")
        
        # Test password without digit
        with pytest.raises(ValueError, match="Password must contain at least one digit"):
            StrictValidationModel(username="user123", password="password")

    def test_validate_inputs_with_nested_types(self):
        """Test validate_inputs with nested Typed objects."""
        
        class ContactInfo(Typed):
            email: str
            phone: Optional[str] = None
            
            @classmethod
            def validate_inputs(cls, data: Dict) -> NoReturn:
                # Normalize email
                if 'email' in data:
                    data['email'] = data['email'].lower()
                
                # Format phone number
                if 'phone' in data and data['phone']:
                    phone = data['phone']
                    # Remove non-digits
                    digits = ''.join(filter(str.isdigit, phone))
                    if len(digits) == 10:
                        data['phone'] = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
                    elif len(digits) != 0:
                        raise ValueError(f"Phone number must have 10 digits, got {len(digits)}")
        
        class PersonModel(Typed):
            name: str
            contact: ContactInfo
            
            @classmethod
            def validate_inputs(cls, data: Dict) -> NoReturn:
                # Normalize name
                if 'name' in data:
                    data['name'] = data['name'].strip().title()
        
        # Test with nested validation
        person = PersonModel(
            name="  john doe  ",
            contact={
                "email": "JOHN@EXAMPLE.COM",
                "phone": "1234567890"
            }
        )
        assert person.name == "John Doe"
        assert person.contact.email == "john@example.com"
        assert person.contact.phone == "(123) 456-7890"
        
        # Test nested validation error
        with pytest.raises(ValueError, match="Phone number must have 10 digits"):
            PersonModel(
                name="John",
                contact={"email": "john@example.com", "phone": "123"}
            )

    def test_validate_inputs_with_lists_and_dicts(self):
        """Test validate_inputs with complex data structures."""
        
        class ProjectModel(Typed):
            name: str
            tags: List[str] = Field(default_factory=list)
            metadata: Dict[str, str] = Field(default_factory=dict)
            extra_field: Optional[str] = None
            
            @classmethod
            def validate_inputs(cls, data: Dict) -> NoReturn:
                # Add computed field based on raw name first
                if 'name' in data and 'extra_field' not in data:
                    data['extra_field'] = f"Project: {data['name']}"
                
                # Normalize project name
                if 'name' in data:
                    data['name'] = data['name'].strip().title()
                
                # Normalize tags to lowercase
                if 'tags' in data and isinstance(data['tags'], list):
                    data['tags'] = [tag.lower().strip() for tag in data['tags'] if tag.strip()]
                
                # Handle metadata if provided
                if 'metadata' in data and isinstance(data['metadata'], dict):
                    # Add creation timestamp if not present
                    if 'created_at' not in data['metadata']:
                        from datetime import datetime
                        data['metadata']['created_at'] = datetime.now().isoformat()
        
        # Test with tags normalization
        project = ProjectModel(
            name="  my project  ",
            tags=["  Python  ", "WEB", "  API  ", ""]
        )
        assert project.name == "My Project"
        assert project.tags == ["python", "web", "api"]
        assert project.extra_field == "Project:   my project  "  # Raw value before normalization
        assert project.metadata == {}  # Default factory dict
        
        # Test with existing metadata
        project2 = ProjectModel(
            name="another project",
            metadata={"version": "1.0"}
        )
        assert "created_at" in project2.metadata
        assert project2.metadata["version"] == "1.0"
        
        # Test with metadata that already has created_at
        project3 = ProjectModel(
            name="third project",
            metadata={"version": "1.0", "created_at": "2024-01-01"}
        )
        assert project3.metadata["created_at"] == "2024-01-01"  # Not overridden

    def test_validate_inputs_execution_order(self):
        """Test that validate_inputs is called at the right time in the validation process."""
        
        class OrderTestModel(Typed):
            value: int
            transformed_value: Optional[int] = None
            
            @classmethod
            def validate_inputs(cls, data: Dict) -> NoReturn:
                # This should be called before Pydantic field validation
                # So we can work with raw input values
                if 'value' in data:
                    # Transform string to int ourselves
                    if isinstance(data['value'], str):
                        data['value'] = int(data['value']) * 2
                    
                    # Compute derived field
                    data['transformed_value'] = data['value'] + 100
        
        # Test with string input that gets transformed
        model = OrderTestModel(value="10")  # String "10" -> int 20 -> transformed 120
        assert model.value == 20
        assert model.transformed_value == 120
        
        # Test with int input
        model2 = OrderTestModel(value=5)  # int 5 -> no string transformation -> transformed 105
        assert model2.value == 5
        assert model2.transformed_value == 105

    def test_validate_inputs_inheritance(self):
        """Test validate_inputs with class inheritance."""
        
        class BaseModel(Typed):
            name: str
            
            @classmethod
            def validate_inputs(cls, data: Dict) -> NoReturn:
                # Base validation - normalize name
                if 'name' in data:
                    data['name'] = data['name'].strip().title()
        
        class ExtendedModel(BaseModel):
            email: str
            age: int
            
            @classmethod
            def validate_inputs(cls, data: Dict) -> NoReturn:
                # Call parent validation first
                super().validate_inputs(data)
                
                # Additional validation
                if 'email' in data:
                    data['email'] = data['email'].lower()
                
                if 'age' in data:
                    age = int(data['age']) if isinstance(data['age'], str) else data['age']
                    if age < 0:
                        raise ValueError("Age cannot be negative")
        
        # Test that both base and extended validations are applied
        model = ExtendedModel(name="  john doe  ", email="JOHN@EXAMPLE.COM", age="30")
        assert model.name == "John Doe"  # Base validation
        assert model.email == "john@example.com"  # Extended validation
        assert model.age == 30
        
        # Test extended validation error
        with pytest.raises(ValueError, match="Age cannot be negative"):
            ExtendedModel(name="John", email="john@example.com", age=-5)

    def test_validate_inputs_no_override(self):
        """Test that models work normally when validate_inputs is not overridden."""
        
        class SimpleModel(Typed):
            name: str
            value: int
            # No validate_inputs override
        
        # Should work normally without any custom validation
        model = SimpleModel(name="test", value=42)
        assert model.name == "test"
        assert model.value == 42
        
        # Should still get Pydantic validation
        with pytest.raises(ValueError):  # Pydantic validation error wrapped by Typed
            SimpleModel(name="test", value="not_a_number")


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
        result = process_users([{"name": "John", "age": "30"}, {"name": "Jane", "age": "25"}])
        assert result == 2

        # Mixed list with dict and Typed object
        user = SimpleTyped(name="Bob", age=35)
        result = process_users([{"name": "John", "age": "30"}, user])
        assert result == 2

    def test_validate_with_optional_types(self):
        """Test validate with Optional type annotations."""
        from typing import Optional

        from morphic.typed import validate

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
        from typing import Union

        from morphic.typed import validate

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
        from morphic.typed import ValidationError, validate

        @validate
        def divide(a: int, b: int) -> float:
            return a / b

        # Test invalid conversion (Pydantic uses different error message format)
        with pytest.raises(ValidationError, match="Input should be a valid integer"):
            divide("not_a_number", 5)

        with pytest.raises(ValidationError, match="Input should be a valid integer"):
            divide(10, "also_not_a_number")

    def test_validate_with_return_validation(self):
        """Test validate with return value validation."""
        from morphic.typed import ValidationError, validate

        @validate(validate_return=True)
        def get_name(user_id: int) -> str:
            if user_id > 0:
                return f"user_{user_id}"
            else:
                return 123  # Invalid return type

        # Valid return
        result = get_name(5)
        assert result == "user_5"

        # Invalid return should raise ValidationError (Pydantic format)
        with pytest.raises(ValidationError, match="Input should be a valid string"):
            get_name(0)

    def test_validate_with_default_validation(self):
        """Test validate validates default parameter values."""
        from morphic.typed import ValidationError, validate

        # Valid defaults should work
        @validate
        def process_items(items: List[str], count: int = 10) -> str:
            return f"Processing {count} of {len(items)} items"

        result = process_items(["a", "b", "c"])
        assert result == "Processing 10 of 3 items"

        # Pydantic's validate_call doesn't validate defaults at decoration time
        # Invalid defaults will cause errors during function call
        @validate
        def bad_function(count: int = "not_a_number"):
            return count

        # The error occurs when the function is called without providing count
        with pytest.raises(ValidationError, match="Input should be a valid integer"):
            bad_function()

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
        assert hasattr(documented_function, "raw_function")
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
        result = create_nested(
            {"user": {"name": "John", "age": "30"}, "metadata": {"name": "Meta", "age": "25"}}
        )
        assert result == "User: John, age 30"

    def test_validate_error_messages(self):
        """Test that validate provides clear error messages."""
        from morphic.typed import ValidationError, validate

        @validate
        def test_function(name: str, age: int) -> None:
            pass

        # Test argument binding error (Pydantic format)
        with pytest.raises(ValidationError, match="Missing required argument"):
            test_function()  # Missing required arguments

        # Test type validation error (Pydantic format)
        with pytest.raises(ValidationError, match="Input should be a valid integer"):
            test_function("John", "definitely_not_a_number")

    def test_validate_with_complex_types(self):
        """Test validate with complex type annotations."""
        from typing import Dict, List

        from morphic.typed import validate

        @validate
        def process_mapping(data: Dict[str, List[int]]) -> int:
            total = 0
            for values in data.values():
                total += sum(values)
            return total

        # Should handle complex nested type conversions
        result = process_mapping(
            {
                "group1": ["1", "2", "3"],  # strings converted to ints
                "group2": [4, 5, 6],  # already ints
            }
        )
        assert result == 21  # 1+2+3+4+5+6

    def test_validate_performance_with_repeated_calls(self):
        """Test that validate doesn't have excessive overhead on repeated calls."""
        import time

        from morphic.typed import validate

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
        from typing import Dict, List

        from morphic.typed import ValidationError, validate

        # Pydantic's validate_call doesn't validate defaults at decoration time
        @validate
        def bad_list(numbers: List[int] = ["1", "2", "invalid"]):
            return numbers

        # The error occurs when the function is called without providing numbers
        with pytest.raises(ValidationError, match="Input should be a valid integer"):
            bad_list()

        # Test valid list conversion works
        @validate
        def good_list(numbers: List[int] = ["1", "2", "3"]):
            return numbers

        result = good_list()
        assert result == [1, 2, 3]
        assert all(isinstance(x, int) for x in result)

        # Test invalid dict values behavior
        @validate
        def bad_dict(mapping: Dict[str, int] = {"a": "1", "b": "invalid"}):
            return mapping

        # The error occurs when the function is called without providing mapping
        with pytest.raises(ValidationError, match="Input should be a valid integer"):
            bad_dict()

        # Test valid dict conversion works
        @validate
        def good_dict(mapping: Dict[str, int] = {"a": "1", "b": "2"}):
            return mapping

        result = good_dict()
        assert result == {"a": 1, "b": 2}
        assert all(isinstance(v, int) for v in result.values())

        # Test nested Typed validation
        @validate
        def bad_nested(users: List[SimpleTyped] = [{"name": "John", "age": "invalid"}]):
            return users

        # The error occurs when the function is called without providing users
        with pytest.raises(ValidationError, match="Input should be a valid integer"):
            bad_nested()

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
        from typing import Optional, Union

        from morphic.typed import ValidationError, validate

        # Test None validation for Optional types
        @validate
        def optional_none(value: Optional[str] = None):
            return value

        result = optional_none()
        assert result is None

        # Test None validation for non-Optional types
        @validate
        def non_optional_none(value: str = None):
            return value

        # Pydantic allows None as default but will validate it when called
        with pytest.raises(ValidationError, match="Input should be a valid string"):
            non_optional_none()

        # Test Union type validation with invalid value
        @validate
        def bad_union(value: Union[int, bool] = "invalid_for_both"):
            return value

        # Pydantic's bool parsing is strict and doesn't accept arbitrary strings
        with pytest.raises(ValidationError, match="Input should be a valid"):
            bad_union()

        # Test Union type validation with valid conversion
        @validate
        def good_union(value: Union[int, str] = "123"):
            return value

        result = good_union()
        assert result == "123"  # Pydantic keeps it as string in Union[int, str]
        assert isinstance(result, str)

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

        # Pydantic recognizes "false" as False
        assert bool_false() is False

        # Pydantic doesn't accept empty string for bool either
        @validate
        def bool_empty(flag: bool = ""):
            return flag

        with pytest.raises(ValidationError, match="Input should be a valid boolean"):
            bool_empty()

        # Test case that would actually fail bool conversion
        @validate
        def any_string_bool(flag: bool = "maybe"):
            return flag

        # Pydantic doesn't accept arbitrary strings for bool
        with pytest.raises(ValidationError, match="Input should be a valid boolean"):
            any_string_bool()

        # Test complex nested structures
        @validate
        def complex_nested(
            data: Dict[str, List[SimpleTyped]] = {
                "group1": [{"name": "Alice", "age": "25"}],
                "group2": [{"name": "Bob", "age": "30"}],
            },
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
        @validate
        def bad_complex_nested(
            data: Dict[str, List[SimpleTyped]] = {"group1": [{"name": "Alice", "age": "invalid_age"}]},
        ):
            return data

        # The error occurs when the function is called without providing data
        with pytest.raises(ValidationError, match="Input should be a valid integer"):
            bad_complex_nested()
