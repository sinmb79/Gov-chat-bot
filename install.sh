#!/usr/bin/env bash
# =============================================================================
# GovBot KR — 자동 설치 스크립트 v1.0
# 지원 OS: Ubuntu 20.04+, Debian 11+, macOS 13+
# 필요 권한: sudo (Docker 설치 시)
# 사용법: curl -fsSL https://raw.githubusercontent.com/22blabs/govbot-kr/main/install.sh | bash
# 또는:   chmod +x install.sh && ./install.sh
# =============================================================================
set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }
step()  { echo -e "\n${BOLD}==> $*${NC}"; }

GOVBOT_DIR="${GOVBOT_DIR:-$HOME/govbot-kr}"
GOVBOT_VERSION="${GOVBOT_VERSION:-latest}"

# ─── 환경 확인 ───────────────────────────────────────────────────────────────
step "환경 확인"

OS=$(uname -s)
ARCH=$(uname -m)
info "OS: $OS / ARCH: $ARCH"

if [[ "$OS" != "Linux" && "$OS" != "Darwin" ]]; then
  error "지원하지 않는 OS입니다. Linux 또는 macOS가 필요합니다.\nWindows는 WSL2를 사용하세요: docs/WSL2_가이드.md"
fi

# ─── Docker 확인 / 설치 ───────────────────────────────────────────────────────
step "Docker 확인"

if command -v docker &>/dev/null; then
  DOCKER_VER=$(docker --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
  info "Docker $DOCKER_VER 감지됨"
else
  warn "Docker가 설치되어 있지 않습니다. 설치를 시작합니다..."
  if [[ "$OS" == "Linux" ]]; then
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$USER"
    info "Docker 설치 완료. 이 터미널을 닫고 다시 열어주세요 (docker 그룹 적용)."
  else
    error "macOS에서는 Docker Desktop을 수동으로 설치해주세요: https://www.docker.com/products/docker-desktop/"
  fi
fi

if ! command -v docker compose &>/dev/null && ! command -v docker-compose &>/dev/null; then
  warn "Docker Compose가 없습니다. Docker Desktop 또는 최신 Docker Engine을 설치하세요."
fi

# ─── 프로젝트 디렉터리 ────────────────────────────────────────────────────────
step "프로젝트 디렉터리: $GOVBOT_DIR"

if [[ -d "$GOVBOT_DIR" ]]; then
  warn "디렉터리가 이미 존재합니다: $GOVBOT_DIR"
  read -rp "계속 진행하시겠습니까? 기존 설정은 유지됩니다. [y/N] " answer
  [[ "$answer" =~ ^[Yy]$ ]] || error "설치를 취소했습니다."
else
  mkdir -p "$GOVBOT_DIR"
  info "디렉터리 생성: $GOVBOT_DIR"
fi

cd "$GOVBOT_DIR"

# ─── .env 파일 생성 ───────────────────────────────────────────────────────────
step ".env 설정 파일 생성"

if [[ -f ".env" ]]; then
  warn ".env 파일이 이미 존재합니다. 덮어쓰지 않습니다."
else
  SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null \
    || openssl rand -hex 32 2>/dev/null \
    || echo "change-this-secret-key-before-production")

  cat > .env << EOF
# GovBot KR 환경 설정
# 생성일: $(date +%Y-%m-%d)

# ── 데이터베이스 ──────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://govbot:govbot@db:5432/govbot

# ── Redis ────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ── ChromaDB ─────────────────────────────────────────
CHROMA_HOST=chromadb
CHROMA_PORT=8001

# ── 보안 ─────────────────────────────────────────────
SECRET_KEY=${SECRET_KEY}

# ── LLM (선택) ───────────────────────────────────────
# LLM_PROVIDER=none          # 기본값: LLM 없이 FAQ+RAG만 사용
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-...
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-...

# ── 로그 ─────────────────────────────────────────────
LOG_LEVEL=INFO
EOF

  info ".env 파일 생성 완료"
  warn "⚠️  SECRET_KEY가 자동 생성되었습니다. 안전하게 보관하세요."
fi

# ─── docker-compose.yml 다운로드 ─────────────────────────────────────────────
step "docker-compose.yml 확인"

if [[ ! -f "docker-compose.yml" ]]; then
  # 소스에서 직접 실행 시: 현재 디렉터리의 파일 사용
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [[ -f "$SCRIPT_DIR/docker-compose.yml" ]]; then
    cp "$SCRIPT_DIR/docker-compose.yml" .
    cp -r "$SCRIPT_DIR/backend" . 2>/dev/null || true
    info "소스 파일 복사 완료"
  else
    error "docker-compose.yml을 찾을 수 없습니다.\nGovBot KR 소스 디렉터리에서 install.sh를 실행해주세요."
  fi
fi

# ─── 서비스 시작 ──────────────────────────────────────────────────────────────
step "Docker 서비스 시작"

COMPOSE_CMD="docker compose"
command -v "docker compose" &>/dev/null || COMPOSE_CMD="docker-compose"

info "이미지 빌드 중... (첫 실행 시 5~10분 소요)"
$COMPOSE_CMD build --quiet

info "서비스 시작 중..."
$COMPOSE_CMD up -d

# ─── DB 마이그레이션 ──────────────────────────────────────────────────────────
step "데이터베이스 마이그레이션"

info "DB 초기화 대기 중..."
sleep 5

$COMPOSE_CMD exec -T backend alembic upgrade head && \
  info "마이그레이션 완료" || \
  warn "마이그레이션 실패. 수동으로 실행하세요: docker compose exec backend alembic upgrade head"

# ─── 헬스 체크 ────────────────────────────────────────────────────────────────
step "서비스 상태 확인"

sleep 3
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")

if [[ "$HTTP_STATUS" == "200" ]]; then
  info "✅ 서비스 정상 동작 확인"
else
  warn "헬스 체크 응답: $HTTP_STATUS (서비스 시작 중일 수 있습니다)"
fi

# ─── 완료 메시지 ──────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}================================================"
echo -e "  GovBot KR 설치 완료!"
echo -e "================================================${NC}"
echo ""
echo -e "  API 서버:       http://localhost:8000"
echo -e "  API 문서:       http://localhost:8000/docs"
echo -e "  헬스 체크:      http://localhost:8000/health"
echo ""
echo -e "  다음 단계:"
echo -e "  1. 관리자 계정 생성:"
echo -e "     ${BOLD}docker compose exec backend python -m app.scripts.create_admin${NC}"
echo -e ""
echo -e "  2. 대시보드 접속 (프론트엔드 빌드 후):"
echo -e "     http://localhost:3000"
echo ""
echo -e "  운영 가이드: docs/운영가이드.md"
echo ""
