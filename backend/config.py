"""설정. API 키와 모델 이름을 환경변수에서만 읽는다. 하드코딩 금지."""

import os

# .env 파일이 있으면 환경변수로 읽어들인다(선택). 없거나 패키지가 없어도 조용히 넘어간다.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# 리라이터가 쓰는 LLM. 지금은 Google Gemini API.
# 키는 환경변수 GEMINI_API_KEY 에서만 읽는다. 코드에 절대 넣지 않는다.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 모델 이름도 환경변수로. 없으면 기본값.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")


def require_api_key() -> str:
    """API 키가 있는지 확인하고 반환. 없으면 명확한 에러."""
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY 환경변수가 없습니다. "
            ".env.example을 참고해 키를 설정하세요."
        )
    return GEMINI_API_KEY
