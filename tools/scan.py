"""Live range-edge scanner for BTC and gold. Rules: STRATEGY.md.

Feed it saved Twelve Data 15min results (outputsize ~2000) and it prints, per instrument:
the 4h side, the 3-day range, how far price is from each edge, and SETUP / WATCH / nothing.
A SETUP comes with the order for both accounts ($25 risk each by default).

usage:
  python3 -I tools/scan.py --gold <xau_15m.json> --btc <btc_15m.json> --btc-nys 82450
      (--btc-nys = the NYS BTC price now, i.e. Crypto.com BTCUSD-PERP last + 100; it sets the price offset)
  python3 -I tools/scan.py --gold <file> --now 2026-10-02T11:45   # replay a past moment
"""
import argparse
import math
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import atr, ema, load_td, resample  # noqa: E402

CFG = {
    # usd_per_lot = dollars per 1.00 lot per 1 point of price
    # min_stop = absolute minimum stop in points (RULES.md), on top of 1.5x H1 ATR
    # range_h = range length in closed 1h candles (gold: 1 day, BTC: 3 days; see STRATEGY.md)
    "GOLD": dict(shift=11, tp_r=4, be_r=2, usd_per_lot=100, step=0.01, min_stop=22, range_h=24, fmt="{:,.1f}"),
    "BTC": dict(shift=0, tp_r=2, be_r=None, usd_per_lot=1, step=0.01, min_stop=650, range_h=72, fmt="{:,.0f}"),
}


def analyze(name, bars15, now, risk_usd, lookback=2):
    """Check the last `lookback` closed 15m bars (newest first) and report the first valid setup."""
    done15 = [b for b in bars15 if b[0] + timedelta(minutes=15) <= now]
    price = done15[-1][4] if done15 else None
    result = None
    for k in range(lookback):
        lines, order = analyze_bar(name, done15[:len(done15) - k], now, risk_usd, price)
        if result is None:
            result = (lines, order)  # the newest bar's status is the default report
        if order:
            if k:
                lines.insert(2, f"  (signal on the 15m candle {k} before the latest closed one)")
            return lines, order
    return result


