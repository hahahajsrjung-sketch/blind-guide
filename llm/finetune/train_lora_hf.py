"""리라이터 LoRA 파인튜닝 — HF(transformers+peft+TRL) 엔진.

train_lora.py(Unsloth 엔진)와 같은 일을 하지만 Unsloth 없이 돈다. **EXAONE 3.5 전용 경로** —
EXAONE은 커스텀 아키텍처(ExaoneForCausalLM, trust_remote_code)라 Unsloth가 지원하지 않을
가능성이 높다(공식 지원 목록에 없음). Qwen2.5 등 Unsloth 네이티브 베이스는 train_lora.py 를
쓰는 게 더 빠르고, EXAONE은 이 스크립트를 쓴다.

  EXAONE:  python train_lora_hf.py --config config.yaml
  Qwen2.5: python train_lora.py    --config config.qwen.yaml   (Unsloth, 별도 config)

응답 마스킹: TRL DataCollatorForCompletionOnlyLM 에 config의 instruction_part/response_part
마커를 넘긴다. 마커가 틀리면 조용히 전부 -100 이 되므로, 첫 예시로 마스킹이 실제로 걸리는지
**하드 검증**한다(train_lora.py 와 같은 원칙).

산출물: outputs/.../lora_adapter + merged_16bit. GGUF 변환은 llama.cpp 로 별도
(RUNBOOK_A100.md 5단계 — llama.cpp 는 EXAONE 아키텍처를 지원한다. Ollama의 exaone3.5 가
GGUF라는 것이 그 증거).
"""

import argparse
import json
from pathlib import Path

import yaml


def load_chat_jsonl(path):
    from datasets import Dataset
    rows = [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines()
            if l.strip()]
    if not rows:
        raise SystemExit(f"[오류] 학습 데이터가 비었다: {path}")
    return Dataset.from_list(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))

    import torch
    from transformers import (AutoModelForCausalLM, AutoTokenizer,
                              BitsAndBytesConfig)
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from trl import SFTTrainer, SFTConfig, DataCollatorForCompletionOnlyLM

    tokenizer = AutoTokenizer.from_pretrained(cfg["base_model"], trust_remote_code=True)

    quant = None
    if cfg["load_in_4bit"]:
        quant = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )
    model = AutoModelForCausalLM.from_pretrained(
        cfg["base_model"],
        quantization_config=quant,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,   # EXAONE 커스텀 아키텍처.
    )
    if cfg["load_in_4bit"]:
        model = prepare_model_for_kbit_training(model)

    lora = LoraConfig(
        r=cfg["lora_r"],
        lora_alpha=cfg["lora_alpha"],
        lora_dropout=cfg["lora_dropout"],
        target_modules=cfg["lora_target_modules"],
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    def format_chat(batch):
        return {"text": [
            tokenizer.apply_chat_template(m, tokenize=False, add_generation_prompt=False)
            for m in batch["messages"]
        ]}

    train_ds = load_chat_jsonl(cfg["train_file"]).map(format_chat, batched=True)

    # 마커 하드 검증 1: 포맷된 문자열에 마커가 존재해야 한다.
    sample = train_ds[0]["text"]
    for name in ("instruction_part", "response_part"):
        if cfg[name] not in sample:
            raise SystemExit(f"[오류] {name}='{cfg[name]}' 가 템플릿 출력에 없다.\n"
                             f"앞부분: {sample[:200]!r}")

    collator = DataCollatorForCompletionOnlyLM(
        response_template=cfg["response_part"],
        instruction_template=cfg["instruction_part"],
        tokenizer=tokenizer,
    )

    # 마커 하드 검증 2: 콜레이터가 실제로 응답 토큰을 남기는지(전부 -100이면 학습 무효).
    probe = collator([tokenizer(sample, truncation=True,
                                max_length=cfg["max_seq_length"])])
    kept = int((probe["labels"] != -100).sum())
    if kept == 0:
        raise SystemExit("[오류] 응답 마스킹 결과 학습 토큰이 0개다. 마커가 토큰 경계와 "
                         "안 맞는다 — config의 instruction/response_part 를 확인하라.")
    print(f"[검증] 첫 예시 학습 토큰 {kept}개 (마스킹 정상).")

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
        bf16=True,
        gradient_checkpointing=True,
        dataset_text_field="text",
        max_seq_length=cfg["max_seq_length"],
        packing=False,               # completion-only 콜레이터는 packing 불가.
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=train_ds,
        data_collator=collator,
        args=sft_cfg,
    )
    trainer.train()

    out = Path(cfg["output_dir"])
    (out / "lora_adapter").mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(out / "lora_adapter"))
    tokenizer.save_pretrained(str(out / "lora_adapter"))
    print(f"[완료] LoRA 어댑터: {out/'lora_adapter'}")

    if cfg.get("save_merged_16bit"):
        # 4bit 학습이어도 병합은 bf16 베이스를 새로 얹어서 한다.
        print("[병합] bf16 베이스에 어댑터 병합 중…")
        from peft import PeftModel
        base = AutoModelForCausalLM.from_pretrained(
            cfg["base_model"], torch_dtype=torch.bfloat16,
            device_map="auto", trust_remote_code=True)
        merged = PeftModel.from_pretrained(base, str(out / "lora_adapter"))
        merged = merged.merge_and_unload()
        merged.save_pretrained(str(out / "merged_16bit"))
        tokenizer.save_pretrained(str(out / "merged_16bit"))
        print(f"[완료] 병합 16bit: {out/'merged_16bit'}  (GGUF 변환은 RUNBOOK 5단계)")


if __name__ == "__main__":
    main()
