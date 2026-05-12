# AGENTS.md - Agentic Coding Guidelines

This file provides guidelines for AI agents working in this repository.

## Project Overview

- **Name**: at-mysql - Python MCP Server (Model Context Protocol)
- **Purpose**: MySQL query, Excel export, and data analysis tools via MCP protocol
- **Entry**: `src/server.py` | **Runtime**: Python 3.x with FastMCP

## Build/Lint/Test Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run MCP server (stdio mode)
python -m src.server

# Run tests
pytest tests/                    # All tests
pytest tests/test_file.py::test_name  # Single test
pytest -v                        # Verbose

# Lint with ruff (project standard)
ruff check src/
ruff check src/ --fix           # Auto-fix
ruff format src/                # Format

# Full quality check
ruff check src/ && ruff format --check src/
```

## Code Style Guidelines

### General Principles

- Type hints for all function signatures
- Docstrings on all public functions (Chinese or English)
- Keep functions focused and single-purpose
- **Max line length**: 88 characters (ruff default)

### Imports (3 sections, blank line between)

1. Standard library (`json`, `logging`, `datetime`)
2. Third-party packages (`pandas`, `mysql.connector`)
3. Local application imports (relative: `from ..core import db_manager`)

```python
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

import pandas as pd
from mysql.connector import pooling, Error

from ..core.db_connection import db_manager
```

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Modules | snake_case | `sql_tools.py` |
| Classes | PascalCase | `DBConnectionPool` |
| Functions/vars | snake_case | `execute_sql()` |
| Constants | UPPER_SNAKE | `MAX_ROWS_LIMIT` |
| Private members | _prefix | `_initialized` |

### Type Hints & Docstrings

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class ServerConfig:
    id: str
    host: str
    port: int
    user: str
    password: str
    database: str
    charset: str = "utf8mb4"

def execute_sql(
    query: str,
    server_id: Optional[str] = None,
    max_rows: int = 1000,
) -> str:
    """
    Execute SQL query and return JSON results.

    Args:
        query: SQL query statement
        server_id: Server ID (optional)
        max_rows: Maximum rows to return

    Returns:
        JSON formatted query results
    """
```

### Error Handling

- **Never** use bare `except:`
- Catch specific exceptions (`Error`, `ValueError`)
- Log with `logging.getLogger(__name__)`
- Return JSON error responses for MCP tools

```python
try:
    result = db_manager.execute_query(query, server_id)
    return json.dumps({"status": "success", "data": result})
except Error as e:
    logger.error(f"Database error: {e}")
    return json.dumps({"status": "error", "message": str(e)})
```

## Project Structure

```
at-mysql/
├── src/
│   ├── server.py          # MCP server main entry
│   ├── core/              # Core functionality
│   │   ├── config_loader.py    # JSON config loading
│   │   ├── db_connection.py    # Connection pool + query execution
│   │   └── path_manager.py     # Path utilities
│   └── tools/             # MCP tools
│       ├── sql_tools.py   # SQL execution tools
│       └── data_tools.py  # Data analysis tools
├── config/
│   ├── .env
│   ├── databases.example.json
│   └── databases.json     # Sensitive - do not commit
├── requirements.txt
└── MCPconfig.json
```

## Configuration

- **DB configs**: `config/databases.json` (git-ignored, see `databases.example.json`)
- **Server IDs**: `YIFEI`, `YUNYAN_OB`
- **Env var**: `DEFAULT_SERVER` in `config/.env`

## MCP Tools

| Tool | Purpose |
|------|---------|
| `MySQL_Yifei` | Query YIFEI server |
| `MySQL_OB` | Query YUNYAN_OB server |
| `list_tables` | List all tables |
| `get_table_schema` | Get table column info |
| `read_table` | Read table with pagination |
| `get_current_datetime` | Get current date/time |
| `analyze_cached_data` | Analyze cached query results |

## Security Guidelines

1. **Never commit secrets**: `config/databases.json` is git-ignored
2. **Use parameterized queries**: Prevent SQL injection
3. **Handle errors gracefully**: Don't expose internal details
4. **Mask sensitive data**: Use `mask_sensitive_data()` for exports
