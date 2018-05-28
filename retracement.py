import sys
import forex as f
from enum import Enum

BLOCK_THRESH = 0.7
FIBS = [0.236, 0.382, 0.5, 0.618, 0.705, 0.786, 1]


class Retracement(Enum):
    NOTHING = 0
    COUNTER = 1
    FORWARD1 = 2
    RETRACING = 3
    FORWARD2 = 4


def retracement(trend, data_, dates):
    buckets = {}
    open = high = low = close = None
    state = Retracement.NOTHING
    swing_f = None
    swing_r = None

    for item in data_:
        if state == Retracement.FORWARD2:
            complete = (trend == f.BearBull.BEARISH and item.close < swing_f) or \
                        (trend == f.BearBull.BULLISH and item.close > swing_f)

            violated = (trend == f.BearBull.BEARISH and item.close > close) or \
                        (trend == f.BearBull.BULLISH and item.close < close)

            if complete or violated:
                fib = abs(swing_r - swing_f) / abs(close - swing_f)
                for level in FIBS:
                    if fib < level:
                        level_s = str(level)
                        c, v = buckets.get(level_s, (0, 0))
                        if complete:
                            c += 1
                        else:
                            v += 1
                        buckets[level_s] = c, v
                        break
                state = Retracement.NOTHING

        elif state == Retracement.RETRACING:
            complete = (trend == f.BearBull.BEARISH and item.close < swing_r) or \
                       (trend == f.BearBull.BULLISH and item.close > swing_r)

            if complete:
                state = Retracement.FORWARD2
            else:
                swing_r = item.close

        elif state == Retracement.FORWARD1:
            complete = (trend == f.BearBull.BEARISH and item.close > swing_f) or \
                       (trend == f.BearBull.BULLISH and item.close < swing_f)

            if complete:
                state = Retracement.RETRACING
                swing_r = item.close
            else:
                swing_f = item.close

        elif state == Retracement.COUNTER:
            complete = (trend == f.BearBull.BEARISH and item.close < close) or \
                       (trend == f.BearBull.BULLISH and item.close > close)

            if complete:
                oc = abs(open - close)
                hl = high - low

                if oc / hl > BLOCK_THRESH:
                    state = Retracement.FORWARD1
                    swing_f = item.close
                else:
                    state = Retracement.NOTHING

            else:
                close = item.close
                if item.high > high:
                    high = item.high
                if item.low < low:
                    low = item.low

        else:
            countertrend = (item.year, item.month, item.day) in dates and \
                           ((f.BearBull.BEARISH and item.close >= item.open) or
                            (f.BearBull.BULLISH and item.close <= item.open))

            if countertrend:
                open = item.open
                close = item.close
                high = item.high
                low = item.low
                state = Retracement.FORWARD1
    return buckets


def weekday(data):
    return f.filter(data, f.filter_weekday)


def dates(data):
    return [(item.time.year, item.time.month, item.time.day) for item in data]


if __name__ == '__main__':
    # years = [2016, 2017, 2018]
    years = [2018]

    # 15m data
    datafile_15m = sys.argv[1]
    data_15m = f.filter(
        f.load_candles(datafile_15m),
        f.filter_year,
        years)

    # day data
    datafile_d = sys.argv[2]
    data_d = weekday(
        f.filter(
            f.load_candles(datafile_d),
            f.filter_year,
            years))

    # profile bearish days
    beardates = dates(f.filter(data_d, f.filter_bearish, False)) # , False)
    bearbuckets = retracement(f.BearBull.BEARISH, data_15m, beardates)
    print(bearbuckets)

    # profile bullish days
    bulldates = dates(f.filter(data_d, f.filter_bullish, False)) # , False)
    bullbuckets = retracement(f.BearBull.BULLISH, data_15m, bulldates)
    print(bullbuckets)
