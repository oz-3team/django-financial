# Django Financial Project

## 프로젝트 개요
- Django 기반 개인 금융 관리 서비스
- 사용자 계좌, 거래 내역, 분석, 알림 등을 관리
- Docker + Docker Compose 환경에서 실행 가능

---

# 데이터베이스 ERD

```mermaid
erDiagram
    USERS {
        string email PK "로그인 시 사용"
        string password
        string nickname
        string name
        string phone_number
        datetime last_login
        boolean is_staff
        boolean is_admin
        boolean is_active
    }
    ACCOUNTS {
        int id PK
        string account_number
        string bank_code "카카오뱅크, KB, NH, IBK 등"
        string account_type "단순 입출금통장, 마이너스 통장 등"
        decimal balance
        int user_id FK
    }
    TRANSACTION_HISTORY {
        int id PK
        int account_id FK
        decimal amount
        decimal post_balance "거래 후 잔액"
        string description "오픈뱅킹 출금, ATM 현금 입금 등"
        string transaction_type "입금, 출금"
        string payment_type "현금, 계좌 이체, 자동 이체, 카드 결제 등"
        datetime transaction_datetime
    }
    ANALYSIS {
        int id PK
        int user_id FK
        string analysis_target "수입/지출"
        string period_type "일간/주간/월간/연간"
        date start_date
        date end_date
        string description
        string result_image
        datetime created_at
        datetime updated_at
    }
    NOTIFICATIONS {
        int id PK
        int user_id FK
        string message
        boolean is_read
        datetime created_at
    }

    USERS ||--o{ ACCOUNTS : "보유"
    ACCOUNTS ||--o{ TRANSACTION_HISTORY : "거래 내역 보유"
    USERS ||--o{ ANALYSIS : "분석 요청"
    USERS ||--o{ NOTIFICATIONS : "알림 수신"

```

# 플로우 차트: 사용자 인증 흐름
<details>
<summary>펼쳐보기</summary>
<div markdown="1">

```mermaid
flowchart TD
    A[사용자 로그인 시도] --> B[이메일, 비밀번호 입력]
    B --> C{인증 정보 검증}
    C -- 인증 성공 --> D[Access, Refresh 토큰 생성]
    D --> E[토큰을 HttpOnly, Secure 쿠키에 저장]
    E --> F[로그인 성공 응답]
    C -- 인증 실패 --> G[로그인 실패 응답]
    F --> H{Access 토큰 유효?}
    H -- 예 --> I[서비스 접근 허용]
    H -- 아니오 --> J[Refresh 토큰으로 토큰 재발급 시도]
    J --> K{재발급 성공?}
    K -- 예 --> I
    K -- 아니오 --> L[재로그인 요청]
```
</div>
</details>

# 📖 API 명세서


