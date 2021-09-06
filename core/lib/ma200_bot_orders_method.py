from core.settings_server import CHAT_ID_TELEGRAM_BOT, TOKEN_TELEGRAM_BOT, MIN_AMOUNT_ORDER, TAKE_PROFIT, STOP_LOSS, \
                               STRATEGY, NAME_BOT, PERCENT_PART_BALANCE
from core.lib.ma200_bot_func import write_log, init_time
from core.lib.ma200_bot_files_method import save_csv, save_archive_order, delete_order_csv, check_open_order

from binance.enums import *
from binance.exceptions import BinanceAPIException

from decimal import Decimal
from pprint import pprint
import time
import math
import telebot


# Открытие сделок
def open_order(self, data):
    symbol = data['symbol']
    type_order = data['type_order']
    get_stop_take = get_stop_take_order(self, data)
    stoploss = get_stop_take['stoploss']
    takeprofit = get_stop_take['takeprofit']
    lot_order = get_order_lot(self, data)

    used_balance = check_open_order(symbol)['balance']
    minimal_quantity_deals = math.floor(
        ((data['balance'] * Decimal(PERCENT_PART_BALANCE)) - used_balance) /
        Decimal(MIN_AMOUNT_ORDER))

    # Подключение telegram бота для уведомлений
    telegram_bot = telebot.TeleBot(TOKEN_TELEGRAM_BOT)

    try:
        if minimal_quantity_deals > 0:
            order = self.client.futures_create_order(
                symbol=symbol,
                side=type_order,
                type=ORDER_TYPE_MARKET,
                quantity=lot_order,
                newOrderRespType=ORDER_RESP_TYPE_RESULT
            )
            pprint(order)

            entry_commission = Decimal()
            status = order['status']

            entry_commissions = self.client.futures_account_trades(symbol=symbol, startTime=order['updateTime'])

            for data in entry_commissions:
                entry_commission += Decimal(data['commission'])

            if status == 'FILLED':
                save_csv(order, stoploss, takeprofit, entry_commission, True)

                telegram_bot.send_message(CHAT_ID_TELEGRAM_BOT,
                                          NAME_BOT + "\n" +
                                          symbol + ' - ' + type_order + '\n'
                                          'Стратегия: ' + STRATEGY + '\n'
                                          'OrderID: ' + str(order['orderId']) + '\n'
                                          'Цена сделки: ' + str(order['avgPrice']) + '\n'
                                          'Take-profit: ' + str(takeprofit) + '\n'
                                          'Stop-loss: ' + str(stoploss) + '\n'
                                          'Lot: ' + str(order['cumQty']))
            elif status == 'EXPIRED':
                save_csv(order, stoploss, takeprofit, entry_commission, False)
            else:
                message = 'Внимание: Ордер по фьючерсу ' + symbol + ' получил статус - ' + str(status)
                print(init_time() + ' - ' + message)
                write_log(self, message)
    except BinanceAPIException as err:
        if 'Invalid quantity' in err.message:
            print(NAME_BOT + ' - ' + STRATEGY + ' - ' + symbol + 'Не хватает лотов для входа')
            telegram_bot.send_message(CHAT_ID_TELEGRAM_BOT, NAME_BOT + ' - ' + STRATEGY + ' - ' + symbol +
                                                                       ' - Не хватает лотов для входа')
            time.sleep(180)
        elif 'Account has insufficient balance for requested action' in err.message:
            print(NAME_BOT + ' - ' + STRATEGY + ' - ' + symbol + ' - Не хватает средств на балансе для входа')
            telegram_bot.send_message(CHAT_ID_TELEGRAM_BOT,
                                      NAME_BOT + ' - ' + STRATEGY + ' - ' + symbol +
                                      ' - Не хватает средств на балансе для входа')
            time.sleep(180)
        elif 'Margin is insufficient' in err.message:
            print(NAME_BOT + ' - ' + STRATEGY + ' - ' + symbol + ' - Не достигнут лимит по входу в сделку')
            telegram_bot.send_message(CHAT_ID_TELEGRAM_BOT,
                                      NAME_BOT + ' - ' + STRATEGY + ' - ' + symbol +
                                      ' - Не достигнут лимит по входу в сделку')
            time.sleep(180)
        elif "Order's notional must be no smaller than" in err.message:
            print(NAME_BOT + ' - ' + STRATEGY + ' - ' + symbol + ' - Не выполнено минимальная сумма для сделки')
            telegram_bot.send_message(CHAT_ID_TELEGRAM_BOT,
                                      NAME_BOT + ' - ' + STRATEGY + ' - ' + symbol +
                                      ' - Не выполнено минимальная сумма для сделки')
            time.sleep(180)
        else:
            print(err)
            write_log(self, err)
    except Exception as err:
        print(err)
        write_log(self, err)


