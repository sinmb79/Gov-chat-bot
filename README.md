# 🏛️ GovBot KR — 한국 지자체 AI 민원 챗봇

> **비개발자도 설치·운영할 수 있는** 오픈소스 AI 민원 챗봇 플랫폼

카카오톡, 웹 채팅 위젯으로 시민의 민원 질문에 자동으로 답변하고,
관리자 대시보드에서 FAQ·문서를 쉽게 관리할 수 있습니다.

---

## ✨ 주요 기능

| 기능 | 설명 |
|------|------|
| 💬 **카카오톡 연동** | 카카오 i 오픈빌더 스킬 API 형식 지원 |
| 🌐 **웹 채팅 위젯** | 홈페이지에 코드 한 줄로 삽입 가능 |
| ❓ **FAQ 자동 응답** | 유사도 기반 즉시 답변 (Tier A) |
| 📄 **문서 기반 응답** | PDF·Word·TXT 업로드 → AI 자동 학습 (Tier B/C) |
| 🤖 **LLM 연동** | Claude·GPT 연결 시 자연어 재서술 응답 (선택) |
| 📊 **관리자 대시보드** | 통계·FAQ·문서·민원이력·악성감지 관리 UI |
| 🔒 **개인정보 보호** | 발화 마스킹·사용자 ID 해시 처리·원문 미저장 |
| 🏢 **멀티 기관 지원** | 하나의 서버에서 여러 기관 독립 운영 가능 |

---

## 🚀 5분 설치 (Linux / macOS)

```bash
# 1. 소스 다운로드
git clone https://github.com/sinmb79/Gov-chat-bot.git
cd Gov-chat-bot

# 2. 설치 스크립트 실행 (Docker 자동 설치 + 서비스 시작)
chmod +x install.sh
./install.sh

# 3. 관리자 계정 생성
docker compose exec backend python -m app.scripts.create_admin
```

설치 완료 후 브라우저에서 접속:
- **관리자 대시보드**: http://localhost:3000
- **API 문서**: http://localhost:8000/docs

> **Windows 사용자**: [WSL2 설치 가이드](docs/WSL2_가이드.md)를 먼저 확인하세요.

---

## 📋 시스템 요구사항

| 항목 | 최소 사양 |
|------|-----------|
| OS | Ubuntu 20.04+ / macOS 13+ / Windows (WSL2) |
| CPU | 2코어 |
| RAM | 4GB |
| 디스크 | 20GB |
| Docker | 24.x 이상 |

---

## 🏗️ 아키텍처

```
시민 질문 입력
     │
     ▼
┌─────────────────────────────────────┐
│           응답 라우팅 엔진             │
│                                     │
│  Tier A: FAQ 유사도 ≥ 0.85 → 즉시 답변 │
│  Tier C: 문서 근거 + LLM 자연어 답변   │
│  Tier B: 문서 근거 템플릿 답변         │
│  Tier D: 담당부서 안내 (폴백)         │
└─────────────────────────────────────┘
     │
     ▼
  응답 반환 (카카오톡 5초 이내 보장)
```

### 기술 스택

| 레이어 | 기술 |
|--------|------|
| API 서버 | Python · FastAPI |
| 데이터베이스 | PostgreSQL 16 |
| 벡터 검색 | ChromaDB |
| 캐시 | Redis 7 |
| 임베딩 모델 | jhgan/ko-sroberta-multitask (한국어 특화) |
| 프론트엔드 | React + Vite |
| 배포 | Docker Compose |

---

## ⚙️ 설정 방법

### 1. 환경 설정 파일 생성

```bash
cp .env.example .env
```

`.env` 파일에서 반드시 수정해야 할 항목:

```env
# 보안 키 (반드시 변경!)
SECRET_KEY=여기에-32자-이상의-랜덤-문자열-입력

# 데이터베이스 비밀번호 (기본값 그대로 사용 가능)
DATABASE_URL=postgresql+asyncpg://govbot:govbot@db:5432/govbot
```

> 보안 키 생성: `python -c "import secrets; print(secrets.token_hex(32))"`

### 2. LLM 연동 (선택 사항)

LLM 없이도 FAQ + 문서 기반 응답이 가능합니다.
더 자연스러운 답변을 원하면 `.env`에 추가:

```env
# Claude 사용 시
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-api-key-here

# GPT 사용 시
LLM_PROVIDER=openai
OPENAI_API_KEY=your-api-key-here
```

---

## 📖 사용 방법

### FAQ 등록

1. 대시보드 → **FAQ 관리** → `+ FAQ 추가`
2. 카테고리, 질문, 답변 입력 후 저장
3. **시뮬레이터**에서 테스트

