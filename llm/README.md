# llm — 자체 리라이터 LLM

이 폴더는 리라이터의 최종 형태인 **자체 LLM**을 만드는 작업(4번 창)이다. 상위 지시서는
`docs/LLM_SPEC.md`, 방침은 `docs/TECH_PLAN.md` 3.4절. 이 창은 **llm 폴더 안에서만** 작업하고
backend/website/app 폴더는 건드리지 않는다. backend와의 연결은 "모델 태그 교체" 한 지점으로
좁혀 두었다(아래 6단계).

## 한눈에 — 전체 파이프라인

```
로컬 구동 ──▶ 평가셋 ──▶ 프롬프트 최대화(v2) ──▶ 증류 데이터 ──▶ LoRA 파인튜닝 ──▶ Ollama 서빙
 (Ollama)    (측정 기준)   (few-shot+제약)      (교사+감수)     (메가존 GPU)     (backend 교체)
```

TECH_PLAN 3.4의 순서를 그대로 코드로 옮겼다. **1~3단계는 이 데스크탑에서 실측까지 끝냈고,
4~6단계(파인튜닝)는 GPU 박스에서 바로 돌 수 있게 스크립트·설정·데이터 생성기를 완성**해 두었다.

## 핵심 발견 (왜 파인튜닝인가)

`scripts/eval_local.py`로 잰 재현 가능한 수치(greedy, temp0):

| 지표 | v1 baseline | v2 프롬프트 |
|---|---|---|
| 길이 초과 | 12/15 | **3/15** |
| 안전문구 오적용 | 6/15 | **1/15** |
| 방송 인사말투 | 5/15 | **0/15** |
| **선천맹 색 이름 누출** | **4/6** | **4/6 (그대로)** |

(greedy도 Ollama 실행 간 ±1 흔들림이 있어 ±1은 오차로 본다 — notes.md 6절.)

**프롬프트로 길이·인사말·안전은 완전히 해결됐다. 그러나 제품의 심장인 "선천맹에게 색 이름 대신
교차감각"은 프롬프트만으로 안 잡힌다.** 이 남은 격차가 파인튜닝의 표적이다(TECH_PLAN 3.4-3).

## 폴더 구조

```
llm/
  data/
    evalset.jsonl                 # 평가셋 15개. 측정 전용(학습에 안 씀, 홀드아웃).
    eval_local_results_7.8b.md    # v1 baseline 평가 결과. 생성물.
    eval_local_results_7.8b_v2.md # v2 프롬프트 평가 결과. 생성물.
    eval_local_results_2.4b.md    # 2.4b 대조군. 생성물.
    sft/
      raw_pool.jsonl              # 학습용 밋밋한 묘사 풀(평가셋과 분리). 원칙만으로 창작.
      train.review.jsonl          # 증류+보정 결과. '감수 대기'. 생성물.
      # train.jsonl               # 사람이 감수해 확정한 학습셋(감수 후 생김).
  scripts/
    try_local.py           # 로컬 손시험. backend/prompts.py 그대로 import.
    rewriter_v2.py         # v2 프롬프트(few-shot + 출력 제약). 프롬프트 최대화.
    eval_local.py          # 정량 규칙 평가기. v1/v2 모드. greedy 재현.
    validate_evalset.py    # 평가셋 형식 검증기.
    rule_repair.py         # 교사 출력 규칙 보정기(색 제거·길이·인사말·안전 정리).
    gen_sft_data.py        # 증류 학습데이터 생성기(교사 초안→보정→감수 대기).
    curate_train.py        # 감수 병합기(자동통과+수정본→train.jsonl, 확정 전 재검증).
    build_chat_dataset.py  # 확정 데이터를 파인튜닝 채팅 형식으로 변환.
  model/
    serve_v2.py            # 프롬프트-only v2 정본: '호출 시 프롬프트 전달' 참조 구현.
  finetune/
    config.yaml            # 베이스 모델·LoRA·하이퍼파라미터·템플릿 마커. 여기 한 곳만 고친다.
    train_lora.py          # Unsloth+TRL LoRA 학습. GPU 박스에서. 마커 하드 검증 포함.
    validate_finetune.py   # GPU 없는 드라이런 게이트(형식·홀드아웃 오염·규칙·마커).
    requirements.txt, export_to_ollama.md, README.md
  notes.md                 # 시험 기록·baseline 표·판단 근거.
  README.md                # 이 문서.
```

