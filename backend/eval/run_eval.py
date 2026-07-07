"""평가셋 러너 (뼈대).

평가셋(JSONL: 각 줄이 {profile, raw, target})을 읽어, 각 raw+profile로 지금 리라이터가
내는 후보(candidate)를 재생성하고, target과 나란히 결과 파일로 남긴다.
"무엇이 나아졌는지" 재려면 이 러너로 후보를 뽑아 target과 비교한다(TECH_PLAN 3.4-1).

채점(score)은 지금 자리만. 나중에 LLM-judge나 규칙 기반으로 교체한다.

사용법:
    python -m eval.run_eval eval/eval_set.example.jsonl
    (backend/ 에서 실행. GEMINI_API_KEY 필요.)
결과는 eval/results/ 에 JSONL로 저장된다.
"""

import os
import sys
import json

# backend/ 를 import 경로에 넣어 rewriter 등을 쓴다.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

import rewriter  # noqa: E402


def score(target: str, candidate: str):
    """후보를 정답과 비교해 점수를 낸다. 지금은 자리만(None).

    나중에 교체: LLM-judge(강한 모델에게 규칙 기준 채점 시키기) 또는 규칙 기반 지표.
    """
    # TODO: 자동 채점 붙이기. 지금은 사람이 target vs candidate를 눈으로 비교.
    return None


def run(eval_path: str) -> str:
    samples = []
    with open(eval_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))

    results = []
    for i, s in enumerate(samples):
        profile = s.get("profile", {})
        raw = s.get("raw", "")
        target = s.get("target")
        # 평가셋은 raw+profile→설명을 본다. 작품 컨텍스트는 여기선 비운다.
        candidate = rewriter.rewrite(raw, profile, artwork=None)
        results.append({
            "i": i,
            "profile": profile,
            "raw": raw,
            "target": target,
            "candidate": candidate,
            "score": score(target, candidate),
        })
        print(f"[{i}] onset={profile.get('onset')} length={profile.get('length')}")
        print(f"    raw      : {raw}")
        print(f"    target   : {target}")
        print(f"    candidate: {candidate}")
        print()

    out_dir = os.path.join(_BACKEND_DIR, "eval", "results")
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(eval_path))[0]
    out_path = os.path.join(out_dir, base + ".results.jsonl")
    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"결과 {len(results)}건 저장: {out_path}")
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python -m eval.run_eval <평가셋.jsonl>")
        raise SystemExit(1)
    run(sys.argv[1])
