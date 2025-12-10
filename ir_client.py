# ir_client.py
import asyncio
import json
import os
import logging
import websockets
from dotenv import load_dotenv
import time
import hmac
import hashlib
from collections import OrderedDict

load_dotenv()

# Configure structured logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

CACHE_TIMEOUT = 300  # 5 minutes

class IndependentReserveWebSocketClient:
    def __init__(self):
        self.ws_url = "wss://ws.independentreserve.com/v2"
        self.api_key = os.getenv("IR_API_KEY")
        self.api_secret = os.getenv("IR_API_SECRET")
        
        # Caches to store the latest data from the WebSocket
        self.tickers = {}
        self.order_books = {}
        self.recent_trades = {}
        self.balances = {}
        self.subscription_cache = OrderedDict()

        self.websocket = None
        self._running = False
        self.active_subscriptions = set()

    async def connect(self):
        """Connects to the WebSocket, listens for messages, and manages subscriptions."""
        if self._running:
            return
        self._running = True
        logging.info("Connecting to Independent Reserve WebSocket...")
        
        asyncio.create_task(self._manage_subscriptions())

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

    async def _manage_subscriptions(self):
        """Periodically checks for and unsubscribes from expired channels."""
        while self._running:
            now = time.time()
            expired_channels = [
                channel for channel, sub_time in self.subscription_cache.items()
                if now - sub_time > CACHE_TIMEOUT
            ]

            for channel in expired_channels:
                await self._unsubscribe(channel)

            await asyncio.sleep(60)  # Check every minute

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
        elif channel == "balance":
            for currency_balance in payload:
                self.balances[currency_balance['CurrencyCode'].lower()] = currency_balance

    def _handle_error(self, data):
        """Handles error messages from the WebSocket."""
        error_message = data.get("o", "Unknown error")
        logging.error(f"Received error from server: {error_message}")

    async def _subscribe(self, channel, is_private=False):
        """Sends a subscription message if not already subscribed or if the subscription has expired."""
        now = time.time()

        if channel in self.subscription_cache and now - self.subscription_cache[channel] < CACHE_TIMEOUT:
            self.subscription_cache[channel] = now  # Refresh the timestamp
            return

        if self.websocket:
            message = {"m": "subscribe", "n": channel}

            if is_private:
                if not self.api_key or not self.api_secret:
                    logging.error("API key and secret are required for private channels.")
                    return

                nonce = str(int(time.time()))

                parameters_for_signature = [
                    'apiKey=' + self.api_key,
                    'nonce=' + nonce,
                    'channel=' + channel
                ]

                message_to_sign = ','.join(parameters_for_signature)

                signature = hmac.new(
                    self.api_secret.encode('utf-8'),
                    msg=message_to_sign.encode('utf-8'),
                    digestmod=hashlib.sha256).hexdigest().upper()

                auth_payload = {
                    "apiKey": self.api_key,
                    "nonce": nonce,
                    "signature": signature
                }

                message["o"] = auth_payload

            await self.websocket.send(json.dumps(message))
            self.active_subscriptions.add(channel)
            self.subscription_cache[channel] = now
            logging.info(f"Subscribed to {channel}")

    async def _unsubscribe(self, channel):
        """Sends an unsubscription message."""
        if channel not in self.active_subscriptions:
            return

        if self.websocket:
            message = {"m": "unsubscribe", "n": channel}
            await self.websocket.send(json.dumps(message))
            self.active_subscriptions.discard(channel)
            del self.subscription_cache[channel]
            logging.info(f"Unsubscribed from {channel}")

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

    async def subscribe_balance(self):
        """Subscribes to the balance channel."""
        await self._subscribe("balance", is_private=True)

    async def _resubscribe_all(self):
        """Resubscribes to all active channels after a disconnect."""
        if not self.websocket or not self.active_subscriptions:
            return

        logging.info(f"Resubscribing to {len(self.active_subscriptions)} channels...")
        for channel in list(self.active_subscriptions):
            is_private = channel in ["balance", "orders", "trades"]

            message = {"m": "subscribe", "n": channel}

            if is_private:
                if not self.api_key or not self.api_secret:
                    logging.error(f"Cannot resubscribe to private channel {channel} without API key and secret.")
                    continue

                nonce = str(int(time.time()))

                parameters_for_signature = [
                    'apiKey=' + self.api_key,
                    'nonce=' + nonce,
                    'channel=' + channel
                ]

                message_to_sign = ','.join(parameters_for_signature)

                signature = hmac.new(
                    self.api_secret.encode('utf-8'),
                    msg=message_to_sign.encode('utf-8'),
                    digestmod=hashlib.sha256).hexdigest().upper()

                auth_payload = {
                    "apiKey": self.api_key,
                    "nonce": nonce,
                    "signature": signature
                }

                message["o"] = auth_payload

            try:
                await self.websocket.send(json.dumps(message))
                self.subscription_cache[channel] = time.time()
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

    def get_my_balance(self):
        """Retrieves all cached balances."""
        return self.balances
        
    def stop(self):
        """Stops the client."""
        self._running = False
