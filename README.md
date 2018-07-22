# S&P100 replication algo for Alpaca API

This is an algorithm that manage your portfolio by simply replication S&P100 index by
buying the underlying stocks.

## Setup

```
$ pipenv install
$ pipenv shell
$ python main.py
```

This also works in Heroku.

## Customization

### Use of previous close prices
The code currently uses the last close price from IEX to calculate the target portfolio, and place
market orders at the market open, but you can change it so that it uses the current prices, and/or
runs at the market close time to be more accurate.  Though, it should not diverge much unless some
big shares move 10+% overnight, which would also be corrected next day.

### Rebalance timing
This algo rebalances everyday. You can change it to more frequently, or less.  Less frequency should
be fine using IEX daily data, but if you are going intraday rebalancing, you should use Alpaca/Polygon
intraday data.

### Other indexes
If you follow the code, you can easily change this for S&P500 or DIJA or whatever you like, as
far as there is a list on the web.
