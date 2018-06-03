import sys
import forex as f

import logging
from enum import Enum


class Touches(Enum):
    NOTHING = 0
    FORMING = 1
    REVERSAL = 2


LOGGER = logging.getLogger(__name__)

WICK_MIN_ = [0.2]
TOUCHES_ = [2]
RECENCY_ = [12]
CANDLELEN_MIN_ = [0.0015]
DELTA_ = [0.0006]
REV_DELTA_ = [0.003] # when counted as a success

# WICK_MIN_ = [0.2]
# # WICK_MAX_ = [0.3]
# TOUCHES_ = [0]
# RECENCY_ = [9]
# CANDLELEN_MIN_ = [0.0005]
# DELTA_ = [0.002]
# CLOSE_FAC_ = [6]
# REV_DELTA_ = [0.0015]

SUCCESS_PC = 50.


class Count:
    def __init__(self, wicks, label, violation, reversal, swing):
        self.count = self.average = self.recency = self.item0 = self.item1 = self.state = None
        self.reset()

        self.violation = violation
        self.reversal = reversal
        self.swing = swing
        self.label = label
        self.pips = 0.
        self.last_idx = self.fails = self.success = self.pipsover = 0
        self.wicks = wicks
        self.times = []

    def reset(self):
        self.count = self.recency = self.clean = 0
        self.average = 0.
        self.state = Touches.NOTHING

    def update(self, wicklen, correctside, correctbound, candlelen, endvalue, item, idx, closes):
        LOGGER.debug((wicklen, correctside, correctbound, candlelen, endvalue, item, idx, closes))
        LOGGER.debug((self.state, self.label, self.recency, self.wicks.c_recency))

        # If we have already started forming a possible set-up, but have not recently retouched or entered
        # REVERSAL, then we abandon the set-up.  It is not a failure as we never followed through.
        #
        if self.state == Touches.FORMING and self.recency > self.wicks.c_recency:
            LOGGER.debug("RECENCY FAIL")
            self.reset()
            return


        # If we are in reversal, and hit a swing point then we declare our position.  This counts as a success
        # even if only minor.
        #
        if self.state == Touches.REVERSAL:
            swinging = self.swing(closes)
            LOGGER.debug((self.average, swinging))
            if swinging:
                pips = abs(closes[-1] - self.average)
                self.pips += pips
                self.pipsover += 1
                self.times.append(
                    (Count._datetime(self.item0),
                     Count._datetime(self.item1),
                     float("{:.5f}".format(pips * 10000.)),
                     float("{:.5f}".format(self.average))))
                self.item0 = self.item1 = None
                self.success +=1
                self.reset()


        # For the first candle, in NOTHING, we check the length of the candle and the wick proportion
        # Future candles can have their wick breach by delta.
        #
        wick_test = (self.state == Touches.NOTHING and candlelen > self.wicks.c_candle_min and wicklen / candlelen > self.wicks.c_wick_min) or \
                    (self.state == Touches.FORMING and correctside)
        touching = self.state == Touches.FORMING and correctbound and wicklen / candlelen > self.wicks.c_wick_min
        LOGGER.debug((self.state, candlelen, correctside, wick_test, touching, self.last_idx, self.recency))
        LOGGER.debug((wick_test, touching, self.last_idx))

        if wick_test:
            LOGGER.debug("Possible updating average, from: {}".format(self.average))
            if self.state == Touches.FORMING:
                if self.reversal(self.label, closes[-1], self.average, self.wicks.c_rev_delta):
                    LOGGER.debug("Possible Reversal")
                    if self.count >= self.wicks.c_touches:
                        LOGGER.debug("Reversal Confirmed")
                        self.state = Touches.REVERSAL
                    else:
                        self.reset()
                elif self.value_above(endvalue) and self.value_below(endvalue):
                    LOGGER.debug("Updating average, to: {}".format(self.average))
                    self.average = (self.average * self.count + endvalue) / (self.count + 1)
            else:
                self.last_idx = idx + 1
                self.state = Touches.FORMING
                self.average = endvalue
                self.item0 = item
            self.item1 = item

            if touching:
                self.count += 1
                self.recency = 0
            else:
                self.recency += 1

        elif self.state == Touches.REVERSAL:
            self.reset()
            self.fails += 1
        else:
            self.reset()

    def value_below(self, value):
        LOGGER.debug((self.label, value, self.average, self.wicks.c_delta))
        return value < self.average + self.wicks.c_delta

    def value_above(self, value):
        LOGGER.debug((self.label, value, self.average, self.wicks.c_delta))
        return self.average - self.wicks.c_delta < value


    @staticmethod
    def swing_low(closes):
        [close3, close2, close1] = closes
        if close3 and close2:
            return close1 > close2 and close3 > close2
        else:
            return False

    @staticmethod
    def swing_high(closes):
        [close3, close2, close1] = closes
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
        self.c_delta = self.c_recency = self.c_wick_min = self.c_touches = self.c_candle_min = self.c_rev_delta = None

    def process(self, data):
        bull = bullset = False
        item_idx = 0

        while True:
            LOGGER.debug((self.wh.state, self.wl.state, self.wh.last_idx, self.wl.last_idx))
            nothing = self.wh.state == Touches.NOTHING and \
                      self.wl.state == Touches.NOTHING
            LOGGER.debug(nothing)
            if nothing or item_idx >= len(data):
                if self.wh.last_idx:
                    item_idx = self.wh.last_idx
                elif self.wl.last_idx:
                    item_idx = self.wl.last_idx
                self.wh.last_idx = self.wl.last_idx = 0

            LOGGER.debug(item_idx)

            if item_idx >= len(data):   # still the case?
                break  # from while

            LOGGER.debug(item_idx)

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
            if not hl:
                continue  # while

            if open1 > close1:
                wlb = close1
                whb = open1

            else:
                wlb = open1
                whb = close1

            wl_len = wlb - low1
            wh_len = high1 - whb

            swl = Count.swing_low([close3, close2, close1])
            swh = Count.swing_high([close3, close2, close1])

            if nothing and (swl or swh):
                bull = swl
                bullset = True

            LOGGER.debug((bull, bullset, swl, swh))

            if bull:
                self.wh.update(
                    wh_len, self.wh.value_below(wlb), self.wh.value_above(high1),
                    hl, high1, item, item_idx, [close3, close2, close1])
            elif bullset:
                self.wl.update(
                    wl_len, self.wh.value_above(whb), self.wh.value_below(low1),
                    hl, low1, item, item_idx, [close3, close2, close1])

        times_ = []
        times_.extend(self.wh.times)
        times_.extend(self.wl.times)
        times_ = sorted(times_)

        success_ = self.wh.success + self.wl.success
        fails_ = self.wh.fails + self.wl.fails

        pips_over_ = self.wh.pipsover + self.wl.pipsover
        pips_ = self.wh.pips + self.wl.pips
        pips_ave_ = float("{pips_ave:.2f}".format(pips_ave=(pips_/pips_over_ * 10000))) if pips_over_ else 0.
        success_pc_ = float("{success:.2f}".format(success=(success_ * 100. / (success_ + fails_)))) if success_ or fails_ else 0.
        return success_pc_, success_, pips_ave_, pips_over_, times_


