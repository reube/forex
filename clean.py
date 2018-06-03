import sys
import forex as f

import logging

LOGGER = logging.getLogger(__name__)
#
# WICK_MIN_ = [0.05, 0.1, 0.15, 0.2]
# WICK_MAX_ = [0.3]
# TOUCHES_ = [0, 1, 2]
# RECENCY_ = [9, 18]
# CANDLELEN_MIN_ = [0.001, 0.002]
# DELTA_ = [0.0002, 0.0004, 0.0006, 0.0008, 0.001]
# CLOSE_FAC_ = [2, 4, 6]
# REV_DELTA_ = [0.0015, 0.003, 0.0045, 0.006]

WICK_MIN_ = [0.2]
# WICK_MAX_ = [0.3]
TOUCHES_ = [1]
RECENCY_ = [9]
CANDLELEN_MIN_ = [0.0005]
DELTA_ = [0.002]
CLOSE_FAC_ = [6]
REV_DELTA_ = [0.0015]

SUCCESS_PC = 80.

class Count:
    def __init__(self, wicks, label, violation, reversal, swing):
        self.resetted = self.count = self.average = self.recency = self.clean = self.price = \
            self.item0 = self.item1 = self.last_idx = None
        self.reset()

        self.violation = violation
        self.reversal = reversal
        self.swing = swing
        self.label = label
        self.pips = 0.
        self.pipsover = 0
        self.wicks = wicks
        self.times = []

    def close_test(self, close):
        fail = 0
        delta = self.wicks.c_closefac * self.wicks.c_delta
        if self.count and self.violation(self.label, close, self.average, delta):
            fail = 1
            self.reset()
        LOGGER.debug("FAIL: {}".format(fail))
        return fail

    def reset(self):
        self.count = self.recency = self.clean = 0
        self.average = 0.
        self.resetted = True

    def update_recency(self):
        self.recency += 1

    def update_average(self, wicklen1, wicklen0, candlelen, endvalue, item, idx):
        LOGGER.debug((self.count, self.label))
        clean = 0
        self.resetted = False
        if self.recency > self.wicks.c_recency:
            self.reset()
        else:
            if self.count:
                test = self.average - self.wicks.c_delta < endvalue < self.average + self.wicks.c_delta
            else:
                test = candlelen > self.wicks.c_candle_min and wicklen1 / candlelen > self.wicks.c_wick_min # and wicklen0 / candlelen < self.wicks.c_wick_max
            if test:
                LOGGER.debug("Updating average, from: {}".format(self.average))
                if self.count:
                    self.average = (self.average * self.count + endvalue) / (self.count + 1)
                else:
                    self.average = endvalue
                    self.item0 = item
                    self.last_idx = idx + 1
                self.item1 = item
                print(Count._datetime(item))
                LOGGER.debug("Updating average, to: {}".format(self.average))
                if self.count and not self.clean:
                    self.clean = clean = 1
                self.count += 1
                self.recency = 0
        return clean

    def test_reversal(self, close):
        reversal = 0
        if self.count > self.wicks.c_touches and self.reversal(self.label, close, self.average, self.wicks.c_rev_delta):  # this will be recent by virtue of update_average running prior
            self.price = self.average
            self.reset()
            reversal = 1
        LOGGER.debug("REVERSAL: {}, average:{}".format(reversal, self.price))
        return reversal

    def test_swing(self, close3, close2, close1):
        swinging = self.swing(close3, close2, close1)
        LOGGER.debug((self.price, swinging))
        if self.price and swinging:
            pips = abs(close1 - self.price)
            self.pips += pips
            self.pipsover += 1
            if self.item0:
                self.times.append(
                    (Count._datetime(self.item0),
                     Count._datetime(self.item1),
                     float("{:.5f}".format(pips * 10000.)),
                     float("{:.5f}".format(self.price))))
                self.item0 = self.item1 = None
            self.price = 0

    @staticmethod
    def swing_low(close3, close2, close1):
        if close3 and close2:
            return close1 > close2 and close3 > close2
        else:
            return False

    @staticmethod
    def swing_high(close3, close2, close1):
        if close3 and close2:
            return close1 < close2 and close3 < close2
        else:
            return False

    @staticmethod
    def threshfun_high(label, close, average, delta):
        LOGGER.debug((label, close, average))
        return close > (average + delta)

    @staticmethod
    def threshfun_low(label, close, average, delta):
        LOGGER.debug((label, close, average))
        return close < (average - delta)

    @staticmethod
    def _datetime(item):
        time = f._time(item)
        return (time.year, time.month, time.day, time.hour, time.minute)


