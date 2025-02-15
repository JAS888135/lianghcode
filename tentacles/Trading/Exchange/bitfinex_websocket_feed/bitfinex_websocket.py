#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import octobot_trading.exchanges as exchanges
from octobot_trading.enums import WebsocketFeeds as Feeds
import tentacles.Trading.Exchange.bitfinex.bitfinex_exchange as bitfinex_exchange


class BitfinexCCXTWebsocketConnector(exchanges.CCXTWebsocketConnector):
    EXCHANGE_FEEDS = {
        Feeds.TRADES: True,
        Feeds.KLINE: Feeds.UNSUPPORTED.value,   # ohlcv is getting closed candles after new ones, this it not yet supported
        Feeds.TICKER: True,
        Feeds.CANDLE: Feeds.UNSUPPORTED.value,  # ohlcv is getting closed candles after new ones, this it not yet supported
    }

    @classmethod
    def get_name(cls):
        return bitfinex_exchange.Bitfinex.get_name()
