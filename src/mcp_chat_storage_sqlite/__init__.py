"""
SQLite storage backend for the mcp-chat-gateway.
https://github.com/okfn/mcp-chat-gateway

The gateway discovers this package through the ``mcp_chat_storage`` entry point

Database location is taken from the ``CHAT_STORAGE_SQLITE_PATH`` environment
variable, defaulting to ``chat_history.sqlite3`` in the working directory.
"""

import json
import os
import sqlite3
import threading

DEFAULT_PATH = "chat_history.sqlite3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id          TEXT PRIMARY KEY,
    created_at  TEXT,
    metadata    TEXT
);
CREATE TABLE IF NOT EXISTS messages (
    conversation_id TEXT,
    turn_index      INTEGER,
    role            TEXT,
    content         TEXT,
    created_at      TEXT,
    PRIMARY KEY (conversation_id, turn_index)
);
CREATE TABLE IF NOT EXISTS tool_calls (
    conversation_id TEXT,
    turn_index      INTEGER,
    seq             INTEGER,
    tool_name       TEXT,
    arguments       TEXT,
    result          TEXT,
    created_at      TEXT,
    PRIMARY KEY (conversation_id, turn_index, seq)
);
CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages (conversation_id);
CREATE INDEX IF NOT EXISTS idx_tool_calls_conv ON tool_calls (conversation_id);
"""


def _dumps(value):
    """JSON-encode dicts/lists; pass strings through; stringify the rest."""
    if value is None or isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, default=str)


class SqliteChatStorage:
    name = "sqlite"
    enabled = True

    def __init__(self, path=None):
        self.path = path or os.getenv("CHAT_STORAGE_SQLITE_PATH", DEFAULT_PATH)
        self._lock = threading.Lock()
        self._conn = None

    def connect(self):
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def ensure_conversation(self, conversation_id, metadata=None):
        with self._lock:
            self._conn.execute(
                "INSERT INTO conversations (id, created_at, metadata) "
                "VALUES (?, datetime('now'), ?) "
                "ON CONFLICT(id) DO NOTHING",
                (conversation_id, _dumps(metadata)),
            )
            self._conn.commit()

    def save_message(self, conversation_id, turn_index, role, content, created_at):
        with self._lock:
            self._conn.execute(
                "INSERT INTO messages "
                "(conversation_id, turn_index, role, content, created_at) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(conversation_id, turn_index) DO UPDATE SET "
                "role=excluded.role, content=excluded.content, "
                "created_at=excluded.created_at",
                (conversation_id, turn_index, role, content, created_at),
            )
            self._conn.commit()

    def save_tool_call(self, conversation_id, turn_index, seq, tool_name,
                       arguments, result, created_at):
        with self._lock:
            self._conn.execute(
                "INSERT INTO tool_calls "
                "(conversation_id, turn_index, seq, tool_name, arguments, "
                " result, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(conversation_id, turn_index, seq) DO UPDATE SET "
                "tool_name=excluded.tool_name, arguments=excluded.arguments, "
                "result=excluded.result, created_at=excluded.created_at",
                (conversation_id, turn_index, seq, tool_name,
                 _dumps(arguments), _dumps(result), created_at),
            )
            self._conn.commit()
