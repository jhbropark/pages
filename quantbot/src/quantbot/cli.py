"""CLI — 데이터 수집, 백테스트, walk-forward, KIS 계좌 스모크 테스트.

예시:
  quantbot fetch 005930 --start 20200102 --end 20251230
  quantbot backtest 005930 --strategy vb --k 0.5
  quantbot walkforward 005930
  quantbot price 005930          # KIS 키 필요
  quantbot balance               # KIS 키 필요
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

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
