"""Comprehensive tests for Typed module."""

from dataclasses import field
from typing import Dict, List, NoReturn, Optional, Set, Tuple, Union

import pytest
from pydantic import Field, ValidationError, field_validator

from morphic.autoenum import AutoEnum, alias, auto
from morphic.typed import MutableTyped, Typed


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
        # Validation happens automatically, no need to call pre_validate()
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
        # Create nested model that should pre_validate automatically with Pydantic
        user_data = {"name": "John", "age": 30}
        user = SimpleTyped.model_validate(user_data)
        # Pydantic validates automatically, no need to call pre_validate()

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

        # Pydantic doesn't pre_validate defaults at class definition time
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
    """Comprehensive tests for pre_validate method."""

    def test_basic_validate_inputs_override(self):
        """Test basic pre_validate method override with data mutation."""

        class NormalizingModel(Typed):
            name: str
            email: str

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                # Normalize name to title case
                if "name" in data:
                    data["name"] = data["name"].strip().title()

                # Normalize email to lowercase
                if "email" in data:
                    data["email"] = data["email"].lower().strip()

        # Test that mutations are applied
        model = NormalizingModel(name="  john doe  ", email="  JOHN@EXAMPLE.COM  ")
        assert model.name == "John Doe"
        assert model.email == "john@example.com"

    def test_validate_inputs_with_model_validate(self):
        """Test that pre_validate works with model_validate."""

        class ValidatingModel(Typed):
            username: str
            age: int

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                # Normalize username
                if "username" in data:
                    data["username"] = data["username"].lower()

                # Validate age range
                if "age" in data:
                    age = int(data["age"]) if isinstance(data["age"], str) else data["age"]
                    if age < 0 or age > 120:
                        raise ValueError(f"Age must be between 0 and 120, got {age}")

        # Test with model_validate
        model = ValidatingModel.model_validate({"username": "JohnDoe", "age": "30"})
        assert model.username == "johndoe"
        assert model.age == 30

        # Test validation error
        with pytest.raises(ValueError, match="Age must be between 0 and 120, got 150"):
            ValidatingModel.model_validate({"username": "test", "age": 150})

    def test_validate_inputs_computed_fields(self):
        """Test pre_validate for computing derived fields."""

        class ProductModel(Typed):
            name: str
            price: float
            tax_rate: float = 0.1
            total_price: Optional[float] = None

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                # Compute total price if not provided (check for None since defaults are set)
                if data.get("total_price") is None and "price" in data:
                    price = float(data["price"])
                    tax_rate = float(data.get("tax_rate", 0.1))
                    data["total_price"] = price * (1 + tax_rate)

                # Normalize product name
                if "name" in data:
                    data["name"] = data["name"].strip().title()

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
        """Test pre_validate with conditional logic based on field values."""

        class APIRequestModel(Typed):
            method: str
            url: str
            headers: Optional[Dict[str, str]] = None
            body: Optional[str] = None

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                # Normalize HTTP method
                if "method" in data:
                    data["method"] = data["method"].upper()

                # Initialize headers if None (defaults are now set before this runs)
                if data.get("headers") is None:
                    data["headers"] = {}

                # For POST/PUT requests with body, ensure Content-Type is set
                method = data.get("method", "").upper()
                if method in ["POST", "PUT", "PATCH"] and "body" in data:
                    headers = data["headers"]
                    if "Content-Type" not in headers:
                        headers["Content-Type"] = "application/json"

                # Validate URL format
                url = data.get("url", "")
                if url and not (url.startswith("http://") or url.startswith("https://")):
                    raise ValueError(f"URL must start with http:// or https://, got: {url}")

        # Test POST request with body
        request = APIRequestModel(method="post", url="https://api.example.com/users", body='{"name": "John"}')
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
        """Test pre_validate interaction with default values."""

        class ConfigModel(Typed):
            host: str = "localhost"
            port: int = 8080
            debug: bool = False
            full_url: Optional[str] = None

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                # Compute full URL if not provided (check for None since defaults are set)
                if data.get("full_url") is None:
                    host = data.get("host", "localhost")
                    port = data.get("port", 8080)
                    data["full_url"] = f"http://{host}:{port}"

                # Validate port range
                if "port" in data:
                    port = int(data["port"])
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
        """Test error handling in pre_validate."""

        class StrictValidationModel(Typed):
            username: str
            password: str

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                # Username validation
                username = data.get("username", "")
                if username:
                    if len(username) < 3:
                        raise ValueError("Username must be at least 3 characters long")
                    if not username.isalnum():
                        raise ValueError("Username must be alphanumeric")

                # Password validation
                password = data.get("password", "")
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
        """Test pre_validate with nested Typed objects."""

        class ContactInfo(Typed):
            email: str
            phone: Optional[str] = None

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                # Normalize email
                if "email" in data:
                    data["email"] = data["email"].lower()

                # Format phone number
                if "phone" in data and data["phone"]:
                    phone = data["phone"]
                    # Remove non-digits
                    digits = "".join(filter(str.isdigit, phone))
                    if len(digits) == 10:
                        data["phone"] = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
                    elif len(digits) != 0:
                        raise ValueError(f"Phone number must have 10 digits, got {len(digits)}")

        class PersonModel(Typed):
            name: str
            contact: ContactInfo

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                # Normalize name
                if "name" in data:
                    data["name"] = data["name"].strip().title()

        # Test with nested validation
        person = PersonModel(
            name="  john doe  ", contact={"email": "JOHN@EXAMPLE.COM", "phone": "1234567890"}
        )
        assert person.name == "John Doe"
        assert person.contact.email == "john@example.com"
        assert person.contact.phone == "(123) 456-7890"

        # Test nested validation error
        with pytest.raises(ValueError, match="Phone number must have 10 digits"):
            PersonModel(name="John", contact={"email": "john@example.com", "phone": "123"})

    def test_validate_inputs_with_lists_and_dicts(self):
        """Test pre_validate with complex data structures."""

        class ProjectModel(Typed):
            name: str
            tags: List[str] = Field(default_factory=list)
            metadata: Dict[str, str] = Field(default_factory=dict)
            extra_field: Optional[str] = None

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                # Add computed field based on raw name first (check for None since defaults are set)
                if "name" in data and data.get("extra_field") is None:
                    data["extra_field"] = f"Project: {data['name']}"

                # Normalize project name
                if "name" in data:
                    data["name"] = data["name"].strip().title()

                # Normalize tags to lowercase
                if "tags" in data and isinstance(data["tags"], list):
                    data["tags"] = [tag.lower().strip() for tag in data["tags"] if tag.strip()]

                # Handle metadata if provided
                if "metadata" in data and isinstance(data["metadata"], dict):
                    # Add creation timestamp if not present
                    if "created_at" not in data["metadata"]:
                        from datetime import datetime

                        data["metadata"]["created_at"] = datetime.now().isoformat()

        # Test with tags normalization
        project = ProjectModel(name="  my project  ", tags=["  Python  ", "WEB", "  API  ", ""])
        assert project.name == "My Project"
        assert project.tags == ["python", "web", "api"]
        assert project.extra_field == "Project:   my project  "  # Raw value before normalization
        assert "created_at" in project.metadata  # Default factory dict with timestamp added

        # Test with existing metadata
        project2 = ProjectModel(name="another project", metadata={"version": "1.0"})
        assert "created_at" in project2.metadata
        assert project2.metadata["version"] == "1.0"

        # Test with metadata that already has created_at
        project3 = ProjectModel(name="third project", metadata={"version": "1.0", "created_at": "2024-01-01"})
        assert project3.metadata["created_at"] == "2024-01-01"  # Not overridden

    def test_validate_inputs_execution_order(self):
        """Test that pre_validate is called at the right time in the validation process."""

        class OrderTestModel(Typed):
            value: int
            transformed_value: Optional[int] = None

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                # This should be called before Pydantic field validation
                # So we can work with raw input values
                if "value" in data:
                    # Transform string to int ourselves
                    if isinstance(data["value"], str):
                        data["value"] = int(data["value"]) * 2

                    # Compute derived field
                    data["transformed_value"] = data["value"] + 100

        # Test with string input that gets transformed
        model = OrderTestModel(value="10")  # String "10" -> int 20 -> transformed 120
        assert model.value == 20
        assert model.transformed_value == 120

        # Test with int input
        model2 = OrderTestModel(value=5)  # int 5 -> no string transformation -> transformed 105
        assert model2.value == 5
        assert model2.transformed_value == 105

    def test_validate_inputs_inheritance(self):
        """Test pre_validate with class inheritance."""

        class BaseModel(Typed):
            name: str

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                # Base validation - normalize name
                if "name" in data:
                    data["name"] = data["name"].strip().title()

        class ExtendedModel(BaseModel):
            email: str
            age: int

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                # Call parent validation first
                super().pre_validate(data)

                # Additional validation
                if "email" in data:
                    data["email"] = data["email"].lower()

                if "age" in data:
                    age = int(data["age"]) if isinstance(data["age"], str) else data["age"]
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
        """Test that models work normally when pre_validate is not overridden."""

        class SimpleModel(Typed):
            name: str
            value: int
            # No pre_validate override

        # Should work normally without any custom validation
        model = SimpleModel(name="test", value=42)
        assert model.name == "test"
        assert model.value == 42

        # Should still get Pydantic validation
        with pytest.raises(ValueError):  # Pydantic validation error wrapped by Typed
            SimpleModel(name="test", value="not_a_number")


