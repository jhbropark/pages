# 콘텐츠 파이프라인

일일 게시를 **모델 호출 없이** 돌리기 위해 생성과 렌더링을 분리했습니다.

```
content-refill.yml   (주 1회, 구독 인증)  ──▶  content/buffer.json
                                                     │
generate-content.yml (매일, 모델 호출 0)  ◀──────────┘
        │
        ├─ images/daily/*.jpg     (카드 렌더링)
        ├─ queue/queue.json       (Instagram 예약)
        └─ linkedin/queue.json    (LinkedIn 한/영 쌍)
```

## 왜 나눴나

2026-08-12부터 09-18까지 **38일 연속** 일일 워크플로가 같은 오류로 실패했습니다.

```
anthropic.BadRequestError: 400 — 'Your credit balance is too low ...'
```

첫 API 호출에서 터지므로 카드도, 큐도, PR도 만들어지지 않았고, 실패 알림이 없어
5주 동안 아무도 몰랐습니다.

분리하면 생성 실패가 **게시 실패로 번지지 않습니다.** 버퍼에 7일치가 있으면
리필이 일주일 늦어도 매일 게시는 계속됩니다. 그리고 버퍼 잔량은 매일 Telegram으로
보고되므로, 문제를 며칠 앞서 압니다.

## 크레딧을 쓰지 않는 경로

| 워크플로 | 주기 | 인증 | 비용 |
|---|---|---|---|
| `generate-content.yml` | 매일 06:00 KST | 없음 | Actions 분만 |
| `content-refill.yml` | 매주 월 05:00 KST | `CLAUDE_CODE_OAUTH_TOKEN` | **구독** (API 크레딧 아님) |

`CLAUDE_CODE_OAUTH_TOKEN`은 Claude Pro/Max/Team/Enterprise 구독으로 인증하는
토큰입니다. 공식 문서에 따르면 OAuth 토큰으로 인증할 때의 실행은 API 과금이 아니라
구독을 사용합니다.

발급:

```bash
claude setup-token          # 로컬에서 실행
# 출력된 토큰을 저장소 Secrets 에 CLAUDE_CODE_OAUTH_TOKEN 으로 추가
```

> **주의.** 공식 문서는 이 토큰을 "long-lived token"이라고 부르지만,
> [claude-code-action#727](https://github.com/anthropics/claude-code-action/issues/727)
> 에는 약 1일 만에 만료된다는 보고가 올라와 있고 2026-09 현재 미해결입니다.
> 그래서 이 파이프라인은 **토큰이 죽어도 게시가 멈추지 않도록** 설계돼 있습니다.
> 리필이 실패하면 Telegram으로 알림이 오고, 버퍼가 남아 있는 동안 게시는 계속됩니다.
> 토큰이 만료되면 위 명령으로 다시 발급해 시크릿을 갱신하세요.

시크릿이 아예 없으면 리필 잡은 실패하지 않고 경고만 남기고 건너뜁니다.

손으로 채우는 API 키 경로도 남아 있습니다:

```bash
ANTHROPIC_API_KEY=... python scripts/generate_content.py --days 7
```

## 버퍼 항목

`content/buffer.json` 은 `{"items": [...]}` 이고, 각 항목은 아래 필드를 가집니다.
`consumed_at` 이 있는 항목은 이미 게시로 나간 것이라 건너뜁니다.

| 필드 | 필수 | 설명 |
|---|---|---|
| `topic` | ✔ | `content/topics.json` 의 주제 문자열 |
| `kicker` |  | 헤드라인 위 작은 라벨 (예: `과학 커뮤니케이션`) |
| `image_headline` | ✔ | 카드 헤드라인. `\n` 하드 개행, `*강조*` 지원 |
| `english_image_headline` | ✔ | LinkedIn 영문 카드용 |
| `note` |  | `*소문자 방주` 캡션 |
| `stat` / `stat_note` |  | 강조 수치와 꼬리말 |
| `role` / `image` |  | 단일 카드의 역할과 사진 (기본 `cover`) |
| `slides` |  | 캐러셀 슬라이드 배열 (아래 참조) |
| `caption` | ✔ | Instagram 본문 (CTA 포함, 220자 이내) |
| `hashtags` | ✔ | 5~7개 |
| `comment_question` / `dm_keyword` / `dm_offer` | ✔ | 전환 장치 |
| `linkedin_ko` / `linkedin_en` | ✔ | 본문 |
| `linkedin_ko_hashtags` / `linkedin_en_hashtags` | ✔ | 각 3~4개 |
| `generated_by` |  | 출처 표시 |

`slides` 의 각 원소는 아래를 가질 수 있습니다. 전부 선택이고, 비워두면
`image_headline` 을 표지로 쓰고 `points` 배열을 이어 붙입니다.

| 필드 | 설명 |
|---|---|
| `role` | `cover` / `statement` / `evidence` / `vertical` / `detail` / `close`. 생략하면 캐러셀 위치에 따라 정해지고, 마지막 장은 항상 `close` |
| `headline` | `\n` 하드 개행, `*강조*` 로 한 단어만 크게·굵게·클레이로 |
| `note` | 보조 문장 |
| `stat` / `stat_note` | `evidence` 의 수치와 꼬리말 |
| `items` | `detail` 의 번호 목록 |
| `image` | 소스 렌더 이름의 일부(`hyper-silico` 등) 또는 저장소 상대 경로. 틀려도 실행은 죽지 않고 인덱스로 대체 |

역할별 구성과 조판 규칙은 `docs/editorial-direction.md` 에 있습니다.

## 포맷 순환

`render_daily.py::FORMAT_CYCLE` 이 슬롯마다 형식을 돌립니다.

```
single_image → carousel(4) → single_image → story → single_image → carousel(4)
```

매일 같은 단일 이미지만 나오던 문제를 여기서 끊습니다.
`images/channel-six-types/` 의 6타입 체계와 같은 방향입니다.

## 운영

- 버퍼가 **3일치 이하**로 떨어지면 일일 알림에 경고가 붙습니다.
- 버퍼가 비면 일일 워크플로는 종료 코드 2로 끝나고 알림을 보냅니다.
- 리필을 지금 돌리려면 Actions → **콘텐츠 버퍼 리필** → Run workflow.
