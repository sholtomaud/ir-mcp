# ir_client.py
import asyncio
import json
import os
import websockets
from dotenv import load_dotenv

load_dotenv()

class IndependentReserveWebSocketClient:
    def __init__(self):
        self.ws_url = "wss://ws.independentreserve.com/v2"
        self.api_key = os.getenv("IR_API_KEY")
        self.api_secret = os.getenv("IR_API_SECRET")
        
        # Caches to store the latest data from the WebSocket
        self.tickers = {}
        self.order_books = {}
        self.recent_trades = {}

        self.websocket = None
        self._running = False

    async def connect(self):
        """Connects to the WebSocket and listens for messages."""
        if self._running:
            return
        self._running = True
        print("Connecting to Independent Reserve WebSocket...")
        
        while self._running:
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    self.websocket = websocket
                    print("WebSocket connection established.")
                    # Resubscribe to channels after reconnecting
                    await self._resubscribe_all()
                    
                    async for message in websocket:
                        await self._handle_message(json.loads(message))
            except (websockets.ConnectionClosedError, ConnectionRefusedError) as e:
                print(f"WebSocket connection lost: {e}. Reconnecting in 5 seconds...")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"An unexpected error occurred: {e}. Reconnecting in 5 seconds...")
                await asyncio.sleep(5)

    async def _handle_message(self, data):
        """Routes incoming messages to the correct handler based on the channel."""
        channel = data.get("n")
        payload = data.get("o")
        
        if channel == "ticker":
            # The key is the currency pair, e.g., "xbtusd"
            self.tickers[payload['PrimaryCurrencyCode'].lower() + payload['SecondaryCurrencyCode'].lower()] = payload
        elif channel == "orderbook":
            key = payload['PrimaryCurrencyCode'].lower() + payload['SecondaryCurrencyCode'].lower()
            self.order_books[key] = payload
        elif channel == "recenttrades":
            key = payload['PrimaryCurrencyCode'].lower() + payload['SecondaryCurrencyCode'].lower()
            self.recent_trades[key] = payload # Stores the full list of recent trades
        # Add other channels like 'balance', 'orders' here if needed

    async def subscribe_ticker(self, primary_currency, secondary_currency):
        """Subscribes to the ticker channel for a given currency pair."""
        if self.websocket:
            channel = f"ticker-{primary_currency.lower()}{secondary_currency.lower()}"
            message = {"m": "subscribe", "n": channel}
            await self.websocket.send(json.dumps(message))
            print(f"Subscribed to {channel}")

    async def subscribe_order_book(self, primary_currency, secondary_currency):
        """Subscribes to the order book channel."""
        if self.websocket:
            channel = f"orderbook-{primary_currency.lower()}{secondary_currency.lower()}"
            message = {"m": "subscribe", "n": channel}
            await self.websocket.send(json.dumps(message))
            print(f"Subscribed to {channel}")

    async def _resubscribe_all(self):
        """Placeholder for resubscribing to channels after a disconnect."""
        # In a more complex version, you'd track active subscriptions and resubscribe.
        pass

    def get_latest_ticker(self, primary_currency, secondary_currency):
        """Retrieves the latest cached ticker data."""
        key = f"{primary_currency.lower()}{secondary_currency.lower()}"
        return self.tickers.get(key)

    def get_latest_order_book(self, primary_currency, secondary_currency):
        """Retrieves the latest cached order book data."""
        key = f"{primary_currency.lower()}{secondary_currency.lower()}"
        return self.order_books.get(key)
        
    def stop(self):
        """Stops the client."""
        self._running = False
