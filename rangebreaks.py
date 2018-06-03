import sys
import forex as f

import logging

LOGGER = logging.getLogger(__name__)

SLACK = 1.05


def rangebreaks(data):
    low = high = low_ = high_ = None
    within = 0
    total = -2 # dont count the first high/low

    data_idx = 2
    while data_idx < len(data):
        if data[data_idx-2].high < data[data_idx-1].high and data[data_idx].high < data[data_idx-1].high:
            high_ = data[data_idx-1].high
        elif data[data_idx-2].low > data[data_idx-1].low and  data[data_idx].low > data[data_idx-1].low:
            low_ = data[data_idx-1].low

        if high_:
            total += 1
            if high and high_ < high * SLACK:
                within += 1
            high = high_
            high_ = None
        elif low_:
            total += 1
            if low and low_ > low / SLACK:
                within += 1
            low = low_
            low_ = None
        data_idx += 1

    return within, total


if __name__ == '__main__':
    logging.basicConfig(
        filename="/tmp/rangebreaks.log",
        filemode='w',
        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s' +
               '%(message)s line:%(lineno)d',
        datefmt='%H:%M:%S',
        level=logging.DEBUG)

    years = [2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018]
    # years = [2018]

    # day data
    datafile_d = sys.argv[1]
    data_d = f.filter(
        f.load_candles(datafile_d),
        f.filter_year,
        years)

    within, total = rangebreaks(data_d)

    pc = within * 100.0 / total
    print("Ranges maintained: {within}/{total}, {pc:.2f}%".format(
        within=within, total=total, pc=pc))
