# ir_client.py
import asyncio
import json
import os
import logging
import websockets
from dotenv import load_dotenv

load_dotenv()

# Configure structured logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

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
        self.active_subscriptions = set()

    async def connect(self):
        """Connects to the WebSocket and listens for messages."""
        if self._running:
            return
        self._running = True
        logging.info("Connecting to Independent Reserve WebSocket...")
        
        while self._running:
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    self.websocket = websocket
                    logging.info("WebSocket connection established.")
                    # Resubscribe to channels after reconnecting
                    await self._resubscribe_all()
                    
                    async for message in websocket:
                        try:
                            await self._handle_message(json.loads(message))
                        except json.JSONDecodeError:
                            logging.error(f"Failed to decode JSON: {message}")
            except (websockets.ConnectionClosedError, ConnectionRefusedError) as e:
                logging.warning(f"WebSocket connection lost: {e}. Reconnecting in 5 seconds...")
                await asyncio.sleep(5)
            except Exception as e:
                logging.error(f"An unexpected error occurred: {e}. Reconnecting in 5 seconds...")
                await asyncio.sleep(5)

    async def _handle_message(self, data):
        """Routes incoming messages to the correct handler based on the channel."""
        event = data.get("e")
        if event == "error":
            self._handle_error(data)
            return

        channel = data.get("n")
        payload = data.get("o")
        
        if not channel or not payload:
            logging.warning(f"Received malformed message: {data}")
            return

        if channel.startswith("ticker"):
            key = payload['PrimaryCurrencyCode'].lower() + payload['SecondaryCurrencyCode'].lower()
            self.tickers[key] = payload
        elif channel.startswith("orderbook"):
            key = payload['PrimaryCurrencyCode'].lower() + payload['SecondaryCurrencyCode'].lower()
            self.order_books[key] = payload
        elif channel.startswith("recenttrades"):
            key = payload['PrimaryCurrencyCode'].lower() + payload['SecondaryCurrencyCode'].lower()
            self.recent_trades[key] = payload
        # Add other channels like 'balance', 'orders' here if needed

    def _handle_error(self, data):
        """Handles error messages from the WebSocket."""
        error_message = data.get("o", "Unknown error")
        logging.error(f"Received error from server: {error_message}")

    async def _subscribe(self, channel):
        """Sends a subscription message if not already subscribed."""
        if channel in self.active_subscriptions:
            return  # Already subscribed

        if self.websocket:
            message = {"m": "subscribe", "n": channel}
            await self.websocket.send(json.dumps(message))
            self.active_subscriptions.add(channel)
            logging.info(f"Subscribed to {channel}")

    async def subscribe_ticker(self, primary_currency, secondary_currency):
        """Subscribes to the ticker channel for a given currency pair."""
        channel = f"ticker-{primary_currency.lower()}{secondary_currency.lower()}"
        await self._subscribe(channel)

    async def subscribe_order_book(self, primary_currency, secondary_currency):
        """Subscribes to the order book channel."""
        channel = f"orderbook-{primary_currency.lower()}{secondary_currency.lower()}"
        await self._subscribe(channel)

    async def subscribe_recent_trades(self, primary_currency, secondary_currency):
        """Subscribes to the recent trades channel."""
        channel = f"recenttrades-{primary_currency.lower()}{secondary_currency.lower()}"
        await self._subscribe(channel)

    async def _resubscribe_all(self):
        """Resubscribes to all active channels after a disconnect."""
        if not self.websocket or not self.active_subscriptions:
            return

        logging.info(f"Resubscribing to {len(self.active_subscriptions)} channels...")
        for channel in list(self.active_subscriptions):
            message = {"m": "subscribe", "n": channel}
            try:
                await self.websocket.send(json.dumps(message))
                logging.info(f"Successfully resubscribed to {channel}")
            except websockets.ConnectionClosed:
                logging.warning(f"Failed to resubscribe to {channel}, connection closed.")
                break

    def get_latest_ticker(self, primary_currency, secondary_currency):
        """Retrieves the latest cached ticker data."""
        key = f"{primary_currency.lower()}{secondary_currency.lower()}"
        return self.tickers.get(key)

    def get_latest_order_book(self, primary_currency, secondary_currency):
        """Retrieves the latest cached order book data."""
        key = f"{primary_currency.lower()}{secondary_currency.lower()}"
        return self.order_books.get(key)

    def get_latest_recent_trades(self, primary_currency, secondary_currency):
        """Retrieves the latest cached recent trades data."""
        key = f"{primary_currency.lower()}{secondary_currency.lower()}"
        return self.recent_trades.get(key)
        
    def stop(self):
        """Stops the client."""
        self._running = False
