import sys
import forex as f


def process(data):
    buckets = {}

    item1 = None
    for item in data:

        if not item1:
            item1 = item
            continue

        delta = abs(item1.close - item.close)
        day = item.time.weekday()

        print(item.high, item.low)

        price, cnt = buckets.get(day, (0., 0))
        price += delta
        cnt += 1
        buckets[day] = (price, cnt)

    for day in buckets:
        price, cnt = buckets[day]
        ave = price/cnt
        buckets[day] = (price, cnt, ave)

    return buckets

if __name__ == '__main__':
    # years = [2013, 2014, 2015, 2016, 2017, 2018]
    years = [2018]

    # data
    datafile = sys.argv[1]
    data = f.filter(
            f.load_candles(datafile),
            f.filter_year,
            years)

    print(process(data))
