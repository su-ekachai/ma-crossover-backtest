"""CLI entry point for EMA-99 backtesting system."""

import sys

import click
from loguru import logger

from src.config import Config
from src.runner import run_comparison, run_optimization, run_single


@click.group()
def cli() -> None:
    """EMA-99 Backtesting System CLI."""
    logger.remove()
    logger.add(sys.stderr, level="INFO")


@cli.command()
@click.option("--data", required=True, help="Path to OHLCV CSV file")
@click.option("--config", help="YAML config file")
@click.option("--ma-type", "ma_type", default="EMA", type=click.Choice(["EMA", "SMA"]))
@click.option("--period", type=int, default=99)
@click.option("--confirm", "confirmation_candles", type=int, default=0)
@click.option(
    "--direction",
    default="both",
    type=click.Choice(["long_only", "short_only", "both"]),
)
@click.option(
    "--sizing-mode",
    "sizing_mode",
    default="all_in",
    type=click.Choice(["all_in", "fixed", "percentage"]),
)
@click.option("--sizing-amount", "sizing_fixed_amount", type=float, default=1000.0)
@click.option("--sizing-risk", "sizing_risk_pct", type=float, default=0.02)
@click.option("--cash", "initial_cash", type=float, default=10000.0)
@click.option("--commission", type=float, default=0.001)
@click.option("--timeframe", default="", help="Target timeframe for resampling")
def run(
    data: str,
    config: str | None,
    ma_type: str,
    period: int,
    confirmation_candles: int,
    direction: str,
    sizing_mode: str,
    sizing_fixed_amount: float,
    sizing_risk_pct: float,
    initial_cash: float,
    commission: float,
    timeframe: str,
) -> None:
    """Run a single backtest."""
    cfg = Config.from_yaml(config) if config else Config()

    cfg.data.path = data
    cfg.data.timeframe = timeframe
    cfg.strategy.ma_type = ma_type
    cfg.strategy.ma_period = period
    cfg.strategy.confirmation_candles = confirmation_candles
    cfg.strategy.direction = direction
    cfg.sizing.mode = sizing_mode
    cfg.sizing.fixed_amount = sizing_fixed_amount
    cfg.sizing.risk_percentage = sizing_risk_pct
    cfg.backtest.initial_cash = initial_cash
    cfg.backtest.commission = commission

    logger.info(f"Running backtest on {data}")
    result = run_single(cfg)
    stats = result["stats"]

    click.echo("\n=== Backtest Results ===")
    click.echo(f"MA: {ma_type}({period})")
    click.echo(f"Confirmation: {confirmation_candles} candles")
    click.echo(f"Direction: {direction}")
    click.echo(f"\nReturn [%]: {stats.get('Return [%]', 0):.2f}")
    click.echo(f"Sharpe Ratio: {stats.get('Sharpe Ratio', 0):.2f}")
    click.echo(f"Max Drawdown [%]: {stats.get('Max. Drawdown [%]', 0):.2f}")
    click.echo(f"Win Rate [%]: {stats.get('Win Rate [%]', 0):.2f}")
    click.echo(f"# Trades: {stats.get('# Trades', 0)}")
    click.echo(f"\nResults saved to: {result['results_dir']}")


@cli.command()
@click.option("--data", required=True, help="Path to OHLCV CSV file")
@click.option("--ma-types", default="EMA,SMA", help="Comma-separated MA types")
@click.option("--periods", default="99", help="Comma-separated periods")
@click.option("--confirm-range", default="0,1,2,3,5", help="Comma-separated confirmation values")
@click.option("--timeframes", default="1h,4h,1d", help="Comma-separated timeframes")
@click.option("--direction", default="both", type=click.Choice(["long_only", "short_only", "both"]))
@click.option("--cash", "initial_cash", type=float, default=10000.0)
@click.option("--commission", type=float, default=0.001)
def compare(
    data: str,
    ma_types: str,
    periods: str,
    confirm_range: str,
    timeframes: str,
    direction: str,
    initial_cash: float,
    commission: float,
) -> None:
    """Run batch comparison across multiple configurations."""
    ma_type_list = [m.strip() for m in ma_types.split(",")]
    period_list = [int(p.strip()) for p in periods.split(",")]
    confirm_list = [int(c.strip()) for c in confirm_range.split(",")]
    timeframe_list = [t.strip() for t in timeframes.split(",")]

    from src.config import BacktestConfig, DataConfig, SizingConfig, StrategyConfig

    configs = []
    for ma_type in ma_type_list:
        for period in period_list:
            for confirm in confirm_list:
                for timeframe in timeframe_list:
                    cfg = Config(
                        strategy=StrategyConfig(
                            ma_type=ma_type,
                            ma_period=period,
                            confirmation_candles=confirm,
                            direction=direction,
                        ),
                        sizing=SizingConfig(),
                        backtest=BacktestConfig(initial_cash=initial_cash, commission=commission),
                        data=DataConfig(path=data, timeframe=timeframe),
                    )
                    configs.append(cfg)

    logger.info(f"Running {len(configs)} configurations...")
    df = run_comparison(configs)

    click.echo("\n" + df.to_string(index=False))


