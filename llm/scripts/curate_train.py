"""감수 병합기 — train.review.jsonl 을 확정 학습셋 train.jsonl 로 만든다.

TECH_PLAN 3.4의 '사람이 감수한다' 단계를 파일로 구현한 것:

  data/sft/train.review.jsonl   생성기 출력. needs_human 플래그 포함.
  data/sft/curated_fixes.jsonl  감수자가 쓴 수정본. {source_id, onset, length, target}.
                                needs_human 항목의 서술형 색을 손질한 정답.
  → data/sft/train.jsonl        확정 학습셋. profile/raw/target (+meta 출처).

병합 규칙:
  - needs_human=False(자동통과) → 그대로 채택.
  - needs_human=True + curated_fixes에 수정본 있음 → 수정 target으로 교체 채택.
  - needs_human=True + 수정본 없음 → 탈락(감수 큐에 남음). 개수만 보고.

확정 직전 전 항목을 감지기(eval_local의 색/인사말 규칙 + 길이)로 재검증한다.
수정본이라도 규칙을 어기면 확정하지 않고 실패로 끝낸다(양보다 질).

사용: python curate_train.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import eval_local  # noqa: E402  COLOR_RE·GREET_RE·LEN_MAX·count_sentences

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DATA = Path(__file__).resolve().parents[1] / "data" / "sft"
REVIEW = DATA / "train.review.jsonl"
FIXES = DATA / "curated_fixes.jsonl"
OUT = DATA / "train.jsonl"


def load_jsonl(path):
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def key_of(source_id, profile):
    return (source_id, profile["onset"], profile.get("length", "medium"))


def check_rules(target, onset, length):
    """확정 직전 재검증. 위반 목록을 돌려준다(비면 통과)."""
    v = []
    if onset == "congenital" and eval_local.COLOR_RE.search(target):
        v.append(f"색 이름 {eval_local.COLOR_RE.findall(target)}")
    n = eval_local.count_sentences(target)
    lim = eval_local.LEN_MAX.get(length, 4)
    if n > lim:
        v.append(f"길이 초과({n}>{lim})")
    if eval_local.GREET_RE.search(target):
        v.append("인사말/예고체")
    return v


def main():
    review = load_jsonl(REVIEW)
    fixes = {key_of(f["source_id"], f): f["target"] for f in load_jsonl(FIXES)}
    if not review:
        raise SystemExit(f"[오류] {REVIEW} 가 없다. gen_sft_data.py 먼저.")

    kept, fixed, dropped, violations = [], 0, [], []
    for r in review:
        k = key_of(r["meta"]["source_id"], r["profile"])
        if r["meta"]["needs_human"]:
            if k in fixes:
                target = fixes[k]
                src = "human-fixed"
                fixed += 1
            else:
                dropped.append(k)
                continue
        else:
            target = r["target"]
            src = "auto"
        v = check_rules(target, r["profile"]["onset"], r["profile"].get("length", "medium"))
        if v:
            violations.append((k, src, v, target[:60]))
            continue
        kept.append({
            "profile": r["profile"],
            "raw": r["raw"],
            "target": target,
            "meta": {"source_id": r["meta"]["source_id"],
                     "category": r["meta"].get("category"),
                     "teacher": r["meta"].get("teacher"),
                     "curation": src},
        })

    print(f"감수 대기 {len(review)} → 확정 {len(kept)} "
          f"(자동 {len(kept)-fixed} / 수정채택 {fixed} / 탈락 {len(dropped)} / 위반배제 {len(violations)})")
    if dropped:
        print(f"감수 큐에 남음(수정본 없음): {len(dropped)}개")
        for k in dropped[:10]:
            print("   -", k)
    if violations:
        print("\n[실패] 확정 직전 재검증 위반 — 확정하지 않는다:")
        for k, src, v, head in violations[:20]:
            print(f"   - {k} [{src}] {v} :: {head}…")
        raise SystemExit(1)

    with OUT.open("w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"저장: {OUT}")
    print("다음: python build_chat_dataset.py --in ../data/sft/train.jsonl")


if __name__ == "__main__":
    main()
