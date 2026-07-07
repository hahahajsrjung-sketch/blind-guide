"""인제스천 — 작가가 작품을 저장하는 순간 AI가 정리해두는 단계.

docs/DATA_PIPELINE.md 2절. 하는 일:
  ① 사진들(+영상 프레임) → CLIP 임베딩 → store의 벡터 인덱스에 저장
  ② 대표컷 1장 → VLM 캡션 (작가가 글을 안 썼어도 시각 정보 확보)
  ③ (기본정보+작가글+캡션+촉각+안전+의도) → ai_profile 생성 (LLM 1회) → 작품에 저장

원칙: 인제스천이 실패해도 등록 자체는 성공한다(best-effort).
정리본이 없으면 관람객 요청 때 기존 방식대로 동작한다(하위호환).
"""

import os
import json
import urllib.request

import config
import store
import embeddings
import recognition

# 로컬 /uploads/ URL이면 디스크에서 바로 읽는다(서버 자신에게 HTTP를 치지 않게).
_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")


def _read_image_bytes(url: str):
    """이미지 URL → 바이트. 로컬 업로드면 디스크에서, 아니면 HTTP로. 실패 시 None."""
    try:
        if "/uploads/" in url:
            name = os.path.basename(url.split("?")[0])
            path = os.path.join(_UPLOAD_DIR, name)
            if os.path.exists(path):
                with open(path, "rb") as f:
                    return f.read()
        with urllib.request.urlopen(url, timeout=15) as resp:
            return resp.read()
    except Exception:
        return None


def ingest(artwork: dict) -> dict:
    """작품 하나를 인제스천. 결과 요약 dict 반환(로그·응답용). 실패는 부분 허용."""
    result = {"embedded_images": 0, "video_frames": 0, "ai_profile": False, "errors": []}

    # ---- ① 임베딩: 모든 사진 + 영상 프레임 ----
    urls = [img.get("url") for img in (artwork.get("images") or []) if img.get("url")]
    if not urls and artwork.get("image_url"):
        urls = [artwork["image_url"]]

    vecs = []
    caption_bytes = None  # ② 캡션용 대표컷 바이트 재사용
    if embeddings.is_available():
        for i, url in enumerate(urls):
            data = _read_image_bytes(url)
            if data is None:
                result["errors"].append(f"이미지 읽기 실패: {url}")
                continue
            if i == 0:
                caption_bytes = data
            try:
                vecs.append(embeddings.embed_image_bytes(data))
                result["embedded_images"] += 1
            except Exception as e:
                result["errors"].append(f"임베딩 실패: {e}")

        # 영상 → 프레임 추출 → 임베딩
        video_url = artwork.get("video_url")
        if video_url and "/uploads/" in video_url:
            path = os.path.join(_UPLOAD_DIR, os.path.basename(video_url.split("?")[0]))
            if os.path.exists(path):
                try:
                    for frame in embeddings.extract_video_frames(path):
                        vecs.append(embeddings.embed_image_bytes(frame))
                        result["video_frames"] += 1
                except Exception as e:
                    result["errors"].append(f"영상 프레임 실패: {e}")
    else:
        result["errors"].append("CLIP 미설치 — 임베딩 생략(텍스트 대조로 폴백)")

    if vecs:
        store.set_embeddings(artwork["id"], vecs)
    elif caption_bytes is None and urls:
        caption_bytes = _read_image_bytes(urls[0])

    # ---- ② 대표컷 VLM 캡션 ----
    caption = ""
    if caption_bytes:
        try:
            caption = recognition._vlm_describe(caption_bytes, "image/jpeg")
        except Exception as e:
            result["errors"].append(f"VLM 캡션 실패: {e}")

    # ---- ③ ai_profile 생성 ----
    try:
        profile = _build_ai_profile(artwork, caption)
        if profile:
            artwork["ai_profile"] = profile
            result["ai_profile"] = True
    except Exception as e:
        result["errors"].append(f"ai_profile 실패: {e}")

    return result


def _build_ai_profile(artwork: dict, caption: str) -> dict:
    """작가 입력 + VLM 캡션을 화면해설 재료로 재구성. LLM 1회. 교체 경계: rewriter.call_llm."""
    import rewriter

    material_lines = []
    for label, key in [("제목", "title"), ("작가", "artist"), ("재질", "material"),
                       ("크기", "size"), ("제작연도", "year"), ("전시 위치", "location")]:
        v = artwork.get(key)
        if v:
            material_lines.append(f"{label}: {v}")
    for label, key in [("작가가 쓴 설명", "description"), ("촉각·재질감(작가 메모)", "tactile"),
                       ("안전·관람 규칙", "safety"), ("작가 의도", "intent")]:
        v = artwork.get(key)
        if v:
            material_lines.append(f"{label}: {v}")
    if caption:
        material_lines.append(f"대표 사진의 객관 묘사(VLM): {caption}")

    if not material_lines:
        return None

    system = (
        "당신은 시각장애인 화면해설을 준비하는 편집자입니다. "
        "주어진 재료를 해설 '재료'로 재구성합니다. 지어내지 않고, 재료에 있는 사실만 씁니다. "
        "반드시 JSON 하나만 출력합니다."
    )
    user = (
        "다음 재료를 아래 JSON 형식으로 정리하세요.\n\n"
        "재료:\n" + "\n".join(material_lines) + "\n\n"
        "형식(JSON만 출력, 다른 말 금지):\n"
        "{\n"
        '  "visual_summary": "구도·형태·색을 전체→부분, 위→아래 순서로 정리한 3~5문장",\n'
        '  "tactile_summary": "촉각·재질 중심 1~2문장 (재료에 촉각 정보가 없으면 재질에서 유추 가능한 것만)",\n'
        '  "safety_notes": "안전·관람 규칙 그대로 (없으면 빈 문자열)",\n'
        '  "key_features": ["다른 작품과 구별되는 두드러진 특징 3~5개"]\n'
        "}"
    )
    raw = rewriter.call_llm(system, user)
    # 모델이 ```json 펜스를 붙여도 파싱되게 정리
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw.strip())
    return {
        "visual_summary": str(data.get("visual_summary", "")),
        "tactile_summary": str(data.get("tactile_summary", "")),
        "safety_notes": str(data.get("safety_notes", "")),
        "key_features": [str(x) for x in (data.get("key_features") or [])][:5],
    }
