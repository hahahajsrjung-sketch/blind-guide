"""파인튜닝 입력 드라이런 검증기 — GPU 없이 config + 학습셋 정합성을 검사한다.

GPU 박스(메가존)로 넘기기 전 마지막 게이트. torch/unsloth 를 import 하지 않으므로
이 데스크탑에서 그대로 돈다. 검사 항목:

  1. config.yaml 필수 키 존재, 마커가 베이스 모델과 맞는지(EXAONE이면 [|user|]/[|assistant|]).
  2. train_chat.jsonl 형식 — 매 줄 {"messages":[system,user,assistant]}, 내용 비지 않음.
  3. 시스템 프롬프트가 backend 원본과 정확히 일치(설계 결정: 규칙을 가중치에 내재화).
  4. 홀드아웃 오염 — 평가셋(evalset.jsonl)의 raw 가 학습 user 턴에 없어야 한다.
  5. 규칙 준수 — congenital 정답에 색 이름 0(eval_local.COLOR_RE), 길이 상한, 인사말 없음.
  6. onset/길이 균형과 대략적 시퀀스 길이(문자 수 < max_seq_length*2 근사).

사용: python validate_finetune.py  (finetune/ 에서)
종료코드 0 = 통과. 위반이 있으면 1로 끝나고 위반 목록을 찍는다.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
LLM = HERE.parent
sys.path.insert(0, str(LLM / "scripts"))
import eval_local  # noqa: E402  COLOR_RE·GREET_RE·LEN_MAX·count_sentences 재사용
import try_local   # noqa: E402  backend SYSTEM_PROMPT

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REQUIRED_KEYS = [
    "base_model", "max_seq_length", "load_in_4bit", "lora_r", "lora_alpha",
    "lora_dropout", "lora_target_modules", "train_file", "num_train_epochs",
    "per_device_train_batch_size", "gradient_accumulation_steps", "learning_rate",
    "output_dir", "instruction_part", "response_part",
]

# 길이 규칙 문자열 → 상한 (evalset/학습 프롬프트의 '길이 규칙:' 줄에서 역추출).
LENGTH_LINE_RE = re.compile(r"길이 규칙: (한두 문장|서너 문장|네다섯 문장)")
RULE_TO_MAX = {"한두 문장": 2, "서너 문장": 4, "네다섯 문장": 5}
COLOR_LINE_CONG = "색을 시각 기억으로 설명하지 않는다"  # congenital 규칙 문장의 고정 앞부분.


def fail_list():
    problems = []

    # 1. config
    cfg_path = HERE / "config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    for k in REQUIRED_KEYS:
        if k not in cfg:
            problems.append(f"config.yaml에 필수 키 없음: {k}")
    if "EXAONE" in str(cfg.get("base_model", "")).upper():
        if cfg.get("instruction_part") != "[|user|]" or cfg.get("response_part") != "[|assistant|]":
            problems.append(
                "base_model이 EXAONE인데 마커가 [|user|]/[|assistant|]가 아님 "
                "(Ollama 실물 템플릿으로 확인된 값)."
            )

    # 2~3. 학습셋 형식 + 시스템 프롬프트 일치
    train_path = HERE / cfg["train_file"]
    if not train_path.exists():
        problems.append(f"학습 파일 없음: {train_path} (build_chat_dataset.py 먼저)")
        return problems, cfg, []
    rows = [json.loads(l) for l in train_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not rows:
        problems.append("학습 파일이 비어 있음")
        return problems, cfg, rows

    holdout = {json.loads(l)["raw"].strip()
               for l in (LLM / "data" / "evalset.jsonl").read_text(encoding="utf-8").splitlines()
               if l.strip()}

    stats = {"onset": {}, "len_max": {}, "max_chars": 0}
    for i, r in enumerate(rows):
        msgs = r.get("messages")
        if not msgs or [m.get("role") for m in msgs] != ["system", "user", "assistant"]:
            problems.append(f"[{i}] messages 형식이 [system,user,assistant]가 아님")
            continue
        sys_c, user_c, asst_c = (m.get("content", "") for m in msgs)
        if not (sys_c.strip() and user_c.strip() and asst_c.strip()):
            problems.append(f"[{i}] 비어 있는 메시지 있음")
            continue
        if sys_c != try_local.prompts.SYSTEM_PROMPT:
            problems.append(f"[{i}] 시스템 프롬프트가 backend 원본과 다름")

        # 4. 홀드아웃 오염
        for h in holdout:
            if h and h in user_c:
                problems.append(f"[{i}] 평가셋 raw가 학습 입력에 포함됨(오염): {h[:30]}…")

        # 5. 규칙 준수 — user 턴에서 규칙을 읽어 정답을 검사.
        is_cong = COLOR_LINE_CONG in user_c
        m = LENGTH_LINE_RE.search(user_c)
        lim = RULE_TO_MAX.get(m.group(1)) if m else 4
        n_sent = eval_local.count_sentences(asst_c)
        if is_cong and eval_local.COLOR_RE.search(asst_c):
            hits = eval_local.COLOR_RE.findall(asst_c)
            problems.append(f"[{i}] congenital 정답에 색 이름 {hits}: {asst_c[:50]}…")
        if n_sent > lim:
            problems.append(f"[{i}] 길이 초과({n_sent}>{lim}): {asst_c[:50]}…")
        if eval_local.GREET_RE.search(asst_c):
            problems.append(f"[{i}] 정답에 인사말/예고체: {asst_c[:50]}…")

        # 6. 통계
        onset = "congenital" if is_cong else ("etc")
        stats["onset"][onset] = stats["onset"].get(onset, 0) + 1
        stats["len_max"][lim] = stats["len_max"].get(lim, 0) + 1
        total_chars = len(sys_c) + len(user_c) + len(asst_c)
        stats["max_chars"] = max(stats["max_chars"], total_chars)

    # 대략적 길이 여유(한국어 ~1.5토큰/char 보수 근사 대신 문자<max_seq*2 체크).
    if stats["max_chars"] > cfg["max_seq_length"] * 2:
        problems.append(f"가장 긴 예시 {stats['max_chars']}자 — max_seq_length "
                        f"{cfg['max_seq_length']} 대비 잘릴 수 있음")

    return problems, cfg, (rows, stats)


def main():
    problems, cfg, extra = fail_list()
    if isinstance(extra, tuple):
        rows, stats = extra
        print(f"학습 예시 {len(rows)}개 | congenital {stats['onset'].get('congenital',0)} "
              f"/ 기타 {stats['onset'].get('etc',0)} | 길이상한 분포 {stats['len_max']} "
              f"| 최장 {stats['max_chars']}자")
    if problems:
        print(f"\n[실패] 위반 {len(problems)}건:")
        for p in problems[:40]:
            print("  -", p)
        if len(problems) > 40:
            print(f"  … 외 {len(problems)-40}건")
        raise SystemExit(1)
    print("[통과] config·형식·홀드아웃·규칙 검사 모두 통과. GPU 박스로 넘겨도 된다.")


if __name__ == "__main__":
    main()
