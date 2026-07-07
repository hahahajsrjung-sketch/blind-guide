"""평가셋 형식 검증기.

llm/data/evalset.jsonl 이 LLM_SPEC 2.2의 형식을 지키는지 확인한다.
데이터 내용을 바꾸지 않는다 — 검사만 한다. 수량을 늘릴 때도 이걸로 회귀 확인.

검사 항목:
- 각 줄이 유효한 JSON 이고 profile/raw/target 키를 가진다.
- profile.onset ∈ {congenital, acquired, unknown}, length ∈ {short, medium, long}.
- profile.interest 키 존재(값은 null 허용).
- raw, target 이 비어있지 않은 문자열.
- 같은 raw 에 onset 만 다른 쌍이 최소 1개 이상 존재(색 설명 차이 측정용 필수 요건).

사용:  python validate_evalset.py
종료코드: 위반 없으면 0, 있으면 1.
"""

import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DATA = Path(__file__).resolve().parents[1] / "data" / "evalset.jsonl"
ONSETS = {"congenital", "acquired", "unknown"}
LENGTHS = {"short", "medium", "long"}


def main():
    if not DATA.exists():
        print(f"[FAIL] 파일 없음: {DATA}")
        return 1

    lines = [l for l in DATA.read_text(encoding="utf-8").splitlines() if l.strip()]
    errors = []
    items = []
    for i, line in enumerate(lines):
        try:
            o = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"줄 {i}: JSON 파싱 실패 — {e}")
            continue
        items.append(o)

        prof = o.get("profile")
        if not isinstance(prof, dict):
            errors.append(f"줄 {i}: profile 없음/형식오류")
            continue
        if prof.get("onset") not in ONSETS:
            errors.append(f"줄 {i}: onset='{prof.get('onset')}' (허용: {sorted(ONSETS)})")
        if prof.get("length") not in LENGTHS:
            errors.append(f"줄 {i}: length='{prof.get('length')}' (허용: {sorted(LENGTHS)})")
        if "interest" not in prof:
            errors.append(f"줄 {i}: interest 키 누락(값 null 허용이지만 키는 있어야 함)")
        for k in ("raw", "target"):
            v = o.get(k)
            if not isinstance(v, str) or not v.strip():
                errors.append(f"줄 {i}: {k} 가 비어있거나 문자열 아님")

    # 같은 raw · onset만 다른 쌍이 있는지
    by_raw = {}
    for o in items:
        prof = o.get("profile", {})
        by_raw.setdefault(o.get("raw"), set()).add(prof.get("onset"))
    pairs = {raw: onsets for raw, onsets in by_raw.items() if len(onsets) >= 2}
    if not pairs:
        errors.append("같은 raw 에 onset 만 다른 쌍이 하나도 없음 (LLM_SPEC 필수 요건 위반)")

    # 요약
    n = len(items)
    onset_counts = {}
    length_counts = {}
    for o in items:
        prof = o.get("profile", {})
        onset_counts[prof.get("onset")] = onset_counts.get(prof.get("onset"), 0) + 1
        length_counts[prof.get("length")] = length_counts.get(prof.get("length"), 0) + 1

    print(f"평가셋: {DATA}")
    print(f"항목 수: {n}  (LLM_SPEC 권장 10~20)")
    print("onset 분포: " + ", ".join(f"{k}={v}" for k, v in sorted(onset_counts.items(), key=lambda x: str(x[0]))))
    print("length 분포: " + ", ".join(f"{k}={v}" for k, v in sorted(length_counts.items(), key=lambda x: str(x[0]))))
    print(f"onset만 다른 raw 쌍: {len(pairs)}개")
    for raw, onsets in pairs.items():
        print(f"  - [{', '.join(sorted(onsets))}] {raw[:34]}…")

    if errors:
        print(f"\n[FAIL] 위반 {len(errors)}건:")
        for e in errors:
            print("  - " + e)
        return 1
    print("\n[OK] 형식 검증 통과.")
    if not (10 <= n <= 20):
        print(f"  참고: 항목 수 {n} 이 권장 범위(10~20) 밖. (검토 후 확대 시 무시 가능)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
