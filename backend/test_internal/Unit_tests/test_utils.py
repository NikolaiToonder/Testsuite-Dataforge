import os
from app.internal.utils import (
    compute_signature, compute_spec_signature, debug_enabled
)


class TestComputeSignature:
    def test_consistent_hash(self):
        text = "test_string"
        hash1 = compute_signature(text)
        hash2 = compute_signature(text)
        assert hash1 == hash2

    def test_different_inputs_produce_different_hashes(self):
        hash1 = compute_signature("input1")
        hash2 = compute_signature("input2")
        assert hash1 != hash2


class TestComputeSpecSignature:
    def test_consistent_hash_for_dict(self):
        obj = {"key": "value", "num": 42}
        hash1 = compute_spec_signature(obj)
        hash2 = compute_spec_signature(obj)
        assert hash1 == hash2

    def test_key_order_does_not_affect_hash(self):
        obj1 = {"a": 1, "b": 2}
        obj2 = {"b": 2, "a": 1}
        assert compute_spec_signature(obj1) == compute_spec_signature(obj2)


class TestDebugEnabled:
    def test_returns_false_when_env_not_set(self, monkeypatch):
        monkeypatch.delenv("ENABLE_DEBUG_PRINTS", raising=False)
        assert debug_enabled() is False

    def test_returns_true_when_env_is_1(self, monkeypatch):
        monkeypatch.setenv("ENABLE_DEBUG_PRINTS", "1")
        assert debug_enabled() is True
