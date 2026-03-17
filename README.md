# ✈️ 최저가 항공권 검색기

Google Flights 실시간 데이터 기반 최저가 항공권 검색 CLI.
전 세계 모든 공항 간 편도/왕복/당일치기 검색을 지원합니다.

## 동작 원리

[`fast-flights`](https://github.com/AWeirdDev/flights) 라이브러리를 통해 Google Flights 웹페이지를 스크래핑합니다.

- 데이터 소스: `https://www.google.com/travel/flights` (공식 API 아님, 웹 스크래핑)
- 파싱: Google Flights의 Protobuf 응답을 `fast-flights`가 디코딩
- 검색 단위: 날짜 1일 = HTTP 요청 1회, 편도 기준
- 병렬 처리: `ThreadPoolExecutor(max_workers=4)`로 동시 4개 날짜 검색
- 좌석: 이코노미, 성인 1명 기준
- 결과: 각 날짜별 최저가 1건 추출 후 정렬

### 기술 스택

| 구성 | 라이브러리 | 역할 |
|------|-----------|------|
| 스크래핑 | `fast-flights` 2.2 | Google Flights Protobuf 파싱 |
| HTTP | `requests` | 프록시 환경 대응 (CA 인증서 지정) |
| 출력 | `rich` | 터미널 테이블 포맷팅 |
| 직렬화 | `protobuf` | Google Flights 응답 디코딩 (fast-flights 의존) |
| HTML 파싱 | `selectolax` | 응답 HTML 파싱 (fast-flights 의존) |

### 제약 사항

- Google Flights 웹 스크래핑이므로 Google 측 변경 시 동작이 깨질 수 있음
- 과도한 요청 시 일시적 차단 가능 (4 workers로 제한)
- LCC 최저가 기준이라 수하물/좌석 선택 비용 별도

## 설치

```bash
git clone git@github.dop.admin.rnd.aws.kakaoinsure.net:mark-sc/flight-price-tracker.git
cd flight-price-tracker
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

### 로컬 개발 환경 설치

> Python 3.9 이상이 필요합니다.

```bash
git clone git@github.dop.admin.rnd.aws.kakaoinsure.net:mark-sc/filight-price-tracker.git
cd filight-price-tracker

# 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 개발 모드 설치 (소스 수정 시 재설치 불필요)
pip install -e .

# 설치 확인
flights --help
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

회사 네트워크에서 Menlo Security 등의 SSL 프록시를 사용하는 경우, 다음과 같은 오류가 발생할 수 있습니다:

```
SSLCertVerificationError: certificate verify failed: unable to get local issuer certificate
```

### 해결 방법

1. 프록시의 루트 인증서를 추출합니다:

```bash
echo | openssl s_client -connect www.google.com:443 -servername www.google.com -showcerts 2>/dev/null \
  | awk '/BEGIN CERTIFICATE/{cert=""} {cert=cert"\n"$0} /END CERTIFICATE/{last=cert} END{print last}' \
  > /tmp/proxy_root.pem
```

2. Python certifi의 CA 번들에 추가합니다:

```bash
CERTIFI_PATH=$(python3 -c "import certifi; print(certifi.where())")
echo -e "\n# Company Proxy Root CA" >> "$CERTIFI_PATH"
cat /tmp/proxy_root.pem >> "$CERTIFI_PATH"
```

3. 정상 동작을 확인합니다:

```bash
python3 -c "import requests; print(requests.get('https://www.google.com').status_code)"
# 200 출력 시 정상
```

> ⚠️ `pip install --upgrade certifi` 실행 시 추가한 인증서가 초기화되므로 재설정이 필요합니다.

프록시가 없는 환경에서는 설정 불필요.