class Wicks:
    def __init__(self):
        self.wh = Count(self, "high", Count.threshfun_high, Count.threshfun_low, Count.swing_low)
        self.wl = Count(self, "low", Count.threshfun_low, Count.threshfun_high, Count.swing_high)
        self.c_closefac = self.c_delta = self.c_recency = self.c_wick_min = self.c_wick_max = self.c_touches = \
            self.c_candle_min = self.c_rev_delta = None

    def process(self, data):
        fails = 0
        success = 0
        cleans = 0
        bull = bullset = False
        item_idx = 0

        while True:
            resetted = self.wh.resetted and self.wl.resetted
            if resetted:
                if self.wh.last_idx:
                    item_idx = self.wh.last_idx
                elif self.wl.last_idx:
                    item_idx = self.wl.last_idx
                self.wh.last_idx = self.wl.last_idx = None

            if item_idx >= len(data):
                break  # from while

            item = data[item_idx]
            open1 = item.open
            high1 = item.high
            low1 = item.low
            close1 = item.close
            if item_idx > 0:
                close2 = data[item_idx - 1].close
                if item_idx > 1:
                    close3 = data[item_idx - 2].close
                else:
                    close3 = close2
            else:
                close2 = close3 = close1

            item_idx += 1

            LOGGER.debug((open1, high1, low1, close1, close2, close3))

            # wlb and whb values
            hl = high1 - low1
            if open1 > close1:
                wlb = close1
                whb = open1

            else:
                wlb = open1
                whb = close1

            wl_len = wlb - low1
            wh_len = high1 - whb

            swl = Count.swing_low(close3, close2, close1)
            swh = Count.swing_high(close3, close2, close1)

            if resetted and (swl or swh):
                bull = swl
                bullset = True

            LOGGER.debug((resetted, bull, bullset, swl, swh))

            if bull:
                fails += self.wh.close_test(close1)
                self.wh.update_recency()
                cleans += self.wh.update_average(wh_len, wl_len, hl, high1, item, item_idx)
                reversal = self.wh.test_reversal(close1)
                success += reversal
                bull = False if reversal else True
            elif bullset:
                fails += self.wl.close_test(close1)
                self.wl.update_recency()
                cleans += self.wl.update_average(wl_len, wh_len, hl, low1, item, item_idx)
                reversal = self.wh.test_reversal(close1)
                success += reversal
                bull = True if reversal else False

            self.wh.test_swing(close3, close2, close1)
            self.wl.test_swing(close3, close2, close1)

        times = []
        times.extend(self.wh.times)
        times.extend(self.wl.times)
        times = sorted(times)
        pips_over = self.wh.pipsover + self.wl.pipsover
        pips = self.wh.pips + self.wl.pips
        pips_ave = float("{pips_ave:.2f}".format(pips_ave=(pips/pips_over * 10000))) if pips_over else 0.
        success_pc = float("{success:.2f}".format(success=(success * 100. / (success + fails)))) if success or fails else 0.
        return success_pc, success, pips_ave, pips_over, cleans, times


if __name__ == '__main__':
    logging.basicConfig(
        filename="/tmp/clean.log",
        filemode='w',
        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s' +
               '%(message)s line:%(lineno)d',
        datefmt='%H:%M:%S',
        level=logging.DEBUG)

    years = [2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018]
    #
    # years = [2018]

    # day data
    datafile = sys.argv[1]
    data = f.filter(
        f.load_candles(datafile),
        f.filter_year,
        years)

    successes = []

    for wmin in WICK_MIN_:
        #for wmax in WICK_MAX_:
            for touches in TOUCHES_:
                for recency in RECENCY_:
                    for candle_min in CANDLELEN_MIN_:
                        for delta in DELTA_:
                            for closefac in CLOSE_FAC_:
                                for revdelta in REV_DELTA_:

                                    wicks = Wicks()
                                    wicks.c_rev_delta = revdelta
                                    wicks.c_closefac = closefac
                                    wicks.c_delta = delta
                                    wicks.c_candle_min = candle_min
                                    wicks.c_recency = recency
                                    wicks.c_touches = touches
                                    # wicks.c_wick_max = wmax
                                    wicks.c_wick_min = wmin

                                    config = (revdelta, closefac, delta, candle_min, recency, touches, wmin) # wmax, wmin)

                                    success_pc, success, pips_ave, pips_over, cleans, times = wicks.process(data)
                                    LOGGER.info((success_pc,
                                                 success,
                                                 pips_ave,
                                                 pips_over,
                                                 float("{pips:.2f}".format(pips=(pips_ave * pips_over))),
                                                 config))

                                    if success_pc > SUCCESS_PC:
                                        successes.append((times, (success_pc, success, pips_ave, pips_over, cleans, config)))
                                        LOGGER.info(successes)
    successes = sorted(successes, reverse=True)
    for t, s in successes:
        LOGGER.info((t, s))
        for t_ in t:
            print(t_)
        print(s)