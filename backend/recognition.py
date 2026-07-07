"""인식. 이미지를 밋밋한 묘사로 바꾼다.

2단계(TECH_PLAN 3.2): 기성 VLM(지금은 Gemini 비전)으로 실제 이미지를 묘사로 바꾼다.
플랜 방침대로 인식 모델을 직접 만들지 않고 가져다 쓴다. 투자처는 리라이터 하나.

- image가 http(s) URL이거나 data URI면 실제로 읽어 VLM으로 묘사한다.
- image가 없거나 자리표시자면 고정 묘사로 폴백한다(뼈대/app 경로 호환).
- VLM 호출부(_vlm_describe)는 별도 함수로 분리 — 나중에 로컬 오픈소스 VLM으로 교체.
- 작품 식별(어느 작품인지)은 다음 단계. 지금은 묘사까지만.

recognize(image) -> str 시그니처는 유지한다.
"""

import base64
import json
import urllib.request

import config

# image를 못 읽을 때 쓰는 고정 묘사(뼈대 호환).
FALLBACK_DESCRIPTION = "받침대 위에 선 남자 조각상. 대리석."

# VLM에게 주는 지시. 밋밋하고 객관적인 묘사만 뽑는다(해석은 리라이터 몫).
_VLM_INSTRUCTION = (
    "이 이미지에 보이는 것을 한국어로 객관적으로 묘사하세요. "
    "해석이나 감상 없이 형태, 재질, 색, 배치 같은 사실만 담담하게. "
    "목록이나 기호 없이 자연스러운 문장으로."
)


def recognize(image) -> str:
    """이미지를 받아 밋밋한 묘사 문자열을 반환한다.

    image가 실제 이미지(URL/data URI)면 VLM으로 묘사하고,
    그렇지 않으면(없음/자리표시자) 고정 묘사로 폴백한다.
    """
    loaded = _load_image(image)
    if loaded is None:
        return FALLBACK_DESCRIPTION
    image_bytes, mime_type = loaded
    return _vlm_describe(image_bytes, mime_type)


def is_recognizable(image) -> bool:
    """image가 실제로 인식 가능한 입력(URL/data URI)인지. 자리표시자/빈값은 False."""
    return isinstance(image, str) and (
        image.startswith("http://")
        or image.startswith("https://")
        or image.startswith("data:")
    )


def identify(raw_description: str, catalog) -> str:
    """밋밋한 묘사를 카탈로그와 대조해 어느 작품인지 artwork_id를 고른다.

    확신이 없으면 None을 반환한다(플랜 3.2: 이미지 식별은 어려우므로 억지로 맞추지 않는다.
    나중에 QR/NFC 태깅으로 정확도를 보강한다). 매칭 판단부(_match_llm)는 별도 함수로 분리 —
    나중에 임베딩 유사도나 태그 조회로 교체 가능.
    """
    if not catalog:
        return None
    # 카탈로그를 매칭 판단에 필요한 필드만 추려 전달한다.
    items = [
        {
            "id": a.get("id"),
            "title": a.get("title", ""),
            "artist": a.get("artist", ""),
            "material": a.get("material", ""),
            "description": a.get("description", ""),
        }
        for a in catalog
    ]
    valid_ids = {a.get("id") for a in catalog}
    guess = _match_llm(raw_description, items)
    return guess if guess in valid_ids else None


def _match_llm(raw_description: str, items) -> str:
    """묘사와 카탈로그를 받아 가장 맞는 id 또는 'none'을 반환한다. 지금은 Gemini.

    나중에 임베딩 검색이나 태그 조회로 교체할 부분. 이 함수만 바꾸면 된다.
    """
    from google import genai

    catalog_text = json.dumps(items, ensure_ascii=False)
    prompt = (
        "다음은 미술관 작품 카탈로그다.\n"
        f"{catalog_text}\n\n"
        "그리고 다음은 어떤 대상을 밋밋하게 묘사한 글이다.\n"
        f"묘사: {raw_description}\n\n"
        "이 묘사가 카탈로그의 어느 작품인지 판단해라. 확실히 일치하는 게 있으면 그 id만, "
        "확신이 없거나 해당 없음이면 정확히 none 이라고만 답해라. "
        "다른 말, 설명, 문장부호 없이 id 또는 none 한 단어만 출력한다."
    )
    client = genai.Client(api_key=config.require_api_key())
    response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=prompt,
    )
    answer = (response.text or "").strip().split()
    return answer[0] if answer else "none"


def _load_image(image):
    """image 입력을 (bytes, mime_type)로 정규화한다. 못 읽으면 None."""
    if not image or not isinstance(image, str):
        return None
    if image.startswith("data:"):
        # data:image/png;base64,....
        try:
            header, b64 = image.split(",", 1)
            mime = header[len("data:"):].split(";")[0] or "image/jpeg"
            return base64.b64decode(b64), mime
        except Exception:
            return None
    if image.startswith("http://") or image.startswith("https://"):
        try:
            with urllib.request.urlopen(image, timeout=15) as resp:
                data = resp.read()
                mime = resp.headers.get_content_type() or "image/jpeg"
                return data, mime
        except Exception:
            return None
    return None


def _vlm_describe(image_bytes: bytes, mime_type: str) -> str:
    """VLM으로 이미지를 밋밋한 묘사로 바꾼다. 지금은 Gemini 비전.

    나중에 로컬 오픈소스 VLM(Qwen2-VL 등)으로 교체할 부분. 이 함수만 바꾸면 된다.
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=config.require_api_key())
    response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            _VLM_INSTRUCTION,
        ],
    )
    return (response.text or "").strip() or FALLBACK_DESCRIPTION
