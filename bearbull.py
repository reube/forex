import sys
import forex as f


def print_yr_summary(datafile):
    data = f.filter_thisyr(
        f.load_candles(datafile))

    samplesizes = f.get_sample_sizes(
        f.get_interday_summary(data, f.classify_month))

    bearbull = f.get_bearbull_summary(data)

    for bb in f.BEARBULL_KEYS:
        print("**** {key} ****".format(key=bb))
        f.print_complete_summary(bearbull.get(bb, []), [f.Summaries.MONTHS], samplesizes)


def print_mth_summary(datafile):
    data = f.filter_thismth(
        f.load_candles(datafile))

    samplesizes = f.get_sample_sizes(
        f.get_interday_summary(data, f.classify_day))

    bearbull = f.get_bearbull_summary(data)

    for bb in f.BEARBULL_KEYS:
        print("**** {key} ****".format(key=bb))
        f.print_complete_summary(bearbull.get(bb, []), [f.Summaries.DAY], samplesizes)


if __name__ == '__main__':
    print_yr_summary(sys.argv[1])
