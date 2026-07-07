"""리라이터. 밋밋한 묘사를 사용자 시각 상태에 맞춰 다시 쓴다.

prompts에서 시스템 프롬프트와 규칙을 가져와 프롬프트를 조립하고,
call_llm으로 LLM(지금은 Gemini API)을 호출한다.
call_llm은 별도 함수로 분리해 나중에 로컬 모델로 교체 가능하게 한다.
"""

import prompts
import config


def rewrite(raw_description, profile, artwork) -> str:
    """묘사 + 프로필 + 작품정보로 맞춤 설명을 만든다.

    - profile의 onset에 따라 색 설명 규칙을 고른다.
    - artwork 정보가 있으면 컨텍스트로 넣는다.
    - artwork의 description(작가가 쓴 글)이 있으면 우선 참고 재료로 쓴다.
    """
    onset = profile.get("onset", "unknown")
    length = profile.get("length", "medium")

    color_rule = prompts.color_rule(onset)
    length_rule = prompts.length_rule(length)

    # 작품 컨텍스트 조립. 있는 필드만 넣는다.
    # v2(docs/DATA_PIPELINE.md 4절): 안전은 맨 앞, 촉각은 선천맹의 색 대체 재료,
    # ai_profile(등록 시 AI 정리본)이 있으면 정확한 시각 구성으로 활용.
    context_lines = []
    if artwork:
        ai = artwork.get("ai_profile") or {}

        # 안전이 최우선 (시스템 프롬프트 원칙 7과 호응)
        safety = artwork.get("safety") or ai.get("safety_notes")
        if safety:
            context_lines.append(f"안전·관람 규칙(반드시 가장 먼저 전달): {safety}")

        for label, key in [
            ("제목", "title"),
            ("작가", "artist"),
            ("재질", "material"),
            ("크기", "size"),
            ("제작연도", "year"),
            ("전시 위치", "location"),
        ]:
            value = artwork.get(key)
            if value:
                context_lines.append(f"{label}: {value}")

        if ai.get("visual_summary"):
            context_lines.append(f"작품의 시각 구성(정리본): {ai['visual_summary']}")

        # 촉각 재료 — 특히 congenital에서 색 대신 쓸 교차감각
        tactile = artwork.get("tactile") or ai.get("tactile_summary")
        if tactile:
            context_lines.append(f"촉각·재질감(색 대신 쓸 수 있는 감각 재료): {tactile}")

        artist_note = artwork.get("description")
        if artist_note:
            context_lines.append(f"작가가 쓴 설명(우선 참고): {artist_note}")

        intent = artwork.get("intent")
        if intent:
            context_lines.append(f"작가 의도(해석하지 말고 맥락으로만): {intent}")

    interest = profile.get("interest")
    if interest:
        context_lines.append(f"사용자 관심사: {interest}")

    context_block = "\n".join(context_lines) if context_lines else "(추가 작품 정보 없음)"

    # 리라이터에게 주는 사용자 메시지.
    user_prompt = f"""인식된 묘사:
{raw_description}

작품 정보:
{context_block}

색 설명 규칙: {color_rule}
길이 규칙: {length_rule}

위 규칙을 지켜, 인식된 묘사와 작품 정보를 바탕으로 이 사용자에게 들려줄 설명을 작성하세요."""

    return call_llm(prompts.SYSTEM_PROMPT, user_prompt)


def call_llm(system_prompt: str, user_prompt: str) -> str:
    """LLM 호출. 지금은 Google Gemini API.

    나중에 로컬 모델이나 파인튜닝 모델로 교체할 부분. 이 함수만 바꾸면 된다.
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=config.require_api_key())
    response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
        ),
    )
    return (response.text or "").strip()
