"""Compare five common strategies on BTC and gold (15m data, ~50 days), same risk rules for all.

Shared rules: SL >= 1.5x ATR(1h,14) (widened if tighter), skip if > 3x ATR; entry at the next 15m open;
exits TP 2R, or TP 3R with SL -> entry at 2R; flat at 21:00 UTC (22:00 Lagos) unless SL is at entry;
weekdays only; one position at a time; max 2 entries/day; SL assumed first on ties; costs deducted.

1 RANGE   3-day high/low: 15m rejection wick or fake breakout back inside; never fade into the 4h trend;
          opposite edge must be >= 2R away. 08-20 UTC.
2 LSWEEP  London sweep of the Asian range (00-07 UTC): 15m trades beyond it and closes back inside
          between 07-10 UTC -> fade. One per day.
3 LBREAK  London breakout: first 15m close beyond the Asian range between 07-10 UTC -> follow. SL at the
          other side of the Asian range. One per day.
4 NYORB   New York opening range (13:30-14:00 UTC): first 15m close beyond it between 14:00-16:00 UTC ->
          follow. SL at the other side of the range. One per day.
5 BBRSI   1h close outside Bollinger(20,2) with RSI(14) beyond 70/30, next 1h close back inside -> fade.
          SL beyond those two candles. Entries 08-20 UTC.

usage: python3 -I backtests/compare_strategies.py <name> <15m json> <1h json> <tz_shift> <cost_points>
  e.g. ... GOLD xau_15m.json xau_1h.json 11 0.4    |    ... BTC btc_15m.json btc_1h.json 0 40
"""
import os
import sys
from bisect import bisect_right
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import common  # noqa: E402


class bt:
    load = staticmethod(lambda path, shift: common.load_td(path, shift))
    resample = staticmethod(lambda bars, hours: common.resample(bars, hours * 60))
    ema = staticmethod(common.ema)

SPLIT = datetime(2026, 9, 27)


def prepare(p15, p1h, shift):
    m15, h1 = bt.load(p15, shift), bt.load(p1h, shift)
    h4 = bt.resample(h1, 4)
    e50 = bt.ema([b[4] for b in h4], 50)
    trend_t, trend_v = [], []
    for i, b in enumerate(h4):
        if i < 55:
            continue
        slope = e50[i] - e50[i - 5]
        trend_t.append(b[0] + timedelta(hours=4))
        trend_v.append(1 if (b[4] > e50[i] and slope > 0) else -1 if (b[4] < e50[i] and slope < 0) else 0)
    trs = []
    for i, b in enumerate(h1):
        pc = h1[i - 1][4] if i else b[4]
        trs.append(max(b[2] - b[3], abs(b[2] - pc), abs(b[3] - pc)))
    atr_t = [h1[i][0] + timedelta(hours=1) for i in range(14, len(h1))]
    atr_v = [sum(trs[i - 13:i + 1]) / 14 for i in range(14, len(h1))]
    h1_close = [b[0] + timedelta(hours=1) for b in h1]
    idx15 = {b[0]: i for i, b in enumerate(m15)}
    return dict(m15=m15, h1=h1, trend_t=trend_t, trend_v=trend_v, atr_t=atr_t, atr_v=atr_v,
                h1_close=h1_close, idx15=idx15)


def lookup(times, vals, t):
    k = bisect_right(times, t) - 1
    return vals[k] if k >= 0 else None


def simulate(d, i_entry, sig, sl, tp_r, use_be, cost):
    m15 = d["m15"]
    entry = m15[i_entry][1]
    risk = (entry - sl) * sig
    tp = entry + tp_r * risk * sig
    be_trig = entry + 2 * risk * sig
    stop, at_be, j = sl, False, i_entry
    while j < len(m15):
        ts, o, h, l, c = m15[j]
        adverse, favor = (l, h) if sig == 1 else (h, l)
        if (adverse - stop) * sig <= 0:
            return (stop - entry) * sig / risk - cost / risk, j
        if (favor - tp) * sig >= 0:
            return tp_r - cost / risk, j
        if use_be and not at_be and (favor - be_trig) * sig >= 0:
            stop, at_be = entry, True
        end = ts + timedelta(minutes=15)
        if not at_be and ((end.hour == 21 and end.minute == 0) or end.weekday() == 5):
            return (c - entry) * sig / risk - cost / risk, j
        j += 1
    return None, j