### 문서 업로드

1. 대시보드 → **문서 관리** → `+ 문서 업로드`
2. PDF · Word · TXT · Markdown 파일 선택
3. 처리 완료 후 **승인** 클릭 → AI가 자동 학습

### 카카오톡 연결

카카오 i 오픈빌더에서 스킬 서버 URL 설정:
```
https://your-server.com/skill/{기관-슬러그}
```

### 웹 홈페이지 위젯 삽입

홈페이지 HTML의 `</body>` 바로 앞에 한 줄 추가:
```html
<script
  src="https://your-server.com/widget/govbot-widget.js"
  data-tenant="기관-슬러그"
  data-api="https://your-server.com"
  data-title="AI 민원 도우미"
></script>
```

---

## 📁 프로젝트 구조

```
Gov-chat-bot/
├── backend/                  # API 서버 (Python · FastAPI)
│   ├── app/
│   │   ├── core/             # 설정, DB, 인증, 미들웨어
│   │   ├── models/           # 데이터베이스 모델
│   │   ├── routers/          # API 엔드포인트
│   │   ├── services/         # 비즈니스 로직
│   │   └── providers/        # LLM·임베딩·벡터DB 플러그인
│   ├── alembic/              # DB 마이그레이션
│   ├── tests/                # 자동화 테스트 (127개)
│   └── requirements.txt
├── frontend/                 # 관리자 대시보드 (React · Vite)
│   ├── src/
│   │   ├── pages/            # 대시보드·FAQ·문서·민원·모더레이션
│   │   └── components/
│   └── widget/               # 웹 채팅 위젯 (govbot-widget.js)
├── docs/
│   ├── 운영가이드.md          # 상세 운영 매뉴얼 (한글)
│   └── WSL2_가이드.md        # Windows 설치 가이드
├── docker-compose.yml         # 서비스 구성 (DB·Redis·ChromaDB·API·UI)
├── install.sh                 # 자동 설치 스크립트
└── .env.example              # 환경 설정 예시
```

---

## 🔒 개인정보 보호 설계

- **발화 원문 미저장**: 모든 민원 내용은 마스킹 처리 후 저장
- **주민번호·전화번호·이메일·카드번호** 자동 마스킹
- **사용자 ID**: SHA-256 해시값만 저장 (복원 불가)
- **관리자도 원문 열람 불가**: 대시보드에서 마스킹 상태로만 표시

---

## 🧪 개발자를 위한 테스트 실행

```bash
cd backend

# 의존성 설치
pip install -r requirements.txt

# 테스트 실행 (Docker 없이 가능)
pytest tests/ -v

# 결과: 127 passed
```

---

## 📚 상세 문서

- [운영 가이드 (한글)](docs/운영가이드.md) — 설치부터 일상 운영까지
- [WSL2 설치 가이드](docs/WSL2_가이드.md) — Windows에서 실행하기
- [API 문서](http://localhost:8000/docs) — 서버 실행 후 접속

---

## 🤝 기여 방법

1. 이 저장소를 Fork
2. 새 브랜치 생성: `git checkout -b feature/기능명`
3. 변경사항 커밋: `git commit -m "feat: 기능 설명"`
4. Pull Request 생성

버그 제보나 기능 제안은 [Issues](https://github.com/sinmb79/Gov-chat-bot/issues)에 남겨주세요.

---

## 📄 라이선스

[MIT License](LICENSE) — 자유롭게 사용, 수정, 배포 가능합니다.
상업적 이용도 허용됩니다.

---

## ❓ 자주 묻는 질문

**Q. 클라우드 서버 없이 사용할 수 있나요?**
A. 네. 사무실 PC(Ubuntu)나 노트북(macOS)에서 Docker만 있으면 실행됩니다.

**Q. 카카오 i 오픈빌더 계정이 있어야 하나요?**
A. 카카오톡 연동은 선택 사항입니다. 웹 위젯만으로도 운영 가능합니다.

**Q. LLM(AI) API 키가 필수인가요?**
A. 아닙니다. API 키 없이도 FAQ + 문서 기반 응답이 가능합니다. LLM은 선택 기능입니다.

**Q. 개인정보가 외부로 나가나요?**
A. 시민 발화는 서버 내에서 마스킹 처리되며, LLM을 사용하지 않으면 외부 API 호출이 없습니다. LLM 사용 시에는 마스킹된 내용만 전송됩니다.

**Q. 여러 기관이 함께 사용할 수 있나요?**
A. 네. 하나의 서버에서 테넌트(tenant) 단위로 데이터가 완전히 분리됩니다.
