"""파인튜닝 직후 A100에서 도는 사후 평가기 (Ollama 불필요, transformers 직접 생성).

eval_local.py 와 같은 평가셋(llm/data/evalset.jsonl 15개)·같은 감지기(색/길이/안전/인사말)를
쓰되, 생성만 Ollama 대신 학습 산출물(merged_16bit 또는 베이스+어댑터)로 한다.
→ GGUF 변환·전송 전에 A100에서 즉시 "파인튜닝이 효과 있었나"를 판정한다.

성공 기준: 선천맹 색 이름 누출이 baseline(v1 4/6)·v2(4/6)보다 실제로 줄 것.
비교 기준표(데스크탑 실측, ±1 오차):
  v1: 색누출 4/6, 길이 12/15, 안전 6/15, 인사 5/15
  v2: 색누출 4/6, 길이  3/15, 안전 1/15, 인사 0/15

사용 (A100, 학습 후):
  python eval_hf.py outputs/blindguide-rewriter-lora/merged_16bit
  python eval_hf.py --adapter outputs/.../lora_adapter --base LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct
결과: 콘솔 표 + <모델경로>/eval_hf_results.md
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LLM = HERE.parent
sys.path.insert(0, str(LLM / "scripts"))
import eval_local  # noqa: E402  감지기(COLOR_RE 등)·count_sentences 재사용
import try_local   # noqa: E402  build_user_prompt + backend SYSTEM_PROMPT

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

EVALSET = LLM / "data" / "evalset.jsonl"

BASELINE = {  # 데스크탑 실측(±1 오차). 아래 표와 나란히 찍는다.
    "v1 (EXAONE 7.8b, 프롬프트 단독)": dict(leak="4/6", over="12/15", safety="6/15", greet="5/15"),
    "v2 (few-shot+제약)":              dict(leak="4/6", over="3/15",  safety="1/15", greet="0/15"),
}


def load_model(args):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if args.adapter:
        from peft import PeftModel
        tok = AutoTokenizer.from_pretrained(args.base, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            args.base, torch_dtype=torch.bfloat16, device_map="auto",
            trust_remote_code=True)
        model = PeftModel.from_pretrained(model, args.adapter)
        name = f"{args.base} + {args.adapter}"
    else:
        tok = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            args.model, torch_dtype=torch.bfloat16, device_map="auto",
            trust_remote_code=True)
        name = args.model
    model.eval()
    return model, tok, name


def generate(model, tok, system, user, max_new_tokens=300):
    import torch
    msgs = [{"role": "system", "content": system},
            {"role": "user", "content": user}]
    ids = tok.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True,
                                  return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(ids, max_new_tokens=max_new_tokens,
                             do_sample=False, temperature=None, top_p=None,
                             pad_token_id=tok.eos_token_id)
    return tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model", nargs="?", default=None,
                    help="병합 모델 경로(merged_16bit) 또는 HF 모델 id")
    ap.add_argument("--adapter", default=None, help="LoRA 어댑터 경로(--base 필요)")
    ap.add_argument("--base", default=None, help="어댑터용 베이스 모델")
    args = ap.parse_args()
    if not args.model and not args.adapter:
        raise SystemExit("모델 경로를 주거나 --adapter/--base 를 써라.")
    if args.adapter and not args.base:
        raise SystemExit("--adapter 에는 --base 가 필요하다.")

    model, tok, name = load_model(args)
    system = try_local.prompts.SYSTEM_PROMPT  # backend 원본 — 파인튜닝 모델의 실전 조건.

    items = [json.loads(l) for l in EVALSET.read_text(encoding="utf-8").splitlines()
             if l.strip()]
    print(f"# 사후 평가 — {name}  (평가셋 {len(items)}개, greedy)\n")

    results = []
    for i, it in enumerate(items):
        profile, raw = it["profile"], it["raw"]
        onset = profile.get("onset", "unknown")
        length = profile.get("length", "medium")
        user = try_local.build_user_prompt(raw, profile, artwork=None)
        out = generate(model, tok, system, user)

        color_hits = len(eval_local.COLOR_RE.findall(out))
        n_sent = eval_local.count_sentences(out)
        over = n_sent > eval_local.LEN_MAX.get(length, 4)
        raw_safety = any(c in raw for c in eval_local.SAFETY_CUES)
        safety_bad = ("안전" in out) and not raw_safety
        greet = bool(eval_local.GREET_RE.search(out))
        leak = (onset == "congenital") and color_hits > 0
        results.append(dict(onset=onset, length=length, raw=raw, out=out,
                            color_hits=color_hits, leak=leak, n_sent=n_sent,
                            over=over, safety_bad=safety_bad, greet=greet))
        flags = [f for f, on in [(f"색누출({color_hits})", leak),
                                 (f"길이초과({n_sent})", over),
                                 ("안전오적용", safety_bad), ("인사말투", greet)] if on]
        print(f"[{i:2}] {onset:10} {length:6} | " + (", ".join(flags) or "OK"))

    cong = [r for r in results if r["onset"] == "congenital"]
    agg = dict(
        leak=f"{sum(r['leak'] for r in cong)}/{len(cong)}",
        over=f"{sum(r['over'] for r in results)}/{len(results)}",
        safety=f"{sum(r['safety_bad'] for r in results)}/{len(results)}",
        greet=f"{sum(r['greet'] for r in results)}/{len(results)}",
    )

    print("\n--- 비교 (색누출 / 길이 / 안전오적용 / 인사말투) ---")
    for label, b in BASELINE.items():
        print(f"  {label:34} {b['leak']:>5} {b['over']:>6} {b['safety']:>5} {b['greet']:>5}")
    print(f"  {'★ 파인튜닝(이번)':34} {agg['leak']:>5} {agg['over']:>6} "
          f"{agg['safety']:>5} {agg['greet']:>5}")

    by_raw = {}
    for r in results:
        by_raw.setdefault(r["raw"], {})[r["onset"]] = r["color_hits"]
    print("\n--- 쌍 비교 (색 이름 수 cong vs acq — cong이 0에 가까워야 성공) ---")
    for raw, d in by_raw.items():
        if "congenital" in d and "acquired" in d:
            print(f"  cong {d['congenital']}  vs  acq {d['acquired']}  | {raw[:24]}…")

    out_dir = Path(args.model) if args.model and Path(args.model).exists() else HERE
    md = [f"# 사후 평가 — `{name}`", "",
          "| 구성 | 색누출 | 길이 | 안전오적용 | 인사말투 |", "|---|---|---|---|---|"]
    for label, b in BASELINE.items():
        md.append(f"| {label} | {b['leak']} | {b['over']} | {b['safety']} | {b['greet']} |")
    md.append(f"| **파인튜닝(이번)** | **{agg['leak']}** | {agg['over']} "
              f"| {agg['safety']} | {agg['greet']} |")
    md += ["", "## 생성 원문"]
    for i, r in enumerate(results):
        md += [f"**[{i}] {r['onset']}/{r['length']}**  ", f"raw: {r['raw']}  ",
               f"out: {r['out']}", ""]
    (out_dir / "eval_hf_results.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\n저장: {out_dir / 'eval_hf_results.md'}")


if __name__ == "__main__":
    main()
