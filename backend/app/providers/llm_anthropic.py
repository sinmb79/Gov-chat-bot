"""
Anthropic Claude LLM Provider.
근거(context_chunks)가 있을 때만 호출.
할루시네이션 방지: 근거 없으면 None 반환.
"""
from typing import Optional

from app.providers.llm import LLMProvider

SYSTEM_PROMPT_TEMPLATE = """당신은 {tenant_name}의 민원 안내 AI입니다.
반드시 아래 근거 문서에 있는 내용만을 바탕으로 답변하세요.
근거 없는 내용은 절대 추측하거나 생성하지 마세요.

근거 문서:
{context}

규칙:
1. 근거 문서에 없는 내용은 "담당 부서에 문의해 주세요"로 안내
2. 답변은 간결하고 명확하게 (3문장 이내)
3. 전문 용어는 쉬운 말로 바꿔 설명
"""


class AnthropicLLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        self.api_key = api_key
        self.model = model

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        context_chunks: list,
        max_tokens: int = 512,
    ) -> Optional[str]:
        """근거 없으면 None 반환. 예외 발생 시 None 반환."""
        if not context_chunks:
            return None  # 할루시네이션 방지 — 근거 없으면 LLM 미호출

        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=self.api_key)
            message = await client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            return message.content[0].text if message.content else None
        except Exception:
            return None  # 실패 시 None — 호출자가 Tier D로 폴백


class OpenAILLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        context_chunks: list,
        max_tokens: int = 512,
    ) -> Optional[str]:
        if not context_chunks:
            return None

        try:
            import openai
            client = openai.AsyncOpenAI(api_key=self.api_key)
            response = await client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
            return response.choices[0].message.content
        except Exception:
            return None
