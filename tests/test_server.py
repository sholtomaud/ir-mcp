import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from server import handle_call_tool

class TestServer(unittest.IsolatedAsyncioTestCase):
    @patch('server.ir_client', new_callable=AsyncMock)
    async def test_get_ticker(self, mock_ir_client):
        # Configure the synchronous method with MagicMock
        mock_ir_client.get_latest_ticker = MagicMock(return_value={
            "PrimaryCurrencyCode": "Xbt",
            "SecondaryCurrencyCode": "Usd",
            "LastPrice": 52000.0,
        })

        result = await handle_call_tool("get_ticker", {"primary_currency": "xbt", "secondary_currency": "usd"})

        self.assertIn("Ticker for Xbt/Usd", result[0].text)
        self.assertIn("52000.0", result[0].text)
        mock_ir_client.subscribe_ticker.assert_awaited_once_with("xbt", "usd")

    @patch('server.ir_client', new_callable=AsyncMock)
    async def test_get_order_book(self, mock_ir_client):
        mock_ir_client.get_latest_order_book = MagicMock(return_value={
            "PrimaryCurrencyCode": "Eth",
            "SecondaryCurrencyCode": "Aud",
            "BuyOrders": [{"Price": 3000, "Volume": 10}],
            "SellOrders": [{"Price": 3100, "Volume": 10}],
        })

        result = await handle_call_tool("get_order_book", {"primary_currency": "eth", "secondary_currency": "aud"})

        self.assertIn("Order Book for Eth/Aud", result[0].text)
        self.assertIn("3000", result[0].text)
        mock_ir_client.subscribe_order_book.assert_awaited_once_with("eth", "aud")

    @patch('server.ir_client', new_callable=AsyncMock)
    async def test_get_recent_trades(self, mock_ir_client):
        mock_ir_client.get_latest_recent_trades = MagicMock(return_value={
            "PrimaryCurrencyCode": "Btc",
            "SecondaryCurrencyCode": "Usd",
            "Trades": [{"Price": 60000, "Volume": 0.5}],
        })

        result = await handle_call_tool("get_recent_trades", {"primary_currency": "btc", "secondary_currency": "usd"})

        self.assertIn("Recent Trades for Btc/Usd", result[0].text)
        self.assertIn("60000", result[0].text)
        mock_ir_client.subscribe_recent_trades.assert_awaited_once_with("btc", "usd")

    @patch('server.ir_client', new_callable=AsyncMock)
    async def test_unknown_tool(self, mock_ir_client):
        result = await handle_call_tool("unknown_tool", {"primary_currency": "btc", "secondary_currency": "usd"})
        self.assertEqual("Unknown tool.", result[0].text)

if __name__ == '__main__':
    unittest.main()
