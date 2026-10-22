"""Mechanical approximation of the agreed BTC/gold strategy (Thu 22 Oct).

4h = direction (close vs EMA50 + EMA50 slope), 1h = levels (fractal swings + 4h EMA50),
15m = trigger at the level (pin bar / engulfing) -> enter next 15m open.
SL beyond the pullback swing, min 1.5x ATR(1h, 14), skip if > 3x ATR.
Room: nearest opposite 1h swing level must be >= 2R away.
Exits tested: fixed TP at 2R / 3R / 4R, with SL -> entry once 2R is reached (for 3R/4R).
Flat at 21:00 UTC (22:00 Lagos) unless SL is already at entry. No weekend entries.
Entries 08:00-20:00 UTC. One position at a time, max 2 entries per day per instrument.
Intrabar ambiguity: SL assumed first. Costs deducted per trade (spread/commission).

usage: backtest.py <name> <15m json> <1h json> <tz_shift_hours> <cost_points>
"""
import json
import sys
from datetime import datetime, timedelta


def load(path, shift):
    rows = json.load(open(path))["result"].strip().split("\n")[1:]
    out = []
    for r in rows:
        t, o, h, l, c = r.split(";")
        ts = datetime.strptime(t, "%Y-%m-%d %H:%M:%S") - timedelta(hours=shift)
        out.append((ts, float(o), float(h), float(l), float(c)))
    out.sort()
    return out


def resample(bars, hours):
    out, cur = [], None
    for ts, o, h, l, c in bars:
        start = ts.replace(minute=0, second=0) - timedelta(hours=ts.hour % hours)
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


