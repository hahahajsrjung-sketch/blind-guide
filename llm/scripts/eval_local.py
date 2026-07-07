"""로컬 모델 규칙 준수 자동 평가 (결정론적, LLM-judge 아님).

llm/data/evalset.jsonl 을 읽어, 각 항목의 raw+profile 로 로컬 모델 후보 설명을
재생성하고, 규칙 위반을 규칙 기반으로 센다. 목적은 notes.md의 눈대중 소감을 수치로
바꾸는 것. 색 이름 누출·길이 초과·안전문구 오적용·방송 인사말투 4가지를 본다.

주의. 이건 "측정" 도구다. 프롬프트를 바꾸거나 베이스 모델을 정하는 결정은 하지 않는다.
그건 검토 창의 몫. 여기서는 지금 프롬프트/모델의 현재 상태만 잰다.

사용:  python eval_local.py [모델태그]   (기본 exaone3.5:7.8b)
결과:  콘솔 요약 + llm/data/eval_local_results.md (전체 표)
"""

import json
import re
import sys
from pathlib import Path

# stdout을 UTF-8로 (윈도우 cp949 회피).
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 재현 하네스 재사용: 프롬프트 조립과 로컬 호출을 try_local에서 그대로 가져온다.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import try_local  # noqa: E402

MODEL = sys.argv[1] if len(sys.argv) > 1 else "exaone3.5:7.8b"
MODE = sys.argv[2] if len(sys.argv) > 2 else "v1"  # v1=baseline(시스템 단독), v2=few-shot+제약
TAG = MODEL.split(":")[-1] if ":" in MODEL else MODEL  # 7.8b / 2.4b …

if MODE == "v2":
    import rewriter_v2  # noqa: E402

# 재현을 위해 greedy 디코딩으로 고정한다. baseline은 재현돼야 의미가 있으므로
# 손시험(try_local, temp 0.4)과 달리 평가는 온도 0.
DET_OPTIONS = {"temperature": 0, "top_p": 1, "seed": 0}

DATA = Path(__file__).resolve().parents[1] / "data" / "evalset.jsonl"
_SUFFIX = "" if MODE == "v1" else f"_{MODE}"
OUT = Path(__file__).resolve().parents[1] / "data" / f"eval_local_results_{TAG}{_SUFFIX}.md"

# 시각적 색 이름 (온도/질감 어휘는 제외 — 그건 선천맹에 허용되는 보조 수단).
# '자주'는 부사(자주 탐구되는)와 동형이라 오탐이 실제 발생(2.4b [5]) → 자주색/자줏빛만 매칭.
COLOR_RE = re.compile(
    r"빨강|빨간|빨갛|붉|파랑|파란|파랗|노랑|노란|노랗|주황|초록|녹색|연두|청록|보라"
    r"|자주색|자줏빛|분홍|핑크|하양|하얀|흰|검정|검은|까만|회색|잿빛|갈색|밤색|남색"
    r"|청색|적색|황색|백색|흑색|은색|금색"
)
# raw에 안전 단서가 있으면 output의 '안전' 언급은 정당. 없는데 붙이면 오적용.
SAFETY_CUES = ["열차", "선로", "횡단보도", "신호", "뜨겁", "뜨거", "계단", "차도", "승강장"]
GREET_RE = re.compile(r"안녕하세요|여러분|설명드리|소개해|해설을 통해|말씀드리")
LEN_MAX = {"short": 2, "medium": 4, "long": 5}


def count_sentences(text):
    return len([s for s in re.split(r"[.!?]", text) if s.strip()])


def evaluate(item):
    profile = item["profile"]
    raw = item["raw"]
    onset = profile.get("onset", "unknown")
    length = profile.get("length", "medium")

    if MODE == "v2":
        out = rewriter_v2.generate(raw, profile, artwork=None,
                                   options=DET_OPTIONS, model=MODEL)
    else:
        up = try_local.build_user_prompt(raw, profile, artwork=None)
        out = try_local.call_local(try_local.prompts.SYSTEM_PROMPT, up,
                                   options=DET_OPTIONS, model=MODEL)

    color_hits = len(COLOR_RE.findall(out))
    n_sent = count_sentences(out)
    over_len = n_sent > LEN_MAX.get(length, 4)
    raw_has_safety = any(c in raw for c in SAFETY_CUES)
    safety_misapplied = ("안전" in out) and not raw_has_safety
    greeting = bool(GREET_RE.search(out))

    # 선천맹에서만 색 이름 누출을 '위반'으로 본다 (규칙상 색 이름을 빼야 함).
    color_leak_violation = (onset == "congenital") and color_hits > 0

    return {
        "onset": onset,
        "length": length,
        "raw": raw,
        "output": out,
        "color_hits": color_hits,
        "color_leak_violation": color_leak_violation,
        "n_sent": n_sent,
        "over_len": over_len,
        "safety_misapplied": safety_misapplied,
        "greeting": greeting,
    }


