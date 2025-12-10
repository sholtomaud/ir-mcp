# AGENTS.md

This document provides guidance for AI agents working on the Independent Reserve MCP Server codebase.

## Project Structure

- `server.py`: The main MCP server. It handles tool definitions (`handle_list_tools`) and tool calls (`handle_call_tool`) from the AI. When adding a new tool, you must update both of these functions.
- `ir_client.py`: The WebSocket client responsible for connecting to the Independent Reserve API, managing subscriptions, and caching data. All interactions with the WebSocket API should be handled in this file.
- `requirements.txt`: Python dependencies. Use `pip install -r requirements.txt` to install them.
- `.env`: API keys and secrets are stored in a `.env` file. A template is provided in `.env.example`.

## Authentication

The client uses HMAC-SHA256 to authenticate with the Independent Reserve WebSocket API for private channels. The signature is generated using the API key, a nonce, and the channel name.

- The authentication logic is implemented in the `_subscribe` method in `ir_client.py`.
- The API key and secret must be set in the `.env` file for private channels to work.

## Caching

The `ir_client.py` uses a caching mechanism to avoid redundant subscriptions.

- A subscription is cached for 5 minutes (`CACHE_TIMEOUT`).
- A background task (`_manage_subscriptions`) runs periodically to unsubscribe from expired channels.
- When adding new subscription-based tools, ensure they use the `_subscribe` method to take advantage of the caching logic.

## Adding New Tools

To add a new tool:

1.  **Add the tool definition** to the list in the `handle_list_tools` function in `server.py`.
2.  **Implement the tool's logic** in `server.py` by adding a new `elif` block in the `handle_call_tool` function.
3.  **Add a corresponding method** in `ir_client.py` to handle the data subscription and retrieval from the WebSocket API.

## Testing

The `tests/` directory contains tests for the server and client.

- `test_server.py`: Tests for the MCP server logic.
- `test_ir_client.py`: Tests for the WebSocket client.

When adding new features, please add corresponding tests to ensure they work correctly and do not introduce regressions.
