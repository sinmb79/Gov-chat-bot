import hashlib
import re

# 마스킹 패턴 정의
_PATTERNS = [
    # 주민등록번호: 6자리-1~4자리+6자리 (숫자 금액과 구분: 앞에 비숫자 또는 시작, 뒤에 비숫자 또는 끝)
    (re.compile(r"(?<!\d)\d{6}-[1-4]\d{6}(?!\d)"), "######-*######"),
    # 전화번호: 010-1234-5678 형식
    (re.compile(r"0\d{1,2}-\d{3,4}-\d{4}"), "***-****-****"),
    # 이메일
    (re.compile(r"[\w._%+\-]+@[\w.\-]+\.[a-zA-Z]{2,}"), "***@***.***"),
    # 카드번호: 4자리씩 4그룹
    (re.compile(r"\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}"), "****-****-****-****"),
]


def mask_text(text: str) -> str:
    """텍스트에서 개인정보 패턴을 마스킹하여 반환."""
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def hash_user_key(kakao_id: str) -> str:
    """SHA-256 해시 앞 16자리 반환."""
    return hashlib.sha256(kakao_id.encode()).hexdigest()[:16]


def has_sensitive_data(text: str) -> bool:
    """텍스트에 개인정보 패턴이 포함되어 있으면 True."""
    for pattern, _ in _PATTERNS:
        if pattern.search(text):
            return True
    return False
