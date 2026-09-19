"""quantbot — Korean equities quant trading bot.

Layers (mirrors the development plan):
  data/       price collection & storage (pykrx backfill, KIS daily/minute bars)
  strategy/   signal generation (volatility breakout, dual momentum, mean reversion)
  backtest/   event-driven simulator with KRX costs, plus metrics & walk-forward
  execution/  KIS OpenAPI REST client (paper/real), rate-limited
  risk/       position sizing, daily loss limit, kill switch
  notify/     Telegram alerts
"""

__version__ = "0.1.0"
