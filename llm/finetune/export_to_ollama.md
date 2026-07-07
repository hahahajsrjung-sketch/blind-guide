# 파인튜닝 모델을 Ollama로 서빙하기

학습이 끝나면 `outputs/blindguide-rewriter-lora/gguf/` 에 GGUF 파일이 생긴다(train_lora.py의
`save_gguf`). 이걸 Ollama 커스텀 모델로 등록하면, backend는 `call_llm`이 부르는 모델 태그만
`blindguide-rewriter`로 바꿔 자체 파인튜닝 모델로 교체된다(TECH_PLAN "백엔드 나머지는 그대로").

## 1. Modelfile 작성

`outputs/.../gguf/` 안에 아래 내용으로 `Modelfile`을 만든다(GGUF 파일명은 실제 생성물에 맞춘다):

```
FROM ./blindguide-rewriter.Q4_K_M.gguf

# 파인튜닝으로 규칙을 내재화했으므로 시스템 프롬프트는 backend 원본(최소)만 얹는다.
# (v2의 제약 부록은 학습에 녹았으니 여기서 다시 붙이지 않는다.)
SYSTEM """당신은 시각장애인을 위한 화면해설 작가입니다. ..."""   # backend/prompts.SYSTEM_PROMPT 원문

PARAMETER temperature 0.4
PARAMETER top_p 0.9
```

시스템 프롬프트 원문은 `backend/prompts.py`의 `SYSTEM_PROMPT`를 그대로 복사한다.

## 2. 등록

```
ollama create blindguide-rewriter -f Modelfile
ollama run blindguide-rewriter   # 손시험
```

## 3. 백엔드 연결 (backend 창 소관)

`backend`의 LLM 호출 함수(call_llm)에 로컬 Ollama 분기를 두고, 모델 태그를
`blindguide-rewriter`로 가리키면 된다. 이 파일(llm 폴더)에서는 backend 코드를 건드리지 않는다.
연결 지점만 문서로 남긴다.

## 4. 검증

교체 후 `llm/scripts/eval_local.py blindguide-rewriter v1` 로 규칙 준수 수치를 다시 잰다
(v1 모드 = 시스템 프롬프트 단독, 파인튜닝 모델의 실력을 그대로 본다). baseline(exaone3.5:7.8b v1)
및 v2 표와 비교해 선천맹 색 누출이 실제로 줄었는지 확인한다. 그것이 파인튜닝 성공의 기준이다.
