import sys
import forex as f

import logging

LOGGER = logging.getLogger(__name__)

WICK_MIN = 0.1
DELTA = 0.005


class Wicks:
    def __init__(self):
        self.reset()

    def store_result(self, buckets):
        bucket = buckets.get(str(self.wick_crosses), [])
        bucket.append(self.wick_item)
        buckets[str(self.wick_crosses)] = bucket
        self.reset()

    def reset(self):
        self.wick_high = self.wick_low = 0.
        self.wick_item = None
        self.wick_crosses = 0

    def process(self, data):
        wick_fails = 0
        wick_success = 0
        success = {}
        fails = {}

        for item in data:
            open = item.open
            high = item.high
            low = item.low
            close = item.close

            # wlb and whb values
            hl = high - low
            if open > close:
                wlb = close
                whb = open

            else:
                wlb = open
                whb = close

            wl = wlb - low
            wh = high - whb

            if self.wick_high and close > self.wick_high or self.wick_low and close < self.wick_low:
                self.store_result(fails)  # no reversal
                wick_fails += 1
                continue

            # we have a higher wick, and the wick proportinally is greater than WICK_MIN,
            # the existing wick high if present is still greater than this candle's body with the new high being
            # greater still, in which case it takes the new wick high
            #
            high_cond = wh > wl and wh/hl > WICK_MIN and \
                        ((self.wick_high and whb < self.wick_high < high) or not self.wick_high)
            low_cond = wl > wh and wl/hl > WICK_MIN and \
                        ((self.wick_low and low < self.wick_low < wlb) or not self.wick_low)

            if high_cond:
                self.wick_high = high
                if self.wick_low:
                    self.wick_low = 0.
                    self.wick_crosses = 1
                else:
                    self.wick_crosses += 1
                self.wick_item = item
            elif low_cond:
                self.wick_low = low
                if self.wick_high:
                    self.wick_high = 0.
                    self.wick_crosses = 1
                else:
                    self.wick_crosses += 1
                self.wick_item = item
            elif self.wick_high and high < self.wick_high - DELTA or self.wick_low and low + DELTA:
                self.store_result(success)
                wick_success += 1

        return (wick_success, success), (wick_fails, fails)


if __name__ == '__main__':
    logging.basicConfig(
        filename="/tmp/rangebreaks.log",
        filemode='w',
        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s' +
               '%(message)s line:%(lineno)d',
        datefmt='%H:%M:%S',
        level=logging.DEBUG)

    # years = [2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018]
    years = [2018]

    # day data
    datafile = sys.argv[1]
    data = f.filter(
        f.load_candles(datafile),
        f.filter_year,
        years)

    (wick_success, success), (wick_fails, fails) = Wicks().process(data)
    print(wick_success)
    print(wick_fails)
