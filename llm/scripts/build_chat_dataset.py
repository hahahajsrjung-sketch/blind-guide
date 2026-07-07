"""감수 통과 데이터(profile/raw/target)를 파인튜닝용 채팅 형식으로 변환한다.

핵심 설계 결정 — 학습에 쓰는 시스템 프롬프트는 backend/prompts.SYSTEM_PROMPT(원본, 최소)다.
v2의 제약 부록(rewriter_v2.CONSTRAINTS)은 학습에 넣지 않는다. 이유:

  파인튜닝의 목적은 v2 제약이 프롬프트로 억지로 시키던 규칙(선천맹 색 제거·길이·인사말 억제)을
  '가중치'에 내재화하는 것이다. 그래야 backend는 프롬프트를 늘리지 않고 call_llm 만 자체 모델로
  바꾸면 된다(TECH_PLAN "백엔드 나머지는 그대로"). 그래서 학습 입력은 backend/rewriter 가
  실제로 보내는 것과 똑같은 형식 — 시스템=원본 프롬프트, 사용자=build_user_prompt — 으로 맞추고,
  정답만 규칙을 지킨 target 을 준다. 모델은 '같은 입력에서 규칙을 지킨 출력'을 배운다.

출력: 한 줄에 {"messages":[{system},{user},{assistant}]} (OpenAI/Unsloth 호환 채팅 형식).

사용:
  # 감수 완료 파일에서(권장):
  python build_chat_dataset.py --in ../data/sft/train.jsonl
  # 감수 전 미리보기(자동통과분만, needs_human 제외):
  python build_chat_dataset.py --in ../data/sft/train.review.jsonl --auto-only
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import try_local  # noqa: E402  build_user_prompt + backend prompts

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "finetune" / "data" / "train_chat.jsonl"
# --auto-only(감수 전 미리보기)는 기본적으로 별도 파일에 쓴다.
# 같은 경로에 쓰면 미리보기가 실제 학습 파일(config.yaml train_file)을 덮어써서,
# 감수 안 된 데이터로 학습이 돌아가는 사고가 난다.
PREVIEW_OUT = ROOT / "finetune" / "data" / "train_chat.preview.jsonl"

SYSTEM = try_local.prompts.SYSTEM_PROMPT  # backend 원본 최소 프롬프트.


def to_chat(item):
    profile = item["profile"]
    raw = item["raw"]
    target = item["target"]
    user = try_local.build_user_prompt(raw, profile, artwork=None)
    return {"messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user},
        {"role": "assistant", "content": target},
    ]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="profile/raw/target JSONL")
    ap.add_argument("--out", default=None,
                    help=f"출력 경로. 기본: {DEFAULT_OUT} (--auto-only면 {PREVIEW_OUT})")
    ap.add_argument("--auto-only", action="store_true",
                    help="meta.needs_human=True 항목을 제외(감수 전 미리보기용).")
    args = ap.parse_args()

    src = Path(args.inp)
    rows = [json.loads(l) for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]

    kept, skipped = [], 0
    for r in rows:
        if args.auto_only and r.get("meta", {}).get("needs_human"):
            skipped += 1
            continue
        # 최소 유효성: target 이 비었으면 버린다.
        if not r.get("target", "").strip():
            skipped += 1
            continue
        kept.append(to_chat(r))

    out = Path(args.out) if args.out else (PREVIEW_OUT if args.auto_only else DEFAULT_OUT)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"입력 {len(rows)} → 학습예시 {len(kept)}개 (제외 {skipped})")
    print(f"저장: {out}")
    if args.auto_only:
        print("주의: --auto-only 는 감수 전 미리보기다(기본 출력도 *.preview.jsonl 로 분리). "
              "실제 학습은 사람이 감수한 train.jsonl 로 다시 만든다.")


if __name__ == "__main__":
    main()
