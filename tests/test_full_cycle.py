import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, patch, MagicMock

# Ensure we can import project files
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import SessionState, Direction, RegimeEnum
from bitget_client import BitgetClient

async def run_test():
    print("🧪 INITIALIZING FULL SYSTEM TEST...")
    
    # 1. Mock Bitget Client to avoid needing actual CLI/API
    print("  [1/5] Mocking Bitget Client...")
    mock_bitget = MagicMock(spec=BitgetClient)
    
    # Mock technical data to trigger a BULL regime
    mock_tech_data = {
        "15m": {"signal": 0.8, "adx": 30, "atr": 500, "ema_20": 61000, "ema_50": 60000, "ema_200": 59000, "volume": 100},
        "1h": {"signal": 0.8, "adx": 30, "atr": 500, "ema_20": 61000, "ema_50": 60000, "ema_200": 59000, "volume": 100},
        "4h": {"signal": 0.8, "adx": 30, "atr": 500, "ema_20": 61000, "ema_50": 60000, "ema_200": 59000, "volume": 100},
        "1d": {"signal": 0.8, "adx": 30, "atr": 500, "ema_20": 61000, "ema_50": 60000, "ema_200": 59000, "volume": 100},
        "support": 59000, "resistance": 62000, "close": 61500
    }
    mock_bitget.get_technical_analysis = AsyncMock(return_value=mock_tech_data)
    mock_bitget.get_sentiment = AsyncMock(return_value={"fear_greed_index": 75, "btc_funding_rate": 0.0})
    mock_bitget.get_news = AsyncMock(return_value={"headlines": ["BTC moon"], "sentiment_score": 0.8})
    mock_bitget.get_macro = AsyncMock(return_value={"etf_net_flow_24h": 50000000, "whale_net_flow": -10000000, "dxy_trend": "WEAKENING"})
    mock_bitget.get_ticker = AsyncMock(return_value={"lastPrice": 61500.0, "bidPrice": 61490.0, "askPrice": 61510.0})
    mock_bitget.get_balance = AsyncMock(return_value={"totalEquity": 10000.0})
    
    # 2. Initialize State
    print("  [2/5] Initializing Session & Memory...")
    session = SessionState()
    
    # 3. Run Perception
    print("  [3/5] Running Perception Swarm...")
    with patch('agents.technical_agent.bitget', mock_bitget), \
         patch('agents.sentiment_agent.bitget', mock_bitget), \
         patch('agents.onchain_macro_agent.bitget', mock_bitget), \
         patch('decision_engine.litellm_available', False): # Force rule-based for deterministic test
         
        from agents.technical_agent import perceive as tech_p
        from agents.sentiment_agent import perceive as sent_p
        from agents.onchain_macro_agent import perceive as macro_p
        from regime_classifier import classify_regime
        from decision_engine import decide
        from risk_guardian import assess_risk
        from executor import execute_paper
        
        tech_snap, tech_conf = await tech_p("BTCUSDT", session)
        sent_snap, sent_conf = await sent_p("BTCUSDT", session)
        macro_snap, macro_conf = await macro_p("BTCUSDT", session)
        
        assert tech_conf > 0.7, "Technical confidence should be high"
        print(f"     ✓ Tech Conf: {tech_conf:.2f}, Sent Conf: {sent_conf:.2f}, Macro Conf: {macro_conf:.2f}")
        
        # 4. Regime & Decision
        print("  [4/5] Running Regime Classifier & Decision Engine...")
        regime_state = classify_regime(tech_snap, sent_snap, macro_snap, session)
        assert regime_state.regime == RegimeEnum.TRENDING_BULL, "Regime should be TRENDING_BULL"
        print(f"     ✓ Regime: {regime_state.regime.value}")
        
        decision = await decide("BTCUSDT", tech_snap, tech_conf, sent_snap, sent_conf, macro_snap, macro_conf, regime_state, session)
        assert decision.action == Direction.BUY, "Action should be BUY"
        assert decision.confidence_score.gate_passed == True, "Gate should pass"
        print(f"     ✓ Action: {decision.action.value} | Gate Passed: {decision.confidence_score.gate_passed}")
        
        # 5. Risk & Execution
        print("  [5/5] Running Risk Guardian & Executor...")
        with patch('risk_guardian.bitget', mock_bitget), patch('executor.bitget', mock_bitget):
            risk_decision = await assess_risk(decision, session)
            assert risk_decision.approved == True, "Risk should be approved"
            print(f"     ✓ Risk Approved. Size: ${risk_decision.adjusted_size_usd:.2f}")
            
            trade_rec = await execute_paper(decision, risk_decision, session)
            assert trade_rec is not None, "Trade should execute"
            assert os.path.exists("paper_trades.jsonl"), "paper_trades.jsonl should be created"
            print(f"     ✓ Trade Executed. ID: {trade_rec.trade_id}")
            
    print("\n[bold green]✅ ALL TESTS PASSED. SYSTEM IS LEGENDARY.[/]")

if __name__ == "__main__":
    # Clean up test files before run
    for f in ["paper_trades.jsonl", "decisions.jsonl", "regime_log.jsonl"]:
        if os.path.exists(f): os.remove(f)
        
    asyncio.run(run_test())