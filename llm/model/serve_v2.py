"""프롬프트-only v2 배포 — '호출 시 프롬프트 전달' 정본 경로.

파인튜닝 전 '지금 최선'의 로컬 리라이터. backend가 로컬 모드일 때 이 방식 그대로 부르면
v2 동작(길이·인사말·안전 오적용 억제, 선천맹 색 누출 절반↓)을 받는다.

### 왜 Ollama Modelfile로 굽지 않는가 (검증된 발견)

처음엔 v2 프롬프트를 Ollama 커스텀 모델(Modelfile의 SYSTEM/MESSAGE)로 구워 단일 태그로
배포하려 했다. 그런데 **긴 v2 프롬프트를 Modelfile에 구우면 퇴화한다**(temp0 greedy에서 재현):
  - MESSAGE로 few-shot을 박으면 새 입력에서 예시 답을 그대로 되뱉음.
  - SYSTEM에 긴 제약을 구우면 입력에 없는 사물을 환각하고 메타 잡담을 붙임.
반면 **똑같은 텍스트를 호출 시 system/user 메시지로 넘기면 정상 작동**한다. eval_local의 v2
수치도 이 호출 경로로 잰 것이다. 결론: v2는 '굽지 말고 호출 시 전달'한다.

(단일 태그로 굽는 배포는 finetune/ 파인튜닝 모델의 몫이다. 그건 규칙을 가중치에 내재화해
backend의 짧은 원본 프롬프트만으로 동작하므로, 짧은 SYSTEM 굽기는 안전하다 —
finetune/export_to_ollama.md.)

### 사용

    from serve_v2 import rewrite_local
    text = rewrite_local(raw_description, profile, artwork=None)

profile = {"onset": "congenital|acquired|unknown", "interest": str|None, "length": "short|medium|long"}
이 함수는 scripts/rewriter_v2.generate 를 그대로 위임한다. backend가 로컬 리라이터를 붙일 때
이 조립(시스템=SYSTEM_V2, few-shot 3개, 사용자=build_user_prompt)을 복제하면 된다.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import rewriter_v2  # noqa: E402

# 로컬 베이스(파인튜닝 전). 파인튜닝 후에는 blindguide-rewriter 로 바꾸고 rewriter_v2 대신
# backend 원본 프롬프트(짧은)로 호출한다 — 규칙이 가중치에 있으므로 few-shot 불필요.
LOCAL_MODEL = "exaone3.5:7.8b"


def rewrite_local(raw_description, profile, artwork=None, temperature=0.4):
    """로컬 프롬프트-only v2 리라이터. backend call_llm 로컬 분기의 참조 구현."""
    options = {"temperature": temperature}
    return rewriter_v2.generate(raw_description, profile, artwork=artwork,
                                options=options, model=LOCAL_MODEL)


if __name__ == "__main__":
    # 손시험: 선천맹 vs 중도실명 색 처리 대비.
    raw = "빨간 지붕의 집 한 채가 언덕 위에 있다. 파란 하늘이 넓다."
    for onset in ("congenital", "acquired"):
        prof = {"onset": onset, "interest": None, "length": "medium"}
        print(f"--- {onset} ---")
        print(rewrite_local(raw, prof, temperature=0))
        print()
