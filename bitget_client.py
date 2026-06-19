import asyncio
import json
import time
import logging
from typing import Any, Dict, List, Optional
from config import settings

logger = logging.getLogger(__name__)

class BitgetSkillError(Exception):
    pass

class BitgetRateLimitError(Exception):
    pass

class BitgetConnectionError(Exception):
    pass

class TokenBucket:
    def __init__(self, rate: float, capacity: float):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_refill = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self) -> bool:
        async with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_refill = now
            
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            return False

class BitgetClient:
    def __init__(self):
        self.paper_trading = settings.PAPER_TRADING
        self.bucket = TokenBucket(rate=20.0, capacity=20.0)
        self.cache: Dict[str, tuple[float, Any]] = {}
        self.cache_ttl = 300.0  # 5 minutes

    async def _run_bgc(self, skill: str, args: List[str]) -> Dict[str, Any]:
        while not await self.bucket.acquire():
            await asyncio.sleep(0.05)
            
        cmd = ["bgc", "skill", skill] + args + ["--output", "json"]
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
            
            if proc.returncode != 0:
                err_msg = stderr.decode().strip()
                if "rate limit" in err_msg.lower():
                    raise BitgetRateLimitError(err_msg)
                raise BitgetSkillError(f"bgc failed: {err_msg}")
                
            return json.loads(stdout.decode())
        except asyncio.TimeoutError:
            raise BitgetConnectionError("bgc command timed out")
        except json.JSONDecodeError:
            raise BitgetSkillError("Invalid JSON response from bgc")
        except FileNotFoundError:
            raise BitgetConnectionError("bgc CLI not found. Please install Bitget Agent Hub CLI.")

    async def _call_skill(self, skill_name: str, cache_key: str, args: List[str], use_cache: bool = True) -> Dict[str, Any]:
        if use_cache and cache_key in self.cache:
            ts, data = self.cache[cache_key]
            if time.time() - ts < self.cache_ttl:
                logger.debug(f"Returning cached result for {skill_name}")
                return data
                
        try:
            result = await self._run_bgc(skill_name, args)
            self.cache[cache_key] = (time.time(), result)
            return result
        except (BitgetSkillError, BitgetConnectionError, BitgetRateLimitError) as e:
            if cache_key in self.cache:
                logger.warning(f"Skill {skill_name} unreachable. Returning stale cache. Error: {e}")
                return self.cache[cache_key][1]
            raise

    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        return await self._call_skill("market-intel", f"ticker_{symbol}", ["--symbol", symbol, "--type", "ticker"])

    async def get_klines(self, symbol: str, interval: str = "1h", limit: int = 200) -> Dict[str, Any]:
        return await self._call_skill("market-intel", f"klines_{symbol}_{interval}_{limit}", ["--symbol", symbol, "--type", "klines", "--interval", interval, "--limit", str(limit)])

    async def get_orderbook(self, symbol: str, depth: int = 10) -> Dict[str, Any]:
        return await self._call_skill("market-intel", f"orderbook_{symbol}_{depth}", ["--symbol", symbol, "--type", "orderbook", "--depth", str(depth)])

    async def get_balance(self) -> Dict[str, Any]:
        return await self._call_skill("market-intel", "balance", ["--type", "balance"], use_cache=False)

    async def get_positions(self) -> Dict[str, Any]:
        return await self._call_skill("market-intel", "positions", ["--type", "positions"], use_cache=False)

    async def get_technical_analysis(self, symbol: str) -> Dict[str, Any]:
        return await self._call_skill("technical-analysis", f"ta_{symbol}", ["--symbol", symbol])

    async def get_sentiment(self, symbol: str) -> Dict[str, Any]:
        return await self._call_skill("sentiment-analyst", f"sent_{symbol}", ["--symbol", symbol])

    async def get_news(self, symbol: str) -> Dict[str, Any]:
        return await self._call_skill("news-briefing", f"news_{symbol}", ["--symbol", symbol])

    async def get_macro(self) -> Dict[str, Any]:
        return await self._call_skill("macro-analyst", "macro", [])

    async def place_order(self, symbol: str, side: str, size: float, order_type: str = "market", price: Optional[float] = None) -> Dict[str, Any]:
        if self.paper_trading:
            return await self._paper_place_order(symbol, side, size, order_type, price)
        
        # Live path guarded by PAPER_TRADING check
        args = ["--symbol", symbol, "--side", side, "--size", str(size), "--type", order_type]
        if price:
            args.extend(["--price", str(price)])
        return await self._call_skill("place-order", f"order_{symbol}_{side}_{size}", args, use_cache=False)

    async def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        if self.paper_trading:
            return {"status": "CANCELED", "order_id": order_id, "symbol": symbol}
            
        args = ["--symbol", symbol, "--order-id", order_id]
        return await self._call_skill("cancel-order", f"cancel_{order_id}", args, use_cache=False)

    async def _paper_place_order(self, symbol: str, side: str, size: float, order_type: str, price: Optional[float]) -> Dict[str, Any]:
        try:
            ticker = await self.get_ticker(symbol)
            last_price = float(ticker.get("lastPrice", ticker.get("price", 0.0)))
            bid = float(ticker.get("bidPrice", last_price))
            ask = float(ticker.get("askPrice", last_price))
            mid = (bid + ask) / 2.0
        except Exception:
            if price:
                mid = price
            else:
                raise BitgetSkillError("Cannot simulate paper order without a market price.")
                
        # Slippage: 0.05% for BTC/ETH, 0.20% for meme coins
        slippage_pct = 0.0005 if "BTC" in symbol or "ETH" in symbol else 0.0020
        
        if side.lower() == "buy":
            fill_price = mid * (1 + slippage_pct)
        else:
            fill_price = mid * (1 - slippage_pct)
            
        order_id = f"paper_{int(time.time() * 1000)}"
        trade_record = {
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "size": size,
            "order_type": order_type,
            "requested_price": price if price else mid,
            "fill_price": fill_price,
            "timestamp": time.time(),
            "paper_trade": True
        }
        
        with open("paper_trades.jsonl", "a") as f:
            f.write(json.dumps(trade_record) + "\n")
            
        return {
            "status": "FILLED",
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "size": size,
            "fill_price": fill_price
        }
