# AI Trading Lab V9.2 — Live-Data Paper Trading

**No real trades. All fills and P&L are simulated.** This project starts with $10,000 of virtual capital.

## Start the engine
Open [GitHub Actions](https://github.com/kokolo2020/ai-trading-lab/actions/workflows/paper-trading.yml), select **V9.2 Paper Trading Cycle**, then **Run workflow**. Scheduled runs are configured every 5 minutes but GitHub can delay or skip runs. Confirm repository Settings → Actions → General → Workflow permissions allows **Read and write permissions**. If the workflow cannot commit state, it will fail and the dashboard will not update.

## Execution model
- Public Binance spot prices and 1h completed candles (no exchange API keys).
- Synthetic LONG and SHORT positions with 1x fully reserved collateral; SHORTs are **not actual margin/futures trades**.
- Entry: EMA9 above/below EMA21 plus 3h momentum above +0.8% / below -0.8%; liquidity >= $20M quote volume in 24h; excludes extreme moves and volatility.
- 0.5% equity planned risk at stop, <=20% equity notional per position, maximum 3 positions.
- Stops at max(1.7×ATR14, 1.2% of price), target 2× stop distance, 48-hour time exit.
- 2% daily equity loss halt, closes open positions if market prices available.
- Simulated 0.1% fee each side and 0.05% adverse slippage on each fill.
- Every run persists open positions, closed trade ledger, equity history and recent events in `paper_state.json` committed to GitHub. Netlify displays the last committed state.

## Limitations
This is a **forward-test experiment**, not a validated profitable strategy. Price snapshots every ~5 minutes cannot guarantee stop prices, intrabar execution, or order-book liquidity. Synthetic SHORTs omit funding, borrow costs, liquidation, partial fills and margin requirements. GitHub Actions scheduling is best-effort, not a continuously running server. Public repository means the paper ledger is publicly readable. No API keys or real funds should be stored here.