## 실행

### 1) 지금 데스크탑에서 (Ollama 필요)

```
ollama pull exaone3.5:7.8b
python scripts/validate_evalset.py                 # 평가셋 형식 검사
python scripts/try_local.py                        # 손시험(temp 0.4)
python scripts/eval_local.py exaone3.5:7.8b v1     # baseline 정량 평가
python scripts/eval_local.py exaone3.5:7.8b v2     # v2 프롬프트 정량 평가
python model/serve_v2.py                           # 프롬프트-only v2 손시험(호출 경로)
```

> **배포 메모(검증됨):** v2 프롬프트를 Ollama Modelfile(SYSTEM/MESSAGE)로 **구우면 퇴화**한다
> (예시 되뱉기·환각, temp0에서 재현). 똑같은 텍스트를 **호출 시 메시지로 넘기면 정상**이고
> eval의 v2 수치도 그 경로다. 그래서 v2는 굽지 않고 `serve_v2.rewrite_local`로 호출 시 전달한다.
> 단일 태그로 굽는 배포는 짧은 원본 프롬프트만 쓰는 **파인튜닝 모델**의 몫이다(아래 3단계).

### 2) 학습 데이터 만들기 (증류 → 감수 → 확정 → 검증)

```
python scripts/gen_sft_data.py --teacher local-repair --lengths short,medium,long
#   또는  --teacher gemini   (GEMINI_API_KEY, TECH_PLAN '강한 AI' 정석)
# → data/sft/train.review.jsonl (감수 대기, needs_human 플래그).
# 감수: needs_human 항목의 수정 target을 data/sft/curated_fixes.jsonl 에 쓴다
#       ({source_id, onset, length, target} 한 줄씩).
python scripts/curate_train.py                          # 병합+재검증 → train.jsonl 확정
python scripts/build_chat_dataset.py --in ../data/sft/train.jsonl   # (scripts/ 에서)
python finetune/validate_finetune.py                    # GPU 없이 최종 게이트(형식·오염·규칙)
```

### 3) 파인튜닝 (GPU 박스 = 메가존 A100)

```
cd finetune && pip install -r requirements.txt
python train_lora.py --config config.yaml
# → export_to_ollama.md 대로 GGUF를 Ollama에 등록(blindguide-rewriter)
python ../scripts/eval_local.py blindguide-rewriter v1   # 색 누출이 줄었는지 검증
```

Windows에서 한글 출력이 깨지면 `$env:PYTHONUTF8="1"` 후 실행.

## backend 연결 (경계)

파인튜닝 모델은 backend **원본 시스템 프롬프트**로 학습하므로, backend는 `call_llm`이 부르는
모델 태그만 `blindguide-rewriter`로 바꾸면 된다(프롬프트·나머지 코드 불변, TECH_PLAN "백엔드
나머지는 그대로"). 이 폴더에서는 backend 코드를 건드리지 않고, 연결 지점만 문서로 남긴다
(`finetune/export_to_ollama.md`).

## 저작권

target·학습 데이터는 원칙(BACKEND_SPEC 시스템 프롬프트 + 색/길이 규칙)만으로 생성한다.
방송 화면해설 대본 등 남의 저작물은 수집하지도, 생성 AI에 입력하지도 않는다. 평가셋은
홀드아웃으로 학습에서 제외하고, 생성기가 평가셋과 겹치는 raw를 자동으로 뺀다.
