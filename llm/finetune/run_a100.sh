#!/usr/bin/env bash
# A100 원샷 실행 — 번들 압축 해제 후 이 스크립트 하나로 검증→학습→사후평가까지 돈다.
#
#   bash run_a100.sh            # EXAONE 7.8b (HF 엔진, config.yaml)
#   bash run_a100.sh qwen       # Qwen2.5-7B (Unsloth 엔진, config.qwen.yaml)
#
# 위치: 번들의 llm/finetune/ 에서 실행. 소요: 설치 ~10분 + 학습 ~15-30분 + 평가 ~5분.
set -euo pipefail
cd "$(dirname "$0")"

VARIANT="${1:-exaone}"

echo "=== [0/4] 파이썬 환경 ==="
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -U pip -q

echo "=== [1/4] 의존성 설치 ==="
# torch 는 CUDA 12.x 기준. A100 드라이버가 cu121을 못 받으면 cu118로 바꾼다.
pip install -q torch --index-url https://download.pytorch.org/whl/cu121
pip install -q "transformers>=4.44.0" "trl>=0.9.6,<0.13" "peft>=0.11.1" \
               "datasets>=2.20.0" "accelerate>=0.32.0" "bitsandbytes>=0.43.1" pyyaml
if [ "$VARIANT" = "qwen" ]; then
  pip install -q unsloth   # Qwen 경로만 Unsloth 사용. 실패 시 RUNBOOK 트러블슈팅 참조.
fi

echo "=== [2/4] 드라이런 검증 (GPU 불필요) ==="
if [ "$VARIANT" = "qwen" ]; then CFG=config.qwen.yaml; else CFG=config.yaml; fi
python validate_finetune.py --config "$CFG"

echo "=== [3/4] LoRA 학습 ==="
if [ "$VARIANT" = "qwen" ]; then
  python train_lora.py --config "$CFG"
  OUT=outputs/blindguide-rewriter-qwen-lora
else
  python train_lora_hf.py --config "$CFG"
  OUT=outputs/blindguide-rewriter-lora
fi

echo "=== [4/4] 사후 평가 (평가셋 15개, 성공기준: 선천맹 색누출 < 4/6) ==="
python eval_hf.py "$OUT/merged_16bit"

echo ""
echo "완료. 다음 단계:"
echo "  - 결과 확인: $OUT/merged_16bit/eval_hf_results.md"
echo "  - GGUF 변환·Ollama 등록: RUNBOOK_A100.md 5단계"
echo "  - vLLM 상시 서빙: RUNBOOK_A100.md 6단계"
