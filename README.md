# NYS trading assistant

Rules, strategy, scanner and backtests for two NYS Markets $10K prop challenge accounts (BTC and gold only).

- **RULES.md**: risk, lot sizes, stops, trade management, how the assistant communicates.
- **STRATEGY.md**: the range-edge strategy and the backtest results behind it.
- **HISTORY.md**: what happened so far and the lessons.
- **journal/trades.csv**: every trade from 22 Oct onward.
- **tools/scan.py**: live scanner (finds setups at the edges of the 3-day range).
- **backtests/**: strategy tests on Twelve Data 15-minute data.
- **CLAUDE.md**: instructions any Claude session loads automatically when this repo is attached.
