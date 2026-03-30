# ✈️ 최저가 항공권 검색기

멀티 플랫폼 실시간 데이터 기반 최저가 항공권 검색 CLI.
전 세계 모든 공항 간 편도/왕복/당일치기 검색을 지원합니다.

## 지원 플랫폼

| 플랫폼 | 방식 | 특징 |
|--------|------|------|
| **Google Flights** | `fast-flights` 라이브러리 (Protobuf) | 기본 제공, 넓은 커버리지 |
| **Trip.com** | Playwright (헤드리스 Chrome) | 국제선 강점, 아시아 노선 특가 |

여러 플랫폼의 결과를 병합하여 같은 항공편의 최저가를 자동으로 선별합니다.

## 동작 원리

- **Google Flights**: `fast-flights` 라이브러리를 통해 Google Flights Protobuf 응답을 디코딩
- **Trip.com**: Playwright로 검색 페이지를 로드하고 API 응답을 인터셉트하여 JSON 데이터 추출
- 검색 단위: 날짜 1일 = 플랫폼당 HTTP 요청 1회, 편도 기준
- 병렬 처리: `ThreadPoolExecutor(max_workers=4)`로 동시 검색
- 중복 제거: 항공사+날짜+출발시간 기준으로 같은 항공편 판별, 최저가만 유지
- 좌석: 이코노미, 성인 1명 기준

### 기술 스택

| 구성 | 라이브러리 | 역할 |
|------|-----------|------|
| Google Flights | `fast-flights` 2.2 | Protobuf 파싱 |
| Trip.com | `playwright` 1.40+ | 헤드리스 Chrome 스크래핑 |
| HTTP | `requests` | 프록시 환경 대응 |
| 출력 | `rich` | 터미널 테이블 포맷팅 |

### 아키텍처

```
flight_tracker/
├── providers/
│   ├── base.py          # FlightProvider ABC
│   ├── google.py        # Google Flights (fast-flights)
│   └── tripcom.py       # Trip.com (Playwright)
├── aggregator.py        # 멀티 프로바이더 병렬 검색 + 중복 제거
├── scraper.py           # 하위 호환 래퍼
├── models.py            # FlightResult, RoundTripCombo
└── formatter.py         # Rich 테이블 출력, CSV/JSON 저장
```

### 제약 사항

- 웹 스크래핑이므로 플랫폼 측 변경 시 동작이 깨질 수 있음
- 과도한 요청 시 일시적 차단 가능 (4 workers로 제한)
- Trip.com은 시스템에 Google Chrome이 설치되어 있어야 함
- 기업 프록시(Menlo Security 등) 환경에서는 Trip.com이 차단될 수 있음

## 설치

```bash
git clone git@github.dop.admin.rnd.aws.kakaoinsure.net:mark-sc/flight-price-tracker.git
cd flight-price-tracker
python3 -m venv .venv
source .venv/bin/activate
pip install .

# Trip.com 지원을 위한 Playwright 브라우저 설치 (시스템 Chrome 사용 시 생략 가능)
playwright install chromium
```

### 로컬 개발 환경 설치

> Python 3.9 이상, Google Chrome 설치 필요

```bash
git clone git@github.dop.admin.rnd.aws.kakaoinsure.net:mark-sc/flight-price-tracker.git
cd flight-price-tracker

python3 -m venv .venv
source .venv/bin/activate

# 개발 모드 설치
pip install -e .

# Playwright 브라우저 설치 (선택 - 시스템 Chrome이 있으면 자동 사용)
playwright install chromium

# 설치 확인
flights --help
```

## 사용법

설치 후 `flights` 명령어로 실행:

```bash
# 편도 최저가 (김포→제주, 전체 플랫폼)
flights --start 2026-04-01 --end 2026-04-10

# Google Flights만 사용
flights --start 2026-04-01 --end 2026-04-10 --provider google

# Trip.com만 사용
flights --start 2026-04-01 --end 2026-04-10 --provider tripcom

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
  --return-start 2026-10-07 --return-end 2026-10-07

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
| `--provider` | 사용할 플랫폼 (google, tripcom) | 전체 |

### 모드 자동 감지

| 조건 | 모드 |
|------|------|
| `--start` + `--depart-after` | 당일치기 |
| `--depart-start` | 왕복 |
| `--start` only | 편도 |

## 새 플랫폼 추가 방법

1. `providers/` 에 `FlightProvider` 구현 클래스 생성
2. `providers/__init__.py`의 `PROVIDERS` dict에 등록
3. 끝 — aggregator가 자동으로 병렬 검색 + 중복 제거 처리

```python
# providers/example.py
class ExampleProvider(FlightProvider):
    @property
    def name(self) -> str:
        return "example"

    def search_one_day(self, from_airport, to_airport, date_str):
        # 스크래핑 로직
        return [FlightResult(...)]
```

## 회사 프록시 (Menlo Security 등)

SSL 인증서 오류 시 CA 번들 경로를 환경변수로 지정:

```bash
export CA_CERT_PATH=/path/to/cacert.pem
flights --start 2026-04-01 --end 2026-04-10
```

> 기업 프록시 환경에서는 Trip.com 스크래핑이 차단될 수 있습니다. 이 경우 Google Flights 결과만 사용됩니다.
