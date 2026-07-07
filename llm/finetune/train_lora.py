"""리라이터 LoRA 파인튜닝 — Unsloth + TRL SFTTrainer.

TECH_PLAN 3.4의 3단계. 프롬프트(v2)로도 남은 격차 — 선천맹 색을 교차감각으로 푸는 방식,
톤, 한국어 화면해설 관례 — 를 가중치에 학습시킨다. 학습 데이터는 감수를 마친
build_chat_dataset.py 산출물(채팅 형식). 시스템 프롬프트는 backend 원본이므로, 학습된 모델은
backend 리라이터의 현재 프롬프트를 그대로 받고도 규칙을 지키게 된다(프롬프트 변경 불필요).

이 스크립트는 GPU 박스(메가존 A100 등)에서 돈다. 데스크탑(RTX 5070 Ti 16GB)에서도 7.8B QLoRA는
가능하나, 방침은 무거운 학습을 메가존에서. requirements.txt 참고.

사용:
  python train_lora.py --config config.yaml
학습 후 outputs/ 에 LoRA 어댑터(+병합 16bit +GGUF)가 생긴다. Ollama 서빙은 export_to_ollama.md.
"""

import argparse
import json
from pathlib import Path

import yaml


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_chat_jsonl(path):
    from datasets import Dataset
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    if not rows:
        raise SystemExit(f"[오류] 학습 데이터가 비었다: {path}. "
                         f"build_chat_dataset.py 로 먼저 만들어라.")
    return Dataset.from_list(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()
    cfg = load_config(args.config)

    # Unsloth 는 transformers/trl 보다 먼저 import 해야 패치가 걸린다.
    from unsloth import FastLanguageModel
    from unsloth.chat_templates import train_on_responses_only
    from trl import SFTTrainer, SFTConfig

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=cfg["base_model"],
        max_seq_length=cfg["max_seq_length"],
        load_in_4bit=cfg["load_in_4bit"],
        dtype=None,  # 자동.
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=cfg["lora_r"],
        lora_alpha=cfg["lora_alpha"],
        lora_dropout=cfg["lora_dropout"],
        target_modules=cfg["lora_target_modules"],
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=cfg["seed"],
    )

    # 채팅 형식({"messages":[...]}) → 모델 채팅 템플릿 문자열로.
    def format_chat(batch):
        texts = [
            tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)
            for msgs in batch["messages"]
        ]
        return {"text": texts}

    train_ds = load_chat_jsonl(cfg["train_file"]).map(format_chat, batched=True)
    eval_ds = None
    if cfg.get("eval_file"):
        eval_ds = load_chat_jsonl(cfg["eval_file"]).map(format_chat, batched=True)

    sft_cfg = SFTConfig(
        output_dir=cfg["output_dir"],
        num_train_epochs=cfg["num_train_epochs"],
        per_device_train_batch_size=cfg["per_device_train_batch_size"],
        gradient_accumulation_steps=cfg["gradient_accumulation_steps"],
        learning_rate=float(cfg["learning_rate"]),
        warmup_ratio=cfg["warmup_ratio"],
        weight_decay=cfg["weight_decay"],
        lr_scheduler_type=cfg["lr_scheduler_type"],
        logging_steps=cfg["logging_steps"],
        save_steps=cfg["save_steps"],
        seed=cfg["seed"],
        dataset_text_field="text",
        max_seq_length=cfg["max_seq_length"],
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        args=sft_cfg,
    )

    # 손실을 assistant 응답 토큰에만 건다(프롬프트는 학습 신호에서 제외).
    # 마커는 config.yaml에서 온다(베이스 모델별로 다름 — EXAONE는 [|user|]/[|assistant|]).
    # 마커가 틀리면 train_on_responses_only가 '조용히' 잘못 마스킹해 학습이 무효가 되므로,
    # 폴백 없이 하드 검증한다: 실제 템플릿으로 포맷한 문자열에 마커가 없으면 즉시 중단.
    instruction_part = cfg["instruction_part"]
    response_part = cfg["response_part"]
    sample_text = train_ds[0]["text"]
    for name, marker in [("instruction_part", instruction_part),
                         ("response_part", response_part)]:
        if marker not in sample_text:
            raise SystemExit(
                f"[오류] {name}='{marker}' 가 채팅 템플릿 출력에 없다. base_model "
                f"'{cfg['base_model']}' 의 실제 템플릿 마커를 config.yaml에 맞춰라.\n"
                f"템플릿 출력 앞부분: {sample_text[:200]!r}"
            )
    trainer = train_on_responses_only(
        trainer,
        instruction_part=instruction_part,
        response_part=response_part,
    )

    trainer.train()

    out = Path(cfg["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(out / "lora_adapter"))
    tokenizer.save_pretrained(str(out / "lora_adapter"))
    print(f"[완료] LoRA 어댑터 저장: {out / 'lora_adapter'}")

    if cfg.get("save_merged_16bit"):
        model.save_pretrained_merged(str(out / "merged_16bit"), tokenizer,
                                     save_method="merged_16bit")
        print(f"[완료] 병합 16bit 저장: {out / 'merged_16bit'}")

    if cfg.get("save_gguf"):
        model.save_pretrained_gguf(str(out / "gguf"), tokenizer,
                                   quantization_method=cfg.get("gguf_quant", "q4_k_m"))
        print(f"[완료] GGUF 저장: {out / 'gguf'}  (Ollama 서빙 → export_to_ollama.md)")


if __name__ == "__main__":
    main()
