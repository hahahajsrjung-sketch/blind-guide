"""증류(distillation) 학습데이터 생성기.

TECH_PLAN 3.4: "학습 데이터는 증류로 만든다. 강한 AI에 원칙만 주고(대본 입력 금지) 정답을
생성시키고, 사람이 감수한다. 양보다 질." 이 스크립트는 그 파이프라인의 자동 생성 단계다.

흐름:
  raw_pool.jsonl(밋밋한 묘사) × onset(congenital/acquired/unknown)
    → 교사가 초안 생성 (원칙 프롬프트만 사용, 남의 대본 입력 안 함)
    → rule_repair 로 규칙 보정 (선천맹 색 제거·길이·인사말·안전 오적용 정리)
    → data/sft/train.review.jsonl 에 '감수 대기'로 저장
사람이 train.review.jsonl 을 검토(needs_human 우선)해 통과분만 train.jsonl 로 확정한다.
확정 파일이 build_chat_dataset.py 를 거쳐 학습 형식이 된다.

교사 백엔드 두 가지:
  --teacher local-repair  (기본) 로컬 EXAONE 7.8b + v2 프롬프트 초안 → rule_repair.
                          지금 이 데스크탑에서 바로 돈다. 자체완결.
  --teacher gemini        backend/rewriter 의 call_llm(Gemini)로 초안 → rule_repair.
                          TECH_PLAN이 말한 '강한 AI' 정석. GEMINI_API_KEY 필요.
                          (메가존/키 있는 환경에서 더 좋은 정답을 얻는 경로.)

저작권: 초안은 원칙(BACKEND_SPEC 시스템 프롬프트 + 색/길이 규칙)만으로 생성한다.
방송 화면해설 대본 등 남의 저작물은 수집·입력하지 않는다.

사용:
  python gen_sft_data.py                      # local-repair, medium 길이
  python gen_sft_data.py --teacher gemini
  python gen_sft_data.py --lengths short,medium,long
  python gen_sft_data.py --limit 5            # 앞 5개 raw만(빠른 시험)
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import try_local          # noqa: E402  프롬프트 조립 + 로컬 호출
import rewriter_v2        # noqa: E402  v2 few-shot+제약 초안
import rule_repair        # noqa: E402  규칙 보정

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
RAW_POOL = ROOT / "data" / "sft" / "raw_pool.jsonl"
EVALSET = ROOT / "data" / "evalset.jsonl"
OUT = ROOT / "data" / "sft" / "train.review.jsonl"

ONSETS = ["congenital", "acquired", "unknown"]
DET = {"temperature": 0, "top_p": 1, "seed": 0}  # 재현 가능한 생성.
# try_local.MODEL 은 argv에서 읽히므로(여기선 --teacher가 들어감) 교사 모델을 명시적으로 넘긴다.
TEACHER_MODEL = "exaone3.5:7.8b"


def load_jsonl(path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def evalset_raws():
    """홀드아웃 오염 방지: 평가셋에 있는 raw 는 학습에서 제외한다."""
    if not EVALSET.exists():
        return set()
    return {it["raw"].strip() for it in load_jsonl(EVALSET)}


def teach_local_repair(raw, profile):
    """로컬 7.8b + v2 프롬프트로 초안 → rule_repair. (draft, target, meta)"""
    draft = rewriter_v2.generate(raw, profile, artwork=None, options=DET, model=TEACHER_MODEL)
    target, meta = rule_repair.repair(draft, raw, profile)
    return draft, target, meta


def teach_gemini(raw, profile):
    """backend 의 Gemini 리라이터로 초안 → rule_repair. GEMINI_API_KEY 필요."""
    backend = ROOT.parent / "backend"
    sys.path.insert(0, str(backend))
    import rewriter as backend_rewriter  # noqa: E402
    # backend rewriter.rewrite(raw, profile, artwork) 계약을 그대로 사용.
    draft = backend_rewriter.rewrite(raw, profile, artwork=None)
    target, meta = rule_repair.repair(draft, raw, profile)
    return draft, target, meta


TEACHERS = {"local-repair": teach_local_repair, "gemini": teach_gemini}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--teacher", choices=list(TEACHERS), default="local-repair")
    ap.add_argument("--lengths", default="medium",
                    help="쉼표로 구분. short,medium,long 중.")
    ap.add_argument("--limit", type=int, default=0, help="앞 N개 raw만(0=전체).")
    args = ap.parse_args()

    teach = TEACHERS[args.teacher]
    lengths = [x.strip() for x in args.lengths.split(",") if x.strip()]

    pool = load_jsonl(RAW_POOL)
    if args.limit:
        pool = pool[: args.limit]
    banned = evalset_raws()

    rows, n_auto, n_human, n_skip = [], 0, 0, 0
    total = len(pool) * len(ONSETS) * len(lengths)
    done = 0
    print(f"# 증류 생성 — 교사: {args.teacher}, raw {len(pool)}개 × onset {len(ONSETS)} "
          f"× 길이 {len(lengths)} = 목표 {total}개\n")

    for item in pool:
        raw = item["raw"].strip()
        if raw in banned:
            print(f"[skip] 평가셋과 겹침: {item['id']}")
            n_skip += len(ONSETS) * len(lengths)
            continue
        for onset in ONSETS:
            for length in lengths:
                profile = {"onset": onset, "interest": None, "length": length}
                try:
                    draft, target, meta = teach(raw, profile)
                except Exception as e:
                    done += 1
                    print(f"[{done}/{total}] ERROR {item['id']} {onset}/{length}: {e}")
                    continue
                done += 1
                if meta["needs_human"]:
                    n_human += 1
                else:
                    n_auto += 1
                rows.append({
                    "profile": profile,
                    "raw": raw,
                    "target": target,
                    "meta": {
                        "source_id": item["id"],
                        "category": item.get("category"),
                        "teacher": args.teacher,
                        "needs_human": meta["needs_human"],
                        "repair_notes": meta["notes"],
                        "draft": draft,   # 감수자가 원 초안과 비교할 수 있게 보존.
                    },
                })
                flag = "HUMAN" if meta["needs_human"] else "auto "
                print(f"[{done}/{total}] {flag} {item['id']:8} {onset:10} {length:6} "
                      f"| {target[:40]}…")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n--- 요약 ---")
    print(f"생성: {len(rows)}개  (자동통과 {n_auto} / 감수필요 {n_human} / 스킵 {n_skip})")
    print(f"저장: {OUT}")
    print("다음: 사람이 이 파일을 감수(needs_human 우선)해 통과분을 train.jsonl 로 확정 → "
          "build_chat_dataset.py")


if __name__ == "__main__":
    main()
