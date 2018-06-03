import logging
import sys
import forex as f


class EMA:
    def __init__(self):
        pass

    @staticmethod
    def _fl(value):
        return float("{:.2f}".format(value))

    def process(self, data):
        item1 = None
        expanding1 = None
        buy = None
        sell = None
        prof_trades = 0
        loss_trades = 0
        pl = 0.
        for item in data:
            if item1:
                emad1 = item1.emas - item1.emal
                emad = item.emas - item.emal

                bull = emad > 0.
                bear = emad < 0.

                bull1 = emad1 > 0.
                bear1 = emad1 < 0.

                profit = 0.
                crossover = bull and bear1 or bear and bull1

                if crossover:
                    if bull and bear1:
                        if buy:
                            profit = item.close - buy
                            buy = None
                    else:
                        if sell:
                            profit = sell - item.close
                            sell = None
                    if profit > 0.:
                        prof_trades += 1
                    else:
                        loss_trades += 1

                expanding = abs(emad) > abs(emad1)
                contracting = abs(emad) < abs(emad1)

                if not crossover and expanding1 and contracting:
                    if bull:
                        sell = item.close
                    elif bear:
                        buy = item.close

                expanding1 = expanding
                pl += profit

            item1 = item

        prof_pc = EMA._fl(prof_trades * 100 / (prof_trades + loss_trades)) if prof_trades or loss_trades else 0.
        return prof_trades, prof_pc, loss_trades, pl


if __name__ == '__main__':
    logging.basicConfig(
        filename="/tmp/ema.log",
        filemode='w',
        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s' +
               '%(message)s line:%(lineno)d',
        datefmt='%H:%M:%S',
        level=logging.INFO)

    # years = [2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018]
    #
    years = [2018]

    # day data
    datafile = sys.argv[1]
    data = f.filter(
        f.load_candles(datafile),
        f.filter_year,
        years)

    ema = EMA()

    print(ema.process(data))
