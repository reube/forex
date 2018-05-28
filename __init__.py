from collections import namedtuple
from datetime import datetime
import sys
import calendar
from enum import Enum

Candle = namedtuple('Candle', ('time', 'open', 'high', 'low', 'close', 'vol', 'emas', 'emal', 'trend'))

EMAS = 9
EMAL = 18
EMAMULTS = 2. / (EMAS + 1.)
EMAMULTL = 2. / (EMAL + 1.)

TIMEMULT = 1

ID_0003 = '00-03'
ID_0306 = '03-06'
ID_0609 = '06-09'
ID_0912 = '09-12'
ID_1215 = '12-15'
ID_1518 = '15-18'
ID_1821 = '18-21'
ID_2100 = '21-24'

ID_0006 = '00-06'
ID_0612 = '06-12'
ID_1218 = '12-18'
ID_1800 = '18-24'

ID_3hs = [ID_0003, ID_0306, ID_0609, ID_0912, ID_1215, ID_1518, ID_1821, ID_2100]
ID_6hs = [ID_0006, ID_0612, ID_1218, ID_1800]

WEEKS_YR = [str(wk) for wk in range(1, 54)]
DAYS_MTH = [str(day) for day in range(1, 32)]
YEARS = [str(yr) for yr in range(2013, 2020)]


class BearBull(Enum):
    BEARISH = 0
    BULLISH = 1
    COMPRESSBEAR = 2
    COMPRESSBULL = 3
    COMPRESS = 4
BEARBULL_KEYS = [str(i) for i in list(BearBull)]

class Summaries(Enum):
    HOURS = 0
    DAY = 1
    DAYOFWEEK = 2
    WEEKS = 3
    MONTHS = 4
    YEARS = 5


def load_candles(candle_file):
    timestr = '%d.%m.%Y %H:%M:00.000 GMT%z'

    candles = []
    with open(candle_file, 'r') as candles_:
        candles_.readline()
        while True:
            line = candles_.readline().split()
            if not line:
                break
            ohlc = line[2].split(',')
            line[2] = ohlc[0]
            ohlc = ohlc[1:]
            time = datetime.strptime(" ".join(line), timestr)
            weekday = time.weekday()
            if weekday == 5:   # ignore saturday candles
                continue

            open_ = float(ohlc[0])
            high = float(ohlc[1])
            low = float(ohlc[2])
            close = float(ohlc[3])
            vol = float(ohlc[4])

            candles_ema = candles[::TIMEMULT]

            emas = emal = emas_1 = emal_1 = close
            if len(candles_ema) == EMAS:
                emas = sum([c.close for c in candles_ema[-EMAS:]]) / EMAS
            elif len(candles_ema) > EMAS:
                emas_1 = candles_ema[-1].emas
                emas = (close - emas_1) * EMAMULTS + emas_1

            if len(candles_ema) == EMAL:
                emal = sum([c.close for c in candles_ema[-EMAL:]]) / EMAL
            elif len(candles_ema) > EMAL:
                emal_1 = candles_ema[-1].emal
                emal = (close - emal_1) * EMAMULTL + emal_1

            gap = abs(emas - emal)
            gap_1 = abs(emas_1 - emal_1)

            if emas > emal:
                if gap >= gap_1 and gap > 0:
                    trend = BearBull.BULLISH
                else:
                    trend = BearBull.COMPRESSBULL
            elif emal > emas:
                if gap >= gap_1 and gap > 0:
                    trend = BearBull.BEARISH
                else:
                    trend = BearBull.COMPRESSBEAR
            else:
                trend = BearBull.COMPRESS

            candles.append(
                Candle(time, open_, high, low, close, vol, emas, emal, trend))

    return candles


def _time(item):
    time = item
    if isinstance(item, Candle):
        time = item.time
    return time


def dayofweek(item):
    return calendar.day_name[_time(item).weekday()]

def filter_hr(item, hours):
    return _time(item).hour in hours


def filter_day(item, days):
    return _time(item).day in days


def filter_dayofweek(item, days):
    return dayofweek(item) in days


def filter_week(item, weeks):
    return str(_time(item).isocalendar()[1]) in weeks


def filter_month(item, months):
    return calendar.month_name[_time(item).month] in months


def filter_weekday(item, _inlist):
    return _time(item).weekday() < 5


def filter_year(item, years):
    return _time(item).year in years


def filter_bearish(item, compress):
    compressbear = compress and item.trend == BearBull.COMPRESSBEAR
    return item.trend == BearBull.BEARISH or compressbear