def candidates(d, strat):
    """Yield (signal_bar_index, sig, raw_sl) in time order."""
    m15, h1 = d["m15"], d["h1"]
    if strat == "RANGE":
        for i in range(1, len(m15) - 1):
            ts, o, h, l, c = m15[i]
            if not (8 <= ts.hour < 20):
                continue
            t_close = ts + timedelta(minutes=15)
            atr = lookup(d["atr_t"], d["atr_v"], t_close)
            k = bisect_right(d["h1_close"], ts) - 1
            if atr is None or k < 72:
                continue
            w = h1[k - 71:k + 1]
            rh, rl = max(b[2] for b in w), min(b[3] for b in w)
            if rh - rl < 4 * atr or h - l <= 0:
                continue
            rng = h - l
            sig = None
            if (h > rh and c < rh) or (rh - 0.3 * atr <= h <= rh + 0.3 * atr and c < rh and h - max(o, c) >= 0.5 * rng):
                sig = -1
            elif (l < rl and c > rl) or (rl - 0.3 * atr <= l <= rl + 0.3 * atr and c > rl and min(o, c) - l >= 0.5 * rng):
                sig = 1
            if not sig:
                continue
            tr = lookup(d["trend_t"], d["trend_v"], t_close) or 0
            if tr == -sig:
                continue
            yield i, sig, (h + 0.1 * atr if sig == -1 else l - 0.1 * atr), (rh, rl)
    elif strat in ("LSWEEP", "LBREAK", "NYORB"):
        by_day = {}
        for i, b in enumerate(m15):
            by_day.setdefault(b[0].date(), []).append(i)
        for day, idxs in sorted(by_day.items()):
            if strat == "NYORB":
                rng_idx = [i for i in idxs if m15[i][0].hour == 13 and m15[i][0].minute >= 30]
                win_idx = [i for i in idxs if 14 <= m15[i][0].hour < 16]
                need = 2
            else:
                rng_idx = [i for i in idxs if m15[i][0].hour < 7]
                win_idx = [i for i in idxs if 7 <= m15[i][0].hour < 10]
                need = 16
            if len(rng_idx) < need or not win_idx:
                continue
            ah, al = max(m15[i][2] for i in rng_idx), min(m15[i][3] for i in rng_idx)
            hi_so_far, lo_so_far = ah, al
            for i in win_idx:
                ts, o, h, l, c = m15[i]
                atr = lookup(d["atr_t"], d["atr_v"], ts + timedelta(minutes=15))
                if atr is None:
                    break
                hi_so_far, lo_so_far = max(hi_so_far, h), min(lo_so_far, l)
                if strat == "LSWEEP":
                    if h > ah and c < ah:
                        yield i, -1, hi_so_far + 0.1 * atr, None
                        break
                    if l < al and c > al:
                        yield i, 1, lo_so_far - 0.1 * atr, None
                        break
                else:
                    if c > ah:
                        yield i, 1, al - 0.1 * atr, None
                        break
                    if c < al:
                        yield i, -1, ah + 0.1 * atr, None
                        break
    elif strat == "BBRSI":
        closes = [b[4] for b in h1]
        gains, losses = [0.0], [0.0]
        for k in range(1, len(closes)):
            ch = closes[k] - closes[k - 1]
            gains.append(max(ch, 0))
            losses.append(max(-ch, 0))
        rsi = [None] * len(closes)
        ag = al_ = None
        for k in range(1, len(closes)):
            if k == 14:
                ag, al_ = sum(gains[1:15]) / 14, sum(losses[1:15]) / 14
            elif k > 14:
                ag = (ag * 13 + gains[k]) / 14
                al_ = (al_ * 13 + losses[k]) / 14
            if ag is not None:
                rsi[k] = 100 if al_ == 0 else 100 - 100 / (1 + ag / al_)
        for k in range(21, len(h1) - 1):
            w = closes[k - 20:k]  # band for bar k-1
            mean = sum(w) / 20
            sd = (sum((x - mean) ** 2 for x in w) / 20) ** 0.5
            up, dn = mean + 2 * sd, mean - 2 * sd
            w2 = closes[k - 19:k + 1]
            mean2 = sum(w2) / 20
            sd2 = (sum((x - mean2) ** 2 for x in w2) / 20) ** 0.5
            up2, dn2 = mean2 + 2 * sd2, mean2 - 2 * sd2
            prev, cur = h1[k - 1], h1[k]
            entry_t = cur[0] + timedelta(hours=1)
            if not (8 <= entry_t.hour < 20) or entry_t not in d["idx15"] or rsi[k - 1] is None:
                continue
            atr = lookup(d["atr_t"], d["atr_v"], entry_t)
            if atr is None:
                continue
            i_sig = d["idx15"][entry_t] - 1
            if prev[4] > up and rsi[k - 1] > 70 and cur[4] < up2:
                yield i_sig, -1, max(prev[2], cur[2]) + 0.1 * atr, None
            elif prev[4] < dn and rsi[k - 1] < 30 and cur[4] > dn2:
                yield i_sig, 1, min(prev[3], cur[3]) - 0.1 * atr, None