**users/** : 회원가입/로그인/토큰/내 정보 관리  
**accounts/** : 계좌 관리  
**analysis/analysis/** : 분석 데이터  
**analysis/transactions/** : 거래내역 관리  
**notifications/** : 알림 관리  

---

<details>
<summary>📂 전체 API 문서 (펼쳐보기)</summary>

---

<details>
<summary>1. 인증 & 사용자 관리 (Users & Auth)</summary>

### 🔹 회원가입
POST /api/users/register/
Content-Type: application/json

```json
요청:
{ "email": "user@test.com", "password": "비밀번호", "name": "홍길동" }
```
```json
응답: `201 Created`
{ "id": "uuid", "email": "user@test.com", "is_active": false }
```
```undefined
curl -X POST {{base_url}}/api/users/register/
-H "Content-Type: application/json"
-d '{"email":"user@test.com","password":"비밀번호","name":"홍길동"}'
```

---

### 🔹 로그인
POST /api/users/login/
Content-Type: application/json

```json
요청:
{ "email": "user@test.com", "password": "비밀번호" }
```
```json
응답:
{
    "msg": "Login success",
    "refresh": "<jwt_refresh>",
    "access": "<jwt_access>"
}
```
```undefined
curl -X POST {{base_url}}/api/users/login/
-H "Content-Type: application/json"
-d '{"email":"user@test.com","password":"비밀번호"}'
```

---

### 🔹 토큰 재발급
POST /api/users/token/refresh/

```json
요청:
{ "refresh": "<refresh_token>" }
```
```json
응답:
{ "access": "<new_access_token>" }
```
```undefined
curl -X POST {{base_url}}/api/users/token/refresh/
-H "Content-Type: application/json"
-d '{"refresh":"<refresh_token>"}'
```

---

### 🔹 내 정보 조회
GET /api/users/me/
Authorization: Bearer <access_token>

```undefined
curl -X GET {{base_url}}/api/users/me/
-H "Authorization: Bearer <access_token>"
```

---

### 🔹 로그아웃
POST /api/users/logout/
Authorization: Bearer <access_token>

```undefined
curl -X POST {{base_url}}/api/users/logout/
-H "Authorization: Bearer <access_token>"
```

</details>

---

<details>
<summary>2. 계좌 관리 (Accounts)</summary>

### 🔹 계좌 목록 조회
GET /api/accounts/

Authorization: Bearer <access_token>

```json
응답:
[
    {
        "id": "uuid",
        "name": "카카오뱅크",
        "number": "123-456-789",
        "currency": "KRW",
        "balance": "100000.00",
        "status": "ACTIVE"
    }
]
```
```undefined
curl -X GET {{base_url}}/api/accounts/
-H "Authorization: Bearer <access_token>"
```


---

### 🔹 계좌 생성
POST /api/accounts/

Content-Type: application/json

Authorization: Bearer <access_token>

```json
요청:
{ "name": "카카오뱅크", "number": "123-456-789", "currency": "KRW" }
```
```undefined
curl -X POST {{base_url}}/api/accounts/
-H "Authorization: Bearer <access_token>"
-H "Content-Type: application/json"
-d '{"name":"카카오뱅크","number":"123-456-789","currency":"KRW"}'
```


---

### 🔹 특정 계좌 조회
GET /api/accounts/{id}/

Authorization: Bearer <access_token>

```undefined
curl -X GET {{base_url}}/api/accounts/{id}/
-H "Authorization: Bearer <access_token>"
```

---

### 🔹 계좌 삭제
DELETE /api/accounts/{id}/

```undefined
curl -X DELETE {{base_url}}/api/accounts/{id}/
-H "Authorization: Bearer <access_token>"
```

</details>

---

<details>
<summary>3. 거래 내역 (Transactions)</summary>

`/api/analysis/transactions/`

### 🔹 거래 내역 조회
GET /api/analysis/transactions/?tx_type=DEPOSIT&ordering=-occurred_at

- 필터링 지원 : `tx_type`, `amount__gte`, `occurred_at__lte`, `account`  
- 정렬 : `ordering=amount` or `ordering=-occurred_at`  
- 검색 : `?search=급여`

```undefined
curl -X GET "{{base_url}}/api/analysis/transactions/?tx_type=DEPOSIT&ordering=-occurred_at"
-H "Authorization: Bearer <access_token>"
```


---

### 🔹 거래 내역 생성
POST /api/analysis/transactions/

Content-Type: application/json

Authorization: Bearer <access_token>

```json
요청:
    {
        "account": "uuid",
        "tx_type": "DEPOSIT",
        "amount": "50000.00",
        "currency": "KRW",
        "description": "급여 입금"
    }
```
```undefined
curl -X POST {{base_url}}/api/analysis/transactions/
-H "Authorization: Bearer <access_token>"
-H "Content-Type: application/json"
-d '{"account":"uuid","tx_type":"DEPOSIT","amount":"50000.00","currency":"KRW","description":"급여 입금"}'
```


---

### 🔹 단일 거래
GET /api/analysis/transactions/{id}/

PUT /api/analysis/transactions/{id}/

PATCH /api/analysis/transactions/{id}/

DELETE /api/analysis/transactions/{id}/


</details>

---

<details>
<summary>4. 분석 Report (Analysis)</summary>

`/api/analysis/analysis/`

### 🔹 분석 생성
POST /api/analysis/analysis/

Content-Type: application/json

Authorization: Bearer <access_token>

```json
{
    "analysis_target": "EXPENSE",
    "period_type": "MONTHLY",
    "start_date": "2025-07-01",
    "end_date": "2025-07-31",
    "description": "7월 지출 분석"
}
```
```undefined
curl -X POST {{base_url}}/api/analysis/analysis/
-H "Authorization: Bearer <access_token>"
-H "Content-Type: application/json"
-d '{"analysis_target":"EXPENSE","period_type":"MONTHLY","start_date":"2025-07-01","end_date":"2025-07-31","description":"7월 지출 분석"}'
```


---

### 🔹 분석 조회
GET /api/analysis/analysis/?period_type=MONTHLY&analysis_target=INCOME

```undefined
curl -X GET "{{base_url}}/api/analysis/analysis/?period_type=MONTHLY"
-H "Authorization: Bearer <access_token>"
```


---

### 🔹 단일 분석 상세
GET /api/analysis/analysis/{id}/

```undefined
curl -X GET {{base_url}}/api/analysis/analysis/{id}/
-H "Authorization: Bearer <access_token>"
```

</details>

---

<details>
<summary>5. 알림 (Notification)</summary>

`/api/notifications/`

### 🔹 안 읽은 알림 목록
GET /api/notifications/unread/

Authorization: Bearer <access_token>

```json
응답:
[
    {
        "id": 1,
        "message": "새로운 거래 발생",
        "is_read": false,
        "created_at": "2025-08-30T15:00:00Z"
    }
]
```
```undefined
curl -X GET {{base_url}}/api/notifications/unread/
-H "Authorization: Bearer <access_token>"
```


---

### 🔹 알림 읽음 처리
POST /api/notifications/read/{id}/

Authorization: Bearer <access_token>

```json
응답:
{"detail": "알림 읽음 처리 완료"}
```
```undefined
curl -X POST {{base_url}}/api/notifications/read/1/
-H "Authorization: Bearer <access_token>"
```


</details>

---

<details>
<summary>6. Swagger & Redoc</summary>

Swagger UI : GET /swagger/

Redoc : GET /redoc/

```undefined
curl -X GET {{base_url}}/swagger/
curl -X GET {{base_url}}/redoc/
```

</details>

---

</details>