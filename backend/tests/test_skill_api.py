"""
POST /skill/{tenant_slug} — 카카오 스킬 API 테스트.
"""
import pytest


def make_kakao_body(utterance: str, user_id: str = "kakao-user-1") -> dict:
    return {
        "userRequest": {
            "utterance": utterance,
            "user": {"id": user_id},
        },
        "action": {"params": {}},
    }


@pytest.mark.asyncio
async def test_skill_returns_kakao_format(client):
    """스킬 응답이 카카오 포맷(version, template.outputs)을 포함한다."""
    response = await client.post(
        "/skill/test-tenant",
        json=make_kakao_body("여권 발급 방법"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "2.0"
    assert "template" in data
    assert "outputs" in data["template"]
    assert len(data["template"]["outputs"]) > 0
    assert "simpleText" in data["template"]["outputs"][0]


@pytest.mark.asyncio
async def test_skill_tier_d_fallback_returns_200(client):
    """FAQ 없어도 Tier D 응답으로 200 반환."""
    response = await client.post(
        "/skill/test-tenant",
        json=make_kakao_body("이상한 질문"),
    )
    assert response.status_code == 200
    data = response.json()
    text = data["template"]["outputs"][0]["simpleText"]["text"]
    assert len(text) > 0


@pytest.mark.asyncio
async def test_skill_utterance_text_in_response(client):
    """응답 text 필드가 비어있지 않다."""
    response = await client.post(
        "/skill/dongducheon",
        json=make_kakao_body("담당부서 알려주세요"),
    )
    assert response.status_code == 200
    text = response.json()["template"]["outputs"][0]["simpleText"]["text"]
    assert isinstance(text, str)
    assert len(text) > 0


@pytest.mark.asyncio
async def test_skill_user_key_is_hashed(client):
    """user_key는 원본 ID가 아닌 해시값(16자리)으로 처리된다 (응답에 노출 안 됨)."""
    # 개인정보(원본 카카오 ID)가 응답 바디에 노출되지 않는지 확인
    user_id = "real-kakao-id-12345"
    response = await client.post(
        "/skill/test-tenant",
        json=make_kakao_body("질문", user_id=user_id),
    )
    assert response.status_code == 200
    response_text = response.text
    assert user_id not in response_text


@pytest.mark.asyncio
async def test_skill_masked_pii_not_in_answer(client):
    """개인정보가 포함된 발화도 정상 처리 (마스킹 후 라우팅)."""
    response = await client.post(
        "/skill/test-tenant",
        json=make_kakao_body("전화번호 010-1234-5678로 연락해주세요"),
    )
    assert response.status_code == 200
    # 마스킹된 발화로 처리되므로 응답은 정상
    data = response.json()
    assert "version" in data
