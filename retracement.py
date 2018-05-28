import sys
import forex as f
import logging
from enum import Enum

LOGGER = logging.getLogger(__name__)

BODY_THRESH = 0.6
FIBS = [0.236, 0.382, 0.5, 0.618, 0.705, 0.786, 1]
PIP_THRESH = 30
MIN_PRICE_MEMORY = 20
TOUCH_THRESH = 0.0001


class Retracement(Enum):
    NOTHING = 0
    FORWARD1 = 1
    RETRACING = 2
    FORWARD2 = 3


def retracement(trend, data_, dates):
    print(trend)

    buckets = {}
    thresh = close = time = None
    state = Retracement.NOTHING
    swing_f = None
    swing_r = None

    price_memory = []

    item_idx = 0
    last_idx = 0

    while True:
        if state == Retracement.NOTHING and last_idx:
            item_idx = last_idx
            last_idx = 0

        if item_idx >= len(data_):
            break # from while

        item = data_[item_idx]
        item_idx += 1

        price_memory.append(item)

        if len(price_memory) > MIN_PRICE_MEMORY:
            price_memory = price_memory[1:]

        if state == Retracement.FORWARD2:
            complete = (trend == f.BearBull.BEARISH and item.close < swing_f) or \
                        (trend == f.BearBull.BULLISH and item.close > swing_f)

            violated = (trend == f.BearBull.BEARISH and item.close > close) or \
                        (trend == f.BearBull.BULLISH and item.close < close)

            if complete or violated:
                LOGGER.debug((swing_r, swing_f, close))

                fib = abs(swing_r - swing_f) / abs(close - swing_f)
                for level in FIBS:
                    if fib < level:
                        level_s = str(level)
                        c, v = buckets.get(level_s, ([], []))
                        if complete:
                            LOGGER.debug(("COMPLETE", abs(close - swing_f) * 10000))
                            c.append(time)
                        else:
                            LOGGER.debug(("VIOLATED", abs(close - swing_f) * 10000))
                            v.append(time)
                        buckets[level_s] = c, v
                        break

                LOGGER.debug("Done with order block!")
                state = Retracement.NOTHING

            else:
                LOGGER.debug("Still moving forward 2")

        elif state == Retracement.RETRACING:
            violated = (trend == f.BearBull.BEARISH and item.close > close) or \
                       (trend == f.BearBull.BULLISH and item.close < close)

            complete = (trend == f.BearBull.BEARISH and item.close < swing_r) or \
                       (trend == f.BearBull.BULLISH and item.close > swing_r)

            if violated:
                level_s = "1.0+"
                v = buckets.get(level_s, [])
                v.append(time)
                buckets[level_s] = v

                LOGGER.debug(("VIOLATED", abs(close - swing_f) * 10000))

                state = Retracement.NOTHING

                LOGGER.debug("Retracement violation!")
            elif complete:
                state = Retracement.FORWARD2
                LOGGER.debug("Starting moving forward 2 from swing_r: {swingr:.4f}".format(swingr=swing_r))
            else:
                swing_r = item.close
                LOGGER.debug("Still retracing")

        elif state == Retracement.FORWARD1:
            complete = (trend == f.BearBull.BEARISH and item.close > swing_f) or \
                       (trend == f.BearBull.BULLISH and item.close < swing_f)

            trashed = (trend == f.BearBull.BEARISH and item.close > thresh) or \
                       (trend == f.BearBull.BULLISH and item.close < thresh)

            LOGGER.debug(complete)
            LOGGER.debug(trend)
            LOGGER.debug((item.close, swing_f))

            if complete:
                forward_pips = abs(close - swing_f) * 10000
                LOGGER.debug(forward_pips)
                if forward_pips > PIP_THRESH:
                    state = Retracement.RETRACING
                    swing_r = item.close
                    LOGGER.debug("Starting retracement from swing_f: {swingf:.4f}".format(swingf=swing_f))
                elif trashed:
                    state = Retracement.NOTHING
            else:
                swing_f = item.close
                LOGGER.debug("Still moving forward 1")
                LOGGER.debug(state)

        elif len(price_memory) < MIN_PRICE_MEMORY:
            continue

        else:
            countertrend =  (trend == f.BearBull.BEARISH and item.close > item.open) or \
                            (trend == f.BearBull.BULLISH and item.close < item.open)

            LOGGER.debug((item.time, trend, countertrend, item.open, item.high, item.low, item.close))

            if item.high == item.low or not (item.time.year, item.time.month, item.time.day) in dates:
                continue

            if countertrend:
                oc = abs(item.open - item.close)
                hl = item.high - item.low
                LOGGER.debug((oc, hl))

                body = oc / hl > BODY_THRESH

                touches_ = [item.high for item in price_memory] if trend == f.BearBull.BEARISH else \
                    [item.low for item in price_memory]
                touch = item.high if trend == f.BearBull.BEARISH else item.low
                touches = [t for t in touches_ if abs(t - touch) <= TOUCH_THRESH]

                LOGGER.debug((body, touches_, touch, touches))

                if body and touches:
                    close = item.close
                    time = item.time
                    swing_f = item.close
                    thresh = item.low if trend == f.BearBull.BEARISH else item.high
                    state = Retracement.FORWARD1
                    last_idx = item_idx + 1

                    LOGGER.debug("Counter-trend order block: {time}: {open}, {high}, {low}, {close}".format(
                        open=item.open, close=item.close, high=item.high, low=item.low, time=time))

    return buckets