# Получаем значения уровней для Take-profit и Stop-loss
def get_stop_take_order(self, data):
    type_order = data['type_order']
    price_tick = data['price_tick']
    current_price = self.current_price[data['symbol']]
    sl_qty_point = Decimal(current_price * Decimal(STOP_LOSS)).quantize(price_tick)
    tp_qty_point = Decimal(current_price * Decimal(TAKE_PROFIT)).quantize(price_tick)

    if STRATEGY == 'MA200':
        if type_order == 'BUY':
            return {
                'stoploss': Decimal(current_price - sl_qty_point).quantize(price_tick),
                'takeprofit': Decimal(current_price + tp_qty_point).quantize(price_tick),
            }

        if type_order == 'SELL':
            return {
                'stoploss': Decimal(current_price + sl_qty_point).quantize(price_tick),
                'takeprofit': Decimal(current_price - tp_qty_point).quantize(price_tick),
            }
    if STRATEGY == 'MA200+50':
        if type_order == 'BUY':
            return {
                'stoploss': Decimal(current_price - sl_qty_point).quantize(price_tick),
                'takeprofit': None
            }

        if type_order == 'SELL':
            return {
                'stoploss': Decimal(current_price + sl_qty_point).quantize(price_tick),
                'takeprofit': None
            }


# Расчет кол-во лотов для валюты
def get_order_lot(self, data):
    # Кол-во лотов для валюты
    if data['price_lot'] == 1:
        return Decimal(round(Decimal(MIN_AMOUNT_ORDER / self.current_price[data['symbol']]))).quantize(data['price_lot'])
    elif data['price_lot'] < 1:
        return Decimal(MIN_AMOUNT_ORDER / self.current_price[data['symbol']]).quantize(data['price_lot'])


# Закрытие сделок
def close_order(self, symbol, type_order, data_order, result):
    id_order = data_order['id_order']
    entry_price_order = data_order['entry_price']
    entry_lot_price = data_order['entry_lot']
    lot_order = data_order['lot']
    commission_entry_order = data_order['commission']
    side_order = SIDE_SELL if type_order == 'BUY' else SIDE_BUY
    result_order = 'Take-profit' if result else 'Stop-loss'

    # Подключение telegram бота для уведомлений
    telegram_bot = telebot.TeleBot(TOKEN_TELEGRAM_BOT)

    # Алгоритм закрытия сделки
    try:
        order = self.client.futures_create_order(
            symbol=symbol,
            side=side_order,
            type=ORDER_TYPE_MARKET,
            quantity=lot_order,
            newOrderRespType=ORDER_RESP_TYPE_RESULT)

        pprint(order)

        exit_lot_price = order['cumQuote']
        exit_price_order = order['avgPrice']

        # Расчет общей коммиссии по сделке (ВХОД/ВЫХОД)
        exit_commission = Decimal()
        exit_commissions = self.client.futures_account_trades(symbol=symbol, startTime=order['updateTime'])
        for data in exit_commissions:
            exit_commission += Decimal(data['commission'])
        main_commission = Decimal(commission_entry_order) + Decimal(exit_commission)

        if order['status'] == 'FILLED':
            main_profit = Decimal()
            if type_order == 'BUY':
                main_profit = Decimal(exit_lot_price) - entry_lot_price
            elif type_order == 'SELL':
                main_profit = entry_lot_price - Decimal(exit_lot_price)

            telegram_bot.send_message(CHAT_ID_TELEGRAM_BOT,
                                      NAME_BOT + "\n" +
                                      symbol + '[ ' + type_order + ' ]' + ' - СДЕЛКА ЗАКРЫТА\n'
                                      'Стратегия: ' + STRATEGY + '\n'
                                      'OrderID: ' + str(id_order) + '\n'
                                      'Цена закрытия сделки: ' + str(exit_price_order) + '\n'
                                      'Результат: закрыта по ' + result_order + '\n'
                                      'Прибыль: ' + str(main_profit) + '$')

            delete_order_csv(id_order)
            save_archive_order(symbol, id_order, type_order, entry_price_order, exit_price_order,
                               entry_lot_price, exit_lot_price, main_commission, main_profit, lot_order)
    except BinanceAPIException as err:
        print(init_time() + ' - ' + str(err))
        write_log(self, err)
    except Exception as err:
        print(err)
        write_log(self, err)