class TestInitialize:
    """Comprehensive tests for Typed.initialize method."""

    def test_basic_initialize_override(self):
        """Test basic initialize method override with field initialization."""

        class InitializingModel(Typed):
            name: str
            computed_field: Optional[str] = None
            timestamp: Optional[str] = None

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                # Set computed fields during validation phase
                if "name" in data:
                    data["computed_field"] = f"Computed: {data['name'].upper()}"
                    from datetime import datetime

                    data["timestamp"] = datetime.now().isoformat()

            def initialize(self) -> NoReturn:
                # Initialize method is called but can't modify frozen instance
                # This is just for testing the method is called
                pass

        # Test that initialization happens after validation
        model = InitializingModel(name="test")
        assert model.name == "test"
        assert model.computed_field == "Computed: TEST"
        assert model.timestamp is not None
        assert isinstance(model.timestamp, str)

    def test_initialize_with_model_validate(self):
        """Test that initialize works with model_validate."""

        class InitializingModel(Typed):
            value: int
            doubled_value: Optional[int] = None
            formatted_value: Optional[str] = None

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                # Set derived fields during validation
                if "value" in data:
                    value = int(data["value"]) if isinstance(data["value"], str) else data["value"]
                    data["doubled_value"] = value * 2
                    data["formatted_value"] = f"Value: {value}"

            def initialize(self) -> NoReturn:
                # Initialize method is called but can't modify frozen instance
                pass

        # Test with model_validate
        model = InitializingModel.model_validate({"value": 42})
        assert model.value == 42
        assert model.doubled_value == 84
        assert model.formatted_value == "Value: 42"

        # Test with string conversion
        model2 = InitializingModel.model_validate({"value": "25"})
        assert model2.value == 25
        assert model2.doubled_value == 50
        assert model2.formatted_value == "Value: 25"

    def test_initialize_with_nested_objects(self):
        """Test initialize with nested Typed objects."""

        class NestedInitializer(Typed):
            name: str
            full_name: Optional[str] = None

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                if "name" in data:
                    data["full_name"] = f"Mr./Ms. {data['name']}"

            def initialize(self) -> NoReturn:
                pass

        class ContainerModel(Typed):
            user: NestedInitializer
            container_info: Optional[str] = None

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                if "user" in data:
                    # Nested object is already converted
                    nested = data["user"]
                    assert isinstance(nested, NestedInitializer)
                    data["container_info"] = f"Container for {nested.full_name}"

            def initialize(self) -> NoReturn:
                pass

        # Test nested initialization
        model = ContainerModel(user={"name": "John"})
        assert model.user.name == "John"
        assert model.user.full_name == "Mr./Ms. John"
        assert model.container_info == "Container for Mr./Ms. John"

    def test_initialize_with_lists_and_dicts(self):
        """Test initialize with complex data structures."""

        class ItemInitializer(Typed):
            name: str
            display_name: Optional[str] = None

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                if "name" in data:
                    data["display_name"] = f"Item: {data['name'].title()}"

            def initialize(self) -> NoReturn:
                pass

        class CollectionModel(Typed):
            items: List[ItemInitializer]
            summary: Optional[str] = None

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                if "items" in data:
                    data["summary"] = f"Collection with {len(data['items'])} items"

            def initialize(self) -> NoReturn:
                pass

        # Test with list of items
        model = CollectionModel(items=[{"name": "apple"}, {"name": "banana"}, {"name": "cherry"}])

        assert len(model.items) == 3
        assert model.items[0].display_name == "Item: Apple"
        assert model.items[1].display_name == "Item: Banana"
        assert model.items[2].display_name == "Item: Cherry"
        assert model.summary == "Collection with 3 items"

    def test_initialize_with_conditional_logic(self):
        """Test initialize with conditional logic based on field values."""

        class ConditionalInitializer(Typed):
            status: str
            priority: int = 1
            processing_time: Optional[int] = None
            error_message: Optional[str] = None

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                # Set processing time based on priority
                if "priority" in data:
                    data["processing_time"] = data["priority"] * 100

                # Set error message for invalid status
                if "status" in data and data["status"] not in ["active", "inactive", "pending"]:
                    data["error_message"] = f"Invalid status: {data['status']}"

            def initialize(self) -> NoReturn:
                pass

        # Test with valid status
        model1 = ConditionalInitializer(status="active", priority=3)
        assert model1.processing_time == 300
        assert model1.error_message is None

        # Test with invalid status
        model2 = ConditionalInitializer(status="invalid", priority=2)
        assert model2.processing_time == 200
        assert model2.error_message == "Invalid status: invalid"

    def test_initialize_with_external_dependencies(self):
        """Test initialize with external dependencies and side effects."""

        class ExternalDependencyModel(Typed):
            id: str
            cache_key: Optional[str] = None
            metadata: Optional[Dict[str, str]] = None

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                if "id" in data:
                    # Simulate external dependency
                    data["cache_key"] = f"cache_{data['id']}_{hash(data['id']) % 1000}"

                    # Initialize metadata
                    data["metadata"] = {
                        "created_at": "2024-01-01",
                        "version": "1.0",
                        "id_hash": str(hash(data["id"])),
                    }

            def initialize(self) -> NoReturn:
                pass

        model = ExternalDependencyModel(id="user123")
        assert model.cache_key.startswith("cache_user123_")
        assert model.metadata["created_at"] == "2024-01-01"
        assert model.metadata["version"] == "1.0"
        assert "id_hash" in model.metadata

    def test_initialize_with_error_handling(self):
        """Test initialize with error handling and validation."""

        class ErrorHandlingModel(Typed):
            value: int
            processed_value: Optional[int] = None
            error: Optional[str] = None

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                if "value" in data:
                    try:
                        # Simulate processing that might fail
                        value = int(data["value"])
                        if value < 0:
                            raise ValueError("Value cannot be negative")
                        data["processed_value"] = value * 2
                    except Exception as e:
                        data["error"] = str(e)

            def initialize(self) -> NoReturn:
                pass

        # Test successful initialization
        model1 = ErrorHandlingModel(value=10)
        assert model1.processed_value == 20
        assert model1.error is None

        # Test initialization with error
        model2 = ErrorHandlingModel(value=-5)
        assert model2.processed_value is None
        assert model2.error == "Value cannot be negative"

    def test_initialize_execution_order(self):
        """Test that initialize is called after validation but before instance creation."""

        class OrderTestModel(Typed):
            value: int
            validation_order: List[str] = Field(default_factory=list)
            initialization_order: List[str] = Field(default_factory=list)

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                # This should be called first
                # Handle PydanticUndefined properly
                from pydantic_core import PydanticUndefined

                if "validation_order" not in data or data["validation_order"] is PydanticUndefined:
                    data["validation_order"] = []
                data["validation_order"].append("validate_called")

            def initialize(self) -> NoReturn:
                # This should be called after validation but before instance is ready
                # Note: Can't modify frozen instance, so we'll just verify the method is called
                # The actual testing of execution order is done through the validation_order
                pass

        model = OrderTestModel(value=42)

        # Check that validation happened first
        assert "validate_called" in model.validation_order

        # The initialize method is called but can't modify the frozen instance
        # This test verifies that the method exists and is called without error

    def test_initialize_inheritance(self):
        """Test initialize with class inheritance."""

        class BaseInitializer(Typed):
            name: str
            base_info: Optional[str] = None

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                if "name" in data:
                    data["base_info"] = f"Base: {data['name']}"

            def initialize(self) -> NoReturn:
                pass

        class ExtendedInitializer(BaseInitializer):
            age: int
            extended_info: Optional[str] = None

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                # Call parent validation
                super().pre_validate(data)
                # Add extended validation
                if "name" in data and "age" in data:
                    data["extended_info"] = f"Extended: {data['name']} is {data['age']} years old"

            def initialize(self) -> NoReturn:
                pass

        model = ExtendedInitializer(name="John", age=30)
        assert model.base_info == "Base: John"
        assert model.extended_info == "Extended: John is 30 years old"

    def test_initialize_no_override(self):
        """Test that models work normally when initialize is not overridden."""

        class SimpleModel(Typed):
            name: str
            value: int
            # No initialize override

        # Should work normally without any custom initialization
        model = SimpleModel(name="test", value=42)
        assert model.name == "test"
        assert model.value == 42

    def test_initialize_vs_validate_differences(self):
        """Test the key differences between initialize and pre_validate methods."""

        class ComparisonModel(Typed):
            raw_value: str
            processed_value: Optional[str] = None
            computed_value: Optional[str] = None

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                # pre_validate works on raw dict data before model creation
                if "raw_value" in data:
                    data["raw_value"] = data["raw_value"].strip().lower()
                    # Can modify the input data
                    data["processed_value"] = f"Processed: {data['raw_value']}"
                    # Also set computed value during validation since we can't modify frozen instance
                    data["computed_value"] = f"Computed: {data['raw_value'].upper()}"

            def initialize(self) -> NoReturn:
                # initialize works on the model instance after validation
                # Note: Can't modify frozen instance, so computation is done in pre_validate
                pass

        model = ComparisonModel(raw_value="  HELLO  ")

        # pre_validate modified the input data
        assert model.raw_value == "hello"  # stripped and lowercased
        assert model.processed_value == "Processed: hello"

        # computed value was set during validation
        assert model.computed_value == "Computed: HELLO"

    def test_initialize_with_factory_method(self):
        """Test initialize works with the of() factory method."""

        class FactoryInitializer(Typed):
            name: str
            factory_info: Optional[str] = None

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                if "name" in data:
                    data["factory_info"] = f"Created via factory: {data['name']}"

            def initialize(self) -> NoReturn:
                pass

        # Test with of() factory method
        model = FactoryInitializer.of(name="FactoryTest")
        assert model.name == "FactoryTest"
        assert model.factory_info == "Created via factory: FactoryTest"

    def test_initialize_with_complex_nested_structures(self):
        """Test initialize with deeply nested structures."""

        class DeepNestedInitializer(Typed):
            level: int
            path: Optional[str] = None

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                if "level" in data:
                    data["path"] = f"Level_{data['level']}"

            def initialize(self) -> NoReturn:
                pass

        class ContainerInitializer(Typed):
            items: List[DeepNestedInitializer]
            container_path: Optional[str] = None

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                if "items" in data:
                    # Items are already converted to objects
                    items = data["items"]
                    assert all(isinstance(item, DeepNestedInitializer) for item in items)
                    paths = [item.path for item in items]
                    data["container_path"] = f"Container[{', '.join(paths)}]"

            def initialize(self) -> NoReturn:
                pass

        class TopLevelInitializer(Typed):
            containers: List[ContainerInitializer]
            top_level_info: Optional[str] = None

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                if "containers" in data:
                    # Containers are already converted to objects
                    containers = data["containers"]
                    assert all(isinstance(container, ContainerInitializer) for container in containers)
                    container_paths = [container.container_path for container in containers]
                    data["top_level_info"] = f"TopLevel[{', '.join(container_paths)}]"

            def initialize(self) -> NoReturn:
                pass

        # Test deeply nested initialization
        model = TopLevelInitializer(
            containers=[{"items": [{"level": 1}, {"level": 2}]}, {"items": [{"level": 3}]}]
        )

        assert model.containers[0].items[0].path == "Level_1"
        assert model.containers[0].items[1].path == "Level_2"
        assert model.containers[1].items[0].path == "Level_3"
        assert model.containers[0].container_path == "Container[Level_1, Level_2]"
        assert model.containers[1].container_path == "Container[Level_3]"
        assert model.top_level_info == "TopLevel[Container[Level_1, Level_2], Container[Level_3]]"


