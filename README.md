# Independent Reserve MCP Server
This Model Context Protocol (MCP) server provides real-time cryptocurrency data from the Independent Reserve exchange to AI assistants like Claude.

It allows you to ask questions like:

"What is the current price of Bitcoin in USD?"
"Show me the order book for ETH/AUD."
Features
Real-time Ticker Data: Get the latest price, bid, ask, and volume for any currency pair.
Real-time Order Book Data: View the current buy and sell orders.
Automatic Reconnection: The client will automatically reconnect if the connection is lost.
Easy to Use: Exposes simple tools that an AI can understand.
Setup
Clone this repository:
git clone <your-repo-url>cd independentreserve-mcp
Install Python dependencies:
pip install -r requirements.txt
Configure API Keys (Optional):
For public data (tickers, order books), no API key is needed.
If you want to add private data features later (like account balances), create a .env file in the project root.
Copy .env.example to .env and fill in your Independent Reserve API keys.
cp .env.example .env# Then edit .env with your credentials
Connecting to Claude Desktop
To use this server with Claude Desktop, you need to add it to your Claude configuration file.

Find your Claude Desktop config file:
macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
Windows: %APPDATA%\Claude\claude_desktop_config.json
Add the server configuration:Open the file and add the following mcpServers object. Make sure to replace /path/to/your/independentreserve-mcp with the absolute path to the project folder on your computer.
{  "mcpServers": {    "independentreserve": {      "command": "python",      "args": [        "/path/to/your/independentreserve-mcp/server.py"      ],      "env": {        "IR_API_KEY": "your_api_key_if_needed",        "IR_API_SECRET": "your_api_secret_if_needed"      }    }  }}
Restart Claude Desktop.After restarting, Claude will automatically connect to your new MCP server. You can now start asking it about cryptocurrency prices from Independent Reserve!
Next Steps and Improvements
Authentication: Implement the signed message logic to subscribe to private channels like balance, orders, and trades. This would require adding new tools like get_my_balance.
Smarter Subscriptions: Instead of subscribing every time a tool is called, the client could be smarter. For example, if the AI asks for the BTC/USD ticker, it could stay subscribed to it for a few minutes in case of follow-up questions.
Error Handling: Add more robust error handling for invalid currency pairs or API errors.
More Data: Add a tool for get_recent_trades.
