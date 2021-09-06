from core.settings_server import FILES_BOT, STRATEGY

from datetime import datetime
from decimal import Decimal
from threading import Lock
import os
import csv


# Проверка открытых ордеров
def check_open_order(symbol):
    file = FILES_BOT['orders']
    lock = Lock()

    lock.acquire()
    try:
        with open(file, 'r') as fin:
            orders = []
            used_balance = Decimal()
            cin = csv.DictReader(fin)

            for row in cin:
                if row['symbol'] == symbol and row['active-order'] == 'True':
                    orders = row
                used_balance += Decimal(row['price-lot'])

            if len(orders) > 0:
                return {
                    'orders': orders,
                    'balance': used_balance
                }
            else:
                return {
                    'orders': None,
                    'balance': used_balance
                }
    except FileNotFoundError:
        return {
            'orders': None,
            'balance': Decimal()
        }
    finally:
        lock.release()


# Сохранение сделок в файл
def save_csv(order, stoploss, takeprofit, commission, active):
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    file = FILES_BOT['orders']
    lock = Lock()

    header_order = [
        'strategy',
        'date',
        'symbol',
        'order-id',
        'client-order-id',
        'price',
        'stop-loss',
        'takeprofit',
        'status-order',
        'type-order',
        'lot',
        'price-lot',
        'commission',
        'active-order'
    ]
    data_order = {
        'strategy': STRATEGY,
        'date': date,
        'symbol': order['symbol'],
        'order-id': order['orderId'],
        'client-order-id': order['clientOrderId'],
        'price': order['avgPrice'],
        'stop-loss': stoploss,
        'takeprofit': takeprofit,
        'status-order': order['status'],
        'type-order': order['side'],
        'lot': order['cumQty'],
        'price-lot': order['cumQuote'],
        'commission': commission,
        'active-order': active
    }

    if os.path.exists(file):
        lock.acquire()
        try:
            with open(file, 'at', newline='', encoding='UTF-8') as fout:
                csv_writer = csv.DictWriter(fout, header_order)
                csv_writer.writerow(data_order)
        finally:
            lock.release()
    else:
        lock.acquire()
        try:
            with open(file, 'wt', newline='', encoding='UTF-8') as fout:
                csv_writer = csv.DictWriter(fout, header_order)
                csv_writer.writeheader()
                csv_writer.writerow(data_order)
        finally:
            lock.release()


# Сохранение статистики торговли бота
def save_archive_order(symbol, order_id, type_order, entry_price, exit_price, entry_lot_price, exit_lot_price,
                       commission, price_profit, lot):
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    file = FILES_BOT['archive_orders']
    lock = Lock()

    header_order = [
        'strategy',
        'date',
        'symbol',
        'order-id',
        'entry price',
        'exit price',
        'entry lot price',
        'exit lot price',
        'type-order',
        'lot',
        'commission order',
        'profit'
    ]
    data_order = {
        'strategy': STRATEGY,
        'date': date,
        'symbol': symbol,
        'order-id': order_id,
        'entry price': entry_price,
        'exit price': exit_price,
        'entry lot price': entry_lot_price,
        'exit lot price': exit_lot_price,
        'type-order': type_order,
        'lot': lot,
        'commission order': commission,
        'profit': price_profit,
    }

    if os.path.exists(file):
        lock.acquire()
        try:
            with open(file, 'at', newline='', encoding='UTF-8') as fout:
                csv_writer = csv.DictWriter(fout, header_order)
                csv_writer.writerow(data_order)
        finally:
            lock.release()
    else:
        lock.acquire()
        try:
            with open(file, 'wt', newline='', encoding='UTF-8') as fout:
                csv_writer = csv.DictWriter(fout, header_order)
                csv_writer.writeheader()
                csv_writer.writerow(data_order)
        finally:
            lock.release()


# Удаление сделок из файла
def delete_order_csv(id_mark):
    file = FILES_BOT['orders']
    update_list = []
    lock = Lock()

    lock.acquire()
    try:
        with open(file, 'rt') as fin:
            csv_reader = csv.reader(fin)

            for data in csv_reader:
                if id_mark not in data:
                    update_list.append(data)

        with open(file, 'wt', newline='', encoding='UTF-8') as fout:
            csv_writer = csv.writer(fout)

            for data in update_list:
                csv_writer.writerow(data)
    finally:
        lock.release()