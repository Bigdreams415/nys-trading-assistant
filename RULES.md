# Trading rules (source of truth)

Last updated: Thu 22 Oct 2026. These rules override anything older in a chat or handoff.
The user chose these rules. Don't re-argue them; change them only when the user asks.

## Accounts
- Two NYS Markets 2-Step $10K Challenge accounts, Phase 1. Target $10,800. MT5 on the user's phone.
- Same trades on both accounts. Refer to them by balance (the user's "Account 1/2" labels got mixed up).
- Balances (Trade tab, Thu 22 Oct 08:08 Lagos): **$9,556.40** and **$9,429.58**. No open trades.
- NYS limits as we use them (user to confirm on the dashboard): max-loss floor $9,000 (static);
  daily loss limit 5% of the day-start balance; the NYS day starts 01:00 Lagos.
- **Safety line:** if either account drops below **$9,300** -> pause and review.

## What we trade
- **Only BTCUSD and XAUUSD (gold).** Nothing else.
- Strategy: range edges, see STRATEGY.md.

## Risk and lot size
- **Claude's setups: $25 per trade per account** until Claude proves itself again.
  One position per trade: **gold 0.01 lot, BTC 0.03 lot** (lots = $25 / stop distance, rounded down;
  if the minimum lot risks more than $25, say so).
- **Mentor's trades (Amiin Fx, TikTok live): $50 per account.** The user sends every mentor call to Claude
  first; Claude replies fast with the lot size and a stop beyond the spike zone.
  Gold with a proper stop: 0.01 lot risks ~$22-25, so $50 = two 0.01 positions (or one 0.02).
- **Max 4 trades a day** (user, Thu 22 Oct): up to $100 of risk a day per account at $25 each, only when there
  are valid setups (never forced). Open question: do the mentor's $50 trades count inside the 4?
  Never add to a losing trade. No hedging, including across the two accounts.
- Every trade goes through Claude first, including the mentor's and any other signal.

## Stop loss (the most important rule)
- Put the SL at the real structural place: beyond the obvious high/low where spikes hunt stops, not on it.
- At least **1.5x the H1 ATR** from entry and at least **gold 22 points, BTC 650 points**.
- Never squeeze the stop to make targets fit. A wider stop means a smaller lot, not more risk.
- History: most losses came from stops that were too tight (BTC 19 Oct, the mentor's 8-15 point gold stops).

## Managing a trade
- Gold: TP at 4R; at +2R move the SL to entry. BTC: TP at 2R.
- Once in, let it play out: SL/TP only. No moving the SL closer before the rule says so.
- **Bedtime rule (~22:00 Lagos):** close any trade whose SL is not at entry yet. Overnight, only SL/TP work.
  The user sometimes stays up until 00:00-01:00; then the bedtime call moves with them.
- **Friday:** everything closed by ~21:00 Lagos.
- News: no new entries from 10 minutes before to 10 minutes after red-folder USD news.
- The London open (08:00 Lagos; 09:00 from Mon 26 Oct) and the NY open (14:30 Lagos; 15:30 from Mon 2 Nov)
  spike both ways. Wait for the 15m candle to close.

## How Claude works with the user
- Messages SHORT. Clear yes/no. No lectures, no tables. The user gets frustrated after losses.
- Order format (simple list): Type / Volume / Entry / SL / TP (and the SL-to-entry level for gold) /
  market or limit and why / R:R / $ risk and $ target per account.
- Ask for the user's MT5 chart before they place a trade. After they place it, ask for a Trade-tab screenshot.
- Market orders: the user sends the fill price, Claude recomputes SL/TP.
- The user acts fast on the mentor's signals: reply FAST with yes/no and the lot size. If already in,
  give management (SL/TP, don't add, don't move the SL).
- Push notifications only when the user must act (place, move SL, close, delete an order).
- Be honest about results, including losing streaks. Never promise wins.

## Data and time
- Lagos = UTC+1. MT5 server time = Lagos minus 1h. New York -> Lagos = +5h until Sun 1 Nov, +6h after.
  UK clocks change Sun 25 Oct.
- Twelve Data connector: XAU/USD timestamps come back as UTC+11 (Lagos+10h); BTC/USD as UTC.
  Max 8 calls/min. Results over ~25k tokens are saved to a file automatically: pass that path to the scanner.
- Crypto.com connector: BTCUSD-PERP. NYS BTC ~ Crypto.com + 100 (+/-20).
  Twelve Data BTC/USD differs from NYS by roughly 0 to +110: compute the offset each scan (see CLAUDE.md).
- Gold: Twelve Data XAU/USD ~ NYS price (check against the user's chart when it matters).
- The Forex Factory JSON is blocked from the cloud container; use a web search for the day's news.
- Lot math: gold 0.01 lot = $1 per $1 move. BTC 1.00 lot = $1 per $1 move (commission ~$6/lot round trip,
  lot step 0.01).

## Still pending from the user
- History screenshot of the second account (the $9,429.58 one).
- Confirm the NYS daily/max loss limits on the dashboard.
