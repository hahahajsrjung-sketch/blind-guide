# A100 파인튜닝 런북 (메가존, 2개월 상시)

번들(`a100_bundle.zip`)을 A100 박스에 올리고 이 문서대로 실행하면 학습→평가→서빙까지 간다.
번들은 `llm/finetune/package_a100.py` 가 만들며, 필요한 모든 것(학습셋 324개·평가셋·감지기·
backend 프롬프트 스냅샷)이 들어 있어 **레포 없이 자체완결**로 돈다.

## 0. 준비물

- A100 40/80GB 1장, Ubuntu + CUDA 12.x, Python 3.10+, 인터넷(HF 모델 다운로드).
- `a100_bundle.zip` 전송: `scp a100_bundle.zip user@<a100>:~/`

## 1. 원샷 실행

```bash
unzip a100_bundle.zip -d blindguide && cd blindguide/llm/finetune
bash run_a100.sh            # EXAONE 7.8b (기본)
# 또는
bash run_a100.sh qwen       # Qwen2.5-7B (Apache-2.0, 상용 안전)
```

원샷이 하는 일: venv → 의존성 → **드라이런 검증**(validate_finetune) → **LoRA 학습** →
**사후 평가**(eval_hf, 평가셋 15개 greedy 재생성 + 규칙 채점, baseline 표와 나란히 출력).

**성공 판정: 선천맹 색 이름 누출이 4/6 미만으로 떨어졌는가.** (길이/안전/인사말은 v2
프롬프트로도 잡혔던 항목이라 참고 지표. 색누출이 파인튜닝의 존재 이유다.)

예상 소요: 설치 ~10분, 학습 ~15–30분(324예시 × 3에폭 ≈ 122스텝), 평가 ~5분.

## 2. 엔진·베이스 선택 (중요)

| | EXAONE 3.5 7.8B (`config.yaml`) | Qwen2.5 7B (`config.qwen.yaml`) |
|---|---|---|
| 학습 스크립트 | `train_lora_hf.py` (HF 엔진) | `train_lora.py` (Unsloth) |
| 이유 | 커스텀 아키텍처라 Unsloth 미지원 가능성 | Unsloth 네이티브 |
| **라이선스** | **연구용 — 상용은 LG와 별도 계약 필요** | **Apache-2.0 (상용 자유)** |
| 지금까지의 baseline | 로컬 실측 전부 이 모델 기준 | 없음(신규 비교군) |

A100이 2개월 상시라면 **둘 다 학습해서 eval_hf 표로 나란히 비교**하는 것을 권한다.
데이터·시스템 프롬프트·하이퍼파라미터가 동일하므로 순수 베이스 비교가 된다.
상용화(SightSpace) 관점에서는 성능이 비슷하면 Qwen이 안전하다. — 최종 선정은 검토 창 안건.

## 3. 하이퍼파라미터 실험 (선택)

`config*.yaml` 만 바꾸면 된다: `lora_r`(16→32·64), `num_train_epochs`(2~5),
`learning_rate`(1e-4~3e-4). 매 실험 후 `python eval_hf.py <출력>/merged_16bit` 로 같은 잣대 채점.
결과 md가 출력 폴더마다 남으니 표만 모으면 비교표가 된다.

## 4. 수동 실행 (원샷이 안 맞을 때)

```bash
python validate_finetune.py --config config.yaml   # 게이트
python train_lora_hf.py    --config config.yaml    # EXAONE 학습
python eval_hf.py outputs/blindguide-rewriter-lora/merged_16bit
# 어댑터만 있고 병합 전이면:
python eval_hf.py --adapter outputs/.../lora_adapter --base LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct
```

## 5. GGUF 변환 → 데스크탑 Ollama 서빙

llama.cpp 는 EXAONE·Qwen2.5 아키텍처를 모두 지원한다(Ollama의 exaone3.5 가 GGUF라는 것이 증거).

```bash
git clone --depth 1 https://github.com/ggerganov/llama.cpp && cd llama.cpp
pip install -r requirements.txt
python convert_hf_to_gguf.py ../outputs/blindguide-rewriter-lora/merged_16bit \
       --outfile blindguide-rewriter-f16.gguf
cmake -B build && cmake --build build --target llama-quantize -j
./build/bin/llama-quantize blindguide-rewriter-f16.gguf blindguide-rewriter-Q4_K_M.gguf q4_k_m
```

GGUF를 데스크탑으로 가져와 등록(`finetune/export_to_ollama.md` 상세):

```
ollama create blindguide-rewriter -f Modelfile     # FROM ./blindguide-rewriter-Q4_K_M.gguf
python llm/scripts/eval_local.py blindguide-rewriter v1   # 데스크탑 재검증
```

## 6. vLLM 상시 서빙 (A100 2개월 활용)

```bash
pip install vllm
python -m vllm.entrypoints.openai.api_server \
    --model outputs/blindguide-rewriter-lora/merged_16bit \
    --trust-remote-code --dtype bfloat16 --port 8001
```

backend 연결(backend 창 소관): `call_llm` 이 OpenAI 호환 API(`http://<a100>:8001/v1`)를
부르게 분기 하나 추가 — Gemini 리라이터 의존 소멸. 인식(VLM)까지 끊으려면 같은 방식으로
Qwen2.5-VL 을 vLLM에 올리고 `_vlm_describe` 를 교체하면 Gemini 콜이 완전히 0이 된다.

## 트러블슈팅

- **Unsloth 설치/로드 실패(qwen 경로)** → `train_lora_hf.py --config config.qwen.yaml` 로 우회
  (HF 엔진은 어느 베이스든 돈다. Unsloth는 속도 최적화일 뿐).
- **EXAONE 로드 에러** → transformers 버전을 4.44+ 확인, `trust_remote_code=True` 는 코드에
  이미 있음. HF 첫 다운로드에 토큰이 필요하면 `huggingface-cli login`.
- **CUDA OOM** → config에서 `per_device_train_batch_size: 1`, `gradient_accumulation_steps: 8`.
- **"학습 토큰이 0개다" 에러** → 마커가 베이스 템플릿과 다른 것. config의
  instruction_part/response_part 를 해당 모델 템플릿에 맞춘다(에러 메시지에 템플릿 앞부분 출력됨).
- **cu121 torch 설치 실패** → run_a100.sh 의 index-url을 cu118로.

## 저작권·라이선스 메모 (검토 창 안건)

- 학습셋 324개는 원칙만으로 증류·감수(외부 대본 미입력). 평가셋은 홀드아웃.
- EXAONE 3.5 = 연구용 라이선스. **상용 배포 전 베이스 라이선스 결정 필요**(Qwen2.5 = Apache-2.0).
