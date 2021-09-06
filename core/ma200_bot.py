from binance import Client, ThreadedWebsocketManager
from binance.exceptions import BinanceAPIException

from core.settings_server import API_KEY, API_SECRET, TIMEFRAME, TARGET_PERCENT_PRICE_MIN, TARGET_PERCENT_PRICE_MAX, \
    STRATEGY, MAIN_TIMEOUT_BOT, MIN_AMOUNT_ORDER, MAX_PRICE_FUTURES, PERCENT_PART_BALANCE, BIG_MA, SMALL_MA
from core.lib.ma200_bot_func import write_log, get_change_price_percent, init_time
from core.lib.ma200_bot_files_method import check_open_order
from core.lib.ma200_bot_orders_method import open_order, close_order

from twisted.internet import reactor, error
from threading import Thread
from decimal import Decimal
import time
import math


class Ma200Bot:
    def __init__(self):
        # ИНИЦИАЛИЗАЦИЯ ПАРАМЕТРОВ
        self.current_price = {}
        self.list_streams = []
        self.price_tick_size = {}
        self.price_lot_size = {}

        # статический client
        self.client = Client(API_KEY, API_SECRET)

        # client по Socket
        self.twm = ThreadedWebsocketManager(api_key=API_KEY, api_secret=API_SECRET)
        self.twm.start()

        # Получаем информацию по Фьючерсам
        self.info_futures = self.client.futures_exchange_info()['symbols']

    def connect_socket(self, symbol):
        self.list_streams.append(
            self.twm.start_aggtrade_futures_socket(callback=self.handle_socket_message, symbol=symbol))
        self.current_price[symbol] = 0

    def handle_socket_message(self, data):
        try:
            if data['data']:
                self.current_price[data['data']['s']] = Decimal(data['data']['p'])
        except KeyError as err:
            err = "Ошибка в функции handle_socket_message: " + str(err)
            print(err)
            write_log(err)
        except Exception as err:
            err = "Ошибка в функции handle_socket_message: " + str(err)
            print(err)
            write_log(err)

    # Начало торговли ботом
    def start_trade_bot(self, data):
        # Если нет открытых ордеров
        if not data['open_order']:
            if data['minimal_deals'] > 0:
                if 0 < self.current_price[data['symbol']] < MAX_PRICE_FUTURES:
                    self.find_entry_point({
                        'symbol': data['symbol'],
                        'balance': data['balance']
                    })

        # Если есть открытые ордера
        else:
            if self.current_price[data['symbol']] > 0:
                self.monitoring_point({
                    'symbol': data['symbol'],
                    'open_order': data['open_order']
                })

    # Поиск новой точки для открытия сделки
    def find_entry_point(self, data):
        trade_symbol = data['symbol']
        average_price = self.get_average_price(trade_symbol)
        avg_price_big = average_price['avg_price_big']
        avg_price_small = average_price['avg_price_small']
        close_prices_last_2_bars = average_price['last_close_prices_2_bars']
        last_bar_high = Decimal(average_price['last_high_price_bar'])
        last_bar_low = Decimal(average_price['last_low_price_bar'])
        price_tick = Decimal(self.price_tick_size[trade_symbol])
        price_lot = Decimal(self.price_lot_size[trade_symbol])

        if len(close_prices_last_2_bars) >= 2:
            print(init_time() + ' Ищем точку входа для ' + trade_symbol)

            if STRATEGY == 'MA200':
                close_price_last_bar = close_prices_last_2_bars[1]

                # BUY
                if avg_price_small < self.current_price[trade_symbol] > avg_price_big:
                    if avg_price_small < close_price_last_bar > avg_price_big:
                        if self.current_price[trade_symbol] > last_bar_high:
                            if TARGET_PERCENT_PRICE_MIN < get_change_price_percent(avg_price_big,
                                                                                   self.current_price[trade_symbol],
                                                                                   'bulls') < TARGET_PERCENT_PRICE_MAX:
                                print('Входим в покупку по стратегии MA200 - ' + trade_symbol)
                                open_order(self, {
                                    'symbol': trade_symbol,
                                    'balance': data['balance'],
                                    'type_order': 'BUY',
                                    'price_tick': price_tick,
                                    'price_lot': price_lot,
                                })

                # SELL
                if avg_price_small > self.current_price[trade_symbol] < avg_price_big:
                    if avg_price_small > close_price_last_bar < avg_price_big:
                        if self.current_price[trade_symbol] < last_bar_low:
                            if TARGET_PERCENT_PRICE_MIN < get_change_price_percent(avg_price_big,
                                                                                   self.current_price[trade_symbol],
                                                                                   'bears') < TARGET_PERCENT_PRICE_MAX:
                                print('Входим в продажу по стратегии MA200 - ' + trade_symbol)
                                open_order(self, {
                                    'symbol': trade_symbol,
                                    'balance': data['balance'],
                                    'type_order': 'SELL',
                                    'price_tick': price_tick,
                                    'price_lot': price_lot,
                                })

            if STRATEGY == 'MA200+50':
                close_price_last_bar = close_prices_last_2_bars[1]

                # BUY
                if avg_price_big < avg_price_small:
                    if avg_price_small < close_price_last_bar > avg_price_big:
                        if self.current_price[trade_symbol] > last_bar_high:
                            if TARGET_PERCENT_PRICE_MIN < get_change_price_percent(avg_price_big,
                                                                                   self.current_price[trade_symbol],
                                                                                   'bulls') < TARGET_PERCENT_PRICE_MAX:
                                print('Входим в покупку по стратегии MA200+50 - ' + trade_symbol)
                                open_order(self, {
                                    'symbol': trade_symbol,
                                    'balance': data['balance'],
                                    'type_order': 'BUY',
                                    'price_tick': price_tick,
                                    'price_lot': price_lot,
                                })

                # SELL
                if avg_price_big > avg_price_small:
                    if avg_price_small > close_price_last_bar < avg_price_big:
                        if self.current_price[trade_symbol] < last_bar_low:
                            if TARGET_PERCENT_PRICE_MIN < get_change_price_percent(avg_price_big,
                                                                                   self.current_price[trade_symbol],
                                                                                   'bears') < TARGET_PERCENT_PRICE_MAX:
                                print('Входим в продажу по стратегии MA200+50 - ' + trade_symbol)
                                open_order(self, {
                                    'symbol': trade_symbol,
                                    'balance': data['balance'],
                                    'type_order': 'SELL',
                                    'price_tick': price_tick,
                                    'price_lot': price_lot,
                                })

    # Мониторинг за открытой позицией
    def monitoring_point(self, data):
        trade_symbol = data['symbol']
        data_open_order = data['open_order'][0]
        type_order = data_open_order['type-order']
        id_order = data_open_order['order-id']
        sl_order = Decimal(data_open_order['stop-loss'])
        entry_price = Decimal(data_open_order['price'])
        entry_lot = Decimal(data_open_order['price-lot'])
        lot_order = Decimal(data_open_order['lot'])
        commission_order = Decimal(data_open_order['commission'])
        average_price = self.get_average_price(trade_symbol)
        avg_price_big = average_price['avg_price_big']
        avg_price_small = average_price['avg_price_small']

        print(init_time() + ' Мониторинг по открытой сделки - ' + trade_symbol)

        if STRATEGY == 'MA200':
            tp_order = Decimal(data_open_order['takeprofit'])

            if type_order == 'BUY':
                # Закрытие по stop-loss
                if 0 < self.current_price[trade_symbol]:
                    if self.current_price[trade_symbol] <= avg_price_big or self.current_price[trade_symbol] <= sl_order:
                        print('Позиция закрыта по Stop-loss - BUY')
                        close_order(self, trade_symbol, 'BUY', {
                            'id_order': id_order,
                            'entry_price': entry_price,
                            'entry_lot': entry_lot,
                            'lot': lot_order,
                            'commission': commission_order
                        }, False)

                # Закрытие по take-profit
                if 0 < self.current_price[trade_symbol] >= tp_order:
                    print('Позиция закрыта по Takeprofit - BUY')
                    close_order(self, trade_symbol, 'BUY', {
                        'id_order': id_order,
                        'entry_price': entry_price,
                        'entry_lot': entry_lot,
                        'lot': lot_order,
                        'commission': commission_order
                    }, True)

            elif type_order == 'SELL':
                # Закрытие по stop-loss
                if 0 < self.current_price[trade_symbol]:
                    if self.current_price[trade_symbol] >= avg_price_big or self.current_price[trade_symbol] >= sl_order:
                        print('Позиция закрыта по Stop-loss - SELL')
                        close_order(self, trade_symbol, 'SELL', {
                            'id_order': id_order,
                            'entry_price': entry_price,
                            'entry_lot': entry_lot,
                            'lot': lot_order,
                            'commission': commission_order
                        }, False)

                # Закрытие по take-profit
                if 0 < self.current_price[trade_symbol] <= tp_order:
                    print('Позиция закрыта по Takeprofit - SELL')
                    close_order(self, trade_symbol, 'SELL', {
                        'id_order': id_order,
                        'entry_price': entry_price,
                        'entry_lot': entry_lot,
                        'lot': lot_order,
                        'commission': commission_order
                    }, True)

        if STRATEGY == 'MA200+50':
            if type_order == 'BUY':
                # Подумать как лучше выход при пересечении ценой 200 или при пересечении 200+50
                # Закрытие по stop-loss
                # if 0 < self.current_price[trade_symbol] <= sl_order:
                #     print('Позиция закрыта по стоплосу - BUY')
                #     close_order(self, trade_symbol, 'BUY', {
                #         'id_order': id_order,
                #         'entry_price': entry_price,
                #         'entry_lot': entry_lot,
                #         'lot': lot_order,
                #         'commission': commission_order
                #     }, False)

                # Закрытие по take-profit
                if avg_price_big > avg_price_small:
                    print('Позиция закрыта по тейкпрофиту - BUY')
                    close_order(self, trade_symbol, 'BUY', {
                        'id_order': id_order,
                        'entry_price': entry_price,
                        'entry_lot': entry_lot,
                        'lot': lot_order,
                        'commission': commission_order
                    }, True)

            elif type_order == 'SELL':
                # Подумать как лучше выход при пересечении ценой 200 или при пересечении 200+50
                # Закрытие по stop-loss
                # if self.current_price[trade_symbol] >= sl_order:
                #     print('Позиция закрыта по стоплосу - SELL')
                #     close_order(self, trade_symbol, 'SELL', {
                #         'id_order': id_order,
                #         'entry_price': entry_price,
                #         'entry_lot': entry_lot,
                #         'lot': lot_order,
                #         'commission': commission_order
                #     }, False)

                # Закрытие по take-profit
                if avg_price_big < avg_price_small:
                    print('Позиция закрыта по тейкпрофиту - SELL')
                    close_order(self, trade_symbol, 'SELL', {
                        'id_order': id_order,
                        'entry_price': entry_price,
                        'entry_lot': entry_lot,
                        'lot': lot_order,
                        'commission': commission_order
                    }, True)

    # Расчет средней цены за 200 дней и 50 дней
    def get_average_price(self, symbol):
        avg_price_small = Decimal()
        avg_price_big = Decimal()
        info_last_candlestick = []
        last_close_prices_2_bars = []
        qty_candlestick = ""

        # Описание для количества свечей
        if TIMEFRAME == Client.KLINE_INTERVAL_1HOUR:
            qty_candlestick = "200 hours ago UTC"
        elif TIMEFRAME == Client.KLINE_INTERVAL_5MINUTE:
            qty_candlestick = "1440 minutes ago UTC"

        try:
            info_last_candlestick = self.client.futures_historical_klines(symbol, TIMEFRAME, qty_candlestick)
        except BinanceAPIException as err:
            err = "Ошибка в функции get_average_price: " + str(err)
            write_log(self, err)
        except Exception as err:
            err = "Ошибка в функции get_average_price: " + str(err)
            write_log(self, err)

        for index, last_bar in enumerate(info_last_candlestick):
            if index >= len(info_last_candlestick) - SMALL_MA:
                avg_price_small += Decimal(last_bar[4])
            if index >= len(info_last_candlestick) - BIG_MA:
                avg_price_big += Decimal(last_bar[4])
            if len(info_last_candlestick) - 1 > index >= len(info_last_candlestick) - 3:
                last_close_prices_2_bars.append(Decimal(last_bar[4]))

        return {
            'avg_price_big': Decimal(avg_price_big / BIG_MA),
            'avg_price_small': Decimal(avg_price_small / SMALL_MA),
            'last_close_prices_2_bars': last_close_prices_2_bars,
            'last_high_price_bar': Decimal(info_last_candlestick[-2][2]),
            'last_low_price_bar': Decimal(info_last_candlestick[-2][3])
        }

    # Получение информации по фьючерсу
    def get_info_futures(self, symbol):
        try:
            for info_contract in self.info_futures:
                if info_contract['symbol'] == symbol:
                    for info_contract_filter in info_contract['filters']:
                        filter_type = info_contract_filter['filterType']
                        if filter_type == 'PRICE_FILTER':
                            self.price_tick_size[symbol] = Decimal(info_contract_filter['tickSize'])
                        elif filter_type == 'LOT_SIZE':
                            self.price_lot_size[symbol] = Decimal(
                                info_contract_filter['stepSize']).normalize()
        except BinanceAPIException as err:
            write_log(err.message, symbol=symbol)

    def start(self):
        list_symbols = []

        while True:
            list_trade_symbols = []
            list_open_orders = []
            minimal_quantity_deals = 0
            balance_usdt_account = Decimal(self.client.futures_account_balance()[1]['balance']) \
                .quantize(Decimal('0.01'))

            print(init_time() + ' Бот ожидает сделок')

            for symbol in self.info_futures:
                is_open_order = check_open_order(symbol['symbol'])
                data_open_order = is_open_order['orders']
                used_balance = is_open_order['balance']
                minimal_quantity_deals = math.floor(
                    ((balance_usdt_account * Decimal(PERCENT_PART_BALANCE)) - used_balance) /
                    Decimal(MIN_AMOUNT_ORDER))
                name_stream = str(symbol['symbol']).lower() + '@aggTrade'

                # Добавление незарегистрированных потоков
                if name_stream not in self.list_streams:
                    if symbol['contractType'] != 'CURRENT_QUARTER':
                        # Добавление фьючерса в массив фьючерсов
                        list_symbols.append(symbol['symbol'])

                        # Получение информации по фьючерсу
                        get_info_futures = Thread(target=self.get_info_futures, args=(symbol['symbol'],))
                        get_info_futures.start()
                        get_info_futures.join()

                        # Подписка на сокет фьючерса
                        start_socket_symbol = Thread(target=self.connect_socket(symbol['symbol']))
                        start_socket_symbol.start()
                        start_socket_symbol.join()

                if data_open_order is not None:
                    list_trade_symbols.append(symbol['symbol'])
                    list_open_orders.append(data_open_order)

            # Можно еще входить в сделки
            if minimal_quantity_deals > 0:
                for active_symbol in list_symbols:
                    start_trade_thread = Thread(target=self.start_trade_bot, args=(
                        {
                            'symbol': active_symbol,
                            'balance': balance_usdt_account,
                            'minimal_deals': minimal_quantity_deals,
                            'open_order': [order for order in list_open_orders if order['symbol'] == active_symbol]
                        },
                    ))
                    start_trade_thread.start()
                    start_trade_thread.join(timeout=0.2)

            # Баланс исчерпан, только следим за сделками
            if minimal_quantity_deals < 1:
                for trade_symbol in list_trade_symbols:
                    start_monitoring_thread = Thread(target=self.monitoring_point, args=(
                        {
                            'symbol': trade_symbol,
                            'open_order': [order for order in list_open_orders if order['symbol'] == trade_symbol]
                        },
                    ))
                    start_monitoring_thread.start()
                    start_monitoring_thread.join()

            time.sleep(1 * 60 * MAIN_TIMEOUT_BOT)

    def stop(self):
        print('Websocket stopped')
        self.twm.stop()

        try:
            reactor.stop()
        except error.ReactorNotRunning:
            print('Programm stopped')
