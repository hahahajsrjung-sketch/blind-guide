# 평가셋 인프라 (3단계 씨앗)

TECH_PLAN 3.4의 순서를 지킨다: **평가셋부터 만들고 → 프롬프트로 최대한 뽑고 → 남는 격차만 파인튜닝.**
이 폴더는 그 첫걸음인 "무엇이 나아졌는지 재는 자" 를 위한 뼈대다.

## 데이터 형식

한 줄이 하나의 샘플인 JSONL. 형식은 플랜 3.4를 따른다.

```json
{"profile": {"onset": "congenital", "interest": "역사", "length": "medium"},
 "raw": "밋밋한 묘사(인식 결과)",
 "target": "사람이 감수한 정답 설명"}
```

- `profile` — onset(congenital/acquired/unknown), interest, length(short/medium/long).
- `raw` — 인식이 뽑은 밋밋한 묘사.
- `target` — 정답 설명. **사람이 감수해서** 채운다. 평가셋은 학습에 쓰지 않고 따로 뺀다(홀드아웃).

견본: [`eval_set.example.jsonl`](./eval_set.example.jsonl).

## 흐름

1. **수집.** 서버가 도는 동안 `/describe` 한 건마다 `eval_log.py`가
   `logs/interactions.jsonl` 에 `{profile, raw, model_output, target:null, meta}` 를 쌓는다.
   (환경변수 `EVAL_LOG_ENABLED=0` 으로 끌 수 있음.)
2. **감수.** 쌓인 로그에서 좋은 샘플을 골라 `target` 을 사람이 채운다. 양보다 질(플랜 3.4).
   이렇게 만든 것이 평가셋(홀드아웃)과 학습셋이 된다.
3. **평가.** `run_eval.py` 로 평가셋의 각 `raw+profile` 에 대해 지금 리라이터의 후보를 재생성해
   `target` 과 나란히 본다. 프롬프트를 고칠 때마다 돌려 나아졌는지 확인한다.

```bash
# backend/ 에서 (GEMINI_API_KEY 필요)
python -m eval.run_eval eval/eval_set.example.jsonl
# 결과: eval/results/eval_set.example.results.jsonl
```

## 지금 자리만 (나중 교체)

- `run_eval.score()` — 자동 채점. 지금은 None(사람 눈 비교). 나중에 LLM-judge나 규칙 지표로 교체.
- 수집 로그의 `model_output` 은 감수 전 후보다. 이걸 그대로 target으로 쓰지 않는다.

## 저작권·프라이버시

- 방송 화면해설 대본을 긁어 학습하지 않는다. 생성 AI에 대본을 입력하지도 않는다(플랜 3.4).
- 실제 사용자 데이터를 수집하려면 동의·PII 처리가 필요하다. 지금은 데모 데이터뿐.
- `logs/` 와 `results/` 는 커밋하지 않는다(.gitignore).
