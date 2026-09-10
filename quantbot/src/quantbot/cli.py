"""CLI — 데이터 수집, 백테스트, walk-forward, KIS 계좌 스모크 테스트.

예시:
  quantbot fetch 005930 --start 20200102 --end 20251230
  quantbot backtest 005930 --strategy vb --k 0.5
  quantbot walkforward 005930
  quantbot price 005930          # KIS 키 필요
  quantbot balance               # KIS 키 필요
  quantbot run 005930,000660 --strategy vb        # 장중 실행 루프 (KIS 키 필요)
  quantbot run 005930 --demo                       # 오프라인 데모 (키 불필요)
"""

from __future__ import annotations

import argparse
import json
import logging

from .backtest.engine import run_backtest
from .backtest.metrics import summarize
from .backtest.walkforward import run_walk_forward
from .config import load_settings
from .data.store import load_ohlcv, save_ohlcv
from .strategy.mean_reversion import BollingerReversion
from .strategy.volatility_breakout import VolatilityBreakout

log = logging.getLogger(__name__)


def _make_strategy(args: argparse.Namespace):
    if args.strategy == "vb":
        return VolatilityBreakout(k=args.k)
    if args.strategy == "mr":
        return BollingerReversion()
    raise SystemExit(f"알 수 없는 전략: {args.strategy}")


def cmd_fetch(args: argparse.Namespace) -> None:
    from .data.collector import fetch_daily

    df = fetch_daily(args.ticker, args.start, args.end, source=args.source)
    path = save_ohlcv(df, args.ticker)
    print(f"{args.ticker}: {len(df)}개 봉 저장 → {path}")


def cmd_backtest(args: argparse.Namespace) -> None:
    settings = load_settings()
    df = load_ohlcv(args.ticker, start=args.start_date, end=args.end_date)
    result = run_backtest(df, _make_strategy(args), args.cash, settings.costs)
    print(json.dumps(summarize(result.equity, result.trades_df), indent=2))


def cmd_walkforward(args: argparse.Namespace) -> None:
    settings = load_settings()
    df = load_ohlcv(args.ticker, start=args.start_date, end=args.end_date)
    grid = [{"k": k / 10} for k in range(3, 9)]  # k = 0.3 ~ 0.8
    result = run_walk_forward(
        df, VolatilityBreakout, grid, initial_cash=args.cash, costs=settings.costs
    )
    print(json.dumps({"windows": result["windows"], "oos": result["summary"]}, indent=2))


def cmd_price(args: argparse.Namespace) -> None:
    from .execution.kis_client import KISClient

    client = KISClient(load_settings().kis)
    out = client.current_price(args.ticker)
    print(f"{args.ticker} 현재가 {int(out['stck_prpr']):,}원 (전일대비 {out['prdy_vrss']})")


def cmd_balance(args: argparse.Namespace) -> None:
    from .execution.kis_client import KISClient

    client = KISClient(load_settings().kis)
    data = client.balance()
    total = data["output2"][0]
    print(f"[{load_settings().kis.env}] 총평가금액 {int(total['tot_evlu_amt']):,}원")
    for holding in data["output1"]:
        if int(holding["hldg_qty"]) > 0:
            print(
                f"  {holding['pdno']} {holding['prdt_name']}: "
                f"{int(holding['hldg_qty'])}주, 평가 {int(holding['evlu_amt']):,}원"
            )


def _make_strategy_for(strategy: str, k: float):
    if strategy == "vb":
        return VolatilityBreakout(k=k)
    if strategy == "mr":
        return BollingerReversion()
    raise SystemExit(f"알 수 없는 전략: {strategy}")


def cmd_run(args: argparse.Namespace) -> None:
    from .notify.telegram import TelegramNotifier
    from .risk.manager import RiskManager
    from .runtime.engine import LiveEngine

    settings = load_settings()
    tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
    if not tickers:
        raise SystemExit("종목코드를 하나 이상 지정하세요")
    strategies = {t: _make_strategy_for(args.strategy, args.k) for t in tickers}
    notifier = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)
    risk = RiskManager(settings.risk)

    if args.demo:
        _run_demo(tickers, strategies, risk, notifier, args.cash, args.k)
        return

    if args.dry_run:
        from .execution.broker import DryRunBroker

        histories = {t: load_ohlcv(t) for t in tickers}
        prices = {t: float(df["close"].iloc[-1]) for t, df in histories.items()}
        broker = DryRunBroker(cash=args.cash, prices=prices)
        # dry-run 시세는 정지 상태 — 시가 주문 경로만 검증(intraday stop 미발동)
        history_provider = lambda t: histories[t].iloc[:-1]  # noqa: E731
    else:
        from .execution.broker import KISBroker
        from .execution.kis_client import KISClient

        broker = KISBroker(KISClient(settings.kis))
        history_provider = load_ohlcv

    engine = LiveEngine(broker, strategies, risk, notifier, history_provider)
    if args.once:
        engine.open_session()
        engine.poll()
        engine.close_session()
    else:
        from .runtime import scheduler

        scheduler.run(engine, poll_interval=args.interval)


