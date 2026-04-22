import pytest
from pydantic import BaseModel
from app.internal.notifications import (
    is_recursive_call, params_as_json
)

class TestIsRecursiveCall():
    def test_is_recursive_when_called_recursively(self):
        def recursive_fn():
            if is_recursive_call(): #Calls itself 2 times to simulate a stack
                return True
            return recursive_fn()
        
        assert recursive_fn() is True

    def test_is_not_recursive_in_normal_call(self):
        def normal_fn():
            return is_recursive_call()
        
        assert normal_fn() is False

# JSON object for params_as_json tests
class testModel(BaseModel):
    name: str

class TestParamsAsJson:
    def test_with_model(self):
        model = testModel(name="test")
        assert params_as_json(model) == '{"name":"test"}'

    def test_with_none_returns_empty_object(self):
        assert params_as_json(None) == "{}"
