# finetune — 리라이터 LoRA 파인튜닝

TECH_PLAN 3.4의 3단계. 프롬프트(v2)로도 남는 격차 — **선천맹 색을 교차감각으로 푸는 방식**,
톤, 한국어 화면해설 관례 — 를 LoRA로 가중치에 학습시킨다. 학습된 모델은 backend 리라이터의
**현재 프롬프트를 그대로 받고도** 규칙을 지키므로, backend는 `call_llm`이 부르는 모델 태그만
바꾸면 된다(백엔드 코드 나머지 불변).

## 왜 파인튜닝이 필요한가 (근거)

`llm/scripts/eval_local.py`로 잰 재현 가능한 수치:

| 지표 | v1 baseline | v2 프롬프트(few-shot+제약) |
|---|---|---|
| 길이 초과 | 12/15 | 3/15 |
| 안전문구 오적용 | 6/15 | 1/15 |
| 방송 인사말투 | 5/15 | 0/15 |
| **선천맹 색 이름 누출** | **4/6** | **4/6 (그대로)** |

(±1은 실행 간 오차 — notes.md 6절.)

프롬프트로 길이·인사말·안전은 **완전히** 잡혔다. 그러나 제품의 심장인 "선천맹에게 색 이름
대신 교차감각"은 프롬프트만으로 안 잡힌다(누출 항목 수 불변, 누출량만 절반). 이 남은 격차가
파인튜닝의 표적이다. — TECH_PLAN 3.4-3 예측 그대로.

## 파이프라인 (llm 폴더 안에서 완결)

```
1. raw_pool.jsonl           학습용 밋밋한 묘사 풀 (평가셋과 분리, 원칙만으로 창작)
        │  scripts/gen_sft_data.py   (교사 초안 → rule_repair → 감수 대기)
        ▼
2. data/sft/train.review.jsonl   감수 대기. needs_human 우선으로 사람이 검토,
        │                         수정 target은 data/sft/curated_fixes.jsonl 에 기록.
        │  scripts/curate_train.py   (자동통과+수정본 병합, 확정 전 규칙 재검증)
        ▼
3. data/sft/train.jsonl          확정 학습셋 (profile/raw/target)
        │  scripts/build_chat_dataset.py   (backend 원본 프롬프트로 채팅 형식화)
        ▼
4. finetune/data/train_chat.jsonl   {"messages":[system,user,assistant]}
        │  finetune/validate_finetune.py   (GPU 없는 최종 게이트: 형식·오염·규칙·마커)
        │  finetune/train_lora.py --config config.yaml   ← GPU 박스(메가존 A100)
        ▼
5. outputs/.../gguf/             LoRA 병합 + GGUF
        │  export_to_ollama.md
        ▼
6. ollama: blindguide-rewriter   backend call_llm 이 이 태그를 부름 → 자체 모델 서빙
```

## 실행

### 데이터 만들기 (데스크탑에서)

```
cd llm/scripts
python gen_sft_data.py --teacher local-repair --lengths medium   # 지금 바로 도는 자체완결 경로
# 또는 (키 있으면, TECH_PLAN '강한 AI' 정석):
python gen_sft_data.py --teacher gemini
```
→ `data/sft/train.review.jsonl` 생성. **사람이 감수**해 `data/sft/train.jsonl`로 확정.
감수 요령: `meta.needs_human`이 True인 항목(서술형 색 잔존 등)부터 손본다. `meta.draft`에
교사 원 초안이 있어 비교할 수 있다.

```
python build_chat_dataset.py --in ../data/sft/train.jsonl   # 확정본을 학습 형식으로
```

### 학습 (GPU 박스에서)

```
cd llm/finetune
pip install -r requirements.txt          # CUDA GPU. Unsloth 공식 설치안내 우선.
python train_lora.py --config config.yaml
```

### 서빙 + 검증

`export_to_ollama.md` 대로 GGUF를 Ollama에 등록(`blindguide-rewriter`) 후:

```
python ../scripts/eval_local.py blindguide-rewriter v1
```
v1/v2 표와 비교해 **선천맹 색 누출이 실제로 줄었는지**가 성공 기준.

## 교사 선택

- `local-repair` — EXAONE 7.8b v2 초안 + 결정론적 rule_repair. 지금 데스크탑에서 자체완결로
  돈다. 관형형 색은 자동 제거, 서술형 색 잔존은 감수 플래그. 검증·부트스트랩용으로 충분.
- `gemini` — backend의 Gemini 리라이터로 초안(규칙 준수 품질이 더 높음, notes.md §5). 정식
  증류 경로. `GEMINI_API_KEY` 필요. 저작권: 원칙만 입력, 남의 대본 입력 금지.

## 저작권 / 검토

- 학습 데이터는 원칙(BACKEND_SPEC 시스템 프롬프트 + 색/길이 규칙)만으로 증류한다. 방송 화면해설
  대본 등 남의 저작물은 수집·입력하지 않는다.
- 평가셋(`data/evalset.jsonl`)은 학습에 쓰지 않는다(홀드아웃). gen_sft_data가 평가셋과 겹치는
  raw를 자동 제외한다.
- TECH_PLAN상 베이스 모델 최종 선정·파인튜닝 착수는 검토 지점이다. 이 폴더는 **검토가 끝나면
  바로 학습으로 갈 수 있게** 파이프라인을 완성해 둔 상태다. config.yaml의 `base_model` 한 줄로
  베이스를 바꾼다.
