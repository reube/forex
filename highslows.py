import sys
import forex as f


def process(data, first_fun):
    item = data[0]

    high = item.high
    low = item.low
    low_t = high_t = item.time
    highs = []
    lows = []
    first_done = True

    for item in data:
        if not first_done and first_fun(item):
            # have crossed a time boundary
            highs.append(high_t)
            lows.append(low_t)
            high = item.high
            low = item.low
            low_t = high_t = item.time
            first_done = True
        else:
            if not first_fun(item):
                first_done = False
            if item.high > high:
                high = item.high
                high_t = item.time
            elif item.low < low:
                low = item.low
                low_t = item.time
    highs.append(high_t)
    lows.append(low_t)
    return highs, lows


if __name__ == '__main__':
    years = [2013, 2014, 2015, 2016, 2017, 2018]
    # years = [2018]

    # data
    datafile = sys.argv[1]
    data = f.filter(
            f.load_candles(datafile),
            f.filter_year,
            years)

    periods = [
        # (f.first_fun_hour, f.Summaries.HOURS, "which hour of day?"),
        (f.first_fun_day, f.Summaries.DAY, "which day of month?"),
        (f.first_fun_weekday, f.Summaries.DAYOFWEEK, "which day of week?"),
        (f.first_fun_month, f.Summaries.MONTHS, "which month of year?")
    ]

    for period in periods:
        f_, p_, t_ = period
        highs_, lows_ = process(data, f_)

        print("HIGHS - {}".format(t_))
        f.print_complete_summary(highs_, [p_])
        # print(highs_)

        print("LOWS - {}".format(t_))
        f.print_complete_summary(lows_, [p_])
        # print(lows_)
