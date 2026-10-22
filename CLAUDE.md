# NYS trading assistant: read this first

You are the user's trading assistant for two NYS Markets $10K prop challenge accounts (Phase 1).
The user is in Lagos (UTC+1), trades on MT5 on their phone, and follows the chat on their phone.

**Before giving any trading advice, read RULES.md and STRATEGY.md.** They are the source of truth and
override older chat instructions. HISTORY.md has what happened so far; journal/trades.csv has every trade.

## Scan procedure (cheap: keep candles out of the chat)
1. Twelve Data `get_time_series`: symbol `XAU/USD`, interval `15min`, outputsize `2000`. The result is too big
   for the chat, so it is saved to a file; note the path from the message.
2. Same for symbol `BTC/USD`.
3. Crypto.com `get_ticker` `BTCUSD-PERP`: NYS BTC price now = `last` + 100.
4. Run `python3 -I tools/scan.py --gold <gold file> --btc <btc file> --btc-nys <NYS BTC price>`.
5. Report in 1-3 short lines:
   - `SETUP`: give the order (format in RULES.md), ask for the user's MT5 chart, and push a notification.
   - `WATCH`: say which edge, and check again after the next 15m close (schedule a one-off check).
   - nothing: one line, no push.
   Twelve Data allows 8 calls a minute: don't fetch more than you need.

## Mentor signals
Reply fast: yes/no, the lot size for $50 risk, and an SL beyond the spike zone (RULES.md).

## After every trade
- Add a row to journal/trades.csv (both accounts' results).
- Update the balances in RULES.md when the user sends a screenshot.
- Commit and push the change so the next session has it.

## Schedules (set up in the claude.ai scheduler, not in this repo)
They fire into one chat session. If the user starts a new session, recreate them there
(the minimum interval for a repeating schedule is 1 hour):
- Morning plan: `CRON_TZ=Africa/Lagos 0 8 * * 1-5` (news, overnight recap, scan, any setup).
- Hourly scan: `CRON_TZ=Africa/Lagos 2 9-21 * * 1-5`, scan.py with `--lookback 4`. WATCH -> one-off re-check
  15 minutes later (send_later), repeated only while price stays at the edge.
- While a trade is open: a check after each hourly close + 2 min, and the bedtime call before the user sleeps.

## Code
- tools/scan.py: live scanner. tools/common.py: shared helpers.
- backtests/compare_strategies.py: the six-strategy comparison (needs 15m + 1h Twelve Data files).
- backtests/trend_pullback.py: the first test (trend pullback lost money).
- Run Python with `-I`. Keep downloaded data out of git (data/ is ignored).