def analyze_bar(name, done15, now, risk_usd, price):
    cfg = CFG[name]
    f = cfg["fmt"].format
    if len(done15) < 400:
        return [f"{name}: not enough data ({len(done15)} closed 15m bars)"], None
    last = done15[-1]
    if now - (last[0] + timedelta(minutes=15)) > timedelta(minutes=75):
        return [f"{name}: data is stale (last closed 15m bar {last[0]:%a %H:%M} UTC) - market closed or feed lag"], None
    h1 = [b for b in resample(done15, 60) if b[0] + timedelta(hours=1) <= now]
    h4 = [b for b in resample(done15, 240) if b[0] + timedelta(hours=4) <= now]
    a = atr(h1, 14)
    e50 = ema([b[4] for b in h4], 50)
    if a is None or len(h4) < 56:
        return [f"{name}: not enough history for ATR / 4h EMA50"], None
    slope = e50[-1] - e50[-6]
    c4 = h4[-1][4]
    trend = 1 if (c4 > e50[-1] and slope > 0) else -1 if (c4 < e50[-1] and slope < 0) else 0
    side_txt = {1: "UP -> buys at the bottom only", -1: "DOWN -> sells at the top only", 0: "no trend -> both edges"}[trend]

    # range from the 1h bars that closed at or before the signal bar's start
    win = [b for b in h1 if b[0] + timedelta(hours=1) <= last[0]][-cfg["range_h"]:]
    days = cfg["range_h"] // 24
    rh, rl = max(b[2] for b in win), min(b[3] for b in win)
    ts, o, h, l, c = last
    lines = [f"{name} {f(c)} | 4h {side_txt} | {days}-day range {f(rl)} - {f(rh)} | 1h ATR {f(a)}",
             f"  top {f(rh - c)} away ({(rh - c) / a:.1f} ATR), bottom {f(c - rl)} away ({(c - rl) / a:.1f} ATR)"]
    if rh - rl < 4 * a:
        lines.append("  -> range too narrow (< 4 ATR): no trade")
        return lines, None

    rng = h - l
    sig = None
    if rng > 0:
        if (h > rh and c < rh) or (rh - 0.3 * a <= h <= rh + 0.3 * a and c < rh and h - max(o, c) >= 0.5 * rng):
            sig = -1
        elif (l < rl and c > rl) or (rl - 0.3 * a <= l <= rl + 0.3 * a and c > rl and min(o, c) - l >= 0.5 * rng):
            sig = 1
    if sig and trend == -sig:
        lines.append(f"  15m {'rejection at the top' if sig == -1 else 'rejection at the bottom'} "
                     f"but it fades the 4h trend -> no trade")
        sig = None

    if sig and (price - c) * sig > 0.5 * a:
        lines.append("  15m signal, but price has already moved more than 0.5 ATR from it -> missed, don't chase")
        sig = None
    if sig:
        entry = price  # market order now ~ latest close
        sl = (h + 0.1 * a) if sig == -1 else (l - 0.1 * a)
        risk = (entry - sl) * sig
        floor = max(1.5 * a, cfg["min_stop"])
        if risk < floor:
            risk = floor
            sl = entry - risk * sig
        room = (entry - rl) if sig == -1 else (rh - entry)
        if risk > 3 * a:
            lines.append(f"  15m signal but the stop would be {f(risk)} (> 3 ATR) -> no trade")
        elif room < 2 * risk:
            lines.append(f"  15m signal but only {room / risk:.1f}R of room to the other edge -> no trade")
        else:
            tp = entry + cfg["tp_r"] * risk * sig
            lots = math.floor(risk_usd / (risk * cfg["usd_per_lot"]) / cfg["step"] + 1e-9) * cfg["step"]
            flag = ""
            if lots < cfg["step"]:
                lots = cfg["step"]
                flag = " (min lot risks more than planned)"
            usd_risk = lots * cfg["usd_per_lot"] * risk
            usd_tp = usd_risk * cfg["tp_r"]
            side = "SELL" if sig == -1 else "BUY"
            order = (f"SETUP {name}: {side} market now ~{f(entry)} | SL {f(sl)} ({f(risk)} pts) | "
                     f"TP {f(tp)} ({cfg['tp_r']}R)")
            if cfg["be_r"]:
                order += f" | move SL to entry at {f(entry + cfg['be_r'] * risk * sig)} ({cfg['be_r']}R)"
            order += f" | {lots:.2f} lot on EACH account = risk ${usd_risk:.0f}, target ${usd_tp:.0f}{flag}"
            lines.append("  -> " + order)
            lines.append(f"     why: 15m {'fake breakout' if (h > rh or l < rl) else 'rejection wick'} at the "
                         f"{'top' if sig == -1 else 'bottom'} of the {days}-day range; {room / risk:.1f}R of room")
            return lines, order

    near_top = (rh - c) <= 0.5 * a or h > rh
    near_bot = (c - rl) <= 0.5 * a or l < rl
    if near_top and trend != 1:
        lines.append("  -> WATCH the top: price is at/near it. Re-check after the next 15m close.")
    elif near_bot and trend != -1:
        lines.append("  -> WATCH the bottom: price is at/near it. Re-check after the next 15m close.")
    else:
        lines.append("  -> nothing now")
    return lines, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold")
    ap.add_argument("--btc")
    ap.add_argument("--btc-offset", type=float, default=0.0, help="NYS minus Twelve Data BTC/USD price")
    ap.add_argument("--btc-nys", type=float, help="NYS BTC price now (Crypto.com last + 100); sets --btc-offset")
    ap.add_argument("--gold-offset", type=float, default=0.0, help="NYS minus Twelve Data XAU/USD price")
    ap.add_argument("--risk", type=float, default=25.0, help="$ risk per account")
    ap.add_argument("--now", help="UTC time to evaluate, e.g. 2026-10-22T09:00 (default: now)")
    ap.add_argument("--lookback", type=int, default=2, help="closed 15m candles to check (default 2 = 30 min)")
    args = ap.parse_args()
    now = datetime.fromisoformat(args.now) if args.now else datetime.now(timezone.utc).replace(tzinfo=None)
    lagos = now + timedelta(hours=1)
    print(f"Scan at {lagos:%a %d %b %H:%M} Lagos ({now:%H:%M} UTC), risk ${args.risk:.0f}/account")
    if args.btc and args.btc_nys:
        args.btc_offset = args.btc_nys - load_td(args.btc, 0)[-1][4]
        print(f"BTC offset NYS - Twelve Data = {args.btc_offset:+.0f}")
    setups = []
    for name, path, off in (("GOLD", args.gold, args.gold_offset), ("BTC", args.btc, args.btc_offset)):
        if not path:
            continue
        lines, order = analyze(name, load_td(path, CFG[name]["shift"], off), now, args.risk, args.lookback)
        print("\n".join(lines))
        if order:
            setups.append(order)
    print(f"RESULT: {len(setups)} setup(s)")


if __name__ == "__main__":
    main()