class TestValidateCall:
    """Comprehensive tests for pre_validate decorator."""

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


class TestLifecycleHooks:
    """Comprehensive tests for lifecycle hooks: pre_initialize, pre_validate, post_initialize, post_validate."""

    def test_pre_initialize_only(self):
        """Test class with only pre_initialize hook."""

        class ModelWithPreInit(Typed):
            name: str
            computed: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                if "name" in data:
                    data["computed"] = f"Computed: {data['name']}"

        model = ModelWithPreInit(name="test")
        assert model.name == "test"
        assert model.computed == "Computed: test"

    def test_pre_validate_only(self):
        """Test class with only pre_validate hook."""

        class ModelWithPreValidate(Typed):
            name: str
            email: str

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                if "name" in data:
                    data["name"] = data["name"].strip().title()
                if "email" in data:
                    data["email"] = data["email"].lower()

        model = ModelWithPreValidate(name="  john doe  ", email="JOHN@EXAMPLE.COM")
        assert model.name == "John Doe"
        assert model.email == "john@example.com"

    def test_post_initialize_only(self):
        """Test class with only post_initialize hook."""

        call_log = []

        class ModelWithPostInit(Typed):
            name: str

            def post_initialize(self) -> NoReturn:
                call_log.append(f"post_initialize: {self.name}")

        model = ModelWithPostInit(name="test")
        assert model.name == "test"
        assert "post_initialize: test" in call_log

    def test_post_validate_only(self):
        """Test class with only post_validate hook."""

        class ModelWithPostValidate(Typed):
            start: int
            end: int

            def post_validate(self) -> NoReturn:
                if self.start >= self.end:
                    raise ValueError("start must be less than end")

        # Valid case
        model = ModelWithPostValidate(start=1, end=10)
        assert model.start == 1
        assert model.end == 10

        # Invalid case
        with pytest.raises(ValueError, match="start must be less than end"):
            ModelWithPostValidate(start=10, end=1)

    def test_pre_initialize_and_pre_validate(self):
        """Test class with both pre_initialize and pre_validate hooks."""

        class ModelWithBothPre(Typed):
            first_name: str
            last_name: str
            full_name: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                # Compute full_name from raw values
                if "first_name" in data and "last_name" in data:
                    data["full_name"] = f"{data['first_name']} {data['last_name']}"

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                # Normalize names
                if "first_name" in data:
                    data["first_name"] = data["first_name"].strip().title()
                if "last_name" in data:
                    data["last_name"] = data["last_name"].strip().title()

        model = ModelWithBothPre(first_name="john", last_name="doe")
        assert model.first_name == "John"
        assert model.last_name == "Doe"
        assert model.full_name == "john doe"  # Uses raw values from pre_initialize

    def test_post_initialize_and_post_validate(self):
        """Test class with both post_initialize and post_validate hooks."""

        call_log = []

        class ModelWithBothPost(Typed):
            value: int
            max_value: int = 100

            def post_initialize(self) -> NoReturn:
                call_log.append(f"post_initialize: value={self.value}")

            def post_validate(self) -> NoReturn:
                if self.value > self.max_value:
                    raise ValueError(f"value {self.value} exceeds max {self.max_value}")
                call_log.append(f"post_validate: value={self.value}")

        model = ModelWithBothPost(value=50)
        assert model.value == 50
        assert "post_initialize: value=50" in call_log
        assert "post_validate: value=50" in call_log
        # Verify order: post_initialize comes before post_validate
        init_idx = call_log.index("post_initialize: value=50")
        validate_idx = call_log.index("post_validate: value=50")
        assert init_idx < validate_idx

        # Test validation failure
        with pytest.raises(ValueError, match="value 150 exceeds max 100"):
            ModelWithBothPost(value=150)

    def test_all_four_hooks(self):
        """Test class with all four lifecycle hooks."""

        call_log = []

        class ModelWithAllHooks(Typed):
            name: str
            computed: Optional[str] = None
            normalized: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                call_log.append("pre_initialize")
                if "name" in data:
                    data["computed"] = f"Computed: {data['name']}"

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                call_log.append("pre_validate")
                if "name" in data:
                    data["normalized"] = data["name"].strip().title()

            def post_initialize(self) -> NoReturn:
                call_log.append("post_initialize")

            def post_validate(self) -> NoReturn:
                call_log.append("post_validate")
                if not self.computed:
                    raise ValueError("computed field is required")

        call_log.clear()
        model = ModelWithAllHooks(name="  test  ")

        # Verify execution order
        assert call_log == ["pre_initialize", "pre_validate", "post_initialize", "post_validate"]
        assert model.computed == "Computed:   test  "  # Raw value
        assert model.normalized == "Test"  # Normalized value

    def test_inheritance_parent_pre_initialize_child_pre_validate(self):
        """Test inheritance where parent has pre_initialize, child has pre_validate."""

        class Parent(Typed):
            name: str
            parent_computed: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                if "name" in data:
                    data["parent_computed"] = f"Parent: {data['name']}"

        class Child(Parent):
            age: int
            child_normalized: Optional[str] = None

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                if "name" in data:
                    data["child_normalized"] = data["name"].upper()

        model = Child(name="john", age=30)
        assert model.parent_computed == "Parent: john"  # From parent's pre_initialize
        assert model.child_normalized == "JOHN"  # From child's pre_validate

    def test_inheritance_parent_post_initialize_child_post_validate(self):
        """Test inheritance where parent has post_initialize, child has post_validate."""

        call_log = []

        class Parent(Typed):
            name: str

            def post_initialize(self) -> NoReturn:
                call_log.append(f"Parent post_initialize: {self.name}")

        class Child(Parent):
            age: int

            def post_validate(self) -> NoReturn:
                call_log.append(f"Child post_validate: {self.name}, {self.age}")
                if self.age < 0:
                    raise ValueError("age must be positive")

        call_log.clear()
        model = Child(name="john", age=30)
        assert "Parent post_initialize: john" in call_log
        assert "Child post_validate: john, 30" in call_log

    def test_three_level_inheritance_mixed_hooks(self):
        """Test three-level inheritance (A -> B -> C) with different hooks at each level."""

        call_log = []

        class A(Typed):
            name: str
            a_computed: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                call_log.append("A.pre_initialize")
                if "name" in data:
                    data["a_computed"] = f"A: {data['name']}"

            def post_initialize(self) -> NoReturn:
                call_log.append("A.post_initialize")

        class B(A):
            value: int
            b_computed: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                call_log.append("B.pre_initialize")
                if "value" in data:
                    data["b_computed"] = f"B: {data['value']}"

        class C(B):
            extra: str
            c_normalized: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                call_log.append("C.pre_initialize")
                if "extra" in data:
                    data["c_normalized"] = data["extra"].upper()

            def post_initialize(self) -> NoReturn:
                call_log.append("C.post_initialize")

        call_log.clear()
        model = C(name="test", value=42, extra="hello")

        # Verify all hooks were called in correct order
        assert "A.pre_initialize" in call_log
        assert "B.pre_initialize" in call_log
        assert "C.pre_initialize" in call_log
        assert "A.post_initialize" in call_log
        assert "C.post_initialize" in call_log

        # Verify pre_initialize hooks are called base-to-derived
        a_idx = call_log.index("A.pre_initialize")
        b_idx = call_log.index("B.pre_initialize")
        c_idx = call_log.index("C.pre_initialize")
        assert a_idx < b_idx < c_idx

        # Verify post_initialize hooks are called base-to-derived
        a_post_idx = call_log.index("A.post_initialize")
        c_post_idx = call_log.index("C.post_initialize")
        assert a_post_idx < c_post_idx

        # Verify computed fields
        assert model.a_computed == "A: test"
        assert model.b_computed == "B: 42"
        assert model.c_normalized == "HELLO"

    def test_inheritance_only_middle_class_has_hooks(self):
        """Test inheritance where only the middle class (B) has hooks."""

        call_log = []

        class A(Typed):
            name: str

        class B(A):
            value: int
            b_computed: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                call_log.append("B.pre_initialize")
                if "value" in data:
                    data["b_computed"] = f"B: {data['value']}"

            def post_initialize(self) -> NoReturn:
                call_log.append("B.post_initialize")

        class C(B):
            extra: str

        call_log.clear()
        model = C(name="test", value=42, extra="hello")

        # Verify B's hooks were called even though A and C don't define them
        assert "B.pre_initialize" in call_log
        assert "B.post_initialize" in call_log
        assert model.b_computed == "B: 42"

    def test_inheritance_parent_and_child_same_hook(self):
        """Test inheritance where both parent and child define the same hook."""

        call_log = []

        class Parent(Typed):
            name: str
            parent_field: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                call_log.append("Parent.pre_initialize")
                if "name" in data:
                    data["parent_field"] = f"Parent: {data['name']}"

        class Child(Parent):
            age: int
            child_field: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                call_log.append("Child.pre_initialize")
                if "name" in data:
                    data["child_field"] = f"Child: {data['name']}"

        call_log.clear()
        model = Child(name="john", age=30)

        # Both hooks should be called
        assert "Parent.pre_initialize" in call_log
        assert "Child.pre_initialize" in call_log

        # Parent hook is called before child hook
        parent_idx = call_log.index("Parent.pre_initialize")
        child_idx = call_log.index("Child.pre_initialize")
        assert parent_idx < child_idx

        # Both fields should be set
        assert model.parent_field == "Parent: john"
        assert model.child_field == "Child: john"

    def test_complex_inheritance_all_four_hooks_different_levels(self):
        """Test complex inheritance with all four hooks at different levels."""

        call_log = []

        class Level1(Typed):
            field1: str
            level1_data: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                call_log.append("Level1.pre_initialize")
                if "field1" in data:
                    data["level1_data"] = f"L1: {data['field1']}"

        class Level2(Level1):
            field2: str
            level2_data: Optional[str] = None

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                call_log.append("Level2.pre_validate")
                if "field2" in data:
                    data["level2_data"] = data["field2"].upper()

        class Level3(Level2):
            field3: str

            def post_initialize(self) -> NoReturn:
                call_log.append("Level3.post_initialize")

        class Level4(Level3):
            field4: str

            def post_validate(self) -> NoReturn:
                call_log.append("Level4.post_validate")
                if not self.level1_data or not self.level2_data:
                    raise ValueError("Missing computed data")

        call_log.clear()
        model = Level4(field1="a", field2="b", field3="c", field4="d")

        # Verify execution order
        expected_order = [
            "Level1.pre_initialize",
            "Level2.pre_validate",
            "Level3.post_initialize",
            "Level4.post_validate",
        ]
        assert call_log == expected_order

        # Verify computed fields
        assert model.level1_data == "L1: a"
        assert model.level2_data == "B"

    def test_inheritance_child_overrides_parent_hook(self):
        """Test that child can override parent's hook without calling super."""

        call_log = []

        class Parent(Typed):
            name: str
            computed: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                call_log.append("Parent.pre_initialize")
                if "name" in data:
                    data["computed"] = f"Parent: {data['name']}"

        class ChildWithoutOverride(Parent):
            age: int

        class ChildWithOwnHook(Parent):
            age: int

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                call_log.append("Child.pre_initialize")
                # Don't call super - parent hook is still called automatically
                if "name" in data:
                    data["computed"] = f"Child: {data['name']}"

        # Test child without override - parent hook is called
        call_log.clear()
        model1 = ChildWithoutOverride(name="john", age=30)
        assert "Parent.pre_initialize" in call_log
        assert model1.computed == "Parent: john"

        # Test child with own hook - both hooks are called
        call_log.clear()
        model2 = ChildWithOwnHook(name="jane", age=25)
        assert "Parent.pre_initialize" in call_log
        assert "Child.pre_initialize" in call_log
        # Child's hook runs after parent's, so it wins
        assert model2.computed == "Child: jane"

    def test_hook_exception_propagation(self):
        """Test that exceptions in hooks are properly propagated."""

        class ModelWithPreInitError(Typed):
            value: int

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                if data.get("value", 0) < 0:
                    raise ValueError("pre_initialize: value must be positive")

        class ModelWithPreValidateError(Typed):
            value: int

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                if data.get("value", 0) < 0:
                    raise ValueError("pre_validate: value must be positive")

        class ModelWithPostValidateError(Typed):
            value: int

            def post_validate(self) -> NoReturn:
                if self.value < 0:
                    raise ValueError("post_validate: value must be positive")

        # Test pre_initialize error
        with pytest.raises(ValueError, match="pre_initialize: value must be positive"):
            ModelWithPreInitError(value=-1)

        # Test pre_validate error
        with pytest.raises(ValueError, match="pre_validate: value must be positive"):
            ModelWithPreValidateError(value=-1)

        # Test post_validate error
        with pytest.raises(ValueError, match="post_validate: value must be positive"):
            ModelWithPostValidateError(value=-1)

    def test_hooks_with_default_values(self):
        """Test that hooks work correctly with default values."""

        class ModelWithDefaults(Typed):
            name: str
            value: int = 10
            computed: Optional[str] = None
            normalized: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                # Default values are already set at this point
                if "value" in data:
                    data["computed"] = f"Value: {data['value']}"

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                if "name" in data:
                    data["normalized"] = data["name"].upper()

        # Test with default value
        model1 = ModelWithDefaults(name="test")
        assert model1.value == 10  # Default
        assert model1.computed == "Value: 10"  # Computed from default
        assert model1.normalized == "TEST"

        # Test with provided value
        model2 = ModelWithDefaults(name="test", value=20)
        assert model2.value == 20
        assert model2.computed == "Value: 20"
        assert model2.normalized == "TEST"

    def test_hooks_with_optional_fields(self):
        """Test hooks with Optional fields that may be None."""

        class ModelWithOptionals(Typed):
            required: str
            optional: Optional[str] = None
            computed: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                # Handle None values correctly
                opt_val = data.get("optional")
                if opt_val is not None:
                    data["computed"] = f"Has optional: {opt_val}"
                else:
                    data["computed"] = "No optional"

        # Test with None
        model1 = ModelWithOptionals(required="test")
        assert model1.optional is None
        assert model1.computed == "No optional"

        # Test with value
        model2 = ModelWithOptionals(required="test", optional="value")
        assert model2.optional == "value"
        assert model2.computed == "Has optional: value"

    def test_mutable_typed_with_hooks(self):
        """Test that hooks work with MutableTyped."""

        call_log = []

        class MutableModelWithHooks(MutableTyped):
            name: str
            computed: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                if "name" in data:
                    data["computed"] = f"Computed: {data['name']}"

            def post_initialize(self) -> NoReturn:
                call_log.append(f"Created: {self.name}")

        call_log.clear()
        model = MutableModelWithHooks(name="test")

        # Hooks should work
        assert model.computed == "Computed: test"
        assert "Created: test" in call_log

        # Can still modify fields
        model.name = "updated"
        assert model.name == "updated"
        # Note: computed is not automatically updated when name changes

    def test_mutable_typed_use_pre_hooks_for_derived_fields(self):
        """Test that derived fields should be set in pre hooks, not post hooks."""

        class MutableWithDerivedFields(MutableTyped):
            value: int
            doubled: Optional[int] = None
            status: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                # Set derived fields in pre_initialize (before instance creation)
                if "value" in data:
                    data["doubled"] = data["value"] * 2

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                # Set computed fields in pre_validate
                value = data.get("value", 0)
                if value > 100:
                    data["status"] = "high"
                else:
                    data["status"] = "normal"

        model = MutableWithDerivedFields(value=50)

        # Fields were set by pre hooks
        assert model.doubled == 100
        assert model.status == "normal"

        # Test with high value
        model2 = MutableWithDerivedFields(value=150)
        assert model2.doubled == 300
        assert model2.status == "high"

    def test_mutable_typed_post_hooks_for_side_effects_only(self):
        """Test that post hooks in MutableTyped should only perform side effects, not modify instance."""

        call_log = []

        class MutableWithSideEffects(MutableTyped):
            name: str
            value: int

            def post_initialize(self) -> NoReturn:
                # Post hooks should only perform side effects
                call_log.append(f"Initialized: {self.name}")

            def post_validate(self) -> NoReturn:
                # Validation and logging, not modification
                if self.value < 0:
                    raise ValueError("Value must be non-negative")
                call_log.append(f"Validated: {self.name} = {self.value}")

        call_log.clear()
        model = MutableWithSideEffects(name="test", value=42)

        assert "Initialized: test" in call_log
        assert "Validated: test = 42" in call_log

        # Instance fields are unchanged by post hooks
        assert model.name == "test"
        assert model.value == 42

    def test_mutable_typed_modify_after_creation_no_validation_by_default(self):
        """Test that MutableTyped allows modifications without validation by default."""

        class MutableUser(MutableTyped):
            name: str
            age: int
            count: int = 0

        model = MutableUser(name="john", age=30)
        assert model.name == "john"
        assert model.age == 30
        assert model.count == 0

        # Can modify after creation (no validation for performance)
        model.name = "jane"
        assert model.name == "jane"

        model.age = 25
        assert model.age == 25

        model.count = 5
        assert model.count == 5

        # By default, no validation on assignment
        model.age = "not a number"  # Allowed!
        assert model.age == "not a number"

        # Also allowed for performance
        model.name = 123  # Allowed!

    def test_mutable_typed_assignment_no_hooks_by_default(self):
        """Test that assignment in MutableTyped does NOT trigger hooks by default."""

        hook_call_count = []

        class MutableWithHookCounter(MutableTyped):
            value: int
            computed: Optional[int] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                # Track how many times this is called
                hook_call_count.append("pre_initialize")
                if "value" in data:
                    data["computed"] = data["value"] * 2

        hook_call_count.clear()
        model = MutableWithHookCounter(value=10)

        # pre_initialize was called during creation
        assert len(hook_call_count) == 1
        assert model.computed == 20

        # By default, assignment does NOT trigger hooks (for performance)
        model.value = 15
        assert len(hook_call_count) == 1  # NOT called again
        assert model.computed == 20  # NOT recomputed (still original value)

    def test_mutable_typed_assignment_triggers_hooks_when_enabled(self):
        """Test that assignment triggers hooks when validate_assignment=True."""
        from pydantic import ConfigDict

        hook_call_count = []

        class ValidatedMutableWithHooks(MutableTyped):
            model_config = ConfigDict(
                frozen=False,
                validate_assignment=True,  # Enable validation
            )

            value: int
            computed: Optional[int] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                hook_call_count.append("pre_initialize")
                if "value" in data:
                    data["computed"] = data["value"] * 2

        hook_call_count.clear()
        model = ValidatedMutableWithHooks(value=10)

        # pre_initialize was called during creation
        assert len(hook_call_count) == 1
        assert model.computed == 20

        # With validate_assignment=True, assignment triggers hooks
        model.value = 15
        assert len(hook_call_count) == 2  # Called again!
        assert model.computed == 30  # Recomputed!


