import sys
import forex as f

import logging
import math
import calendar

LOGGER = logging.getLogger(__name__)


def gap(data):
    up = {}
    down = {}
    buckets = {}
    closed = 0
    total = 0

    data_idx = 1
    while data_idx < len(data):
        data_idx_1 = data_idx - 1
        open_ = data[data_idx].open
        close = data[data_idx].close
        time_1 = data[data_idx_1].time

        time = data[data_idx].time
        close_1 = data[data_idx_1].close
        close_1s = str(close_1)

        LOGGER.debug("CLOSE-1: {close_1}, OPEN: {open}, CLOSE: {close}".format(
            close_1=close_1, open=open_, close=close))

        if open_ > close_1:
            LOGGER.debug("OPEN HIGHER: close: {close}, open: {open}".format(
                close=close_1, open=open_))
            entry = down.get(close_1s, [])
            entry.append(time_1)
            down[close_1s] = entry
            total +=1
        elif open_ < close_1:
            LOGGER.debug("OPEN LOWER: close: {close}, open: {open}".format(
                close=close_1, open=open_))
            entry = up.get(close_1s, [])
            entry.append(time_1)
            up[close_1s] = entry
            total += 1

        downer = open_ > close
        closer = down if downer else up
        closees = [c for c in closer.keys() if
                   (downer and close <= float(c) < open_) or (open_ < float(c) <= close)]

        for c in closees:
            for t in closer[c]:
                delta = (time - t).days
                if not delta:
                    delta = 1
                bucket = str(
                    math.trunc(
                        math.log(delta, 2)))
                entry = buckets.get(bucket, [])
                entry.append(t)
                buckets[bucket] = entry
                closed +=1
            del closer[c]

        data_idx += 1

    return buckets, closed, total


if __name__ == '__main__':
    logging.basicConfig(
        filename="/tmp/gap.log",
        filemode='w',
        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s' +
               '%(message)s line:%(lineno)d',
        datefmt='%H:%M:%S',
        level=logging.DEBUG)

    years = [2013, 2014, 2015, 2016, 2017, 2018]
    # years = [2018]

    # day data
    datafile_d = sys.argv[1]
    data_d = f.filter(
        f.load_candles(datafile_d),
        f.filter_year,
        years)

    buckets, closed, total = gap(data_d)

    samples_dow = {}
    samples_mth = {}

    for key in buckets.keys():
        entry = buckets[key]
        for item in entry:
            dayofweek = f.dayofweek(item)
            samples_dow[dayofweek] = samples_dow.get(dayofweek, 0) + 1

            month = calendar.month_name[item.month]
            samples_mth[month] = samples_mth.get(month, 0) + 1

    keys = sorted([int(k) for k in buckets.keys()])
    for key_ in keys:
        key = str(key_)
        entry = buckets[key]
        days_ = int(math.pow(2, float(key) + 1))
        closed_ = len(entry)
        pc_ = closed_ * 100.0 / total

        print("Closed within {days} days: {closed}/{total} {pc:.2f}%".format(closed=closed_, total=total, days=days_, pc=pc_))
        print("-------------------------------------")
        f.print_complete_summary(entry, [f.Summaries.DAYOFWEEK], samples_dow)
        f.print_complete_summary(entry, [f.Summaries.MONTHS], samples_mth)

    pc = closed * 100.0 / total
    print("Gaps closed: {closed}/{total}, {pc:.2f}%".format(
        closed=closed, total=total, pc=pc))