def main():
    name, p15, p1h, shift, cost = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), float(sys.argv[5])
    use_room = "noroom" not in sys.argv[6:]
    use_night = "hold" not in sys.argv[6:]
    m15 = load(p15, shift)
    h1 = load(p1h, shift)
    h4 = resample(h1, 4)

    # 4h trend, known once the 4h bar has closed
    e50 = ema([b[4] for b in h4], 50)
    trend_at = []  # (close_time, trend)
    for i, b in enumerate(h4):
        if i < 55:
            continue
        slope = e50[i] - e50[i - 5]
        tr = 1 if (b[4] > e50[i] and slope > 0) else -1 if (b[4] < e50[i] and slope < 0) else 0
        trend_at.append((b[0] + timedelta(hours=4), tr, e50[i]))

    # 1h ATR(14) and fractal swings, known once confirmed (2 bars after)
    trs = []
    for i, b in enumerate(h1):
        pc = h1[i - 1][4] if i else b[4]
        trs.append(max(b[2] - b[3], abs(b[2] - pc), abs(b[3] - pc)))
    atr_at = []  # (close_time, atr)
    for i in range(14, len(h1)):
        atr_at.append((h1[i][0] + timedelta(hours=1), sum(trs[i - 13:i + 1]) / 14))
    def fractals(k):
        out = []
        for i in range(k, len(h1) - k):
            hi, lo = h1[i][2], h1[i][3]
            if hi > max(h1[j][2] for j in range(i - k, i + k + 1) if j != i):
                out.append((h1[i + k][0] + timedelta(hours=1), hi, "H", h1[i][0]))
            if lo < min(h1[j][3] for j in range(i - k, i + k + 1) if j != i):
                out.append((h1[i + k][0] + timedelta(hours=1), lo, "L", h1[i][0]))
        return out
    swings = fractals(3)
    major = fractals(5)
    stats = {}

    def last_before(series, t):
        lo_, hi_ = 0, len(series) - 1
        if not series or series[0][0] > t:
            return None
        while lo_ < hi_:
            mid = (lo_ + hi_ + 1) // 2
            if series[mid][0] <= t:
                lo_ = mid
            else:
                hi_ = mid - 1
        return series[lo_]

    variants = {"TP2R": (2, False), "TP3R_BE": (3, True), "TP4R_BE": (4, True)}
    results = {}
    for vname, (tp_r, use_be) in variants.items():
        trades, i, day_count = [], 0, {}
        while i < len(m15) - 2:
            ts, o, h, l, c = m15[i]
            t_close = ts + timedelta(minutes=15)
            if ts.weekday() >= 5 or not (8 <= ts.hour < 20):
                i += 1
                continue
            if day_count.get(ts.date(), 0) >= 2:
                i += 1
                continue
            tr = last_before(trend_at, t_close)
            at = last_before(atr_at, t_close)
            if not tr or not at or tr[1] == 0:
                i += 1
                continue
            trend, ema4, atr = tr[1], tr[2], at[1]
            known = [s for s in swings if s[0] <= t_close and s[3] >= ts - timedelta(days=10)]
            levels = [s[1] for s in known] + [ema4]
            prev = m15[i - 1]
            rng = h - l
            if rng <= 0:
                i += 1
                continue
            recent = m15[max(0, i - 96):i + 1]  # last 24h of 15m bars
            sig = None
            if trend == 1:
                pin = (min(o, c) - l) >= 0.5 * rng and (c - l) >= 0.6 * rng
                eng = c > o and prev[4] < prev[1] and c > prev[1] and o <= prev[4]
                touched = [lv for lv in levels if l <= lv + 0.3 * atr and l >= lv - 0.8 * atr and c > lv]
                pulled = max(b[2] for b in recent) - c >= 1.0 * atr
                if (pin or eng) and touched and pulled:
                    sig = 1
            else:
                pin = (h - max(o, c)) >= 0.5 * rng and (h - c) >= 0.6 * rng
                eng = c < o and prev[4] > prev[1] and c < prev[1] and o >= prev[4]
                touched = [lv for lv in levels if h >= lv - 0.3 * atr and h <= lv + 0.8 * atr and c < lv]
                pulled = c - min(b[3] for b in recent) >= 1.0 * atr
                if (pin or eng) and touched and pulled:
                    sig = -1
            if vname == "TP2R":
                stats["trend bars"] = stats.get("trend bars", 0) + 1
                if pin or eng: stats["trigger candle"] = stats.get("trigger candle", 0) + 1
                if (pin or eng) and touched: stats["+ at level"] = stats.get("+ at level", 0) + 1
                if sig: stats["+ pulled back"] = stats.get("+ pulled back", 0) + 1
            if not sig:
                i += 1
                continue
            entry = m15[i + 1][1]
            swing_ext = min(b[3] for b in m15[i - 3:i + 1]) if sig == 1 else max(b[2] for b in m15[i - 3:i + 1])
            sl = swing_ext - 0.1 * atr if sig == 1 else swing_ext + 0.1 * atr
            risk = (entry - sl) * sig
            if risk < 1.5 * atr:
                risk = 1.5 * atr
                sl = entry - risk * sig
            if risk > 3 * atr:
                if vname == "TP2R": stats["skip: stop too wide"] = stats.get("skip: stop too wide", 0) + 1
                i += 1
                continue
            kind = "H" if sig == 1 else "L"
            opp = [s[1] for s in major if s[0] <= t_close and s[3] >= ts - timedelta(days=10)
                   and s[2] == kind and (s[1] - entry) * sig > 0.25 * atr]
            room = min((lv - entry) * sig for lv in opp) if opp else None
            if use_room and room is not None and room < 2 * risk:
                if vname == "TP2R": stats["skip: no room"] = stats.get("skip: no room", 0) + 1
                i += 1
                continue
            # simulate
            tp = entry + tp_r * risk * sig
            be_trig = entry + 2 * risk * sig
            stop, at_be, res, j = sl, False, None, i + 1
            while j < len(m15):
                bt, bo, bh, bl, bc = m15[j]
                adverse = bl if sig == 1 else bh
                favor = bh if sig == 1 else bl
                if (adverse - stop) * sig <= 0:
                    res = (stop - entry) * sig / risk
                    break
                if (favor - tp) * sig >= 0:
                    res = tp_r
                    break
                if use_be and not at_be and (favor - be_trig) * sig >= 0:
                    stop, at_be = entry, True
                end = bt + timedelta(minutes=15)
                if not at_be and ((use_night and end.hour == 21 and end.minute == 0) or end.weekday() == 5):
                    res = (bc - entry) * sig / risk
                    break
                j += 1
            if res is None:
                break
            res -= cost / risk
            trades.append((m15[i + 1][0], sig, round(entry, 2), round(risk, 2), round(res, 2)))
            day_count[ts.date()] = day_count.get(ts.date(), 0) + 1
            i = j + 1
        results[vname] = trades

    print(f"== {name} [{'room filter' if use_room else 'no room filter'}, {'flat 22:00 Lagos' if use_night else 'hold overnight'}]: "
          f"{m15[0][0]:%d %b} - {m15[-1][0]:%d %b %Y} (UTC)")
    for vname, trades in results.items():
        if not trades:
            print(f"  {vname}: no trades")
            continue
        rs = [t[4] for t in trades]
        wins = [r for r in rs if r > 0.05]
        streak = worst = 0
        for r in rs:
            streak = streak + 1 if r < -0.05 else 0
            worst = max(worst, streak)
        eq = peak = dd = 0.0
        for r in rs:
            eq += r
            peak = max(peak, eq)
            dd = min(dd, eq - peak)
        print(f"  {vname}: trades {len(rs)}, win rate {100 * len(wins) / len(rs):.0f}%, avg {sum(rs) / len(rs):+.2f}R, "
              f"net {sum(rs):+.1f}R (= ${25 * sum(rs):+.0f} at $25), worst losing streak {worst}, max drawdown {dd:.1f}R")
    print("  filter counts (15m bars):", stats)
    print("  last 8 trades (TP3R_BE):")
    for t in results["TP3R_BE"][-8:]:
        print(f"    {t[0]:%a %d %b %H:%M} UTC {'BUY ' if t[1] == 1 else 'SELL'} @ {t[2]} risk {t[3]} -> {t[4]:+.2f}R")


if __name__ == "__main__":
    main()