def _run_demo(tickers, strategies, risk, notifier, cash, k) -> None:
    """오프라인 데모 — 합성 일봉 + 모의 장중 랠리로 매수→결산 한 사이클 시연."""
    import numpy as np
    import pandas as pd

    from .execution.broker import DryRunBroker
    from .runtime.engine import LiveEngine

    histories: dict[str, pd.DataFrame] = {}
    opens: dict[str, float] = {}
    for i, ticker in enumerate(tickers):
        rng = np.random.default_rng(1 + i)
        n = 60
        dates = pd.bdate_range("2026-01-02", periods=n)
        close = 50_000 * np.exp(np.cumsum(rng.normal(0.0005, 0.015, n)))
        open_ = close * (1 + rng.normal(0, 0.004, n))
        high = np.maximum(open_, close) * (1 + rng.uniform(0, 0.015, n))
        low = np.minimum(open_, close) * (1 - rng.uniform(0, 0.015, n))
        df = pd.DataFrame(
            {"open": open_, "high": high, "low": low, "close": close,
             "volume": rng.integers(1_000_000, 5_000_000, n)},
            index=dates,
        ).round(0)
        df.index.name = "date"
        histories[ticker] = df
        opens[ticker] = float(df["close"].iloc[-1])  # 당일 시가 ≈ 전일 종가

    broker = DryRunBroker(cash=cash, prices=dict(opens), opens=opens)
    engine = LiveEngine(broker, strategies, risk, notifier, lambda t: histories[t])

    print("=== [DEMO] 장 시작 ===")
    engine.open_session()
    print("=== [DEMO] 장중 +3% 랠리 (변동성 돌파 트리거 유도) ===")
    for ticker in tickers:
        broker.set_price(ticker, opens[ticker] * 1.03)
    engine.poll()
    print("=== [DEMO] 장 마감 ===")
    engine.close_session()
    snap = broker.snapshot()
    print(f"\n체결 내역: {broker.fills or '없음'}")
    print(f"최종 평가금액: {snap.total_equity:,.0f}원, 보유: "
          f"{ {t: p.qty for t, p in snap.positions.items()} }")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(prog="quantbot")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("fetch", help="일봉 백필 (기본 소스: FinanceDataReader)")
    p.add_argument("ticker")
    p.add_argument("--start", default="20200102")
    p.add_argument("--end", default="20261231")
    p.add_argument("--source", choices=["fdr", "pykrx"], default="fdr")
    p.set_defaults(func=cmd_fetch)

    for name, func in (("backtest", cmd_backtest), ("walkforward", cmd_walkforward)):
        p = sub.add_parser(name)
        p.add_argument("ticker")
        p.add_argument("--strategy", choices=["vb", "mr"], default="vb")
        p.add_argument("--k", type=float, default=0.5)
        p.add_argument("--cash", type=float, default=10_000_000)
        p.add_argument("--start-date", default=None)
        p.add_argument("--end-date", default=None)
        p.set_defaults(func=func)

    p = sub.add_parser("price", help="KIS 현재가 조회 (API 키 필요)")
    p.add_argument("ticker")
    p.set_defaults(func=cmd_price)

    p = sub.add_parser("balance", help="KIS 잔고 조회 (API 키 필요)")
    p.set_defaults(func=cmd_balance)

    p = sub.add_parser("run", help="장중 실행 루프 (스케줄러). --demo 는 오프라인 시연")
    p.add_argument("tickers", help="쉼표 구분 종목코드 (예: 005930,000660)")
    p.add_argument("--strategy", choices=["vb", "mr"], default="vb")
    p.add_argument("--k", type=float, default=0.5)
    p.add_argument("--cash", type=float, default=10_000_000)
    p.add_argument("--interval", type=float, default=30.0, help="장중 폴링 주기(초)")
    p.add_argument("--once", action="store_true", help="한 사이클만 즉시 실행")
    p.add_argument("--dry-run", action="store_true", help="모의 브로커 (주문 미전송)")
    p.add_argument("--demo", action="store_true", help="합성 데이터 오프라인 시연 (키 불필요)")
    p.set_defaults(func=cmd_run)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