def filter_bullish(item, compress):
    compressbull = compress and item.trend == BearBull.COMPRESSBULL
    return item.trend == BearBull.BULLISH or compressbull


def filter(data_, filter_fun, inlist=None):
    data = []
    for item in data_:
        if filter_fun(item, inlist):
            data.append(item)
    return data


def filter_thisyr(data):
    return filter(data, filter_year, [datetime.now().year])


def filter_thismth(data):
    now = datetime.now()
    return filter(
        filter(
            data, filter_year, [now.year]), filter_month, [calendar.month_name[now.month]])


def classify_hr(time, periods):
    for period_ in periods:
        period = period_.split('-')
        if int(period[0]) <= time.hour < int(period[1]):
            return period_


def classify_day(time, _periods):
    return str(time.day)


def classify_dayofweek(time, _periods):
    return calendar.day_name[time.weekday()]


def classify_week(time, _periods):
    return str(time.isocalendar()[1])


def classify_month(time, _periods):
    return calendar.month_name[time.month]


def classify_year(time, _periods):
    return str(time.year)


def classify(item, buckets, classify_fun, periods=None):
    time = item
    if isinstance(item, Candle):
        time = item.time
    bucket_period = classify_fun(time, periods)
    bucket = buckets.get(bucket_period, [])
    bucket.append(item)
    buckets[bucket_period] = bucket


def get_intraday_summary(data):
    buckets_3h = {}
    buckets_6h = {}
    for item in data:
        classify(item, buckets_3h, classify_hr, ID_3hs)
        classify(item, buckets_6h, classify_hr, ID_6hs)
    return buckets_3h, buckets_6h


def get_interday_summary(data, classify_fun):
    buckets = {}
    for item in data:
        classify(item, buckets, classify_fun)
    return buckets

def get_bearbull_summary(data):
    buckets = {}
    for item in data:
        bucket_name = str(item.trend)
        bucket = buckets.get(bucket_name, [])
        bucket.append(item)
        buckets[bucket_name] = bucket
    return buckets


def print_buckets_summary(buckets, buckets_keys, samplesizes=None):
    num_items = 0
    for bucket in buckets_keys:
        num_items += len(buckets.get(bucket, []))
    for bucket in buckets_keys:
        bucket_len = len(buckets.get(bucket, []))
        if bucket_len:
            percent_buckets = float(bucket_len * 100) / num_items
            if samplesizes and not (samplesizes[bucket] == 1 and bucket_len == 1):
                percent_samples = float(bucket_len * 100) / samplesizes[bucket]
                print("{bucket}: {len}/{num} {pcb:.2f}%, {len}/{samples} {pcs:.2f}%".format(
                    bucket=bucket, len=bucket_len, num=num_items, pcb=percent_buckets, samples=samplesizes[bucket],
                    pcs=percent_samples))
            else:
                print("{bucket}: {len}/{num} {pcb:.2f}%".format(
                    bucket=bucket, len=bucket_len, num=num_items, pcb=percent_buckets))
    print()


def print_complete_summary(data, which=list(Summaries), samplesizes=None):
    if Summaries.HOURS in which:
        buckets_3h, buckets_6h = get_intraday_summary(data)
        print_buckets_summary(buckets_3h, ID_3hs, samplesizes)

    if Summaries.DAY in which:
        buckets = get_interday_summary(data, classify_day)
        print_buckets_summary(buckets, DAYS_MTH, samplesizes)

    if Summaries.DAYOFWEEK in which:
        buckets = get_interday_summary(data, classify_dayofweek)
        print_buckets_summary(buckets, list(calendar.day_name), samplesizes)

    if Summaries.WEEKS in which:
        buckets = get_interday_summary(data, classify_week)
        print_buckets_summary(buckets, WEEKS_YR, samplesizes)

    if Summaries.MONTHS in which:
        buckets = get_interday_summary(data, classify_month)
        print_buckets_summary(buckets, list(calendar.month_name)[1:], samplesizes)

    if Summaries.YEARS in which:
        buckets = get_interday_summary(data, classify_year)
        print_buckets_summary(buckets, YEARS, samplesizes)


def get_sample_sizes(refdata):
    samplesizes = {}
    for key in refdata.keys():
        samplesizes[key] = len(refdata.get(key))
    return samplesizes


if __name__ == '__main__':
    data = filter_thisyr(load_candles(sys.argv[1]))
    print_complete_summary(data)
