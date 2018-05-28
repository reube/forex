import sys
import forex as f

RANGE = 75


def narrow_asian_range(data_):
    data = []
    low = high = None
    for item in data_:
        if item.time.day < 5:  # mon-fri
            if item.time.hour == 0:
                low = item.low
                high = item.high
            elif item.time.hour < 5:
                if item.low < low:
                    low = item.low
                if item.high > high:
                    high = item.high
            elif item.time.hour == 5:
                delta = (high - low) * 10000
                if delta < RANGE:
                    data.append((item.time.year, item.time.month, item.time.day))
    return data


def narrow_range(data_):
    data = []
    cnt = None
    low = high = None
    for item in data_:
        if item.time.day < 5:  # mon-fri
            if cnt:
                cnt += 1
                if item.low < low:
                    low = item.low
                if item.high > high:
                    high = item.high
            else:
                cnt = 1
                low = item.low
                high = item.high

            delta = (high - low) * 10000
            if delta < RANGE:
                if cnt == 5:
                    data.append((item.time.year, item.time.month, item.time.day))
                    cnt = None
            else:
                cnt = None
        else:
            cnt = None

    data = list(set(data))
    return data


def weekday(data):
    return f.filter(data, f.filter_weekday)


def profile_range_(data, narrow=None):
    openhigh = lowopen = closeopen = 0
    samples = 0
    for item in data:
        if not narrow or (item.time.year, item.time.month, item.time.day) in narrow:
            openhigh += (item.high - item.open)
            lowopen += (item.low - item.open)
            closeopen += (item.close - item.open)  # not abs
            samples += 1
    openhigh = (float(openhigh) / samples) * 10000
    lowopen = (float(lowopen) / samples) * 10000
    closeopen = (float(closeopen) / samples) * 10000
    return openhigh, lowopen, closeopen, samples


def print_range(trend, classif, range):
    openhigh, openlow, closeopen, samples = range
    print("{trend}: {classif}: {samples}: openhigh: {openhigh:.2f}, openlow: {openlow:.2f}, closeopen: {closeopen:.2f}".format(
        trend=trend, classif=classif, samples=samples, openhigh=openhigh, openlow=openlow, closeopen=closeopen))


def profile_range(trend, data, narrow):
    range = profile_range_(data)
    print_range(trend, "NORMAL", range)

    range_narrow = profile_range_(data, narrow)
    print_range(trend, "NARROW", range_narrow)


if __name__ == '__main__':
    years = [2013, 2014, 2015, 2016, 2017, 2018]
    # years = [2018]

    # hour data
    datafile_hr = sys.argv[1]
    data_hr = f.filter(
        f.load_candles(datafile_hr),
        f.filter_year,
        years)
    data_narrow = narrow_range(data_hr) # narrow_asian_range(data_hr)

    # day data
    datafile_d = sys.argv[2]
    data_d = weekday(
        f.filter(
            f.load_candles(datafile_d),
            f.filter_year,
            years))

    # profile bearish days
    beardata = f.filter(data_d, f.filter_bearish, False) # , False)
    profile_range("BEARISH", beardata, data_narrow)

    # profile bullish days
    bulldata = f.filter(data_d, f.filter_bullish, False) # , False)
    profile_range("BULLISH:", bulldata, data_narrow)
