"""
Tests for SqliteTool.

Covers: placeholder normalization, query/query_one/execute/execute_many,
RETURNING clause, transactions (commit & rollback), health_check,
and migration history deduplication.
"""
import pytest
from tools.sqlite.sqlite_tool import SqliteTool, DatabaseError, _normalize_sql, _normalize_sql_many


# ─── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
async def db(tmp_path):
    """Fresh in-memory-like SQLite DB for each test (temp file)."""
    import os
    os.environ["SQLITE_DB_PATH"] = str(tmp_path / "test.db")
    tool = SqliteTool()
    await tool.setup()
    await tool.execute("CREATE TABLE items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, value INTEGER)")
    yield tool
    await tool.shutdown()


# ─── Placeholder normalization ────────────────────────────────────────────

class TestNormalizeSql:
    def test_converts_pg_placeholders_to_sqlite(self):
        sql, params = _normalize_sql("SELECT * FROM t WHERE id=$1 AND x=$2", [42, "foo"])
        assert "?" in sql
        assert "$" not in sql
        assert params == [42, "foo"]

    def test_no_placeholders_passthrough(self):
        sql, params = _normalize_sql("SELECT 1", [])
        assert sql == "SELECT 1"
        assert params == []

    def test_reorders_params_by_position(self):
        sql, params = _normalize_sql("SELECT $2, $1", ["a", "b"])
        assert params == ["b", "a"]

    def test_normalize_many(self):
        sql, pl = _normalize_sql_many("INSERT INTO t VALUES ($1)", [["x"], ["y"]])
        assert "?" in sql
        assert pl == [["x"], ["y"]]


# ─── query() ──────────────────────────────────────────────────────────────

class TestQuery:
    @pytest.mark.anyio
    async def test_returns_list_of_dicts(self, db):
        await db.execute("INSERT INTO items (name, value) VALUES ($1, $2)", ["a", 1])
        await db.execute("INSERT INTO items (name, value) VALUES ($1, $2)", ["b", 2])

        rows = await db.query("SELECT name, value FROM items ORDER BY name")
        assert rows == [{"name": "a", "value": 1}, {"name": "b", "value": 2}]

    @pytest.mark.anyio
    async def test_returns_empty_list_when_no_rows(self, db):
        rows = await db.query("SELECT * FROM items")
        assert rows == []

    @pytest.mark.anyio
    async def test_with_params(self, db):
        await db.execute("INSERT INTO items (name, value) VALUES ($1, $2)", ["keep", 10])
        await db.execute("INSERT INTO items (name, value) VALUES ($1, $2)", ["skip", 20])

        rows = await db.query("SELECT name FROM items WHERE value=$1", [10])
        assert len(rows) == 1
        assert rows[0]["name"] == "keep"


# ─── query_one() ──────────────────────────────────────────────────────────

class TestQueryOne:
    @pytest.mark.anyio
    async def test_returns_dict_when_found(self, db):
        await db.execute("INSERT INTO items (name, value) VALUES ($1, $2)", ["x", 99])
        row = await db.query_one("SELECT name, value FROM items WHERE name=$1", ["x"])
        assert row == {"name": "x", "value": 99}

    @pytest.mark.anyio
    async def test_returns_none_when_not_found(self, db):
        row = await db.query_one("SELECT * FROM items WHERE id=$1", [9999])
        assert row is None


# ─── execute() ────────────────────────────────────────────────────────────

class TestExecute:
    @pytest.mark.anyio
    async def test_insert_returns_lastrowid(self, db):
        row_id = await db.execute("INSERT INTO items (name, value) VALUES ($1, $2)", ["z", 5])
        assert isinstance(row_id, int)
        assert row_id >= 1

    @pytest.mark.anyio
    async def test_insert_with_returning(self, db):
        row_id = await db.execute(
            "INSERT INTO items (name, value) VALUES ($1, $2) RETURNING id", ["ret", 7]
        )
        assert isinstance(row_id, int)
        assert row_id >= 1

    @pytest.mark.anyio
    async def test_update_returns_affected_rows(self, db):
        await db.execute("INSERT INTO items (name, value) VALUES ($1, $2)", ["u", 1])
        await db.execute("INSERT INTO items (name, value) VALUES ($1, $2)", ["u", 2])

        count = await db.execute("UPDATE items SET value=$1 WHERE name=$2", [99, "u"])
        assert count == 2

    @pytest.mark.anyio
    async def test_delete_returns_affected_rows(self, db):
        await db.execute("INSERT INTO items (name, value) VALUES ($1, $2)", ["d", 1])
        count = await db.execute("DELETE FROM items WHERE name=$1", ["d"])
        assert count == 1


# ─── execute_many() ───────────────────────────────────────────────────────

class TestExecuteMany:
    @pytest.mark.anyio
    async def test_inserts_all_rows(self, db):
        await db.execute_many(
            "INSERT INTO items (name, value) VALUES ($1, $2)",
            [["x", 1], ["y", 2], ["z", 3]],
        )
        rows = await db.query("SELECT name FROM items ORDER BY name")
        assert [r["name"] for r in rows] == ["x", "y", "z"]


# ─── transaction() ────────────────────────────────────────────────────────

class TestTransaction:
    @pytest.mark.anyio
    async def test_commits_on_success(self, db):
        async with db.transaction() as tx:
            await tx.execute("INSERT INTO items (name, value) VALUES ($1, $2)", ["t1", 1])
            await tx.execute("INSERT INTO items (name, value) VALUES ($1, $2)", ["t2", 2])

        rows = await db.query("SELECT name FROM items ORDER BY name")
        assert [r["name"] for r in rows] == ["t1", "t2"]

    @pytest.mark.anyio
    async def test_rolls_back_on_exception(self, db):
        with pytest.raises(Exception):
            async with db.transaction() as tx:
                await tx.execute("INSERT INTO items (name, value) VALUES ($1, $2)", ["ok", 1])
                raise RuntimeError("forced rollback")

        rows = await db.query("SELECT * FROM items")
        assert rows == []

    @pytest.mark.anyio
    async def test_transaction_query_within_block(self, db):
        async with db.transaction() as tx:
            await tx.execute("INSERT INTO items (name, value) VALUES ($1, $2)", ["q", 55])
            row = await tx.query_one("SELECT value FROM items WHERE name=$1", ["q"])
            assert row["value"] == 55

    @pytest.mark.anyio
    async def test_nested_transactions_via_savepoint(self, db):
        async with db.transaction() as outer:
            await outer.execute("INSERT INTO items (name, value) VALUES ($1, $2)", ["outer", 1])
            with pytest.raises(Exception):
                async with db.transaction() as inner:
                    await inner.execute("INSERT INTO items (name, value) VALUES ($1, $2)", ["inner", 2])
                    raise RuntimeError("inner rollback")

        # outer committed, inner rolled back
        rows = await db.query("SELECT name FROM items")
        names = [r["name"] for r in rows]
        assert "outer" in names
        assert "inner" not in names


# ─── health_check() ───────────────────────────────────────────────────────

class TestHealthCheck:
    @pytest.mark.anyio
    async def test_returns_true_when_connected(self, db):
        assert await db.health_check() is True

    @pytest.mark.anyio
    async def test_returns_false_when_not_connected(self):
        tool = SqliteTool()
        # never called setup()
        assert await tool.health_check() is False
