import json
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from memory import Memory

logger = logging.getLogger(__name__)

try:
    import litellm
    litellm_available = True
except ImportError:
    litellm_available = False
    logger.warning("litellm not installed. Using fallback mock reflection.")

def run_reflection(trade_record: dict, session: Any) -> None:
    trade_json = json.dumps(trade_record, indent=2)
    session_json = json.dumps(session.to_dict(), indent=2)
    
    prompt = f"""You are Argus, a learning AI trading guardian, analyzing a completed paper trade to improve future discipline and capital protection.
    
    Trade details: {trade_json}
    Session context: {session_json}
    
    Respond in JSON only:
    {{
      'what_worked': str,
      'what_failed': str,
      'confidence_calibration': str,  # was confidence score appropriate?
      'regime_accuracy': str,          # did regime prediction hold?
      'rule_improvement': str,         # one specific rule to adjust
      'next_cycle_note': str           # one sentence for the next decision
    }}"""
    
    reflection_text = ""
    if litellm_available:
        try:
            response = litellm.completion(
                model="claude-sonnet-4-6", # as requested
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            reflection_text = response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}. Using fallback.")
            reflection_text = json.dumps({
                "what_worked": "Fallback: Trade executed and closed.",
                "what_failed": "Fallback: LLM unreachable.",
                "confidence_calibration": "Fallback: Unable to assess.",
                "regime_accuracy": "Fallback: Unable to assess.",
                "rule_improvement": "Fallback: Check API keys.",
                "next_cycle_note": "Fallback: Proceed with caution."
            })
    else:
        reflection_text = json.dumps({
            "what_worked": "Mock: Trade executed.",
            "what_failed": "Mock: litellm missing.",
            "confidence_calibration": "Mock: N/A",
            "regime_accuracy": "Mock: N/A",
            "rule_improvement": "Mock: Install litellm.",
            "next_cycle_note": "Mock: Next cycle."
        })
        
    # Store in ChromaDB
    try:
        mem = Memory()
        mem.store_reflection(reflection_text, trade_record["trade_id"])
    except Exception as e:
        logger.error(f"Failed to store reflection in ChromaDB: {e}")
        
    # Append to reflections.jsonl
    log_entry = {
        "trade_id": trade_record["trade_id"],
        "session_id": session.session_id,
        "reflection": reflection_text,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    with open("reflections.jsonl", "a") as f:
        f.write(json.dumps(log_entry) + "\n")
        
    # Update stats.json
    _update_stats(trade_record)

def _update_stats(trade_record: dict) -> None:
    stats_file = "stats.json"
    stats = {
        "total_trades": 0,
        "wins": 0,
        "total_pnl_pct": 0.0,
        "total_rr": 0.0,
        "confidence_on_wins": [],
        "confidence_on_losses": [],
        "regime_performance": {},
        "confidence_accuracy": {
            "bucket_0.6": {"trades": 0, "wins": 0},
            "bucket_0.7": {"trades": 0, "wins": 0},
            "bucket_0.8": {"trades": 0, "wins": 0},
            "bucket_0.9": {"trades": 0, "wins": 0}
        }
    }
    
    if os.path.exists(stats_file):
        try:
            with open(stats_file, "r") as f:
                stats = json.load(f)
        except json.JSONDecodeError:
            pass
            
    pnl_pct = trade_record.get("pnl_pct", 0.0)
    is_win = pnl_pct > 0
    composite_conf = trade_record.get("confidence_score", {}).get("composite_confidence", 0.0)
    regime = trade_record.get("regime", "UNKNOWN")
    
    stats["total_trades"] += 1
    if is_win:
        stats["wins"] += 1
        stats["confidence_on_wins"].append(composite_conf)
    else:
        stats["confidence_on_losses"].append(composite_conf)
        
    stats["total_pnl_pct"] += pnl_pct
    
    # Simplified R:R calc (assuming 1R = stop distance, just using pnl_pct as proxy)
    stats["total_rr"] += pnl_pct 
    
    # Regime performance
    if regime not in stats["regime_performance"]:
        stats["regime_performance"][regime] = {"trades": 0, "wins": 0, "avg_pnl": 0.0}
    stats["regime_performance"][regime]["trades"] += 1
    if is_win: stats["regime_performance"][regime]["wins"] += 1
    # Running avg approx
    curr_avg = stats["regime_performance"][regime]["avg_pnl"]
    stats["regime_performance"][regime]["avg_pnl"] = curr_avg + ((pnl_pct - curr_avg) / stats["regime_performance"][regime]["trades"])
    
    # Confidence Accuracy Buckets
    bucket = "bucket_0.6"
    if composite_conf >= 0.9: bucket = "bucket_0.9"
    elif composite_conf >= 0.8: bucket = "bucket_0.8"
    elif composite_conf >= 0.7: bucket = "bucket_0.7"
    
    stats["confidence_accuracy"][bucket]["trades"] += 1
    if is_win: stats["confidence_accuracy"][bucket]["wins"] += 1
    
    with open(stats_file, "w") as f:
        json.dump(stats, f, indent=2)
