# Krea 산출물 저장 규칙

`content/plans/20260620-krea-content-production.md`의 파이프라인 통합 규칙에
따라 Krea로 만든 자산을 이 디렉터리에 배치별로 저장한다.

## 구조

```
images/krea/<batch>/manifest.json            기대 자산 목록 (스크립트 생성)
images/krea/<batch>/<concept>/instagram-card-01.jpg ... 06   1080×1080
images/krea/<batch>/<concept>/linkedin-ko.jpg               1200×627
images/krea/<batch>/<concept>/linkedin-en.jpg               1200×627
images/krea/<batch>/<concept>/reel.mp4                      선택 (moa 컨셉)
```

- `<batch>`: `YYYYMMDD-<이름>` (예: `20260620-pilot`).
- `<concept>`: 영문 슬러그. 콘텐츠 초안(`content/instagram`, `content/linkedin`)의
  컨셉과 1:1로 맞춘다.
- Instagram은 정사각형 1080×1080, LinkedIn은 가로 1200×627로 별도 생성한다
  (정사각형 재사용 금지).
- 헤드라인 텍스트는 가급적 Krea 배경 위에 기존 렌더러로 올려 폰트·컬러
  비율·로고 위치를 통제한다.

## 워크플로우

```bash
# 1. 배치 디렉터리 + manifest 생성
python scripts/scaffold_krea_assets.py

# 2. Krea 산출물을 manifest 파일명 규칙에 맞춰 저장

# 3. 존재·규격 검증 (Pillow가 있으면 픽셀 크기까지 확인)
python scripts/scaffold_krea_assets.py --check
```

## 컴플라이언스

AI 생성 비주얼은 컨셉·프리비주얼용이다. 분자 구조·세포 형태·작용 기전의
과학적 정확성은 메디컬 고증 자문위원 검수를 통과해야 하며, 검수 전 자산은
MOA 사실로 게시하지 않는다.