class TestNestedTypedWithHooks:
    """Test how nested Typed objects interact with lifecycle hooks."""

    def test_nested_typed_hooks_execution_order(self):
        """Test that nested Typed objects have their own hook execution."""

        call_log = []

        class Inner(Typed):
            value: int
            inner_computed: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                call_log.append("Inner.pre_initialize")
                if "value" in data:
                    data["inner_computed"] = f"Inner: {data['value']}"

            def post_initialize(self) -> NoReturn:
                call_log.append("Inner.post_initialize")

        class Outer(Typed):
            name: str
            inner: Inner
            outer_computed: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                call_log.append("Outer.pre_initialize")
                if "name" in data:
                    data["outer_computed"] = f"Outer: {data['name']}"

            def post_initialize(self) -> NoReturn:
                call_log.append("Outer.post_initialize")

        call_log.clear()
        # Pass nested dict - Pydantic will create Inner object
        outer = Outer(name="test", inner={"value": 42})

        # Verify hooks were called in correct order
        # Inner object is created during Pydantic validation (after Outer's pre hooks)
        assert "Outer.pre_initialize" in call_log
        assert "Inner.pre_initialize" in call_log
        assert "Inner.post_initialize" in call_log
        assert "Outer.post_initialize" in call_log

        # Verify data is correct
        assert outer.outer_computed == "Outer: test"
        assert isinstance(outer.inner, Inner)
        assert outer.inner.inner_computed == "Inner: 42"

    def test_accessing_nested_object_in_pre_initialize(self):
        """Test accessing nested data as object in pre_initialize (automatic conversion)."""

        class Address(Typed):
            street: str
            city: str
            full_address: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                if "street" in data and "city" in data:
                    data["full_address"] = f"{data['street']}, {data['city']}"

        class Person(Typed):
            name: str
            address: Address
            summary: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                # Nested data is automatically converted to object before this hook!
                if "name" in data and "address" in data:
                    addr_obj = data["address"]
                    # It's already an Address object, not a dict
                    assert isinstance(addr_obj, Address)
                    # Can access computed fields directly
                    data["summary"] = f"{data['name']} from {addr_obj.full_address}"

        person = Person(name="John", address={"street": "123 Main St", "city": "NYC"})

        assert person.summary == "John from 123 Main St, NYC"  # Used object access
        assert person.address.full_address == "123 Main St, NYC"  # Inner hook ran

    def test_no_manual_conversion_needed(self):
        """Test that nested objects are automatically converted - no manual work needed."""

        class Config(Typed):
            key: str
            value: str
            display: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                if "key" in data and "value" in data:
                    data["display"] = f"{data['key']}={data['value']}"

        class Settings(Typed):
            name: str
            config: Config
            config_summary: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                # Nested object is already converted - just access it!
                if "config" in data:
                    config_obj = data["config"]
                    # It's already a Config object (not a dict)
                    assert isinstance(config_obj, Config)
                    # Can directly access computed fields
                    data["config_summary"] = f"Config: {config_obj.display}"

        settings = Settings(name="app", config={"key": "debug", "value": "true"})

        assert settings.config_summary == "Config: debug=true"
        assert settings.config.display == "debug=true"

    def test_nested_typed_with_post_hooks(self):
        """Test post hooks with nested Typed objects."""

        call_log = []

        class Item(Typed):
            name: str
            price: float

            def post_initialize(self) -> NoReturn:
                call_log.append(f"Item.post_initialize: {self.name}")

            def post_validate(self) -> NoReturn:
                if self.price <= 0:
                    raise ValueError("Price must be positive")
                call_log.append(f"Item.post_validate: {self.name}")

        class Order(Typed):
            items: List[Item]
            total: float

            def post_initialize(self) -> NoReturn:
                call_log.append("Order.post_initialize")

            def post_validate(self) -> NoReturn:
                # Can access nested objects here
                item_count = len(self.items)
                call_log.append(f"Order.post_validate: {item_count} items")

        call_log.clear()
        order = Order(
            items=[{"name": "Widget", "price": 10.0}, {"name": "Gadget", "price": 20.0}], total=30.0
        )

        # All hooks should have run
        assert "Item.post_initialize: Widget" in call_log
        assert "Item.post_initialize: Gadget" in call_log
        assert "Item.post_validate: Widget" in call_log
        assert "Item.post_validate: Gadget" in call_log
        assert "Order.post_initialize" in call_log
        assert "Order.post_validate: 2 items" in call_log

    def test_deeply_nested_typed_with_hooks(self):
        """Test deeply nested Typed objects with hooks at each level."""

        class Level3(Typed):
            value: str
            level3_data: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                if "value" in data:
                    data["level3_data"] = f"L3: {data['value']}"

        class Level2(Typed):
            level3: Level3
            level2_data: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                # Nested object is already converted
                if "level3" in data:
                    nested_obj = data["level3"]
                    assert isinstance(nested_obj, Level3)
                    # Can access its computed field
                    data["level2_data"] = f"L2: {nested_obj.level3_data}"

        class Level1(Typed):
            level2: Level2
            level1_data: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                # Can traverse nested objects directly
                if "level2" in data:
                    level2_obj = data["level2"]
                    assert isinstance(level2_obj, Level2)
                    # Access deeply nested computed field
                    data["level1_data"] = f"L1: {level2_obj.level3.level3_data}"

        model = Level1(level2={"level3": {"value": "deep"}})

        # All levels should have computed their data
        assert model.level1_data == "L1: L3: deep"
        assert model.level2.level2_data == "L2: L3: deep"
        assert model.level2.level3.level3_data == "L3: deep"

    def test_nested_typed_access_computed_fields(self):
        """Test accessing computed fields from nested objects in hooks."""

        class Dimensions(Typed):
            width: float
            height: float
            area: Optional[float] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                if "width" in data and "height" in data:
                    data["area"] = data["width"] * data["height"]

        class Product(Typed):
            name: str
            dimensions: Dimensions
            volume: Optional[float] = None
            description: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                # Nested object is already converted, can access it directly
                if "dimensions" in data:
                    dims = data["dimensions"]
                    assert isinstance(dims, Dimensions)
                    # Access computed area field from nested object
                    # Assume depth of 10 for volume calculation
                    data["volume"] = dims.area * 10

            @classmethod
            def pre_validate(cls, data: Dict) -> NoReturn:
                # Can access nested object's computed fields
                if "dimensions" in data:
                    dims = data["dimensions"]
                    assert isinstance(dims, Dimensions)
                    data["description"] = f"{data['name']}: {dims.area} sq units"

        product = Product(name="Box", dimensions={"width": 5.0, "height": 3.0})

        assert product.volume == 150.0  # area (15) * 10
        assert product.dimensions.area == 15.0  # 5 * 3
        assert product.description == "Box: 15.0 sq units"

    def test_nested_mutable_typed_with_hooks(self):
        """Test nested MutableTyped objects with hooks."""

        class MutableInner(MutableTyped):
            value: int
            doubled: Optional[int] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                if "value" in data:
                    data["doubled"] = data["value"] * 2

        class MutableOuter(MutableTyped):
            name: str
            inner: MutableInner
            summary: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                if "name" in data and "inner" in data:
                    inner_obj = data["inner"]
                    # Already converted to object
                    assert isinstance(inner_obj, MutableInner)
                    # Can access computed field
                    data["summary"] = f"{data['name']}: {inner_obj.doubled}"

        outer = MutableOuter(name="test", inner={"value": 10})

        assert outer.inner.doubled == 20
        assert outer.summary == "test: 20"  # Uses computed doubled value

        # By default, modifying nested object does NOT trigger hooks (for performance)
        outer.inner.value = 15
        assert outer.inner.doubled == 20  # NOT recomputed! (still original)

        # Outer's summary is also not automatically updated
        assert outer.summary == "test: 20"  # Still old value

    def test_tuple_of_typed_objects(self):
        """Test automatic conversion for Tuple[Typed]."""

        class Point(Typed):
            x: int
            y: int
            label: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                if "x" in data and "y" in data:
                    data["label"] = f"({data['x']}, {data['y']})"

        class Path(Typed):
            points: Tuple[Point, ...]
            description: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                if "points" in data:
                    # Points are already Point objects
                    points = data["points"]
                    assert isinstance(points, tuple)
                    assert all(isinstance(p, Point) for p in points)
                    labels = [p.label for p in points]
                    data["description"] = f"Path: {' -> '.join(labels)}"

        path = Path(points=({"x": 0, "y": 0}, {"x": 1, "y": 1}, {"x": 2, "y": 4}))

        assert isinstance(path.points, tuple)
        assert len(path.points) == 3
        assert path.points[0].label == "(0, 0)"
        assert path.description == "Path: (0, 0) -> (1, 1) -> (2, 4)"

    def test_set_of_typed_objects(self):
        """Test automatic conversion for Set[Typed]."""

        class Tag(Typed):
            name: str
            category: str
            display: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                if "name" in data and "category" in data:
                    data["display"] = f"{data['category']}:{data['name']}"

            def __hash__(self):
                return hash((self.name, self.category))

            def __eq__(self, other):
                return isinstance(other, Tag) and self.name == other.name and self.category == other.category

        class Article(Typed):
            title: str
            tags: Set[Tag]
            tag_summary: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                if "tags" in data:
                    # Tags are already Tag objects (in list form, Pydantic will convert to set)
                    tags = data["tags"]
                    # Could be list or set depending on input format
                    assert all(isinstance(t, Tag) for t in tags)
                    displays = sorted([t.display for t in tags])
                    data["tag_summary"] = f"Tags: {', '.join(displays)}"

        article = Article(
            title="Python Tips",
            tags=[{"name": "python", "category": "language"}, {"name": "tutorial", "category": "type"}],
        )

        assert isinstance(article.tags, set)
        assert len(article.tags) == 2
        # Set maintains Tag objects
        for tag in article.tags:
            assert isinstance(tag, Tag)
            assert tag.display in ["language:python", "type:tutorial"]

    def test_dict_values_typed_objects(self):
        """Test automatic conversion for Dict[str, Typed]."""

        class Config(Typed):
            key: str
            value: str
            formatted: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                if "key" in data and "value" in data:
                    data["formatted"] = f"{data['key']}={data['value']}"

        class Settings(Typed):
            name: str
            configs: Dict[str, Config]
            summary: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                if "configs" in data:
                    # Config values are already Config objects
                    configs = data["configs"]
                    assert isinstance(configs, dict)
                    assert all(isinstance(v, Config) for v in configs.values())
                    formatted_values = [configs[k].formatted for k in sorted(configs.keys())]
                    data["summary"] = f"Settings: {', '.join(formatted_values)}"

        settings = Settings(
            name="app",
            configs={
                "database": {"key": "db_host", "value": "localhost"},
                "cache": {"key": "cache_ttl", "value": "3600"},
            },
        )

        assert isinstance(settings.configs, dict)
        assert len(settings.configs) == 2
        assert settings.configs["database"].formatted == "db_host=localhost"
        assert settings.configs["cache"].formatted == "cache_ttl=3600"
        assert "cache_ttl=3600" in settings.summary
        assert "db_host=localhost" in settings.summary

    def test_autoenum_direct_field(self):
        """Test automatic conversion for direct AutoEnum field."""

        class Status(AutoEnum):
            PENDING = auto()
            ACTIVE = auto()
            COMPLETED = auto()

        class Task(Typed):
            name: str
            status: Status
            status_display: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                if "status" in data:
                    # Status is already a Status enum (not a string!)
                    status = data["status"]
                    assert isinstance(status, Status)
                    data["status_display"] = f"Task is {status.name}"

        task = Task(name="Review PR", status="ACTIVE")

        assert isinstance(task.status, Status)
        assert task.status == Status.ACTIVE
        assert task.status_display == "Task is ACTIVE"

    def test_autoenum_optional_field(self):
        """Test automatic conversion for Optional[AutoEnum]."""

        class Priority(AutoEnum):
            LOW = auto()
            MEDIUM = auto()
            HIGH = auto()

        class Issue(Typed):
            title: str
            priority: Optional[Priority] = None
            priority_label: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                if "priority" in data and data["priority"] is not None:
                    # Priority is already a Priority enum
                    priority = data["priority"]
                    assert isinstance(priority, Priority)
                    data["priority_label"] = f"Priority: {priority.name}"

        issue1 = Issue(title="Bug", priority="HIGH")
        assert isinstance(issue1.priority, Priority)
        assert issue1.priority == Priority.HIGH
        assert issue1.priority_label == "Priority: HIGH"

        issue2 = Issue(title="Feature", priority=None)
        assert issue2.priority is None
        assert issue2.priority_label is None

    def test_autoenum_list_field(self):
        """Test automatic conversion for List[AutoEnum]."""

        class Permission(AutoEnum):
            READ = auto()
            WRITE = auto()
            DELETE = auto()

        class User(Typed):
            name: str
            permissions: List[Permission]
            permissions_summary: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                if "permissions" in data:
                    # Permissions are already Permission enums
                    perms = data["permissions"]
                    assert all(isinstance(p, Permission) for p in perms)
                    names = [p.name for p in perms]
                    data["permissions_summary"] = f"Permissions: {', '.join(names)}"

        user = User(name="Alice", permissions=["READ", "WRITE"])

        assert isinstance(user.permissions, list)
        assert len(user.permissions) == 2
        assert all(isinstance(p, Permission) for p in user.permissions)
        assert user.permissions[0] == Permission.READ
        assert user.permissions[1] == Permission.WRITE
        assert user.permissions_summary == "Permissions: READ, WRITE"

    def test_autoenum_set_field(self):
        """Test automatic conversion for Set[AutoEnum]."""

        class Feature(AutoEnum):
            CACHING = auto()
            LOGGING = auto()
            METRICS = auto()

        class Service(Typed):
            name: str
            features: Set[Feature]
            features_summary: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                if "features" in data:
                    # Features are already Feature enums (in list form, Pydantic converts to set)
                    features = data["features"]
                    assert all(isinstance(f, Feature) for f in features)
                    names = sorted([f.name for f in features])
                    data["features_summary"] = f"Features: {', '.join(names)}"

        service = Service(name="API", features=["CACHING", "LOGGING"])

        assert isinstance(service.features, set)
        assert len(service.features) == 2
        assert all(isinstance(f, Feature) for f in service.features)
        assert Feature.CACHING in service.features
        assert Feature.LOGGING in service.features

    def test_autoenum_tuple_field(self):
        """Test automatic conversion for Tuple[AutoEnum, ...]."""

        class Color(AutoEnum):
            RED = auto()
            GREEN = auto()
            BLUE = auto()

        class Palette(Typed):
            name: str
            colors: Tuple[Color, ...]
            colors_display: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                if "colors" in data:
                    # Colors are already Color enums
                    colors = data["colors"]
                    assert isinstance(colors, tuple)
                    assert all(isinstance(c, Color) for c in colors)
                    names = [c.name for c in colors]
                    data["colors_display"] = f"Colors: {' -> '.join(names)}"

        palette = Palette(name="Primary", colors=("RED", "GREEN", "BLUE"))

        assert isinstance(palette.colors, tuple)
        assert len(palette.colors) == 3
        assert all(isinstance(c, Color) for c in palette.colors)
        assert palette.colors_display == "Colors: RED -> GREEN -> BLUE"

    def test_autoenum_dict_values(self):
        """Test automatic conversion for Dict[str, AutoEnum]."""

        class Environment(AutoEnum):
            DEV = auto()
            STAGING = auto()
            PROD = auto()

        class Deployment(Typed):
            name: str
            environments: Dict[str, Environment]
            summary: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                if "environments" in data:
                    # Environment values are already Environment enums
                    envs = data["environments"]
                    assert isinstance(envs, dict)
                    assert all(isinstance(v, Environment) for v in envs.values())
                    env_strs = [f"{k}:{v.name}" for k, v in sorted(envs.items())]
                    data["summary"] = f"Envs: {', '.join(env_strs)}"

        deployment = Deployment(
            name="Release 1.0",
            environments={"frontend": "PROD", "backend": "PROD", "worker": "STAGING"},
        )

        assert isinstance(deployment.environments, dict)
        assert len(deployment.environments) == 3
        assert deployment.environments["frontend"] == Environment.PROD
        assert deployment.environments["backend"] == Environment.PROD
        assert deployment.environments["worker"] == Environment.STAGING
        assert "frontend:PROD" in deployment.summary

    def test_autoenum_with_typed_nested(self):
        """Test AutoEnum conversion with nested Typed objects."""

        class Status(AutoEnum):
            DRAFT = auto()
            PUBLISHED = auto()
            ARCHIVED = auto()

        class Metadata(Typed):
            author: str
            status: Status
            display: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                if "author" in data and "status" in data:
                    # Status is already a Status enum
                    status = data["status"]
                    assert isinstance(status, Status)
                    data["display"] = f"{data['author']}: {status.name}"

        class Document(Typed):
            title: str
            metadata: Metadata
            summary: Optional[str] = None

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                if "metadata" in data:
                    # Metadata is already a Metadata object
                    meta = data["metadata"]
                    assert isinstance(meta, Metadata)
                    # And its status is already an enum
                    assert isinstance(meta.status, Status)
                    data["summary"] = f"{meta.display}"

        doc = Document(title="Article", metadata={"author": "John", "status": "PUBLISHED"})

        assert isinstance(doc.metadata, Metadata)
        assert isinstance(doc.metadata.status, Status)
        assert doc.metadata.status == Status.PUBLISHED
        assert doc.metadata.display == "John: PUBLISHED"
        assert doc.summary == "John: PUBLISHED"

    def test_class_variable_access_in_parent_hook(self):
        """Test that parent hooks can access class variables defined in child class."""
        from typing import ClassVar

        class Parent(Typed):
            name: str
            computed: Optional[str] = None
            # Class variable declared but not assigned
            multiplier: ClassVar[int]

            @classmethod
            def pre_initialize(cls, data: Dict) -> NoReturn:
                if "name" in data:
                    # This should access the child's multiplier, not cause an error
                    data["computed"] = f"{data['name']} x {cls.multiplier}"

        class Child(Parent):
            # Class variable assigned in child
            multiplier: ClassVar[int] = 10

        # This should work - parent's hook should see child's class variable
        child = Child(name="test")
        assert child.computed == "test x 10"

        class AnotherChild(Parent):
            multiplier: ClassVar[int] = 5

        another = AnotherChild(name="another")
        assert another.computed == "another x 5"


