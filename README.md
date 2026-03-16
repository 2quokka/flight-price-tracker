# ✈️ 최저가 항공권 검색기

Google Flights 실시간 데이터 기반 최저가 항공권 검색 CLI.
전 세계 모든 공항 간 편도/왕복/당일치기 검색을 지원합니다.

## 설치

```bash
git clone git@github.dop.admin.rnd.aws.kakaoinsure.net:mark-sc/flight-price-tracker.git
cd flight-price-tracker
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

## 사용법

설치 후 `flights` 명령어로 실행:

```bash
# 편도 최저가 (김포→제주)
flights --start 2026-04-01 --end 2026-04-10

# 왕복 최저가
flights --depart-start 2026-04-01 --depart-end 2026-04-05 \
        --return-start 2026-04-03 --return-end 2026-04-07

# 당일치기 (출발/도착 시간 필터)
flights --start 2026-04-01 --end 2026-04-30 \
  --depart-after 08:00 --depart-before 10:00 \
  --return-after 17:00 --arrive-by 21:30
```

### 국제선 예시

```bash
# 인천 → 오사카 편도
flights --from ICN --to KIX --start 2026-10-01 --end 2026-10-07

# 인천 ↔ 세부 왕복
flights --from ICN --to CEB \
  --depart-start 2026-10-02 --depart-end 2026-10-02 \
  --return-start 2026-10-07 --return-end 2026-10-07 \
  --depart-after 06:00 --depart-before 12:00 \
  --return-after 17:00

# 인천 ↔ 방콕 왕복
flights --from ICN --to BKK \
  --depart-start 2026-07-01 --depart-end 2026-07-10 \
  --return-start 2026-07-08 --return-end 2026-07-15

# CSV 저장
flights --from ICN --to NRT --start 2026-10-01 --end 2026-10-07 --output results.csv
```

### 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--from` | 출발 공항 IATA 코드 | GMP |
| `--to` | 도착 공항 IATA 코드 | CJU |
| `--start` | 검색 시작일 (YYYY-MM-DD) | - |
| `--end` | 검색 종료일 | --start와 동일 |
| `--depart-start` | 가는날 시작일 (왕복) | - |
| `--depart-end` | 가는날 종료일 (왕복) | - |
| `--return-start` | 오는날 시작일 (왕복) | - |
| `--return-end` | 오는날 종료일 (왕복) | - |
| `--depart-after` | 가는편 출발 최소 시각 (HH:MM) | - |
| `--depart-before` | 가는편 출발 최대 시각 | 10:00 |
| `--return-after` | 오는편 출발 최소 시각 | 17:00 |
| `--arrive-by` | 오는편 도착 마감 시각 | 21:30 |
| `--top` | 결과 상위 N개 | 10 |
| `--output` | 저장 파일 (.csv / .json) | - |

### 모드 자동 감지

| 조건 | 모드 |
|------|------|
| `--start` + `--depart-after` | 당일치기 |
| `--depart-start` | 왕복 |
| `--start` only | 편도 |

## 회사 프록시 (Menlo Security 등)

SSL 인증서 오류 시 CA 번들 경로를 환경변수로 지정:

```bash
export CA_CERT_PATH=/path/to/cacert.pem
flights --start 2026-04-01 --end 2026-04-10
```

프록시가 없는 환경에서는 설정 불필요.
