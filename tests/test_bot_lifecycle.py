"""Mocked regression tests for Telegram bot lifecycle safety."""

from __future__ import annotations

import importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import app


class BotLifecycleTests(unittest.IsolatedAsyncioTestCase):
    """Verify the polling lifecycle without contacting Telegram or Google."""

    def test_import_does_not_start_polling(self) -> None:
        with patch.object(app.Dispatcher, "start_polling", new=AsyncMock()) as polling:
            importlib.reload(app)
            polling.assert_not_awaited()

    async def test_main_starts_one_poll_and_closes_session(self) -> None:
        bot = MagicMock()
        bot.session.close = AsyncMock()
        dispatcher = MagicMock()
        dispatcher.start_polling = AsyncMock()

        with (
            patch.object(app, "BOT_TOKEN", "test-token"),
            patch.object(app, "Bot", return_value=bot) as bot_factory,
            patch.object(app, "Dispatcher", return_value=dispatcher) as dispatcher_factory,
        ):
            await app.main()

        bot_factory.assert_called_once_with(token="test-token")
        dispatcher_factory.assert_called_once_with()
        dispatcher.start_polling.assert_awaited_once_with(
            bot,
            close_bot_session=False,
        )
        bot.session.close.assert_awaited_once_with()

    async def test_main_closes_session_when_polling_fails(self) -> None:
        bot = MagicMock()
        bot.session.close = AsyncMock()
        dispatcher = MagicMock()
        dispatcher.start_polling = AsyncMock(side_effect=RuntimeError("polling failed"))

        with (
            patch.object(app, "BOT_TOKEN", "test-token"),
            patch.object(app, "Bot", return_value=bot),
            patch.object(app, "Dispatcher", return_value=dispatcher),
        ):
            with self.assertRaisesRegex(RuntimeError, "polling failed"):
                await app.main()

        bot.session.close.assert_awaited_once_with()


if __name__ == "__main__":
    unittest.main()