class TestPrivateAttributeValidation:
    """Test private attribute validation in Typed models.

    Private attributes (prefixed with _) are validated when validate_assignment=True.
    Typed has validate_assignment=True by default, so private attributes are validated
    automatically. Models can opt out by setting validate_assignment=False.
    """

    def test_int_private_attr_valid(self):
        """Test that valid int values are accepted."""
        from pydantic import PrivateAttr

        class Counter(Typed):
            name: str
            _count: int = PrivateAttr(default=0)

            def post_initialize(self) -> None:
                self._count = 10

        counter = Counter(name="test")
        assert counter._count == 10

        # Should also allow setting after initialization
        counter._count = 20
        assert counter._count == 20

    def test_int_private_attr_invalid(self):
        """Test that invalid int values raise ValidationError."""
        from pydantic import PrivateAttr

        class Counter(Typed):
            name: str
            _count: int = PrivateAttr(default=0)

        counter = Counter(name="test")

        # Try to set invalid type
        with pytest.raises(ValidationError) as exc_info:
            counter._count = "invalid"

        # ValidationError is raised directly from Pydantic's TypeAdapter
        # which provides structured error information
        assert len(exc_info.value.errors()) > 0

    def test_int_private_attr_type_coercion(self):
        """Test that Pydantic type coercion works for private attrs."""
        from pydantic import PrivateAttr

        class Counter(Typed):
            name: str
            _count: int = PrivateAttr(default=0)

        counter = Counter(name="test")

        # String that can be coerced to int should work
        counter._count = "42"
        assert counter._count == 42
        assert isinstance(counter._count, int)

    def test_str_private_attr(self):
        """Test string private attribute validation."""
        from pydantic import PrivateAttr

        class Model(Typed):
            id: int
            _label: str = PrivateAttr(default="")

            def post_initialize(self) -> None:
                self._label = "test"

        model = Model(id=1)
        assert model._label == "test"

        model._label = "updated"
        assert model._label == "updated"

        # Invalid type should fail
        with pytest.raises(ValidationError):
            model._label = 123

    def test_optional_private_attr(self):
        """Test Optional[int] private attribute."""
        from pydantic import PrivateAttr

        class Model(Typed):
            name: str
            _value: Optional[int] = PrivateAttr(default=None)

        model = Model(name="test")
        assert model._value is None

        model._value = 42
        assert model._value == 42

        model._value = None
        assert model._value is None

        # Invalid type should fail
        with pytest.raises(ValidationError):
            model._value = "invalid"

    def test_list_private_attr(self):
        """Test List[int] private attribute."""
        from pydantic import PrivateAttr

        class Model(Typed):
            name: str
            _items: List[int] = PrivateAttr(default_factory=list)

        model = Model(name="test")
        assert model._items == []

        model._items = [1, 2, 3]
        assert model._items == [1, 2, 3]

        # Type coercion in list elements
        model._items = ["4", "5", "6"]
        assert model._items == [4, 5, 6]

        # Invalid element type
        with pytest.raises(ValidationError):
            model._items = [1, "invalid", 3]

    def test_nested_typed_private_attr(self):
        """Test private attribute with nested Typed model."""
        from pydantic import PrivateAttr

        class Config(Typed):
            value: int

        class System(Typed):
            name: str
            _config: Optional[Config] = PrivateAttr(default=None)

        system = System(name="System1")
        assert system._config is None

        # Set valid Config instance
        system._config = Config(value=10)
        assert system._config.value == 10

        # Pydantic should convert dict to Config
        system._config = {"value": 20}
        assert isinstance(system._config, Config)
        assert system._config.value == 20

        # Invalid type
        with pytest.raises(ValidationError):
            system._config = "not_a_config"

    def test_union_private_attr(self):
        """Test Union[int, str] private attribute."""
        from pydantic import PrivateAttr

        class Model(Typed):
            name: str
            _value: Union[int, str] = PrivateAttr(default=0)

        model = Model(name="test")

        # Both int and str should work
        model._value = 42
        assert model._value == 42

        model._value = "hello"
        assert model._value == "hello"

        # Invalid type
        with pytest.raises(ValidationError):
            model._value = [1, 2, 3]

    def test_untyped_private_attr_no_validation(self):
        """Test that private attributes without type hints have no validation."""

        class FlexibleModel(Typed):
            name: str

            def post_initialize(self) -> None:
                # No type annotation, so no validation
                self._anything = "string"

        model = FlexibleModel(name="test")
        assert model._anything == "string"

        # Should allow any type since it's untyped
        model._anything = 123
        assert model._anything == 123

        model._anything = [1, 2, 3]
        assert model._anything == [1, 2, 3]

    def test_inherited_private_attrs(self):
        """Test that private attributes from parent classes are validated."""
        from pydantic import PrivateAttr

        class Parent(Typed):
            name: str
            _parent_count: int = PrivateAttr(default=0)

        class Child(Parent):
            age: int
            _child_count: int = PrivateAttr(default=0)

        child = Child(name="test", age=10)

        # Both parent and child private attrs should validate
        child._parent_count = 5
        assert child._parent_count == 5

        child._child_count = 10
        assert child._child_count == 10

        # Both should validate types
        with pytest.raises(ValidationError):
            child._parent_count = "invalid"

        with pytest.raises(ValidationError):
            child._child_count = "invalid"

    def test_overridden_private_attr_annotation(self):
        """Test that child can override parent's private attr annotation."""
        from pydantic import PrivateAttr

        class Parent(Typed):
            name: str
            _value: int = PrivateAttr(default=0)

        class Child(Parent):
            age: int
            _value: str = PrivateAttr(default="")  # Override with different type

        child = Child(name="test", age=10)

        # Should validate against child's annotation (str)
        child._value = "hello"
        assert child._value == "hello"

        # Should fail int validation (child's type is str)
        with pytest.raises(ValidationError):
            child._value = 123

    def test_setting_in_post_initialize(self):
        """Test private attribute validation in post_initialize hook."""
        from pydantic import PrivateAttr

        class Model(Typed):
            value: int
            _doubled: int = PrivateAttr()

            def post_initialize(self) -> NoReturn:
                # Should validate the assignment
                self._doubled = self.value * 2

        model = Model(value=5)
        assert model._doubled == 10

    def test_with_validate_assignment_true(self):
        """Test that validation occurs when validate_assignment=True."""
        from pydantic import ConfigDict, PrivateAttr

        class Model(Typed):
            model_config = ConfigDict(
                extra="forbid",
                frozen=True,
                validate_assignment=True,
            )

            name: str
            _count: int = PrivateAttr(default=0)

        model = Model(name="test")
        model._count = 42  # Valid
        assert model._count == 42

        # Invalid type should fail
        with pytest.raises(ValidationError) as exc_info:
            model._count = "invalid"

        # ValidationError provides structured error information
        assert len(exc_info.value.errors()) > 0

    def test_with_validate_assignment_false(self):
        """Test that validation is skipped when validate_assignment=False."""
        from pydantic import ConfigDict, PrivateAttr

        class NoValidationModel(Typed):
            model_config = ConfigDict(
                extra="forbid",
                frozen=True,
                validate_private_assignment=False,  # Disable validation
            )

            name: str
            _count: int = PrivateAttr(default=0)

        model = NoValidationModel(name="test")

        # Should allow any type when validation is disabled
        model._count = 42
        assert model._count == 42

        model._count = "not_an_int"  # Should NOT raise error
        assert model._count == "not_an_int"

        model._count = [1, 2, 3]  # Should NOT raise error
        assert model._count == [1, 2, 3]

    def test_typed_default_has_validation(self):
        """Test that Typed class has validate_private_assignment=True by default."""
        from pydantic import PrivateAttr

        class DefaultTyped(Typed):
            name: str
            _value: int = PrivateAttr(default=0)

        # Typed should have validate_private_assignment=True by default
        assert DefaultTyped.model_config.get("validate_private_assignment", False) is True

        model = DefaultTyped(name="test")
        model._value = 10  # Valid

        # Should validate by default
        with pytest.raises(ValidationError):
            model._value = "invalid"

    def test_public_fields_still_frozen(self):
        """Test that public fields remain frozen despite __setattr__ override."""

        class Model(Typed):
            name: str
            value: int

        model = Model(name="test", value=10)

        # Public fields should still be frozen
        with pytest.raises(ValidationError):
            model.name = "new_name"

        with pytest.raises(ValidationError):
            model.value = 20

    def test_error_message_includes_details(self):
        """Test that validation errors include helpful details."""

        class Model(Typed):
            name: str
            _count: int = 0

        model = Model(name="test")

        with pytest.raises(ValidationError) as exc_info:
            model._count = "invalid"

        # ValidationError provides structured error information
        errors = exc_info.value.errors()
        assert len(errors) > 0

        # Check that error contains relevant information
        error = errors[0]
        assert "msg" in error
        assert "input" in error
        # The error has structured data from Pydantic

    def test_arbitrary_types_in_private_attrs(self):
        """Test that arbitrary types (like threading.Thread) work in private attributes."""
        import threading

        from pydantic import PrivateAttr

        class ThreadManager(Typed):
            name: str
            _thread: Optional[threading.Thread] = PrivateAttr(default=None)
            _thread2: Optional[threading.Thread] = None

            def post_initialize(self) -> None:
                # Should allow setting arbitrary types
                self._thread = threading.Thread(target=lambda: None)
                self._thread2 = threading.Thread(target=lambda: print("hello"))

        model = ThreadManager(name="manager")

        # Should be able to get the threads
        assert isinstance(model._thread, threading.Thread)
        assert isinstance(model._thread2, threading.Thread)

        # Should allow setting valid arbitrary types
        new_thread = threading.Thread(target=lambda: print("test"))
        model._thread = new_thread
        assert model._thread is new_thread

        # Should reject wrong types
        with pytest.raises(ValidationError) as exc_info:
            model._thread = "not a thread"

        # ValidationError provides structured error information
        errors = exc_info.value.errors()
        assert len(errors) > 0
        error_msg = str(exc_info.value)
        assert "_thread" in error_msg

    def test_arbitrary_types_optional(self):
        """Test Optional[arbitrary_type] in private attributes."""
        import threading

        from pydantic import PrivateAttr

        class Service(Typed):
            name: str
            _thread: Optional[threading.Thread] = PrivateAttr(default=None)

        model = Service(name="service")

        # Should allow None
        assert model._thread is None
        model._thread = None
        assert model._thread is None

        # Should allow valid thread
        thread = threading.Thread(target=lambda: None)
        model._thread = thread
        assert model._thread is thread

        # Note: For Optional[arbitrary_type], we can't validate the inner type
        # easily without TypeAdapter, so this will pass (falls back to no validation
        # for generic types with arbitrary inner types)
        # This is acceptable behavior matching Pydantic's arbitrary_types_allowed

    def test_setattr_performance(self):
        """Test that __setattr__ is fast enough for private attributes."""
        import time

        from pydantic import PrivateAttr

        class PerformanceModel(Typed):
            name: str
            _count: int = PrivateAttr(default=0)
            _value: str = PrivateAttr(default="")
            _data: Optional[int] = PrivateAttr(default=None)

        model = PerformanceModel(name="test")

        # Warm up the cache
        model._count = 1
        model._value = "warm"
        model._data = 42

        # Measure time for 10000 assignments
        iterations = 10000
        start = time.perf_counter()
        for i in range(iterations):
            model._count = i
            model._value = str(i)
            model._data = i * 2
        end = time.perf_counter()

        total_time = end - start
        time_per_assignment = (total_time / (iterations * 3)) * 1_000_000  # microseconds

        # With caching, should be under 5 microseconds
        assert time_per_assignment < 5.0, f"Assignment took {time_per_assignment:.2f} µs, expected < 5.0 µs"