def weekday(data):
    return f.filter(data, f.filter_weekday)


def dates(data):
    return [(item.time.year, item.time.month, item.time.day) for item in data]


def get_sample_sizes(buckets, complete):
    samplesizes = {}
    for key in buckets.keys():
        entry = buckets[key]
        if isinstance(entry, tuple):
            if complete:
                entry, _ = entry
            else:
                _, entry = entry
        elif complete:
            continue

        for item in entry:
            dayofweek = f.dayofweek(item)
            samplesizes[dayofweek] = samplesizes.get(dayofweek, 0) + 1
    return samplesizes


def print_buckets_(buckets, complete):
    samplesizes = get_sample_sizes(buckets, complete)
    len_buckets = 0
    for key in buckets.keys():
        entry = buckets[key]
        if isinstance(entry, tuple):
            if complete:
                entry, _ = entry
            else:
                _, entry = entry
        elif complete:
            continue

        if not entry:
            continue

        len_buckets += len(entry)
        print("****  fib: {key} ****".format(key=key))
        f.print_complete_summary(entry, [f.Summaries.DAYOFWEEK], samplesizes)
        for item in entry:
            print("---- {}".format(item))
        print()

    return len_buckets


def print_buckets(buckets):
    print("COMPLETED: ")
    len_compl = print_buckets_(buckets, True)
    print()

    print("VIOLATIONS: ")
    len_viol = print_buckets_(buckets, False)
    print()

    len_total = len_compl + len_viol
    if len_total:
        pc = len_compl * 100. / len_total
        print("--- Complete: {len_compl}/{len_total}, {pc:.2f}".format(
            len_compl=len_compl, len_total=len_total, pc=pc))
    else:
        print("--- Complete: 0/0")
    print()


if __name__ == '__main__':
    logging.basicConfig(
        filename="/tmp/retracement.log",
        filemode='w',
        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s' +
               '%(message)s line:%(lineno)d',
        datefmt='%H:%M:%S',
        level=logging.DEBUG)

    # years = [2016, 2017, 2018]
    years = [2018]

    # ltf data
    datafile_ltf = sys.argv[1]
    data_ltf = f.filter(
        f.load_candles(datafile_ltf),
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
    beardates = dates(f.filter(data_d, f.filter_bearish, True)) # , False)
    bearbuckets = retracement(f.BearBull.BEARISH, data_ltf, beardates)
    print_buckets(bearbuckets)

    # profile bullish days
    bulldates = dates(f.filter(data_d, f.filter_bullish, True)) # , False)
    bullbuckets = retracement(f.BearBull.BULLISH, data_ltf, bulldates)
    print_buckets(bullbuckets)
