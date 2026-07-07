"""평가셋 수집용 로그 훅.

TECH_PLAN 3.4-1: 파인튜닝 전에 평가셋(밋밋한 묘사 raw + 정답 설명 target)을 먼저 만든다.
그 씨앗으로, /describe 한 건마다 (profile, raw, 생성결과)를 JSONL로 남긴다.
여기 쌓인 로그를 나중에 사람이 감수해 target을 붙이면 평가셋/학습셋이 된다.

원칙:
- best-effort. 로깅이 실패해도 API 응답은 절대 안 깨진다(main에서 감싼다).
- 형식은 평가셋 형식(profile/raw/target)과 호환. 여기서는 target 대신 model_output을 남긴다.
- 실제 배포 시 사용자 데이터 수집은 동의·PII 처리가 필요하다(지금은 데모 데이터).
"""

import os
import json
import datetime

# 로그 위치와 on/off는 환경변수로. 기본은 backend/eval/logs/interactions.jsonl, 켜짐.
_DEFAULT_DIR = os.path.join(os.path.dirname(__file__), "eval", "logs")
EVAL_LOG_ENABLED = os.environ.get("EVAL_LOG_ENABLED", "1") != "0"
EVAL_LOG_DIR = os.environ.get("EVAL_LOG_DIR", _DEFAULT_DIR)
_LOG_PATH = os.path.join(EVAL_LOG_DIR, "interactions.jsonl")


def record(profile, raw_description, model_output, artwork_id=None, image_present=False, model=None):
    """상호작용 한 건을 평가셋 씨앗으로 남긴다. 실패는 조용히 무시(best-effort)."""
    if not EVAL_LOG_ENABLED:
        return
    try:
        sample = {
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            # 평가셋 형식과 맞춘 profile: onset/interest/length만.
            "profile": {
                "onset": profile.get("onset"),
                "interest": profile.get("interest", ""),
                "length": profile.get("length"),
            },
            "raw": raw_description,          # 밋밋한 묘사(인식 결과).
            "model_output": model_output,    # 리라이터가 생성한 설명(감수 전 후보).
            "target": None,                  # 사람이 감수해 채울 정답 자리.
            "meta": {
                "user_id": profile.get("user_id"),
                "artwork_id": artwork_id,
                "image_present": image_present,
                "model": model,
            },
        }
        os.makedirs(EVAL_LOG_DIR, exist_ok=True)
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")
    except Exception:
        # 로깅은 부가 기능. 무슨 일이 있어도 응답 경로를 막지 않는다.
        pass
