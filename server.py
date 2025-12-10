# server.py
import asyncio
import logging
from mcp.server import Server
from mcp.types import Tool, TextContent
from ir_client import IndependentReserveWebSocketClient

# Configure structured logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Initialize the MCP server and our WebSocket client
server = Server("independentreserve-mcp")
ir_client = IndependentReserveWebSocketClient()

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """Returns the list of available tools to the AI."""
    return [
        Tool(
            name="get_ticker",
            description="Gets the latest ticker information for a cryptocurrency pair, including last price, bid, ask, and volume.",
            inputSchema={
                "type": "object",
                "properties": {
                    "primary_currency": {"type": "string", "description": "The primary currency code, e.g., 'Xbt' or 'Eth'"},
                    "secondary_currency": {"type": "string", "description": "The secondary currency code, e.g., 'Usd' or 'Aud'"}
                },
                "required": ["primary_currency", "secondary_currency"]
            }
        ),
        Tool(
            name="get_recent_trades",
            description="Gets the most recent trades for a cryptocurrency pair.",
            inputSchema={
                "type": "object",
                "properties": {
                    "primary_currency": {"type": "string", "description": "The primary currency code, e.g., 'Xbt' or 'Eth'"},
                    "secondary_currency": {"type": "string", "description": "The secondary currency code, e.g., 'Usd' or 'Aud'"}
                },
                "required": ["primary_currency", "secondary_currency"]
            }
        ),
        Tool(
            name="get_order_book",
            description="Gets the latest order book (top 50 bids and asks) for a cryptocurrency pair.",
            inputSchema={
                "type": "object",
                "properties": {
                    "primary_currency": {"type": "string", "description": "The primary currency code, e.g., 'Xbt' or 'Eth'"},
                    "secondary_currency": {"type": "string", "description": "The secondary currency code, e.g., 'Usd' or 'Aud'"}
                },
                "required": ["primary_currency", "secondary_currency"]
            }
        )
    ]

async def _call_tool(tool_name: str, primary_currency: str, secondary_currency: str) -> list[TextContent]:
    """A helper function to reduce code duplication for calling tools."""

    subscription_methods = {
        "get_ticker": ir_client.subscribe_ticker,
        "get_order_book": ir_client.subscribe_order_book,
        "get_recent_trades": ir_client.subscribe_recent_trades,
    }

    data_methods = {
        "get_ticker": ir_client.get_latest_ticker,
        "get_order_book": ir_client.get_latest_order_book,
        "get_recent_trades": ir_client.get_latest_recent_trades,
    }

    formatting_methods = {
        "get_ticker": _format_ticker_data,
        "get_order_book": _format_order_book_data,
        "get_recent_trades": _format_recent_trades_data,
    }

    if tool_name not in subscription_methods:
        logging.error(f"Unknown tool: {tool_name}")
        return [TextContent(type="text", text="Unknown tool.")]

    try:
        # Subscribe to the data stream
        asyncio.create_task(subscription_methods[tool_name](primary_currency, secondary_currency))
        
        # Get the latest data from the cache
        data = data_methods[tool_name](primary_currency, secondary_currency)
        
        if not data:
            return [TextContent(type="text", text=f"Data for {primary_currency}/{secondary_currency} is not available yet. Please try again in a moment.")]

        # Format and return the data
        return [TextContent(type="text", text=formatting_methods[tool_name](data))]

    except KeyError as e:
        logging.error(f"Invalid currency pair: {primary_currency}/{secondary_currency} - {e}")
        return [TextContent(type="text", text=f"Invalid currency pair: {primary_currency}/{secondary_currency}")]
    except Exception as e:
        logging.error(f"An error occurred while calling {tool_name}: {e}")
        return [TextContent(type="text", text=f"An unexpected error occurred.")]

def _format_ticker_data(data: dict) -> str:
    """Formats ticker data into a human-readable string."""
    return (
        f"Ticker for {data['PrimaryCurrencyCode']}/{data['SecondaryCurrencyCode']}:\n"
        f"  - Last Price: {data.get('LastPrice', 'N/A')}\n"
        f"  - Best Bid: {data.get('BestBid', 'N/A')}\n"
        f"  - Best Ask: {data.get('BestAsk', 'N/A')}\n"
        f"  - 24h Volume: {data.get('Volume24Hour', 'N/A')}"
    )

def _format_order_book_data(data: dict) -> str:
    """Formats order book data into a human-readable string."""
    buys = data.get('BuyOrders', [])[:5]
    sells = data.get('SellOrders', [])[:5]

    formatted_buys = "\n".join([f"  - {order['Price']} ({order['Volume']})" for order in buys])
    formatted_sells = "\n".join([f"  - {order['Price']} ({order['Volume']})" for order in sells])

    return (
        f"Order Book for {data['PrimaryCurrencyCode']}/{data['SecondaryCurrencyCode']}:\n"
        f"--- Top 5 Bids (Buy Orders) ---\n{formatted_buys}\n\n"
        f"--- Top 5 Asks (Sell Orders) ---\n{formatted_sells}"
    )

def _format_recent_trades_data(data: dict) -> str:
    """Formats recent trades data into a human-readable string."""
    trades = data.get('Trades', [])[:5]
    formatted_trades = "\n".join([f"  - Price: {trade['Price']}, Volume: {trade['Volume']}" for trade in trades])
    return f"Recent Trades for {data['PrimaryCurrencyCode']}/{data['SecondaryCurrencyCode']}:\n{formatted_trades}"

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handles a tool call from the AI."""
    primary_currency = arguments.get("primary_currency")
    secondary_currency = arguments.get("secondary_currency")

    if not primary_currency or not secondary_currency:
        return [TextContent(type="text", text="Missing primary or secondary currency.")]

    return await _call_tool(name, primary_currency, secondary_currency)


async def main():
    # Start the WebSocket client in the background
    client_task = asyncio.create_task(ir_client.connect())
    
    # Run the MCP server
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )
    
    # Clean up
    ir_client.stop()
    await client_task

if __name__ == "__main__":
    asyncio.run(main())
