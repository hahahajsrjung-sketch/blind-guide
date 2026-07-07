"""리라이터 프롬프트 v2 — few-shot + 강한 출력 제약.

baseline(backend/prompts.py 시스템 프롬프트 단독)은 로컬 EXAONE에서 선천맹 색 규칙을
못 지켰다(notes.md 6절). v2는 그 격차를 프롬프트로 메우려는 시도다. TECH_PLAN 3.4-2
"맞춤형의 대부분은 학습이 아니라 프롬프트로 풀린다"를 실제로 끝까지 밀어본다.

바꾼 것 세 가지:
1. 강한 제약 부록 — 선천맹일 때 금지할 색 이름을 명시하고, 문장 수 상한·인사말/안전문구
   오용 금지를 못박는다. (backend 원문은 그대로 두고 llm 폴더에서 덧댄다. backend 미변경.)
2. few-shot 3개 — 선천맹(색 이름 제거+교차감각), 중도실명(색 그대로), 안전 우선 사례.
   **평가셋(evalset.jsonl)과 겹치지 않는 새 예시**로 만들어 홀드아웃 오염을 피한다.
3. 사용자 턴은 backend rewriter와 동일 형식(try_local.build_user_prompt)으로 유지.

이 모듈은 build_messages()로 메시지 리스트를 만들어 try_local.chat()에 넘긴다.
같은 프롬프트를 Ollama Modelfile(llm/model/Modelfile)에도 구워 커스텀 모델로 만든다.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import try_local  # noqa: E402  (backend/prompts.py 를 이미 sys.path에 올려 둠)

# 선천맹에서 금지하는 색 이름(감지기 COLOR_RE 와 맞춘다).
FORBIDDEN_COLORS = (
    "빨강·빨간·붉은·주황·노랑·노란·초록·녹색·연두·파랑·파란·청록·남색·보라·자주·"
    "분홍·하양·하얀·흰·검정·검은·회색·갈색"
)

# backend 원문 시스템 프롬프트 + 강한 제약 부록.
CONSTRAINTS = f"""

[출력 제약 — 반드시 지킨다]
- 아래 사용자 메시지의 '색 설명 규칙'이 congenital(선천맹)이면, 색 이름을 절대 쓰지 않는다.
  금지: {FORBIDDEN_COLORS} 등 모든 색 이름. 색을 꼭 전해야 하면 온도(따뜻함·서늘함), 질감,
  무게, 재질, 밝기, 문화적·기능적 의미로 바꿔 짧게 전한다.
- acquired(중도실명)와 unknown은 색 이름을 써도 된다. 단 unknown은 색 이름만 중립적으로
  말하고 해석을 얹지 않는다.
- '길이 규칙'의 문장 수를 넘기지 않는다. short는 최대 2문장, medium은 최대 4문장,
  long은 최대 5문장.
- 인사말("안녕하세요", "여러분")이나 예고("설명드리겠습니다", "소개해 드리겠습니다",
  "화면 해설을 통해")로 시작하지 않는다. 바로 대상 묘사로 시작한다.
- 감상 유도·평가("우아한", "고요하고 평온한", "인상적인", "감상해 보세요")를 넣지 않는다.
- 안전 정보(다가오는 열차, 계단, 뜨거운 것, 차도 등)가 인식된 묘사에 있을 때만 안전 안내를
  가장 먼저 하고, 없으면 안전 얘기를 꺼내지 않는다.
- 오직 사용자에게 들려줄 설명 문장만 출력한다. 머리말·꼬리말·메타설명 없이."""

SYSTEM_V2 = try_local.prompts.SYSTEM_PROMPT + CONSTRAINTS

# few-shot 예시 (평가셋과 겹치지 않는 새 raw). 각 (profile, raw, target).
_FEWSHOT_SRC = [
    # 선천맹 + 색 있는 일상 사물 → 색 이름 빼고 형태/기능 중심.
    ({"onset": "congenital", "interest": None, "length": "short"},
     "빨간 우체통이 길가에 서 있다. 위쪽에 편지 투입구가 있고 아래는 둥근 기둥형.",
     "길가에 사람 키만 한 우체통이 서 있습니다. 위쪽에 편지를 넣는 가로 투입구가 있고, 아래는 둥근 기둥 모양입니다."),
    # 중도실명 + 미술 → 색 그대로.
    ({"onset": "acquired", "interest": "미술", "length": "medium"},
     "해바라기를 그린 정물화. 가운데 갈색 씨앗 부분을 노란 꽃잎이 둘러쌌고 배경은 청록색.",
     "해바라기 한 송이를 담은 정물화입니다. 가운데 갈색 씨앗 부분을 노란 꽃잎이 둥글게 둘러싸고 있습니다. 배경은 청록색으로 채워져 꽃을 또렷하게 받쳐 줍니다."),
    # 선천맹 + 안전 단서 있는 공간 → 안전 우선 + 색 제거 + 기능.
    ({"onset": "congenital", "interest": None, "length": "medium"},
     "계단 입구. 첫 계단 앞바닥에 노란 경고선이 칠해져 있다. 난간은 오른쪽에 있다.",
     "바로 앞에서 계단이 시작되니 조심하세요. 첫 계단 앞바닥에는 경고 표시가 되어 있고, 오른쪽에 잡을 수 있는 난간이 있습니다."),
]


def _fewshot_messages():
    msgs = []
    for profile, raw, target in _FEWSHOT_SRC:
        user = try_local.build_user_prompt(raw, profile, artwork=None)
        msgs.append({"role": "user", "content": user})
        msgs.append({"role": "assistant", "content": target})
    return msgs


def build_messages(raw, profile, artwork=None):
    """v2 메시지 리스트: 시스템(제약) + few-shot + 실제 사용자 턴."""
    final_user = try_local.build_user_prompt(raw, profile, artwork)
    return (
        [{"role": "system", "content": SYSTEM_V2}]
        + _fewshot_messages()
        + [{"role": "user", "content": final_user}]
    )


def generate(raw, profile, artwork=None, options=None, model=None):
    return try_local.chat(build_messages(raw, profile, artwork), options=options, model=model)
