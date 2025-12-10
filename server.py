# server.py
import asyncio
import json
from mcp.server import Server
from mcp.types import Tool, TextContent
from ir_client import IndependentReserveWebSocketClient

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

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handles a tool call from the AI."""
    if name == "get_ticker":
        primary = arguments.get("primary_currency")
        secondary = arguments.get("secondary_currency")
        
        # Ensure we are subscribed to the data
        asyncio.create_task(ir_client.subscribe_ticker(primary, secondary))
        
        # Get the latest data from the cache
        data = ir_client.get_latest_ticker(primary, secondary)
        
        if not data:
            return [TextContent(type="text", text=f"Ticker data for {primary}/{secondary} is not available yet. Please try again in a moment.")]
            
        # Format the data for the AI
        formatted_data = (
            f"Ticker for {data['PrimaryCurrencyCode']}/{data['SecondaryCurrencyCode']}:\n"
            f"  - Last Price: {data.get('LastPrice', 'N/A')}\n"
            f"  - Best Bid: {data.get('BestBid', 'N/A')}\n"
            f"  - Best Ask: {data.get('BestAsk', 'N/A')}\n"
            f"  - 24h Volume: {data.get('Volume24Hour', 'N/A')}"
        )
        return [TextContent(type="text", text=formatted_data)]

    elif name == "get_order_book":
        primary = arguments.get("primary_currency")
        secondary = arguments.get("secondary_currency")

        # Ensure we are subscribed to the data
        asyncio.create_task(ir_client.subscribe_order_book(primary, secondary))

        data = ir_client.get_latest_order_book(primary, secondary)

        if not data:
            return [TextContent(type="text", text=f"Order book data for {primary}/{secondary} is not available yet. Please try again in a moment.")]
        
        # Format the top of the order book
        buys = data.get('BuyOrders', [])[:5]
        sells = data.get('SellOrders', [])[:5]

        formatted_buys = "\n".join([f"  - {order['Price']} ({order['Volume']})" for order in buys])
        formatted_sells = "\n".join([f"  - {order['Price']} ({order['Volume']})" for order in sells])
        
        formatted_data = (
            f"Order Book for {data['PrimaryCurrencyCode']}/{data['SecondaryCurrencyCode']}:\n"
            f"--- Top 5 Bids (Buy Orders) ---\n{formatted_buys}\n\n"
            f"--- Top 5 Asks (Sell Orders) ---\n{formatted_sells}"
        )
        return [TextContent(type="text", text=formatted_data)]

    return [TextContent(type="text", text="Unknown tool.")]


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
