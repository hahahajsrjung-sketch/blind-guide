"""API 입구. FastAPI.

요청을 받아 파이프라인을 부르고 응답을 반환한다.
흐름: 앱 → /describe → 프로필/작품 조회 → 인식(가짜) → 리라이터 → JSON 응답
"""

import os
import uuid
import shutil

from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

import store
import recognition
import rewriter
import eval_log
import ingestion
import config

app = FastAPI(title="시각장애인 안내 AI 백엔드")

# 웹사이트와 앱이 브라우저/폰에서 이 백엔드를 부른다. 뼈대 단계라 전부 허용.
# (개발 중 웹사이트 Vite 서버 http://localhost:5173 포함해서 전부 허용.)
# TODO: 나중에 실제 배포 도메인만 허용하도록 좁힌다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 업로드한 이미지를 로컬 폴더에 저장하고 그대로 URL로 제공한다.
# TODO: 나중에 실제 오브젝트 스토리지(S3 등)로 교체.
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


class DescribeRequest(BaseModel):
    user_id: str
    # image: 이미지 URL 또는 data URI(base64). 있으면 VLM으로 인식, 없으면 고정 묘사로 폴백.
    image: Optional[str] = None
    # artwork_id: 어느 작품인지 알 때. 선택.
    artwork_id: Optional[str] = None


@app.post("/describe")
def describe(req: DescribeRequest):
    # 1. 사용자 프로필 조회.
    profile = store.get_profile(req.user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"프로필 없음: {req.user_id}")

    # 2. 작품 조회. artwork_id가 명시되면 그걸 우선. 없는 id면 프로필과 같게 404.
    artwork = store.get_artwork(req.artwork_id) if req.artwork_id else None
    if req.artwork_id and artwork is None:
        raise HTTPException(status_code=404, detail=f"작품 없음: {req.artwork_id}")
    resolved_artwork_id = req.artwork_id

    # 3. 인식으로 밋밋한 묘사 얻기.
    #    image가 실제 이미지(URL/data URI)면 VLM으로 묘사, 없으면 고정 묘사로 폴백.
    try:
        raw_description = recognition.recognize(req.image)
    except RuntimeError as e:
        # 설정 문제(예: API 키 없음).
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        # VLM 호출 자체가 실패(네트워크, 인증, 할당량 등).
        raise HTTPException(status_code=502, detail=f"인식(VLM) 호출 실패: {e}")

    # 3.5 artwork_id를 몰라도 실제 이미지가 왔으면 어느 작품인지 식별해 본다. 2단(DATA_PIPELINE 3절):
    #     1차 임베딩(CLIP) — 확정이면 LLM 호출 없이 끝. 애매하면 2차 LLM 대조로 폴백.
    #     확신 없으면 None → 작품 컨텍스트 없이 묘사만으로 설명(플랜 3.2: 억지로 안 맞춘다).
    if artwork is None and recognition.is_recognizable(req.image):
        guessed_id, _sim, decided = recognition.identify_by_image(
            req.image, store.get_embedding_index()
        )
        if not decided:
            try:
                guessed_id = recognition.identify(raw_description, store.list_artworks())
            except Exception:
                guessed_id = None  # 식별 실패는 치명적이지 않다. 그냥 컨텍스트 없이 간다.
        if guessed_id:
            artwork = store.get_artwork(guessed_id)
            resolved_artwork_id = guessed_id

    # 4. 리라이터로 시각 상태에 맞춘 설명 생성.
    try:
        description = rewriter.rewrite(raw_description, profile, artwork)
    except RuntimeError as e:
        # 설정 문제(예: API 키 없음). 무엇이 문제인지 그대로 알려준다.
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        # LLM 호출 자체가 실패(네트워크, 인증, 할당량 등).
        raise HTTPException(status_code=502, detail=f"리라이터(LLM) 호출 실패: {e}")

    # 5. 평가셋 씨앗으로 (profile, raw, 생성결과)를 남긴다. best-effort — 실패해도 응답엔 영향 없음.
    eval_log.record(
        profile=profile,
        raw_description=raw_description,
        model_output=description,
        artwork_id=resolved_artwork_id,
        image_present=bool(req.image),
        model=config.GEMINI_MODEL,
    )

    # 6. JSON 반환. artwork_id는 최종 확정된 값(식별로 찾았으면 그 id).
    return {
        "user_id": req.user_id,
        "onset": profile.get("onset"),
        "artwork_id": resolved_artwork_id,
        "identified": bool(resolved_artwork_id) and resolved_artwork_id != req.artwork_id,
        "raw_description": raw_description,
        "description": description,
    }


# ---- 작품 저장/조회 (웹사이트 입력 페이지가 쓴다) ----


class ArtworkImageIn(BaseModel):
    url: str
    # main(대표) / angle(각도) / detail(세부) / context(설치 전경)
    kind: Optional[str] = "angle"


class ArtworkIn(BaseModel):
    # 대표 사진(하위호환). images를 주면 생략 가능 — 서버가 images[0]을 미러.
    image_url: Optional[str] = ""
    # v2: 여러 각도·세부·전경 사진. 임베딩 식별의 재료 (docs/DATA_PIPELINE.md 1.1)
    images: Optional[list[ArtworkImageIn]] = None
    # v2: 작품 주위를 도는 짧은 영상. 서버가 프레임 추출.
    video_url: Optional[str] = ""
    title: Optional[str] = ""
    artist: Optional[str] = ""
    material: Optional[str] = ""
    size: Optional[str] = ""
    year: Optional[str] = ""
    description: Optional[str] = ""
    # v2: 촉각·안전·위치·의도 (docs/DATA_PIPELINE.md 1.3)
    tactile: Optional[str] = ""
    safety: Optional[str] = ""
    location: Optional[str] = ""
    intent: Optional[str] = ""


@app.post("/uploads")
def upload_image(request: Request, file: UploadFile = File(...)):
    """이미지 파일을 받아 로컬에 저장하고 접근 가능한 image_url을 반환한다.

    동기 def — 파일 복사가 블로킹 I/O라, async def로 두면 이벤트 루프를 막아
    업로드 중 다른 요청(/describe 포함)이 전부 멈춘다. def면 스레드풀에서 돈다.
    """
    ext = os.path.splitext(file.filename or "")[1]
    name = f"{uuid.uuid4().hex}{ext}"
    dest = os.path.join(UPLOAD_DIR, name)
    with open(dest, "wb") as out:
        shutil.copyfileobj(file.file, out)
    # 다른 오리진(웹사이트)에서도 쓰도록 절대 URL로 돌려준다.
    image_url = str(request.base_url).rstrip("/") + f"/uploads/{name}"
    return {"image_url": image_url}


@app.post("/artworks")
def create_artwork(body: ArtworkIn):
    """작품을 저장하고, 저장 즉시 AI가 정리(인제스천)한다.

    인제스천 = 임베딩 인덱스 생성(사진들+영상 프레임) + VLM 캡션 + ai_profile.
    인제스천이 부분 실패해도 등록은 성공한다(best-effort). 결과는 _ingestion 필드로 알려준다.
    """
    if not body.image_url and not (body.images or []):
        raise HTTPException(status_code=400, detail="사진이 최소 1장 필요합니다 (image_url 또는 images)")
    artwork = store.add_artwork(body.dict())
    summary = ingestion.ingest(artwork)
    return {**artwork, "_ingestion": summary}


@app.get("/artworks")
def get_artworks():
    """저장된 작품 목록 반환."""
    return {"artworks": store.list_artworks()}


@app.get("/health")
def health():
    return {"status": "ok"}
