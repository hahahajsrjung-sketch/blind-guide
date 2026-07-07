"""A100 전송용 자체완결 번들(zip) 생성기.

레포 전체 대신, 파인튜닝에 필요한 것만 레포와 같은 상대 구조로 담는다. 그래야 기존 코드
(try_local→backend/prompts.py 상대경로 import, validate_finetune→llm/data 등)가 수정 없이
그대로 돈다. backend/prompts.py 는 스냅샷 복사(읽기만 — backend 폴더 불변).

번들 구조:
  backend/prompts.py                (스냅샷)
  llm/scripts/{try_local,eval_local,rewriter_v2}.py
  llm/data/evalset.jsonl            (사후 평가용 홀드아웃)
  llm/finetune/{config.yaml, config.qwen.yaml, train_lora.py, train_lora_hf.py,
                eval_hf.py, validate_finetune.py, run_a100.sh,
                RUNBOOK_A100.md, requirements.txt, export_to_ollama.md}
  llm/finetune/data/train_chat.jsonl  (확정 학습셋 324 — 감수 완료본)

사용: python package_a100.py   →  llm/dist/a100_bundle.zip
"""

import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent          # llm/finetune
LLM = HERE.parent                                # llm
REPO = LLM.parent                                # blind-guide
OUT = LLM / "dist" / "a100_bundle.zip"

FILES = [
    # (아카이브 경로, 실제 경로)
    ("backend/prompts.py", REPO / "backend" / "prompts.py"),
    ("llm/scripts/try_local.py", LLM / "scripts" / "try_local.py"),
    ("llm/scripts/eval_local.py", LLM / "scripts" / "eval_local.py"),
    ("llm/scripts/rewriter_v2.py", LLM / "scripts" / "rewriter_v2.py"),
    ("llm/data/evalset.jsonl", LLM / "data" / "evalset.jsonl"),
    ("llm/finetune/config.yaml", HERE / "config.yaml"),
    ("llm/finetune/config.qwen.yaml", HERE / "config.qwen.yaml"),
    ("llm/finetune/train_lora.py", HERE / "train_lora.py"),
    ("llm/finetune/train_lora_hf.py", HERE / "train_lora_hf.py"),
    ("llm/finetune/eval_hf.py", HERE / "eval_hf.py"),
    ("llm/finetune/validate_finetune.py", HERE / "validate_finetune.py"),
    ("llm/finetune/run_a100.sh", HERE / "run_a100.sh"),
    ("llm/finetune/RUNBOOK_A100.md", HERE / "RUNBOOK_A100.md"),
    ("llm/finetune/requirements.txt", HERE / "requirements.txt"),
    ("llm/finetune/export_to_ollama.md", HERE / "export_to_ollama.md"),
    ("llm/finetune/data/train_chat.jsonl", HERE / "data" / "train_chat.jsonl"),
]


def main():
    missing = [str(src) for _, src in FILES if not src.exists()]
    if missing:
        print("[오류] 번들에 넣을 파일이 없다:")
        for m in missing:
            print("  -", m)
        if any("train_chat" in m for m in missing):
            print("→ scripts/curate_train.py 와 build_chat_dataset.py 를 먼저 돌려라.")
        raise SystemExit(1)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for arc, src in FILES:
            z.write(src, arc)
    size = OUT.stat().st_size
    print(f"번들 생성: {OUT}  ({size/1024:.0f} KB, 파일 {len(FILES)}개)")
    print("전송:  scp", OUT.name, "user@<a100>:~/")
    print("실행:  unzip a100_bundle.zip -d blindguide && "
          "cd blindguide/llm/finetune && bash run_a100.sh")


if __name__ == "__main__":
    main()