if __name__ == '__main__':
    logging.basicConfig(
        filename="/tmp/touches.log",
        filemode='w',
        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s' +
               '%(message)s line:%(lineno)d',
        datefmt='%H:%M:%S',
        level=logging.INFO)

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
        for touches in TOUCHES_:
            for recency in RECENCY_:
                for candle_min in CANDLELEN_MIN_:
                    for delta in DELTA_:
                        for revdelta in REV_DELTA_:

                            wicks = Wicks()
                            wicks.c_rev_delta = revdelta
                            wicks.c_delta = delta
                            wicks.c_candle_min = candle_min
                            wicks.c_recency = recency
                            wicks.c_touches = touches
                            wicks.c_wick_min = wmin

                            config = (revdelta, delta, candle_min, recency, touches, wmin)

                            success_pc, success, pips_ave, pips_over, times = wicks.process(data)
                            LOGGER.info((success_pc,
                                         success,
                                         pips_ave,
                                         pips_over,
                                         float("{pips:.2f}".format(pips=(pips_ave * pips_over))),
                                         config))

                            if success_pc > SUCCESS_PC:
                                successes.append((success_pc, (times, (success, pips_ave, pips_over, config))))
                                LOGGER.info(successes)
    successes = sorted(successes, reverse=True)
    for p, (t, s) in successes:
        LOGGER.info((p, t, s))
        # for t_ in t:
        #     print(t_)
        print(p, s)