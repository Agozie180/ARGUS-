import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any
from datetime import datetime
import json
import logging
from config import settings

logger = logging.getLogger(__name__)

class Memory:
    def __init__(self, path: str = settings.CHROMA_PATH):
        self.client = chromadb.PersistentClient(path=path)
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        self.trades_collection = self.client.get_or_create_collection(
            name="trades",
            embedding_function=self.embedding_function
        )
        self.regimes_collection = self.client.get_or_create_collection(
            name="regimes",
            embedding_function=self.embedding_function
        )
        self.reflections_collection = self.client.get_or_create_collection(
            name="reflections",
            embedding_function=self.embedding_function
        )

    def _flatten_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """ChromaDB metadata must be primitive types. Flatten dicts and lists."""
        flat = {}
        for k, v in metadata.items():
            if isinstance(v, (str, int, float, bool)):
                flat[k] = v
            elif isinstance(v, dict):
                for dk, dv in v.items():
                    if isinstance(dv, (str, int, float, bool)):
                        flat[f"{k}_{dk}"] = dv
                    else:
                        flat[f"{k}_{dk}"] = str(dv)
            else:
                flat[k] = str(v)
        return flat

    def store_trade(self, trade_dict: Dict[str, Any]) -> None:
        trade_id = trade_dict.get("trade_id", f"trade_{int(datetime.now().timestamp() * 1000)}")
        
        conf = trade_dict.get("confidence_score", {})
        text = (
            f"Trade {trade_id}: Symbol {trade_dict.get('symbol')}, "
            f"Direction {trade_dict.get('direction')}, "
            f"Regime {trade_dict.get('regime')}, "
            f"Composite Confidence {conf.get('composite_confidence', 'N/A')}, "
            f"Reasoning: {trade_dict.get('reasoning', 'N/A')}"
        )
        
        metadata = self._flatten_metadata(trade_dict)
        
        self.trades_collection.add(
            ids=[trade_id],
            documents=[text],
            metadatas=[metadata]
        )

    def store_regime(self, regime_snapshot_dict: Dict[str, Any]) -> None:
        regime_id = regime_snapshot_dict.get("regime_id", f"regime_{int(datetime.now().timestamp() * 1000)}")
        text = f"Regime snapshot: {json.dumps(regime_snapshot_dict, default=str)}"
        
        metadata = self._flatten_metadata(regime_snapshot_dict)
        
        self.regimes_collection.add(
            ids=[regime_id],
            documents=[text],
            metadatas=[metadata]
        )

    def store_reflection(self, text: str, trade_id: str) -> None:
        reflection_id = f"reflection_{trade_id}_{int(datetime.now().timestamp())}"
        
        self.reflections_collection.add(
            ids=[reflection_id],
            documents=[text],
            metadatas=[{"trade_id": trade_id}]
        )

    def retrieve_similar_regimes(self, feature_vector: List[float], n: int = 5) -> List[Dict[str, Any]]:
        results = self.regimes_collection.query(
            query_embeddings=[feature_vector],
            n_results=n
        )
        
        past_outcomes = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                past_outcomes.append({
                    "document": doc,
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i]
                })
        return past_outcomes

    def retrieve_recent_trades(self, session_id: str, n: int = 20) -> List[Dict[str, Any]]:
        results = self.trades_collection.get(
            where={"session_id": session_id},
            limit=n
        )
        
        trades = []
        if results and results.get("ids"):
            for i, trade_id in enumerate(results["ids"]):
                trades.append({
                    "trade_id": trade_id,
                    "document": results["documents"][i],
                    "metadata": results["metadatas"][i]
                })
        return trades

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        results = self.trades_collection.get(
            where={"session_id": session_id}
        )
        
        if not results or not results.get("ids"):
            return {
                "session_id": session_id,
                "win_rate": 0.0,
                "avg_rr": 0.0,
                "regime_breakdown": {},
                "total_trades": 0
            }
            
        total_trades = len(results["ids"])
        wins = 0
        rr_sum = 0.0
        regime_breakdown = {}
        
        for meta in results["metadatas"]:
            pnl = float(meta.get("pnl", 0.0))
            if pnl > 0:
                wins += 1
                
            rr = float(meta.get("rr", 0.0))
            rr_sum += rr
            
            regime = meta.get("last_regime", "UNKNOWN")
            if regime not in regime_breakdown:
                regime_breakdown[regime] = {"count": 0, "wins": 0}
            regime_breakdown[regime]["count"] += 1
            if pnl > 0:
                regime_breakdown[regime]["wins"] += 1
                
        return {
            "session_id": session_id,
            "total_trades": total_trades,
            "win_rate": wins / total_trades if total_trades > 0 else 0.0,
            "avg_rr": rr_sum / total_trades if total_trades > 0 else 0.0,
            "regime_breakdown": regime_breakdown
        }
