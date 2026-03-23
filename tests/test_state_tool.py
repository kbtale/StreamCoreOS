"""
Tests for StateTool — in-memory key/value store with namespaces.

Covers: get/set, namespaces, default values, increment, delete, thread safety.
"""
import threading
import pytest
from tools.state.state_tool import StateTool


@pytest.fixture
def state():
    return StateTool()


class TestSetGet:
    def test_set_and_get(self, state):
        state.set("key", "value")
        assert state.get("key") == "value"

    def test_get_missing_returns_default(self, state):
        assert state.get("missing") is None
        assert state.get("missing", default=42) == 42

    def test_overwrite_value(self, state):
        state.set("k", 1)
        state.set("k", 2)
        assert state.get("k") == 2

    def test_stores_any_type(self, state):
        state.set("list", [1, 2, 3])
        state.set("dict", {"a": 1})
        assert state.get("list") == [1, 2, 3]
        assert state.get("dict") == {"a": 1}


class TestNamespaces:
    def test_same_key_in_different_namespaces_are_isolated(self, state):
        state.set("key", "ns1_value", namespace="ns1")
        state.set("key", "ns2_value", namespace="ns2")

        assert state.get("key", namespace="ns1") == "ns1_value"
        assert state.get("key", namespace="ns2") == "ns2_value"

    def test_default_namespace_does_not_bleed(self, state):
        state.set("key", "default")
        assert state.get("key", namespace="other") is None

    def test_namespace_created_on_demand(self, state):
        # Should not raise
        state.set("k", "v", namespace="brand_new")
        assert state.get("k", namespace="brand_new") == "v"


class TestIncrement:
    def test_increment_from_zero(self, state):
        result = state.increment("counter")
        assert result == 1

    def test_increment_existing_value(self, state):
        state.set("n", 10)
        result = state.increment("n", amount=5)
        assert result == 15

    def test_increment_by_custom_amount(self, state):
        result = state.increment("n", amount=3)
        assert result == 3

    def test_increment_non_numeric_raises(self, state):
        state.set("k", "text")
        with pytest.raises(ValueError):
            state.increment("k")

    def test_increment_respects_namespace(self, state):
        state.increment("c", namespace="a")
        state.increment("c", namespace="a")
        state.increment("c", namespace="b")

        assert state.get("c", namespace="a") == 2
        assert state.get("c", namespace="b") == 1


class TestDelete:
    def test_delete_removes_key(self, state):
        state.set("k", "v")
        state.delete("k")
        assert state.get("k") is None

    def test_delete_nonexistent_key_is_safe(self, state):
        # Should not raise
        state.delete("ghost")

    def test_delete_only_affects_target_key(self, state):
        state.set("a", 1)
        state.set("b", 2)
        state.delete("a")
        assert state.get("b") == 2


class TestThreadSafety:
    def test_concurrent_increments_are_consistent(self, state):
        errors = []

        def worker():
            try:
                for _ in range(100):
                    state.increment("shared_counter")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert errors == []
        assert state.get("shared_counter") == 1000

    def test_concurrent_set_get_no_race(self, state):
        errors = []

        def writer():
            for i in range(50):
                state.set("shared", i)

        def reader():
            for _ in range(50):
                try:
                    state.get("shared")
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=writer)] + [threading.Thread(target=reader) for _ in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert errors == []
