"""로컬 모델 시험 하네스.

backend/prompts.py의 시스템 프롬프트와 색/길이 규칙을 그대로 import 하고,
backend/rewriter.py의 user_prompt 조립을 똑같이 재현한다.
다른 점은 call_llm 뿐 — Gemini API 대신 로컬 Ollama(/api/chat)를 부른다.

BACKEND_SPEC/TECH_PLAN 방침: "call_llm만 바꾸면 로컬로 교체 가능"을 실제로 확인하는 것.
사용법:  python try_local.py [모델태그]   (기본 exaone3.5:7.8b)
"""

import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

# backend/prompts.py 를 그대로 가져다 쓴다 (원문 재현).
BACKEND = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND))
import prompts  # noqa: E402

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = sys.argv[1] if len(sys.argv) > 1 else "exaone3.5:7.8b"


def build_user_prompt(raw_description, profile, artwork):
    """backend/rewriter.py 의 조립 로직을 그대로 옮김."""
    onset = profile.get("onset", "unknown")
    length = profile.get("length", "medium")
    color_rule = prompts.color_rule(onset)
    length_rule = prompts.length_rule(length)

    context_lines = []
    if artwork:
        for label, key in [("제목", "title"), ("작가", "artist"),
                           ("재질", "material"), ("크기", "size"), ("제작연도", "year")]:
            value = artwork.get(key)
            if value:
                context_lines.append(f"{label}: {value}")
        note = artwork.get("description")
        if note:
            context_lines.append(f"작가가 쓴 설명(우선 참고): {note}")
    interest = profile.get("interest")
    if interest:
        context_lines.append(f"사용자 관심사: {interest}")
    context_block = "\n".join(context_lines) if context_lines else "(추가 작품 정보 없음)"

    return f"""인식된 묘사:
{raw_description}

작품 정보:
{context_block}

색 설명 규칙: {color_rule}
길이 규칙: {length_rule}

위 규칙을 지켜, 인식된 묘사와 작품 정보를 바탕으로 이 사용자에게 들려줄 설명을 작성하세요."""


def chat(messages, options=None, model=None):
    """로컬 Ollama /api/chat 저수준 호출. messages 를 그대로 보낸다.

    options 로 샘플링 제어. 손시험은 자연스러움을 위해 기본 temperature 0.4,
    평가(eval_local)는 재현을 위해 temperature 0(greedy)을 넘긴다.
    """
    if options is None:
        options = {"temperature": 0.4}
    body = json.dumps({
        "model": model or MODEL,
        "messages": messages,
        "stream": False,
        "options": options,
    }).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise SystemExit(
            f"[오류] Ollama 서버에 연결 실패({e}). 'ollama serve'가 떠 있는지, "
            f"모델 '{model or MODEL}'을 받았는지 확인하세요 (ollama list)."
        )
    return data["message"]["content"].strip()


def call_local(system_prompt, user_prompt, options=None, model=None):
    """시스템+사용자 단일 턴 호출 (baseline 경로)."""
    return chat(
        [{"role": "system", "content": system_prompt},
         {"role": "user", "content": user_prompt}],
        options=options, model=model,
    )


# 시험 케이스: 같은 raw(+작품정보)에 onset만 바꿔 색 설명이 갈라지는지 본다.
CASES = [
    {
        "name": "유화(색 강함)",
        "raw": "노란 배경에 파란 원피스를 입은 여자가 의자에 앉아 정면을 보고 있는 유화. 여자의 뒤로 붉은 커튼이 드리워져 있다.",
        "artwork": {"title": "앉아 있는 여인", "artist": "김OO", "material": "캔버스에 유채", "size": "90x70cm", "year": "1998"},
        "length": "medium",
    },
    {
        "name": "대리석 조각(백엔드 예시 묘사)",
        "raw": "받침대 위에 선 남자 조각상. 대리석. 오른팔을 앞으로 뻗고 있고 왼발이 반보 앞에 나와 있다.",
        "artwork": None,
        "length": "medium",
    },
    {
        "name": "추상 색면화",
        "raw": "캔버스가 위아래로 두 색면으로 나뉜 추상화. 위는 주황, 아래는 짙은 파랑. 두 색이 만나는 경계는 흐릿하다.",
        "artwork": None,
        "length": "medium",
    },
]

def main():
    print(f"# 로컬 모델 시험 — 모델: {MODEL}\n")
    for case in CASES:
        print("=" * 70)
        print(f"[케이스] {case['name']}")
        print(f"[raw] {case['raw']}\n")
        for onset in ("congenital", "acquired"):
            profile = {"onset": onset, "interest": "미술", "length": case["length"]}
            up = build_user_prompt(case["raw"], profile, case["artwork"])
            out = call_local(prompts.SYSTEM_PROMPT, up)
            label = {"congenital": "선천맹 congenital", "acquired": "중도실명 acquired"}[onset]
            print(f"  --- {label} ---")
            print(f"  {out}\n")


if __name__ == "__main__":
    main()
