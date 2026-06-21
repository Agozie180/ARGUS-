import os
import json
import asyncio
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from typing import List, Dict, Any

from config import settings, SessionState, Direction, RegimeEnum, ConfidenceScore
from regime_classifier import classify_regime
from decision_engine import decide
from risk_guardian import assess_risk
from memory import Memory

logger = logging.getLogger(__name__)
console = Console()

def generate_mock_klines(symbol: str, days: int = 180) -> pd.DataFrame:
    """Generates mock 1h klines for backtesting if real data is unavailable."""
    np.random.seed(42)
    periods = days * 24
    dates = pd.date_range(end=datetime.now(), periods=periods, freq='1h')
    
    if "BTC" in symbol:
        start_price = 60000
    elif "ETH" in symbol:
        start_price = 3000
    else:
        start_price = 100
        
    returns = np.random.normal(0.0001, 0.02, periods)
    prices = start_price * np.exp(np.cumsum(returns))
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices * (1 + np.random.uniform(-0.005, 0.005, periods)),
        'high': prices * (1 + np.abs(np.random.normal(0, 0.01, periods))),
        'low': prices * (1 - np.abs(np.random.normal(0, 0.01, periods))),
        'close': prices,
        'volume': np.random.uniform(10, 1000, periods)
    })
    return df

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates technical indicators for backtest simulation."""
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    df['atr'] = (df['high'] - df['low']).rolling(window=14).mean()
    df['atr_pct'] = (df['atr'] / df['close']) * 100
    
    # Simple ADX proxy
    df['adx'] = np.where(abs(df['close'].pct_change(10)) * 100 > 2, 30, 15)
    
    # BB
    df['bb_mid'] = df['close'].rolling(window=20).mean()
    df['bb_std'] = df['close'].rolling(window=20).std()
    df['bb_lower'] = df['bb_mid'] - (df['bb_std'] * 2)
    df['bb_upper'] = df['bb_mid'] + (df['bb_std'] * 2)
    
    df['high_20'] = df['high'].rolling(window=20).max()
    df['low_20'] = df['low'].rolling(window=20).min()
    
    return df.dropna()

def simulate_snapshot(row: pd.Series, symbol: str):
    """Converts a historical df row into snapshot dicts for the engine."""
    from agents.technical_agent import TechnicalSnapshot
    from agents.sentiment_agent import SentimentSnapshot
    from agents.onchain_macro_agent import MacroSnapshot
    from config import FearGreedZone, InstitutionalBias
    
    adx = float(row['adx'])
    atr_p = float(min(100.0, max(0.0, row['atr_pct'] * 10)))
    
    if row['close'] > row['ema20'] > row['ema50']:
        ema_stack = "BULL"
        trend_dir = Direction.BUY
        regime_hint = RegimeEnum.TRENDING_BULL if adx > 25 else RegimeEnum.RANGING
    elif row['close'] < row['ema20'] < row['ema50']:
        ema_stack = "BEAR"
        trend_dir = Direction.SELL
        regime_hint = RegimeEnum.TRENDING_BEAR if adx > 25 else RegimeEnum.RANGING
    else:
        ema_stack = "MIXED"
        trend_dir = Direction.HOLD
        regime_hint = RegimeEnum.RANGING
        
    tech = TechnicalSnapshot(
        symbol=symbol, signal_strength=float(row['rsi']/100), trend_direction=trend_dir,
        adx=adx, atr_percentile=atr_p, ema_stack=ema_stack, support=float(row['low_20']),
        resistance=float(row['high_20']), timeframe_agreement=100.0 if trend_dir != Direction.HOLD else 0.0,
        regime_hint=regime_hint, raw_indicators={
            "close": float(row['close']), "atr": [float(row['atr'])], "rsi": float(row['rsi']),
            "bb_lower": float(row['bb_lower']), "bb_upper": float(row['bb_upper']),
            "high_20": float(row['high_20']), "low_20": float(row['low_20'])
        }, timestamp=row['timestamp']
    )
    tech_conf = 0.80 if adx > 25 else 0.60
    
    sent = SentimentSnapshot(
        fear_greed_index=50, fear_greed_zone=FearGreedZone.NEUTRAL, fear_greed_signal=Direction.HOLD,
        btc_long_short_ratio=1.0, eth_long_short_ratio=1.0, btc_funding_rate=0.0, eth_funding_rate=0.0,
        funding_signal=Direction.HOLD, news_headlines=[], news_sentiment_score=0.0,
        composite_sentiment=0.0, timestamp=row['timestamp']
    )
    sent_conf = 0.50
    
    macro = MacroSnapshot(
        etf_net_flow_24h=0.0, etf_flow_signal=Direction.HOLD, whale_net_flow=0.0,
        whale_signal=Direction.HOLD, btc_nasdaq_correlation=0.0, dxy_trend="FLAT",
        macro_headwind=False, institutional_bias=InstitutionalBias.NEUTRAL,
        macro_score=0.0, timestamp=row['timestamp']
    )
    macro_conf = 0.50
    
    return tech, tech_conf, sent, sent_conf, macro, macro_conf

async def run_backtest():
    symbols = ["BTCUSDT", "ETHUSDT"]
    total_days = 180
    in_sample = 90
    out_sample = 30
    step = 30
    
    all_results = []
    
    for symbol in symbols:
        console.print(f"\n[bold cyan]Loading data for {symbol}...[/]")
        df = generate_mock_klines(symbol, total_days)
        df = calculate_indicators(df)
        
        # Walk-forward windows
        for i in range(0, total_days - in_sample - out_sample + 1, step):
            start_idx = i * 24
            end_idx = (i + in_sample + out_sample) * 24
            test_start = (i + in_sample) * 24
            
            window_df = df.iloc[test_start:end_idx].copy()
            if window_df.empty: continue
            
            session = SessionState()
            session.daily_pnl_pct = 0.0 # Track pct directly
            cum_return = 0.0           # running cumulative return for the equity curve
            equity_curve = [1.0]
            trades = []
            gated_count = 0
            passed_count = 0
            passed_wins = 0
            gated_wins = 0 # Would-be wins if we took the trade
            
            for idx, row in window_df.iterrows():
                tech, tech_c, sent, sent_c, macro, macro_c = simulate_snapshot(row, symbol)
                regime = classify_regime(tech, sent, macro, session)
                session.last_regime = regime.regime
                
                decision = await decide(symbol, tech, tech_c, sent, sent_c, macro, macro_c, regime, session)

                if not decision.confidence_score.gate_passed:
                    gated_count += 1
                    # Simulate what would have happened had we taken the blocked trade
                    if decision.action != Direction.NO_TRADE:
                        try:
                            future_ret = window_df.loc[idx:, 'close'].pct_change(24).iloc[24] if idx + 24 < window_df.index[-1] else 0
                        except (IndexError, KeyError):
                            future_ret = 0
                        if (decision.action == Direction.BUY and future_ret > 0) or (decision.action == Direction.SELL and future_ret < 0):
                            gated_wins += 1
                    continue

                if decision.action != Direction.NO_TRADE:
                    passed_count += 1
                    risk = await assess_risk(decision, session)
                    if risk.approved:
                        # Simulate trade outcome 24 bars later
                        future_idx = idx + 24
                        if future_idx < window_df.index[-1]:
                            entry = row['close']
                            exit_p = window_df.loc[future_idx, 'close']
                            if decision.action == Direction.BUY:
                                pnl_pct = (exit_p - entry) / entry
                            else:
                                pnl_pct = (entry - exit_p) / entry
                            
                            session.update_after_trade(pnl_pct)
                            cum_return += pnl_pct
                            session.daily_pnl_pct = cum_return
                            trades.append({"pnl": pnl_pct, "regime": regime.regime.value})
                            if pnl_pct > 0: passed_wins += 1

                session.cycle_count += 1
                equity_curve.append(1.0 + cum_return)
                
            # Window Metrics
            total_trades = len(trades)
            wins = sum(1 for t in trades if t['pnl'] > 0)
            win_rate = wins / total_trades if total_trades > 0 else 0
            
            equity = pd.Series(equity_curve)
            returns = equity.pct_change().dropna()
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252*24) if returns.std() > 0 else 0
            sortino = (returns.mean() / returns[returns < 0].std()) * np.sqrt(252*24) if len(returns[returns < 0]) > 0 else 0
            
            peak = equity.expanding(min_periods=1).max()
            dd = (equity/peak) - 1
            max_dd = dd.min()
            
            all_results.append({
                "Symbol": symbol,
                "Window Start": window_df.iloc[0]['timestamp'].strftime('%Y-%m-%d'),
                "Trades": total_trades,
                "Win Rate": f"{win_rate:.1%}",
                "Sharpe": f"{sharpe:.2f}",
                "Sortino": f"{sortino:.2f}",
                "Max DD": f"{max_dd:.1%}",
                "Gated": gated_count,
                "Passed WR": f"{(passed_wins/passed_count):.1%}" if passed_count > 0 else "N/A",
                "Gated WR": f"{(gated_wins/gated_count):.1%}" if gated_count > 0 else "N/A"
            })
            
            # Save Equity Curve
            plt.figure(figsize=(10, 5))
            plt.plot(equity.values)
            plt.title(f"{symbol} Equity Curve ({window_df.iloc[0]['timestamp'].strftime('%Y-%m-%d')})")
            plt.savefig(f"equity_curve_{symbol}_{i}.png")
            plt.close()

    # Output Rich Table
    table = Table(title="Walk-Forward Backtest Results")
    table.add_column("Symbol", style="cyan")
    table.add_column("Window Start", style="white")
    table.add_column("Trades", justify="right", style="yellow")
    table.add_column("Win Rate", justify="right", style="green")
    table.add_column("Sharpe", justify="right")
    table.add_column("Sortino", justify="right")
    table.add_column("Max DD", justify="right", style="red")
    table.add_column("Gated", justify="right", style="magenta")
    table.add_column("Passed WR", justify="right", style="bold green")
    table.add_column("Gated WR", justify="right", style="bold red")

    for r in all_results:
        table.add_row(*[str(v) for v in r.values()])

    console.print(table)
    
    # Save CSV
    pd.DataFrame(all_results).to_csv("backtest_results.csv", index=False)
    console.print("\n[bold green]Backtest complete. Saved to backtest_results.csv and equity_curve_*.png[/]")

if __name__ == "__main__":
    asyncio.run(run_backtest())
