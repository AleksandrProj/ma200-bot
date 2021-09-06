from core.settings_server import FILES_BOT, TOKEN_TELEGRAM_BOT_ERROR, CHAT_ID_TELEGRAM_BOT, STRATEGY, NAME_BOT
from datetime import datetime
from decimal import Decimal
import telebot


# Подключение telegram бота для уведомлений под ошибки
telegramBot = telebot.TeleBot(TOKEN_TELEGRAM_BOT_ERROR)


def init_time():
    return datetime.now().ctime()


# Вычисление изменения цены от MA200 в %
def get_change_price_percent(level_ma200, current_price, type_bar):
    if type_bar == 'bulls':
        return abs(Decimal((current_price / (level_ma200 / 100)) - 100).quantize(Decimal('0.01')))
    elif type_bar == 'bears':
        return abs(Decimal((level_ma200 / (current_price / 100)) - 100).quantize(Decimal('0.01')))


def write_log(error, symbol=None):
    telegramBot.send_message(CHAT_ID_TELEGRAM_BOT, NAME_BOT + ' [' + symbol + '] ' + STRATEGY + ' - ' + str(error))
    with open(FILES_BOT['bot_log'], 'at') as fout:
        fout.write(init_time() + ' - ' + str(error) + '\n')