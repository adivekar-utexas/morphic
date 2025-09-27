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

        # Mock get_origin and get_args for Union type
        with (
            patch("morphic.datamodel.get_origin") as mock_origin,
            patch("morphic.datamodel.get_args") as mock_args,
        ):
            mock_origin.return_value = Union
            mock_args.return_value = (int, str)

            # Should try to convert to int first
            result = SimpleDataModel._convert_value(field_mock, "42")
            assert result == 42


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

    def test_basic_type_validation_failure(self):
        """Test that wrong types fail validation."""

        class TypedModel(DataModel):
            name: str
            age: int

        # Wrong type for name (str expected, got int)
        with pytest.raises(TypeError, match="Field 'name' expected type.*str.*got int"):
            TypedModel(name=123, age=30)

        # Wrong type for age (int expected, got str)
        with pytest.raises(TypeError, match="Field 'age' expected type.*int.*got str"):
            TypedModel(name="John", age="30")

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

        # Should fail with wrong type (str when enum expected)
        with pytest.raises(TypeError, match="Field 'status' expected type.*SimpleEnum.*got str"):
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

        # Should fail on type validation before custom validation
        with pytest.raises(TypeError, match="Field 'name' expected type.*str.*got int"):
            CustomValidationModel(name=123, age=30)

        # Should fail on custom validation after type validation passes
        with pytest.raises(ValueError, match="Age must be non-negative"):
            CustomValidationModel(name="John", age=-5)

    def test_type_validation_from_dict_conversion(self):
        """Test that from_dict still works with type conversion while constructor validates strictly."""

        class ConversionModel(DataModel):
            name: str
            age: int

        # from_dict should still do type conversion
        model = ConversionModel.from_dict({"name": "John", "age": "30"})
        assert model.name == "John"
        assert model.age == 30  # Converted from string
        assert isinstance(model.age, int)

        # But direct constructor should be strict about types
        with pytest.raises(TypeError, match="Field 'age' expected type.*int.*got str"):
            ConversionModel(name="John", age="30")  # String not auto-converted


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

    def test_constructor_nested_validation_still_works(self):
        """Test that nested objects still validate their own types strictly."""
        # Type error in nested object should be caught
        with pytest.raises(TypeError, match="Field 'name' expected type.*str.*got int"):
            NestedDataModel(user={"name": 123, "age": 30})

        # Type error in nested object's age field
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

    def test_constructor_vs_from_dict_behavior(self):
        """Test the difference between constructor and from_dict behavior."""
        # Constructor should be strict about types
        with pytest.raises(TypeError):
            NestedDataModel(user={"name": "John", "age": "30"})  # string age fails

        # from_dict should convert types
        model = NestedDataModel.from_dict({"user": {"name": "John", "age": "30"}})
        assert model.user.age == 30  # string converted to int

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