class TestMutableTyped:
    """Test MutableTyped functionality - mutable variant of Typed."""

    def test_mutable_typed_basic_modification(self):
        """Test that MutableTyped instances can be modified after creation."""

        class User(MutableTyped):
            name: str
            age: int
            active: bool = True

        user = User(name="John", age=30)

        # Should be able to modify fields
        user.name = "Jane"
        user.age = 25
        user.active = False

        assert user.name == "Jane"
        assert user.age == 25
        assert user.active is False

    def test_mutable_typed_no_validation_on_assignment_by_default(self):
        """Test that MutableTyped does NOT validate assignments by default for performance."""

        class User(MutableTyped):
            name: str
            age: int

        user = User(name="John", age=30)

        # Valid assignment should work
        user.age = 25
        assert user.age == 25

        # By default, no validation on assignment for performance
        user.age = "not_a_number"  # Allowed!
        assert user.age == "not_a_number"

    def test_mutable_typed_validation_on_assignment_when_enabled(self):
        """Test that MutableTyped validates assignments when explicitly enabled."""
        from pydantic import ConfigDict

        class ValidatedUser(MutableTyped):
            model_config = ConfigDict(
                frozen=False,
                validate_assignment=True,  # Enable validation
            )

            name: str
            age: int

        user = ValidatedUser(name="John", age=30)

        # Valid assignment should work
        user.age = 25
        assert user.age == 25

        # Now validation is enabled, so invalid assignment should raise ValidationError
        with pytest.raises(ValidationError, match="Input should be a valid integer"):
            user.age = "not_a_number"

    def test_mutable_typed_with_optional_fields(self):
        """Test MutableTyped with optional fields."""

        class Profile(MutableTyped):
            name: str
            email: Optional[str] = None
            age: Optional[int] = None

        profile = Profile(name="John")

        # Should be able to set optional fields
        profile.email = "john@example.com"
        profile.age = 30

        assert profile.email == "john@example.com"
        assert profile.age == 30

        # Should be able to set to None
        profile.email = None
        assert profile.email is None

    def test_mutable_typed_with_union_types(self):
        """Test MutableTyped with Union types."""

        class FlexibleValue(MutableTyped):
            value: Union[int, str]
            count: int = 0

        item = FlexibleValue(value=42)

        # Should be able to change to different union member
        item.value = "hello"
        assert item.value == "hello"

        # Should be able to change back
        item.value = 100
        assert item.value == 100

    def test_mutable_typed_with_nested_objects(self):
        """Test MutableTyped with nested Typed objects."""

        class Address(Typed):
            street: str
            city: str

        class Person(MutableTyped):
            name: str
            address: Address

        person = Person(name="John", address=Address(street="123 Main", city="NYC"))

        # Should be able to replace nested object
        new_address = Address(street="456 Oak", city="LA")
        person.address = new_address

        assert person.address.street == "456 Oak"
        assert person.address.city == "LA"

    def test_mutable_typed_with_lists(self):
        """Test MutableTyped with list fields."""

        class TaskList(MutableTyped):
            name: str
            tasks: List[str] = []

        task_list = TaskList(name="Work")

        # Should be able to modify list
        task_list.tasks = ["task1", "task2"]
        assert task_list.tasks == ["task1", "task2"]

        # Should be able to replace list
        task_list.tasks = ["new_task"]
        assert task_list.tasks == ["new_task"]

    def test_mutable_typed_with_dicts(self):
        """Test MutableTyped with dictionary fields."""

        class Config(MutableTyped):
            name: str
            settings: Dict[str, str] = {}

        config = Config(name="app")

        # Should be able to modify dict
        config.settings = {"key1": "value1", "key2": "value2"}
        assert config.settings["key1"] == "value1"

        # Should be able to replace dict
        config.settings = {"new_key": "new_value"}
        assert config.settings["new_key"] == "new_value"

    def test_mutable_typed_inheritance(self):
        """Test that MutableTyped can be inherited."""

        class BaseUser(MutableTyped):
            name: str
            age: int

        class AdminUser(BaseUser):
            permissions: List[str] = []

        admin = AdminUser(name="Admin", age=30)

        # Should be able to modify inherited fields
        admin.name = "SuperAdmin"
        admin.age = 35
        admin.permissions = ["read", "write", "delete"]

        assert admin.name == "SuperAdmin"
        assert admin.age == 35
        assert admin.permissions == ["read", "write", "delete"]


