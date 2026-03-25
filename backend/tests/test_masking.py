import pytest

from app.services.masking import mask_text, hash_user_key, has_sensitive_data


def test_rrn_full_masking():
    """주민번호 마스킹."""
    result = mask_text("주민번호: 901225-1234567")
    assert result == "주민번호: ######-*######"


def test_phone_masking():
    """전화번호 마스킹."""
    result = mask_text("전화: 010-1234-5678")
    assert result == "전화: ***-****-****"


def test_email_masking():
    """이메일 마스킹."""
    result = mask_text("user@example.com")
    assert result == "***@***.***"


def test_card_masking():
    """카드번호 마스킹."""
    result = mask_text("4242-4242-4242-4242")
    assert result == "****-****-****-****"


def test_no_false_positive_number():
    """금액 숫자는 마스킹되지 않아야 함."""
    original = "예산액: 1,234,567원"
    result = mask_text(original)
    assert result == original


def test_multiple_patterns_in_one_text():
    """전화번호와 이메일이 같이 있는 문장에서 둘 다 마스킹."""
    text = "연락처: 010-1234-5678, 이메일: admin@gov.kr"
    result = mask_text(text)
    assert "010-1234-5678" not in result
    assert "admin@gov.kr" not in result
    assert "***-****-****" in result
    assert "***@***.***" in result


def test_hash_user_key_length():
    """hash_user_key 결과 길이 == 16."""
    assert len(hash_user_key("any_id")) == 16


def test_hash_user_key_deterministic():
    """같은 입력에 항상 같은 결과."""
    assert hash_user_key("test_user") == hash_user_key("test_user")


def test_has_sensitive_data_detection():
    """민감 데이터 감지."""
    assert has_sensitive_data("010-1234-5678") is True
    assert has_sensitive_data("일반 민원 내용입니다") is False
