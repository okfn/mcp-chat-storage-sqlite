"""Tests for the SQLite chat-storage backend."""

import sqlite3

import pytest

from mcp_chat_storage_sqlite import SqliteChatStorage, _dumps


@pytest.fixture
def store(tmp_path):
    s = SqliteChatStorage(path=str(tmp_path / "chat.sqlite3"))
    s.connect()
    return s


def _rows(path, sql):
    conn = sqlite3.connect(path)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# _dumps helper
# ---------------------------------------------------------------------------


def test_dumps_encodes_dicts():
    assert _dumps({"a": 1}) == '{"a": 1}'


def test_dumps_passes_strings_through():
    assert _dumps("already a string") == "already a string"


def test_dumps_none_stays_none():
    assert _dumps(None) is None


def test_dumps_stringifies_non_json_serialisable():
    # default=str fallback — must not raise.
    class Weird:
        def __str__(self):
            return "weird"

    assert "weird" in _dumps({"x": Weird()})


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def test_connect_creates_tables(store):
    names = {
        r[0]
        for r in _rows(store.path, "SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"conversations", "messages", "tool_calls"} <= names


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


def test_ensure_conversation_inserts(store):
    store.ensure_conversation("conv-1", {"model": "deepseek-chat"})
    rows = _rows(store.path, "SELECT id, metadata FROM conversations")
    assert rows == [("conv-1", '{"model": "deepseek-chat"}')]


def test_ensure_conversation_is_idempotent(store):
    store.ensure_conversation("conv-1", {"model": "first"})
    store.ensure_conversation("conv-1", {"model": "second"})  # must not overwrite
    rows = _rows(store.path, "SELECT id, metadata FROM conversations")
    assert rows == [("conv-1", '{"model": "first"}')]


def test_ensure_conversation_allows_null_metadata(store):
    store.ensure_conversation("conv-2", None)
    rows = _rows(store.path, "SELECT id, metadata FROM conversations WHERE id='conv-2'")
    assert rows == [("conv-2", None)]


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


def test_save_message_inserts(store):
    store.save_message("conv-1", 0, "user", "hola", "2026-06-19T14:00:00")
    rows = _rows(
        store.path,
        "SELECT turn_index, role, content, created_at FROM messages",
    )
    assert rows == [(0, "user", "hola", "2026-06-19T14:00:00")]


def test_save_message_upserts_same_turn(store):
    store.save_message("conv-1", 1, "assistant", "draft", "2026-06-19T14:00:05")
    store.save_message("conv-1", 1, "assistant", "final", "2026-06-19T14:00:06")
    rows = _rows(
        store.path,
        "SELECT content, created_at FROM messages WHERE conversation_id='conv-1' AND turn_index=1",
    )
    assert rows == [("final", "2026-06-19T14:00:06")]


# ---------------------------------------------------------------------------
# Tool calls
# ---------------------------------------------------------------------------


def test_save_tool_call_inserts_with_json(store):
    store.save_tool_call(
        "conv-1", 1, 0, "matriz", {"anio": 2024}, {"rows": 10}, "2026-06-19T14:00:03"
    )
    rows = _rows(
        store.path,
        "SELECT turn_index, seq, tool_name, arguments, result FROM tool_calls",
    )
    assert rows == [(1, 0, "matriz", '{"anio": 2024}', '{"rows": 10}')]


def test_save_tool_call_upserts_same_seq(store):
    store.save_tool_call("conv-1", 1, 0, "t", {"v": 1}, {"r": 1}, "2026-06-19T14:00:03")
    store.save_tool_call("conv-1", 1, 0, "t", {"v": 2}, {"r": 2}, "2026-06-19T14:00:04")
    rows = _rows(
        store.path,
        "SELECT arguments, result FROM tool_calls WHERE conversation_id='conv-1' AND turn_index=1 AND seq=0",
    )
    assert rows == [('{"v": 2}', '{"r": 2}')]


def test_multiple_tool_calls_same_turn_distinct_seq(store):
    store.save_tool_call("conv-1", 1, 0, "a", {}, {}, "t")
    store.save_tool_call("conv-1", 1, 1, "b", {}, {}, "t")
    rows = _rows(
        store.path,
        "SELECT seq, tool_name FROM tool_calls WHERE conversation_id='conv-1' ORDER BY seq",
    )
    assert rows == [(0, "a"), (1, "b")]


def test_save_tool_call_accepts_string_result(store):
    # The gateway may pass an error string instead of a dict.
    store.save_tool_call("conv-1", 1, 0, "t", {}, "Error calling tool: boom", "t")
    rows = _rows(store.path, "SELECT result FROM tool_calls")
    assert rows == [("Error calling tool: boom",)]
