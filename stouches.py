import sys
import forex as f

import logging
import math

LOGGER = logging.getLogger(__name__)

WICK_MIN_ = [0.1]  # 0.2 yields slightly better accuracy
TOUCHES_ = [2]
RECENCY_ = [9]
# CANDLELEN_MIN_ = [0.001]

# WICK_MIN_ = [0.3]
# TOUCHES_ = [3]
# RECENCY_ = [6]
# CANDLELEN_MIN_ = [0.001]


class Touches:
    def __init__(self):
        self.c_wick_min = self.c_candle_min = 0.
        self.c_recency = self.c_touches = 0
        self.c_ema = None

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

    def churn_buckets(self, buckets_, recencyfac):
        recency_ = recencyfac * self.c_recency
        buckets = {}
        keys = buckets_.keys()
        for key in keys:
            bucket_ = buckets_.get(key)
            next_ = []
            bucket = []
            limit = None
            for time in bucket_:
                if limit:
                    if time.timestamp() > limit:
                        if len(next_) >= self.c_touches:
                            bucket.append(next_)
                        next_ = [time]
                        limit = time.timestamp() + recency_
                    else:
                        next_.append(time)
                else:
                    next_ = [time]
                    limit = time.timestamp() + recency_

            if len(next_) > 1:
                bucket.append(next_)
            if bucket:
                buckets[key] = bucket
        return buckets

    @staticmethod
    def find_swing_price(swings, time0):
        for time, close2 in swings:
            if time.timestamp() > time0.timestamp():
                return close2
        return 0.

    @staticmethod
    def extract_pl(buckets, high, swings):
        keys = buckets.keys()
        winners_ = losers_ = 0
        winner_pips_ = loser_pips_ = 0.
        winner_touches_ = loser_touches_ = 0

        for price_ in keys:
            bucket_ = buckets.get(price_)
            for list in bucket_:
                time0 = list[0]
                price = Touches.find_swing_price(swings, time0)
                if price:
                    winner = high and price < price_ or not high and price > price_
                    price_diff = abs(price - price_)
                    if winner:
                        LOGGER.debug(('winner', time0, price_diff))
                        winners_ += 1
                        winner_pips_ += price_diff
                        winner_touches_ += len(list)
                    else:
                        LOGGER.debug(('loser', time0, price_diff))
                        losers_ += 1
                        loser_pips_ += price_diff
                        loser_touches_ += len(list)
        return winners_, losers_, winner_pips_, loser_pips_, winner_touches_, loser_touches_

    @staticmethod
    def _fl(value):
        return float("{:.2f}".format(value))

    def process(self, data, emas, emal):
        lows = {}
        highs = {}
        swings = []

        timestamp0 = data[0].time.timestamp()
        timestamp1 = data[1].time.timestamp()

        recencyfac = timestamp1 - timestamp0

        close3 = close2 = 0.

        time2 = None

        for item in data:
            open1 = item.open
            high1 = item.high
            low1 = item.low
            close1 = item.close
            time1 = item.time

            if not time2:
                time2 = time1
                continue

            time1_ = time1.year, time1.month, time1.day
            time2_ = time2.year, time2.month, time2.day

            bull1 = bear1 = False

            if self.c_ema:
                emas2 = emas.get(time2_)
                emas1 = emas.get(time1_)
                emal2 = emal.get(time2_)
                emal1 = emal.get(time1_)

                if not emas1 or not emas2 or not emal1 or not emal2:
                    continue

                emad2 = emas2 - emal2
                emad1 = emas1 - emal1

                bull2 = emad2 > 0.
                bear2 = emad2 < 0.

                bull1 = emad1 > 0.
                bear1 = emad1 < 0.

                crossover = bull2 and bear1 or bear2 and bull1

                if crossover:
                    continue

                contracting = emad1 < emad2

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

            hight = math.trunc(2000. * high1 + 0.5) / 2000.
            lowt = math.trunc(2000. * low1 + 0.5) / 2000.


            bullcond = (self.c_ema and bull1 and contracting) or not self.c_ema
            bearcond = (self.c_ema and bear1 and contracting) or not self.c_ema

            if hl > self.c_candle_min and wh_len / hl > self.c_wick_min and bullcond:
                bucket = highs.get(hight, [])
                bucket.append(time1)
                highs[hight] = bucket
            elif hl > self.c_candle_min and wl_len / hl > self.c_wick_min and bearcond:
                bucket = lows.get(lowt, [])
                bucket.append(time1)
                lows[lowt] = bucket

            swl = Touches.swing_low([close3, close2, close1])
            swh = Touches.swing_high([close3, close2, close1])

            if swl:
                swings.append((time1, close2))
            elif swh:
                swings.append((time1, close2))

            close3 = close2
            close2 = close1

        lows = self.churn_buckets(lows, recencyfac)
        highs = self.churn_buckets(highs, recencyfac)

        winners_l, losers_l, winner_pips_l, loser_pips_l, winner_touches_l, loser_touches_l = \
            Touches.extract_pl(lows, False, swings)

        winners_h, losers_h, winner_pips_h, loser_pips_h, winner_touches_h, loser_touches_h = \
            Touches.extract_pl(highs, True, swings)

        winners = winners_h + winners_l
        losers = losers_h + losers_l
        winner_pips = winner_pips_h + winner_pips_l
        loser_pips = loser_pips_h + loser_pips_l
        winner_touches = winner_touches_h + winner_touches_l
        loser_touches = loser_touches_h + loser_touches_l

        winners_pc = Touches._fl(winners * 100 / (winners + losers)) if winners or losers else 0.

        return winners_pc, winners, (losers, Touches._fl(winner_pips), Touches._fl(loser_pips), winner_touches, loser_touches)


    @staticmethod
    def ema(data):
        emas = {}
        emal = {}
        for item in data:
            time_ = item.time
            time = time_.year, time_.month, time_.day
            emas[time] = item.emas
            emal[time] = item.emal

        return emas, emal


