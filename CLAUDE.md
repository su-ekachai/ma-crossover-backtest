# CLAUDE.md

## Project: EMA-99 Backtester

A Python backtesting system for evaluating Moving Average (MA) based trading strategies on historical OHLCV data.

## Architecture

```
main.py              → Click CLI entry point (run, compare, optimize, web)
src/config.py        → Dataclass config with YAML parsing and validation
src/data_loader.py   → CSV loading, validation, timeframe resampling
src/indicators.py    → EMA/SMA wrappers (pandas-ta)
src/strategies/      → Backtesting.py Strategy subclass
  ma_strategy.py     → MAStrategy: confirmation candles, direction, sizing
src/runner.py        → Backtest execution, result saving, batch/optimize modes
web/app.py           → Flask viewer for browsing saved results
```

## Commands

```bash
uv run python main.py run --data <csv>       # Single backtest
uv run python main.py compare --data <csv>   # Multi-config batch comparison
uv run python main.py optimize --data <csv>  # Parameter optimization sweep
uv run python main.py web                    # Launch results web viewer

uv run pytest                                # Run test suite
uv run pytest --cov=src                      # Run with coverage
uv run ruff check .                          # Lint
uv run ruff format .                         # Format
```

## Key Constraints

- **Strategy class variables**: Backtesting.py's `optimize()` modifies class-level attributes on MAStrategy. This is by design — don't convert to instance variables.
- **Python 3.12+**, managed with `uv` (not pip/poetry)
- **Local-only**: No live trading, no exchange APIs, no credentials. CSV data in, stats/charts out.
- **Results are timestamped**: Each run creates `results/YYYYMMDD_HHMMSS_*/` — never overwrite.

## Conventions

- Type hints on all function signatures
- Loguru for logging (not stdlib `logging`)
- Click for CLI (not argparse)
- Dataclasses for config (not dicts or pydantic)
- YAML for external config via `yaml.safe_load`
- Ruff for both linting and formatting (line-length=100)

## Gotchas

- `confirmation_candles=N` means N additional bars after the initial crossing. So 0 = enter on crossing bar, 1 = wait 1 more bar after crossing.
- `_apply_config_to_strategy()` mutates class-level state (not thread-safe). Run batch configs sequentially.
- Position size is clamped to 0.99 max to prevent margin-trading behavior.
- Chart generation can fail (Bokeh CDN issues) — failures are logged as warnings, not fatal.

---

## Behavioral Guidelines

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
