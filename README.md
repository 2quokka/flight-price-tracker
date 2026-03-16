# ✈️ 김포↔제주 최저가 항공권 검색기

Google Flights 실시간 데이터 기반 최저가 항공권 검색 CLI.

## 설치

```bash
pip install git+https://github.com/your-username/flight-price-tracker.git
```

또는 로컬:

```bash
git clone <repo-url>
cd flight-price-tracker
pip install .
```

## 사용법

설치 후 `flights` 명령어로 실행:

```bash
# 당일치기 최저가 (출발/도착 시간 필터)
flights --start 2026-04-01 --end 2026-04-30 \
  --depart-after 08:00 --depart-before 10:00 \
  --return-after 17:00 --arrive-by 21:30 \
  --top 10

# 편도 최저가
flights --start 2026-04-01 --end 2026-04-10

# 왕복 최저가
flights --depart-start 2026-04-01 --depart-end 2026-04-05 \
        --return-start 2026-04-03 --return-end 2026-04-07

# 공항 변경 (기본: GMP↔CJU)
flights --from PUS --to CJU --start 2026-04-01 --end 2026-04-10

# CSV 저장
flights --start 2026-04-01 --end 2026-04-10 --output results.csv
```

### 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--from` | 출발 공항 IATA 코드 | GMP |
| `--to` | 도착 공항 IATA 코드 | CJU |
| `--start` | 검색 시작일 (YYYY-MM-DD) | - |
| `--end` | 검색 종료일 | --start와 동일 |
| `--depart-after` | 가는편 출발 최소 시각 (HH:MM) | - |
| `--depart-before` | 가는편 출발 최대 시각 | 10:00 |
| `--return-after` | 오는편 출발 최소 시각 | 17:00 |
| `--arrive-by` | 오는편 도착 마감 시각 | 21:30 |
| `--top` | 결과 상위 N개 | 10 |
| `--output` | 저장 파일 (.csv / .json) | - |

## 회사 프록시 (Menlo Security 등)

SSL 인증서 오류 시 CA 번들 경로를 환경변수로 지정:

```bash
export CA_CERT_PATH=/path/to/cacert.pem
flights --start 2026-04-01 --end 2026-04-10
```

프록시가 없는 환경에서는 설정 불필요.
