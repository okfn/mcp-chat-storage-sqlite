# mcp-chat-storage-sqlite

SQLite storage backend for the [mcp-chat-gateway](https://github.com/okfn/mcp-chat-gateway).
Persists chat conversations (conversations, messages, tool calls) so they can be analysed later.

This is an **optional** plugin. The gateway works without it (no history is
recorded). Installing this package into the gateway's environment turns
persistence on automatically — the gateway discovers it through the
`mcp_chat_storage` entry point group.

## Configure

| Env var | Default | Meaning |
|---------|---------|---------|
| `CHAT_STORAGE_SQLITE_PATH` | `chat_history.sqlite3` | DB file path |

No DB server needed.