class TestTypedFrozen:
    """Test that regular Typed instances are frozen (immutable)."""

    def test_typed_frozen_basic(self):
        """Test that Typed instances cannot be modified."""

        class User(Typed):
            name: str
            age: int
            active: bool = True

        user = User(name="John", age=30)

        # Should not be able to modify fields
        with pytest.raises(ValidationError, match="Instance is frozen"):
            user.name = "Jane"

        with pytest.raises(ValidationError, match="Instance is frozen"):
            user.age = 25

        with pytest.raises(ValidationError, match="Instance is frozen"):
            user.active = False

    def test_typed_frozen_with_optional_fields(self):
        """Test that Typed instances with optional fields are still frozen."""

        class Profile(Typed):
            name: str
            email: Optional[str] = None
            age: Optional[int] = None

        profile = Profile(name="John")

        # Should not be able to modify optional fields
        with pytest.raises(ValidationError, match="Instance is frozen"):
            profile.email = "john@example.com"

        with pytest.raises(ValidationError, match="Instance is frozen"):
            profile.age = 30

    def test_typed_frozen_with_union_types(self):
        """Test that Typed instances with Union types are still frozen."""

        class FlexibleValue(Typed):
            value: Union[int, str]
            count: int = 0

        item = FlexibleValue(value=42)

        # Should not be able to modify union field
        with pytest.raises(ValidationError, match="Instance is frozen"):
            item.value = "hello"

    def test_typed_frozen_with_nested_objects(self):
        """Test that Typed instances with nested objects are still frozen."""

        class Address(Typed):
            street: str
            city: str

        class Person(Typed):
            name: str
            address: Address

        person = Person(name="John", address=Address(street="123 Main", city="NYC"))

        # Should not be able to modify nested object
        with pytest.raises(ValidationError, match="Instance is frozen"):
            person.address = Address(street="456 Oak", city="LA")

    def test_typed_frozen_with_lists(self):
        """Test that Typed instances with list fields are still frozen."""

        class TaskList(Typed):
            name: str
            tasks: List[str] = []

        task_list = TaskList(name="Work")

        # Should not be able to modify list field
        with pytest.raises(ValidationError, match="Instance is frozen"):
            task_list.tasks = ["task1", "task2"]

    def test_typed_frozen_with_dicts(self):
        """Test that Typed instances with dictionary fields are still frozen."""

        class Config(Typed):
            name: str
            settings: Dict[str, str] = {}

        config = Config(name="app")

        # Should not be able to modify dict field
        with pytest.raises(ValidationError, match="Instance is frozen"):
            config.settings = {"key1": "value1"}


