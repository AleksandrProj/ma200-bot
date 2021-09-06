import os
from binance import Client

BASEDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES_BOT = {
    'orders': os.path.join(BASEDIR, 'files', 'orders.csv'),
    'archive_orders': os.path.join(BASEDIR, 'files', 'archive_orders.csv'),
    'bot_log': os.path.join(BASEDIR, 'logs', 'bot_log.txt')
}

# Настройки для телеграм бота
TOKEN_TELEGRAM_BOT = os.environ['TOKEN_TB']
TOKEN_TELEGRAM_BOT_ERROR = os.environ['TOKEN_TB_ERROR']
CHAT_ID_TELEGRAM_BOT = os.environ['CHAT_ID_TB']

# Data bot
API_KEY = os.environ['API_KEY_BIN']
API_SECRET = os.environ['API_SECRET_BIN']

# Параметры для бота
NAME_BOT = "MA200 Bot [FUTURES]"
TIMEFRAME = Client.KLINE_INTERVAL_5MINUTE
MAIN_TIMEOUT_BOT = 0.01

# Настройки для стратегии (Информация по правилам торговли https://www.binance.com/ru/trade-rule)
STRATEGY = 'MA200'           # Тип стратегии торговли ['MA200', 'MA200+50']
MAX_PRICE_FUTURES = 8           # Максимальная цена фьючерса
MIN_AMOUNT_ORDER = 10           # Размер ордера для торговли
PERCENT_PART_BALANCE = 1        # На какой % от депозита разрешено торговать боту
STOP_LOSS = 0.01                # Отступ от уровня минимальной цены предыдущего бара (указывается в пунктах)
TAKE_PROFIT = 0.05             # Насколько Takeprofit больше Stoploss (множитель)
TARGET_PERCENT_PRICE_MIN = 0.5  # Отступ от MA200 минимум (проценты)
TARGET_PERCENT_PRICE_MAX = 1.5  # Отступ от MA200 максимум (проценты)
BIG_MA = 288                    # Период большой скользящей средней
SMALL_MA = 72                   # Период маленькой скользящей средней
