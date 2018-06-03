from json import loads
from datetime import datetime

with open("bitcoin_1d.json", "r") as bitcoin:

    prices = loads(
        bitcoin.readlines()[0].strip())
    datestr = "%Y-%m-%d"
    keys = sorted(d for d in
        [datetime.strptime(p, datestr) for p in prices.keys()] if d.year > 2016)

    with open("bitcoin_1d.csv", "w") as csv:
        csv.write("junk line\n")
        for key_ in keys:
            key = "{y}-{m:02}-{d:02}".format(y=key_.year, m=key_.month, d=key_.day)
            close = prices[key]
            line = "{d:02}.{m:02}.{y} 01:00:00.000 GMT+1200,{o},{h},{l},{c},10000.1\n".format(
                y=key_.year, m=key_.month, d=key_.day, o=close, h=close, l=close, c=close)
            csv.write(line)
