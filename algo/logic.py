import alpaca_trade_api as tradeapi

from bs4 import BeautifulSoup
import iexfinance as iex
import logging
import pandas as pd
import requests
import time


logger = logging.getLogger(__name__)
api = tradeapi.REST()


def _fake_submit(*args, **kwargs):
    print(f'fake_submit({args}, {kwargs}))')

# api.submit_order = _fake_submit


def get_sp100():
    '''Scrape wikipedia and returns the list of SP100 symbols'''

    url = 'https://en.wikipedia.org/wiki/S%26P_100'
    resp = requests.get(url)
    resp.raise_for_status()
    content = resp.content
    soup = BeautifulSoup(content, 'html.parser')

    return [
        row.select('td')[0].text.strip()
        for row in soup.select('table')[2].select('tbody tr')[1:]
    ]


def get_stockdata(symbols):
    '''Get stock data (key stats and previous) from IEX.
    Just deal with IEX's 99 stocks limit per request.
    '''
    partlen = 99
    result = {}
    for i in range(0, len(symbols), partlen):
        part = symbols[i:i + partlen]
        kstats = iex.Stock(part).get_key_stats()
        previous = iex.Stock(part).get_previous()
        for symbol in part:
            kstats[symbol].update(previous[symbol])
        result.update(kstats)

    return pd.DataFrame(result)


def calc_target(api, stkdata):
    '''Returns a DataFrame with:
    - target_qty: calculated shares to be held
    - current_qty: current holding shares
    - last_close: last closing price
    - weight: portfolio weight based on the market cap
    - marketcap: market cap from IEX API

    Note current_qty may include symbols outside of sp100 list,
    which should be sold. These symbols will have 0 in marketcap
    in this DataFrame.
    '''
    weights = (stkdata.T['marketcap'] / stkdata.T['marketcap'].sum())
    pval = float(api.get_account().portfolio_value)

    target_qty = (pval * weights) // stkdata.T['close']
    current_qty = pd.Series({
        p.symbol: int(p.qty)
        for p in api.list_positions()})

    return pd.DataFrame({
        'target_qty': target_qty,
        'current_qty': current_qty,
        'last_close': stkdata.T['close'],
        'weight': weights,
        'marketcap': stkdata.T['marketcap'],
    }).fillna(0)


def submit_and_wait(orders, side):
    '''Submit orders and wait all of them go through.'''
    for symbol, qty in orders.items():
        try:
            api.submit_order(
                symbol=symbol,
                side=side,
                qty=qty,
                type='market',
                time_in_force='day',
            )
        except Exception as e:
            logger.error(e)
    while True:
        orders = api.list_orders()
        if len(orders) == 0:
            break
        time.sleep(1)


def trade(df):
    '''Execute trade based on the target portfolio vs current'''
    diff = df['target_qty'] - df['current_qty']

    # sell first, to have enough buying power back
    sells = {symbol: -int(qty) for symbol, qty in diff.items() if qty < 0}
    submit_and_wait(sells, 'sell')

    buys = {symbol: int(qty) for symbol, qty in diff.items() if qty > 0}
    submit_and_wait(buys, 'buy')


def rebalance():
    '''Get up-to-date symbol list and calculate optimal portfolio, then
    trade accordingly.'''
    symbols = get_sp100()
    stkdata = get_stockdata(symbols)
    df = calc_target(api, stkdata)
    trade(df)


def main():
    '''The main loop. Perform rebalance() in the morning of
    market open day.
    '''
    open_dates = set([
        c._raw['date'] for c in api.get_calendar()])
    done = None
    while True:
        clock = api.get_clock()
        today = clock.timestamp.strftime('%Y-%m-%d')

        if today in open_dates and done != today:
            if clock.timestamp.time() >= pd.Timestamp('09:30').time():
                rebalance()
                done = today
        time.sleep(30)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
