# Roadmap: from scanner to a smarter system, step by step

Principle: every step has to prove itself on data before we trust it with money.
No system predicts every move. The edge comes from tested rules, discipline and good risk control.

## Who does what today
- **tools/scan.py** does the mechanical part: the same tested rules every time, no emotions, no chasing.
- **Claude** is the judgment layer: reads the scanner, checks news and headlines (Fed, US data, war news),
  looks at the user's MT5 chart, checks the mentor's calls, sizes every trade, manages open trades
  and explains each decision.

## Step 1: prove the current strategy live (now)
- Range-edge trades on BTC and gold at $25 risk. Log every trade in journal/trades.csv.
- After 10 trades: compare live results with the backtest. Keep, adjust or replace.

## Step 2: bigger and fairer tests (1-2 weeks)
- Collect 6+ months of BTC and gold history (Twelve Data by date range) and keep it for re-use.
- Walk-forward testing: choose the rules on older months, check them on newer months the rules never saw.
- Test the open ideas in STRATEGY.md (resting limit orders at the edges, 2-day / 4-day ranges).

## Step 3: smarter filters
- News filter: no entries around big US data, Fed speakers or major headlines.
- Volatility filter: don't fade an edge when volatility is exploding (a real breakout, not a fake one).
- Mentor checker: score the mentor's calls with the same rules and track his results in the journal too.

## Step 4: trade scoring (only once we have enough trades, ~100+)
- Record features for every setup: range size, wick size, time of day, 4h trend strength, distance to the EMA.
- Test whether a simple model can tell the better setups from the weaker ones.
  Adopt it only if it beats the plain rules on data it has never seen.

## Step 5: a dashboard
- One page with the current ranges and levels, open trades, balances vs the $9,300 safety line,
  and journal stats (win rate, average R, results by setup and by source: Claude / mentor / user).

## Step 6: automation (optional, much later)
- Only if NYS allows automated trading (check their rules first: many prop firms restrict bots).
- Would need MT5 on a PC or VPS. Until then the user places every order by hand.