def main():
    items = [json.loads(l) for l in DATA.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"# 규칙 준수 평가 — 모델: {MODEL}  (항목 {len(items)}개)\n")

    results = []
    for i, it in enumerate(items):
        r = evaluate(it)
        results.append(r)
        flags = []
        if r["color_leak_violation"]:
            flags.append(f"색누출({r['color_hits']})")
        elif r["color_hits"]:
            flags.append(f"색{r['color_hits']}")
        if r["over_len"]:
            flags.append(f"길이초과({r['n_sent']}/{LEN_MAX[r['length']]})")
        if r["safety_misapplied"]:
            flags.append("안전오적용")
        if r["greeting"]:
            flags.append("인사말투")
        print(f"[{i:2}] {r['onset']:10} {r['length']:6} | " + (", ".join(flags) if flags else "OK"))

    # 집계
    cong = [r for r in results if r["onset"] == "congenital"]
    cong_leak = sum(1 for r in cong if r["color_leak_violation"])
    over = sum(1 for r in results if r["over_len"])
    safety_bad = sum(1 for r in results if r["safety_misapplied"])
    greet = sum(1 for r in results if r["greeting"])

    print("\n--- 집계 ---")
    print(f"선천맹 색 이름 누출: {cong_leak}/{len(cong)} 항목")
    print(f"길이 초과: {over}/{len(results)}")
    print(f"안전문구 오적용: {safety_bad}/{len(results)}")
    print(f"방송 인사말투: {greet}/{len(results)}")

    # 같은 raw · onset만 다른 쌍에서 색 이름 사용 수 비교
    by_raw = {}
    for r in results:
        by_raw.setdefault(r["raw"], {})[r["onset"]] = r["color_hits"]
    print("\n--- 쌍 비교 (색 이름 사용 수: congenital vs acquired) ---")
    pair_lines = []
    for raw, d in by_raw.items():
        if "congenital" in d and "acquired" in d:
            short = raw[:24].replace("\n", " ")
            line = f"cong {d['congenital']}  vs  acq {d['acquired']}  | {short}…"
            print("  " + line)
            pair_lines.append((raw, d))

    # 마크다운 결과 저장
    md = [f"# 규칙 준수 평가 결과 — 모델 `{MODEL}`", ""]
    md.append(f"항목 {len(items)}개. 결정론적 규칙 검사(LLM-judge 아님). "
              f"생성은 greedy 디코딩(temperature 0, seed 0)으로 재현 가능. "
              f"`python eval_local.py {MODEL}` 로 갱신.\n")
    md.append("## 집계")
    md.append("")
    md.append("| 지표 | 값 |")
    md.append("|---|---|")
    md.append(f"| 선천맹 색 이름 누출 | {cong_leak}/{len(cong)} 항목 |")
    md.append(f"| 길이 초과 | {over}/{len(results)} |")
    md.append(f"| 안전문구 오적용 | {safety_bad}/{len(results)} |")
    md.append(f"| 방송 인사말투 | {greet}/{len(results)} |")
    md.append("")
    md.append("## 쌍 비교 — 색 이름 사용 수 (congenital vs acquired)")
    md.append("")
    md.append("규칙대로면 congenital은 0에 가까워야 하고 acquired보다 확연히 적어야 한다.")
    md.append("")
    md.append("| raw (앞부분) | congenital | acquired |")
    md.append("|---|---|---|")
    for raw, d in pair_lines:
        md.append(f"| {raw[:30].replace(chr(10),' ')}… | {d['congenital']} | {d['acquired']} |")
    md.append("")
    md.append("## 항목별")
    md.append("")
    md.append("| # | onset | length | 색수 | 문장수 | 길이초과 | 안전오적용 | 인사말투 |")
    md.append("|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(results):
        md.append(f"| {i} | {r['onset']} | {r['length']} | {r['color_hits']} | "
                  f"{r['n_sent']} | {'Y' if r['over_len'] else ''} | "
                  f"{'Y' if r['safety_misapplied'] else ''} | {'Y' if r['greeting'] else ''} |")
    md.append("")
    md.append("## 생성된 후보 (감수용 원문)")
    md.append("")
    for i, r in enumerate(results):
        md.append(f"**[{i}] {r['onset']} / {r['length']}**  ")
        md.append(f"raw: {r['raw']}  ")
        md.append(f"out: {r['output']}")
        md.append("")
    OUT.write_text("\n".join(md), encoding="utf-8")
    print(f"\n저장: {OUT}")


if __name__ == "__main__":
    main()
