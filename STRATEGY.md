# Strategy: range edges (BTC and gold)

Chosen Thu 22 Oct 2026 after backtesting six strategies on 31 Aug - 22 Oct 2026 data.
Review after 10 live trades (journal/trades.csv). If it stops working, test again and change.

## The rules (what tools/scan.py checks)
1. **Levels:** the high and low of the last **1 day for gold** (24 closed 1h candles) and the last
   **3 days for BTC** (72 candles). The range must be at least 4x the H1 ATR tall.
2. **Side (4h chart):** never fade into the 4h trend. Trend = 4h close vs the 4h EMA50 and the EMA50's slope
   over 5 candles.
   - 4h downtrend -> only SELL at the top. 4h uptrend -> only BUY at the bottom. No trend -> both edges.
3. **Confirmation (15m chart),** on a closed 15m candle at the edge:
   - a rejection wick: the candle's high (low) is within 0.3 ATR of the top (bottom), the wick is at least
     half the candle, and it closes back inside the range; or
   - a fake breakout: the candle trades beyond the edge and closes back inside.
4. **Entry:** market order at the next 15m open (the user enters right away).
5. **Stop:** beyond the wick + 0.1 ATR, at least 1.5x H1 ATR and at least gold 22 / BTC 650 points.
   Skip if the stop would be more than 3x ATR.
6. **Room:** the opposite edge must be at least 2R away.
7. **Targets:** gold TP 4R, SL to entry at 2R. BTC TP 2R.
8. **Time:** weekdays; entries 09:00-21:00 Lagos; bedtime rule (close at ~22:00 Lagos unless SL is at entry);
   max 4 trades a day ($25 each).

## Backtest results (31 Aug - 22 Oct 2026, 15m data, $25 risk, costs included)
Same risk rules for every strategy. "Halves" = before/after 27 Sep, to check the result isn't one lucky week.

- **Range edges (this strategy):**
  - Gold: 10 trades, 6 won. TP 2R: +4.3R (+$107). TP 3R + BE: +6.3R (+$157). TP 4R + BE: +8.3R (+$207).
    Positive in both halves. Worst losing streak: 1.
  - BTC: 11 trades, 7 won. TP 2R: +3.2R (+$79). TP 4R + BE: -1.8R (bigger targets don't work on BTC).
- London sweep of the Asian range: gold -6.2R; BTC +2.0R but -4.3R / +6.3R by half (unreliable).
- London breakout of the Asian range: 2-7 trades, about break-even.
- New York opening-range breakout: gold -10.3R, BTC -4.4R (the NY open fakes out breakouts).
- Bollinger + RSI reversal: gold -3.5R, BTC -4.8R.
- Trend pullback (4h trend, 1h level, 15m trigger): about 50 trades each, ~30% win rate, -3R to -8R.

## Range length test (Thu 22 Oct, same data)
The user wants more trades per day, so shorter ranges were tested:
- Gold, 1-day range: 18-19 trades, about half won. TP 2R +5.5R (+$139), TP 4R + BE +11.2R (+$280); positive in both halves.
  -> gold now uses the 1-day range (about twice as many trades as the 3-day range).
- BTC, 1-day range: 20-25 trades, net -1.1R to -1.4R (-6R in the first half). Rejected.
  BTC 2-day range: 15 trades, +2.5R, worst streak 6. BTC keeps the 3-day range (11 trades, +3.2R).
- Expect roughly 4-5 setups a week across both markets, sometimes 2 in a day. Forcing more means taking
  setups that tested negative.

## Honest caveats
- About 10 trades per market is a small sample; part of the result can be luck.
- These 7 weeks were mostly sideways. Range trading loses more when a market trends hard;
  the 4h filter is the protection. Many results ended at the bedtime cut-off with small +/- R.
- Expect about 4-5 trades a week across both markets; roughly +$150-250 a month at $25 if it keeps working.

## Ideas to test next
- Limit orders resting at the edges (no 15m confirmation) vs the current market entry.
- Longer history (Twelve Data 1h data back to July) for more trades.
