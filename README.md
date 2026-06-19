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

## Develop / run tests

This package is built with [uv](https://docs.astral.sh/uv/) (`uv_build` backend).
The `dev` dependency group (pytest) is installed automatically by `uv run`.

```bash
uv sync          # create the venv and install deps (incl. the dev group)
uv run pytest    # run the test suite
uv run pytest -q tests/test_sqlite_storage.py   # a single file
```

No database server or network is required — the tests use a temporary on-disk
SQLite file. The same commands run in CI (see `.github/workflows/tests.yml`).