def run(d, strat, tp_r, use_be, cost):
    m15 = d["m15"]
    trades, busy_until, day_count = [], -1, {}
    for i_sig, sig, sl, rng in candidates(d, strat):
        i_entry = i_sig + 1
        if i_entry >= len(m15) or i_entry <= busy_until:
            continue
        ts = m15[i_entry][0]
        if ts.weekday() >= 5 or day_count.get(ts.date(), 0) >= 2:
            continue
        atr = lookup(d["atr_t"], d["atr_v"], m15[i_sig][0] + timedelta(minutes=15))
        entry = m15[i_entry][1]
        risk = (entry - sl) * sig
        if risk < 1.5 * atr:
            sl = entry - 1.5 * atr * sig
            risk = 1.5 * atr
        if risk > 3 * atr:
            continue
        if rng:
            rh, rl = rng
            room = (rh - entry) if sig == 1 else (entry - rl)
            if room < 2 * risk:
                continue
        res, j = simulate(d, i_entry, sig, sl, tp_r, use_be, cost)
        if res is None:
            break
        trades.append((ts, sig, res))
        busy_until = j
        day_count[ts.date()] = day_count.get(ts.date(), 0) + 1
    return trades


def fmt(trades):
    if not trades:
        return "no trades"
    rs = [t[2] for t in trades]
    wins = sum(1 for r in rs if r > 0.05)
    a = sum(t[2] for t in trades if t[0] < SPLIT)
    b = sum(t[2] for t in trades if t[0] >= SPLIT)
    streak = worst = 0
    for r in rs:
        streak = streak + 1 if r < -0.05 else 0
        worst = max(worst, streak)
    return (f"{len(rs):3d} trades, win {100 * wins / len(rs):3.0f}%, net {sum(rs):+5.1f}R (${25 * sum(rs):+5.0f}), "
            f"1st half {a:+5.1f}R / 2nd half {b:+5.1f}R, worst streak {worst}")


def main():
    name, p15, p1h, shift, cost = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), float(sys.argv[5])
    d = prepare(p15, p1h, shift)
    print(f"== {name}: {d['m15'][0][0]:%d %b} - {d['m15'][-1][0]:%d %b} (UTC); halves split at {SPLIT:%d %b}")
    for strat in ("RANGE", "LSWEEP", "LBREAK", "NYORB", "BBRSI"):
        for tp_r, be in ((2, False), (3, True)):
            print(f"  {strat:6s} TP{tp_r}R{'+BE' if be else '   '}: {fmt(run(d, strat, tp_r, be, cost))}")


if __name__ == "__main__":
    main()