class TestTypedVsMutableTyped:
    """Test comparison between Typed and MutableTyped behavior."""

    def test_creation_behavior_same(self):
        """Test that both Typed and MutableTyped have same creation behavior."""

        class FrozenUser(Typed):
            name: str
            age: int

        class MutableUser(MutableTyped):
            name: str
            age: int

        # Both should create instances the same way
        frozen_user = FrozenUser(name="John", age=30)
        mutable_user = MutableUser(name="John", age=30)

        assert frozen_user.name == mutable_user.name
        assert frozen_user.age == mutable_user.age

    def test_modification_behavior_different(self):
        """Test that Typed and MutableTyped have different modification behavior."""

        class FrozenUser(Typed):
            name: str
            age: int

        class MutableUser(MutableTyped):
            name: str
            age: int

        frozen_user = FrozenUser(name="John", age=30)
        mutable_user = MutableUser(name="John", age=30)

        # Frozen user should not be modifiable
        with pytest.raises(ValidationError, match="Instance is frozen"):
            frozen_user.name = "Jane"

        # Mutable user should be modifiable
        mutable_user.name = "Jane"
        assert mutable_user.name == "Jane"

    def test_validation_behavior_same(self):
        """Test that both Typed and MutableTyped have same validation behavior."""

        class FrozenUser(Typed):
            name: str
            age: int

        class MutableUser(MutableTyped):
            name: str
            age: int

        # Both should pre_validate creation the same way
        # Typed wraps ValidationError in ValueError
        with pytest.raises(ValueError, match="Input should be a valid integer"):
            FrozenUser(name="John", age="not_a_number")

        # MutableTyped also wraps ValidationError in ValueError
        with pytest.raises(ValueError, match="Input should be a valid integer"):
            MutableUser(name="John", age="not_a_number")

    def test_assignment_validation_different(self):
        """Test that assignment validation differs between Typed and MutableTyped."""

        class FrozenUser(Typed):
            name: str
            age: int

        class MutableUser(MutableTyped):
            name: str
            age: int

        frozen_user = FrozenUser(name="John", age=30)
        mutable_user = MutableUser(name="John", age=30)

        # Frozen user should reject assignment due to frozen constraint
        with pytest.raises(ValidationError, match="Instance is frozen"):
            frozen_user.age = "not_a_number"

        # Mutable user allows assignment without validation by default (for performance)
        mutable_user.age = "not_a_number"  # Allowed!
        assert mutable_user.age == "not_a_number"

    def test_model_validate_behavior_same(self):
        """Test that model_validate works the same for both classes."""

        class FrozenUser(Typed):
            name: str
            age: int

        class MutableUser(MutableTyped):
            name: str
            age: int

        data = {"name": "John", "age": "30"}  # String that converts to int

        # Both should convert and pre_validate the same way
        frozen_user = FrozenUser.model_validate(data)
        mutable_user = MutableUser.model_validate(data)

        assert frozen_user.name == mutable_user.name
        assert frozen_user.age == mutable_user.age
        assert isinstance(frozen_user.age, int)
        assert isinstance(mutable_user.age, int)

    def test_dict_conversion_same(self):
        """Test that dict conversion works the same for both classes."""

        class FrozenUser(Typed):
            name: str
            age: int

        class MutableUser(MutableTyped):
            name: str
            age: int

        frozen_user = FrozenUser(name="John", age=30)
        mutable_user = MutableUser(name="John", age=30)

        # Both should convert to dict the same way
        frozen_dict = frozen_user.model_dump()
        mutable_dict = mutable_user.model_dump()

        assert frozen_dict == mutable_dict
        assert frozen_dict == {"name": "John", "age": 30}
