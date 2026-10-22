"""Shared helpers for the scanner and backtests: load Twelve Data JSON, resample, EMA, ATR."""
import json
from datetime import datetime, timedelta


def load_td(path, shift_hours=0.0, offset=0.0):
    """Load a saved Twelve Data get_time_series result ({"result": "datetime;open;high;low;close\\n..."}).

    shift_hours: hours to subtract to get UTC (XAU/USD comes back as UTC+11, BTC/USD as UTC).
    offset: points added to every price (e.g. to convert a feed to NYS MT5 prices).
    Returns bars sorted oldest first: (start_utc, open, high, low, close).
    """
    rows = json.load(open(path))["result"].strip().split("\n")[1:]
    out = []
    for r in rows:
        t, o, h, l, c = r.split(";")[:5]
        ts = datetime.strptime(t, "%Y-%m-%d %H:%M:%S") - timedelta(hours=shift_hours)
        out.append((ts, float(o) + offset, float(h) + offset, float(l) + offset, float(c) + offset))
    out.sort()
    return out


def resample(bars, minutes):
    """Group bars into UTC-aligned buckets of `minutes`. Returns (start, o, h, l, c) per bucket."""
    out, cur = [], None
    for ts, o, h, l, c in bars:
        since_midnight = ts.hour * 60 + ts.minute
        start = ts.replace(hour=0, minute=0, second=0) + timedelta(minutes=since_midnight - since_midnight % minutes)
        if cur is None or cur[0] != start:
            if cur:
                out.append(tuple(cur))
            cur = [start, o, h, l, c]
        else:
            cur[2] = max(cur[2], h)
            cur[3] = min(cur[3], l)
            cur[4] = c
    if cur:
        out.append(tuple(cur))
    return out


def ema(vals, n):
    k, e, out = 2 / (n + 1), None, []
    for v in vals:
        e = v if e is None else e + k * (v - e)
        out.append(e)
    return out


def atr(bars, n=14):
    """Simple average of the true range over the last n bars (None if not enough bars)."""
    if len(bars) < n + 1:
        return None
    trs = []
    for i in range(len(bars) - n, len(bars)):
        h, l, pc = bars[i][2], bars[i][3], bars[i - 1][4]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs) / n
