from app.internal.parsing import (
    parse_dict, parse_json_list, parse_json, stringify_basemodel
)

from pydantic import BaseModel

# JSON object for the tests below.
class testModel(BaseModel):
    name: str
    value: int

class TestRoundtrip:
    # This is technically an integration test :)
    def test_stringify_then_parse_json(self):
        original = testModel(name="test", value=42)
        json_str = stringify_basemodel(original)
        result = parse_json(json_str, testModel)
        assert result == original

    def test_parse_dict(self):
        result = parse_dict({"name": "test", "value": 42}, testModel)
        assert result == testModel(name="test", value=42)

    def test_parse_json_list(self):
        json_str = '[{"name": "a", "value": 1}, {"name": "b", "value": 2}]'
        result = parse_json_list(json_str, testModel)
        assert len(result) == 2
        assert result[0] == testModel(name="a", value=1)

    def test_stringify_with_indent(self):
        model = testModel(name="test", value=42)
        result = stringify_basemodel(model, indent=2)
        assert "\n" in result 