if __name__ == '__main__':
    for period in ['15_M', '1_Hour', '1_D']:
        for pair in f.PAIRS:
            datafile_p = "/home/andrew/forex/all/{pair}_Candlestick_{period}_BID_01.05.2013-01.06.2018.csv".format(
                period=period, pair=pair)
            # datafile_d = "/home/andrew/forex/all/{pair}_Candlestick_1_D_BID_01.05.2013-01.06.2018.csv".format(
            #     pair=pair)
            print(pair, period)

            logging.basicConfig(
                filename="/tmp/{pair}_{period}_touches.log".format(
                    period=period, pair=pair),
                filemode='w',
                format='%(asctime)s,%(msecs)d %(name)s %(levelname)s' +
                       '%(message)s line:%(lineno)d',
                datefmt='%H:%M:%S',
                level=logging.DEBUG)

            # years = [2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018]
            #
            # years = [2018]

            years = [2013, 2014, 2015, 2016, 2017, 2018]

            # data
            data = f.filter(
                f.load_candles(datafile_p),
                f.filter_year,
                years)

            # # day data
            # if period == '1_D':
            #     data_d = data
            # else:
            #     data_d = f.filter(
            #         f.load_candles(datafile_d),
            #         f.filter_year,
            #         years)
            #     emas, emal = Touches.ema(data_d)
            emas = emal = None

            winners_max = 0

            runs = []
            for wick_min in WICK_MIN_:
                for recency in RECENCY_:
                    for num_touches in TOUCHES_:
                        # for candle_min in CANDLELEN_MIN_:
                        for ema_ in [False]:
                            candle_min = 0.
                            touches = Touches()
                            touches.c_recency = recency
                            touches.c_wick_min = wick_min
                            touches.c_touches = num_touches
                            touches.c_candle_min = candle_min
                            touches.c_ema = ema_

                            config = (wick_min, recency, num_touches, candle_min, ema_)
                            LOGGER.debug(config)
                            pc, winners, info = touches.process(data, emas, emal)
                            runs.append((pc, (winners, info, config)))
                            if winners > winners_max:
                                winners_max = winners

            winners_max /= 2

            runs = sorted(runs, reverse=True)
            for r in runs:
                pc, (winners, info, config) = r
                if winners > winners_max:
                    print(r)
                LOGGER.debug(r)
