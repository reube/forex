import sys
import forex as f


def get_trend(trend_, compress):
    trend = f.BearBull.COMPRESS
    trend_compressbear = compress and trend_ == f.BearBull.COMPRESSBEAR
    trend_compressbull = compress and trend_ == f.BearBull.COMPRESSBULL

    if trend_ == f.BearBull.BEARISH or trend_compressbear:
        trend = f.BearBull.BEARISH
    elif trend_ == f.BearBull.BULLISH or trend_compressbull:
        trend = f.BearBull.BULLISH
    return trend


def week_highlow(data, notwed=True, compress=False):
    bear_cnt = 0
    bull_cnt = 0
    bear_high_cnt = 0
    bull_low_cnt = 0

    trend_m = trend_t = trend_w = f.BearBull.COMPRESS
    open = close = high = low = bear_high = bull_low = None

    for item in data:
        dayofweek = f.dayofweek(item)

        if dayofweek == 'Monday':
            if not trend_m == f.BearBull.COMPRESS and trend_m == trend_t and (notwed or trend_m == trend_w):

                #  some follow over from the previous week
                if trend_m == f.BearBull.BEARISH:
                    bear_cnt += 1
                    if high == bear_high and close < open:
                        bear_high_cnt += 1

                elif trend_m == f.BearBull.BULLISH:
                    bull_cnt += 1
                    if low == bull_low and close > open:
                        bull_low_cnt += 1

            trend_t = trend_w = f.BearBull.COMPRESS
            trend_m = get_trend(item.trend, compress)
            open = item.open

            if trend_m == f.BearBull.BEARISH:
                high = bear_high = item.high
            elif trend_m == f.BearBull.BULLISH:
                low = bull_low = item.low

        elif dayofweek == 'Tuesday'or (dayofweek == 'Wednesday' and not notwed):
            trend = get_trend(item.trend, compress)

            if dayofweek == 'Tuesday':
                trend_t = trend
            else:
                trend_w = trend

            if trend_m == f.BearBull.BEARISH and item.high > bear_high:
                high = bear_high = item.high

            elif trend_m == f.BearBull.BULLISH and item.low < bull_low:
                low = bull_low = item.low

        elif trend_m == f.BearBull.BEARISH and item.high > high:
            high = item.high
        elif trend_m == f.BearBull.BULLISH and item.low < low:
            low = item.low

        if dayofweek == 'Friday':
            close = item.close

    bear_pc = (bear_high_cnt * 100.) / bear_cnt if bear_cnt else 100
    bear_result = "BEARISH WEEKS: M-T/ HIGH: {num}/{tot} {pc:.2f}%".format(
        num=bear_high_cnt, tot=bear_cnt, pc=bear_pc)
    print(bear_result)

    bull_pc = (bull_low_cnt * 100.) / bull_cnt if bull_cnt else 100
    bull_result = "BULLISH WEEKS: M-T/ LOW: {num}/{tot} {pc:.2f}%".format(
        num=bull_low_cnt, tot=bull_cnt, pc=bull_pc)
    print(bull_result)


if __name__ == '__main__':
    data = f.filter(
        f.load_candles(sys.argv[1]),
        f.filter_year,
        #[2013, 2014, 2015, 2016, 2017, 2018])
        [2018])
    week_highlow(data, False)
