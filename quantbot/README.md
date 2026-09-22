# quantbot — 한국 주식 퀀트 매매 봇

한국투자증권 KIS Developers OpenAPI + Python 기반. 백테스트부터 모의투자까지
단계적으로 검증한 뒤에만 실전에 투입하는 구조입니다.

## 구조 (개발 계획의 레이어 그대로)

```
src/quantbot/
├── data/        # pykrx 백필 + parquet 저장 (data/1d/<ticker>.parquet)
├── strategy/    # 변동성 돌파, 볼린저+RSI 평균회귀, 듀얼 모멘텀
├── backtest/    # 이벤트 방식 엔진 + 성과지표 + walk-forward 검증
├── execution/   # KIS REST 클라이언트 + Broker 어댑터 + WebSocket 체결통보
├── risk/        # 포지션 사이징, 일일 손실 한도, kill switch
├── runtime/     # 장중 실행 엔진(LiveEngine) + 장 시간 스케줄러
└── notify/      # Telegram 체결/에러/일일 결산 알림
```

`runtime/`는 백테스트에서 검증한 전략(`Strategy.on_bar`)을 그대로 실전에 태우는
얇은 어댑터다. `LiveEngine`이 하루를 open→poll→close 세션으로 돌리며 시가/stop
주문을 처리하고, 모든 매수는 `RiskManager` 게이트(비중 한도·일일 손실 한도·kill
switch)를 통과한다. `Broker` 추상화 덕에 실거래(`KISBroker`)와 오프라인
시뮬(`DryRunBroker`)이 동일 엔진으로 돈다.

백테스트 엔진이 반영하는 한국 시장 특수성: 수수료(기본 0.015%), 증권거래세
(매도 0.15%, 2025년 세율 — 과거 데이터는 `CostConfig`에서 0.18%로 조정),
슬리피지, 호가단위(2023년 개편 기준), 상·하한가 잠김 시 체결 불가,
거래정지일(거래량 0) 체결 불가.

## 설치

```bash
cd quantbot
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[data,dev]"      # 백테스트 + pykrx 데이터 수집
cp .env.example .env              # KIS 키 입력 (모의투자부터!)
```

## 사용

```bash
# 1. 과거 데이터 수집 (pykrx, API 키 불필요)
quantbot fetch 005930 --start 20200102 --end 20261231

# 2. 백테스트 — 변동성 돌파 k=0.5
quantbot backtest 005930 --strategy vb --k 0.5

# 3. walk-forward 검증 (train 2년 / test 6개월 롤링, k 그리드 탐색)
quantbot walkforward 005930

# 4. KIS 연결 확인 (모의투자 키 발급 후)
quantbot price 005930
quantbot balance

# 5. 장중 실행 루프 오프라인 데모 (합성 데이터, 키 불필요)
quantbot run 005930,000660 --demo

# 6. 장중 실행 루프 (KIS 모의투자 키 필요 — KIS_ENV=paper)
quantbot run 005930,000660 --strategy vb           # 스케줄러 상시 운영
quantbot run 005930 --dry-run --once               # 주문 미전송, 한 사이클만
```

`run`은 KRX 장 시간(09:00–15:30 KST)에 맞춰 자동으로 open→poll→close 세션을
돌린다. 실시간 체결 통보는 `execution/kis_websocket.py`(WebSocket, tr_id
H0STCNI0/H0STCNI9)로 받는다 — approval key 발급과 AES-CBC 복호화까지 구현돼 있고,
`.[live]` 익스트라(`websockets`, `pycryptodome`)가 필요하다.

## 개발 로드맵 체크리스트

- [x] **Phase 1** 프로젝트 구조, pykrx 데이터 파이프라인, KIS 인증/시세/주문/잔고
- [x] **Phase 2** 백테스트 엔진 (비용·호가단위·상하한가·거래정지 반영), 성과지표, walk-forward
- [x] **Phase 3** 변동성 돌파 · 평균회귀 · 듀얼 모멘텀(월 리밸런싱 근사)
- [x] **Phase 4** RiskManager: 비중 한도, 일일 손실 한도, kill switch (테스트 포함)
- [x] **Phase 5** 장중 실행 엔진(LiveEngine) + 장 시간 스케줄러 + WebSocket 체결통보 + `run` CLI (테스트 포함)
- [ ] **운영** 모의투자 1개월 → 소액 실전 → 클라우드 상시 운영 + Telegram 모니터링

## 테스트

```bash
pip install -e ".[dev]"
pytest
```

## 주의

- 모의투자 검증 없이 실전 키를 넣지 마세요. `KIS_ENV=paper`가 기본값입니다.
- 백테스트 수익률은 실전에서 절반만 나와도 성공입니다 — OOS(walk-forward)
  성과만 믿으세요.
- KIS API 호출 제한: 실전 초당 20건, 모의 초당 2건 (`RateLimiter`가 강제).
- 투자 손실 책임은 본인에게 있습니다. 감당 가능한 금액만 투입하세요.