@cli.command()
@click.option("--data", required=True, help="Path to OHLCV CSV file")
@click.option("--maximize", default="Sharpe Ratio", help="Metric to maximize")
@click.option("--confirm-range", default="0-5", help="Confirmation range (e.g., 0-5)")
@click.option("--period-range", default="50-200", help="MA period range (e.g., 50-200)")
@click.option("--direction", default="both", type=click.Choice(["long_only", "short_only", "both"]))
@click.option("--cash", "initial_cash", type=float, default=10000.0)
@click.option("--commission", type=float, default=0.001)
@click.option("--timeframe", default="", help="Target timeframe for resampling")
def optimize(
    data: str,
    maximize: str,
    confirm_range: str,
    period_range: str,
    direction: str,
    initial_cash: float,
    commission: float,
    timeframe: str,
) -> None:
    """Run parameter optimization."""
    try:
        confirm_start, confirm_end = (int(x) for x in confirm_range.split("-"))
    except (ValueError, TypeError) as err:
        raise click.BadParameter(
            f"Expected format 'START-END' (e.g., '0-5'), got '{confirm_range}'",
            param_hint="'--confirm-range'",
        ) from err

    try:
        period_start, period_end = (int(x) for x in period_range.split("-"))
    except (ValueError, TypeError) as err:
        raise click.BadParameter(
            f"Expected format 'START-END' (e.g., '50-200'), got '{period_range}'",
            param_hint="'--period-range'",
        ) from err

    period_range_obj = range(period_start, period_end + 1)

    from src.config import BacktestConfig, DataConfig, SizingConfig, StrategyConfig

    cfg = Config(
        strategy=StrategyConfig(
            ma_type="EMA",
            ma_period=99,
            confirmation_candles=0,
            direction=direction,
        ),
        sizing=SizingConfig(),
        backtest=BacktestConfig(initial_cash=initial_cash, commission=commission),
        data=DataConfig(path=data, timeframe=timeframe),
    )

    logger.info(f"Running optimization on {data}")
    result = run_optimization(
        cfg,
        param_name="ma_period",
        param_range=period_range_obj,
        maximize=maximize,
    )

    optimized_params = result["optimized_params"]
    stats = result["stats"]

    click.echo(f"\nOptimized ma_period: {optimized_params.get('ma_period')}")
    click.echo(f"Return [%]: {stats.get('Return [%]', 0):.2f}")
    click.echo(f"Sharpe Ratio: {stats.get('Sharpe Ratio', 0):.2f}")
    click.echo(f"Max Drawdown [%]: {stats.get('Max. Drawdown [%]', 0):.2f}")
    click.echo(f"# Trades: {stats.get('# Trades', 0)}")
    click.echo(f"\nResults saved to: {result['results_dir']}")


@cli.command()
@click.option("--port", default=5000, help="Port for Flask app")
@click.option("--host", default="127.0.0.1", help="Host for Flask app")
@click.option("--debug/--no-debug", default=False, help="Enable debug mode (development only)")
def web(port: int, host: str, debug: bool) -> None:
    """Launch the web viewer."""
    import web.app

    web.app.app.run(host=host, port=port, debug=debug)


@cli.command()
@click.option("--port", default=8501, help="Port for Streamlit app")
def dashboard(port: int) -> None:
    """Launch the Streamlit dashboard."""
    import subprocess

    subprocess.run(
        ["streamlit", "run", "streamlit_app/app.py", "--server.port", str(port)],
        check=True,
    )


if __name__ == "__main__":
    cli()
