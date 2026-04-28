# AGENTS.md - Agentic Coding Guidelines

This file provides guidelines for AI agents working in this repository.

## Project Overview

- **Project Name**: at-mysql
- **Type**: Python MCP Server (Model Context Protocol)
- **Purpose**: Provides MySQL query and Excel export tools via MCP protocol
- **Main Entry**: `src/server.py`
- **Runtime**: Python 3.x with FastMCP

## Build/Lint/Test Commands

### Running the MCP Server

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server (stdio mode for MCP)
python -m src.server

# Or via FastMCP CLI
fastmcp run src.server: mcp
```

### Running Tests

Currently **no test suite exists**. If adding tests:

```bash
# Using pytest (recommended)
pytest tests/                    # Run all tests
pytest tests/test_file.py::test_name  # Run single test
pytest -v                        # Verbose output

# Using unittest
python -m unittest discover -s tests
```

### Linting

```bash
# Python linting with ruff (recommended)
ruff check src/

# With auto-fix
ruff check src/ --fix

# Type checking with mypy
mypy src/

# Format code with black
black src/
```

### Code Quality Commands

```bash
# Full check
ruff check src/ && mypy src/

# Format check
black --check src/
```

## Code Style Guidelines

### General Principles

- Write clean, readable code with clear intent
- Use type hints for all function signatures
- Add docstrings to all public functions (Chinese or English)
- Keep functions focused and single-purpose
- Maximum line length: 100 characters

### Imports

**Order** (each section separated by blank line):
1. Standard library
2. Third-party packages
3. Local application imports

**Relative vs Absolute**:
- Use relative imports within the package: `from ..core import db_manager`
- Use absolute imports for external packages: `import pandas as pd`

**Example**:
```python
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

import pandas as pd
from mysql.connector import pooling, Error

from ..core.db_connection import db_manager
from ..core.config_loader import get_config
```

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Modules | snake_case | `sql_tools.py` |
| Classes | PascalCase | `DBConnectionPool` |
| Functions | snake_case | `execute_sql()` |
| Variables | snake_case | `max_rows` |
| Constants | UPPER_SNAKE | `MAX_ROWS_LIMIT` |
| Private members | prefix with `_` | `_internal_method()` |

### Type Hints

**Always use type hints for function signatures**:
```python
# Good
def execute_sql(query: str, server_id: Optional[str] = None, max_rows: int = 1000) -> str:
    ...

# Avoid
def execute_sql(query, server_id=None, max_rows=1000):
    ...
```

**Common type imports**:
```python
from typing import Optional, List, Dict, Any, Union, Tuple
```

### Docstrings

Use Google-style or simple docstrings:
```python
def execute_sql(query: str, server_id: Optional[str] = None) -> str:
    """
    执行SQL查询并返回JSON结果

    Args:
        query: SQL查询语句
        server_id: 服务器ID（可选）

    Returns:
        JSON格式的查询结果
    """
```

### Error Handling

**Always use try/except for external operations**:
```python
try:
    results = db_manager.execute_query(query, server_id)
    return json.dumps({"status": "success", "data": results})
except Error as e:
    logger.error(f"查询失败: {e}")
    return json.dumps({"status": "error", "message": str(e)})
```

**Rules**:
- Never let exceptions propagate silently
- Log errors before returning
- Return error status in JSON, don't raise
- Use specific exception types when possible

### JSON Responses

**Always use `ensure_ascii=False`** for Chinese support:
```python
return json.dumps({
    "status": "success",
    "message": "操作成功",
    "data": results
}, ensure_ascii=False, indent=2)
```

### Logging

**Use module-level loggers**:
```python
logger = logging.getLogger(__name__)

# Or with prefix
logger = logging.getLogger("mcp_agent.tools.sql")
```

**Log levels**:
- `logger.debug()` - Detailed diagnostic info
- `logger.info()` - General operational events
- `logger.warning()` - Unexpected but handled issues
- `logger.error()` - Serious problems

### Database Operations

- Use connection pooling (`DBConnectionPool`)
- Always use context managers for connections
- Limit query results with `max_rows` parameter
- Close connections in finally blocks

### Pandas Usage

- Use vectorized operations over loops
- Handle empty DataFrame cases
- Return meaningful error messages
- Use `to_dict('records')` for JSON conversion

### File Operations

- Use context managers (`with open(...) as f:`)
- Handle encoding explicitly (UTF-8)
- Close files even on errors

### Async/Await

- Use `async def` for MCP tool functions
- Keep async operations non-blocking
- Use `asyncio` for concurrent operations when needed

## Project Structure

```
at-mysql/
├── src/
│   ├── server.py          # Main MCP server entry
│   ├── core/
│   │   ├── db_connection.py   # Database connection pool
│   │   ├── config_loader.py   # Configuration management
│   │   └── path_manager.py    # Path utilities
│   └── tools/
│       ├── sql_tools.py       # SQL execution tools
│       ├── data_tools.py      # Data processing tools
│       ├── excel_writer.py    # Excel export tools
│       └── ...
├── config/
│   └── databases.json     # Database configurations
└── requirements.txt       # Python dependencies
```

## Configuration

Database configurations are stored in `config/databases.json`:
- Never commit actual credentials
- Use `databases.example.json` as template
- Environment variables take precedence

## Common Patterns

### MCP Tool Definition
```python
@mcp.tool()
async def tool_name(param: str) -> str:
    """Tool description"""
    try:
        # Implementation
        return json.dumps({"status": "success", ...})
    except Exception as e:
        logger.error(...)
        return json.dumps({"status": "error", ...})
```

### Database Query
```python
from ..core.db_connection import db_manager

results = db_manager.execute_query(query, server_id, max_rows=1000)
```

### Returning JSON
```python
import json

return json.dumps({
    "key": "value"
}, ensure_ascii=False, indent=2)
```

## Important Notes

1. **No existing tests** - Add tests when modifying code
2. **MCP protocol** - All tools must use `@mcp.tool()` decorator
3. **String returns** - MCP tools return JSON strings, not Python objects
4. **Chinese support** - Always use `ensure_ascii=False` for JSON
5. **Connection pooling** - Don't create new connections; use pool