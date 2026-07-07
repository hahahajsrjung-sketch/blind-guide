"""이미지 임베딩 — 관람객 사진과 작가 등록 사진을 시각적으로 대조하기 위한 벡터.

오픈소스 CLIP(ViT-B/32, sentence-transformers)을 로컬에서 돌린다. 키·비용 없음.
- 등록 시: 작품 사진들(+영상 프레임) → 벡터 여러 개 → 인덱스에 저장
- 조회 시: 관람객 사진 → 벡터 → 코사인 유사도 top-1

교체 경계: embed_image_bytes()만 바꾸면 SigLIP 등 다른 모델로 전환 가능.
검색은 지금 NumPy 완전탐색(작품 수백 개까지 충분). 수천 개 넘으면 FAISS로 교체.
문서: docs/DATA_PIPELINE.md 2·3·5절.
"""

import io
import threading

import numpy as np

# 모델은 무겁다(~600MB 다운로드, 첫 로드 수 초). 프로세스당 1회만 lazy 로드.
_model = None
_model_lock = threading.Lock()

# sentence-transformers가 없거나 로드 실패해도 서버는 떠야 한다(폴백: LLM 대조).
_available = None


def is_available() -> bool:
    """CLIP을 쓸 수 있는 환경인지. 아니면 호출측이 텍스트 대조로 폴백한다."""
    global _available
    if _available is None:
        try:
            import sentence_transformers  # noqa: F401
            _available = True
        except ImportError:
            _available = False
    return _available


def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer
                _model = SentenceTransformer("clip-ViT-B-32")
    return _model


def embed_image_bytes(image_bytes: bytes) -> list:
    """이미지 바이트 → 512차원 벡터(정규화). 교체 경계: 이 함수만 바꾸면 모델 전환."""
    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    vec = _get_model().encode(img, normalize_embeddings=True)
    return vec.tolist()


def extract_video_frames(video_path: str, max_frames: int = 6) -> list:
    """영상에서 프레임을 균등 추출해 JPEG 바이트 리스트로 반환. OpenCV 사용."""
    import cv2

    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    frames = []
    if total <= 0:
        cap.release()
        return frames
    indices = [int(total * i / max_frames) for i in range(max_frames)]
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            continue
        ok, buf = cv2.imencode(".jpg", frame)
        if ok:
            frames.append(buf.tobytes())
    cap.release()
    return frames


def best_match(query_vec: list, index: dict):
    """쿼리 벡터를 인덱스 전체와 대조해 (artwork_id, similarity) 반환. 없으면 (None, 0.0).

    index: {artwork_id: [vec, vec, ...]} — 작품당 각도별 벡터 여러 개.
    작품 점수는 그 작품 벡터들과의 최대 유사도(가장 비슷한 각도 하나면 충분).
    """
    if not index:
        return None, 0.0
    q = np.asarray(query_vec, dtype=np.float32)
    best_id, best_sim = None, -1.0
    for artwork_id, vecs in index.items():
        if not vecs:
            continue
        m = np.asarray(vecs, dtype=np.float32)
        sim = float(np.max(m @ q))  # 벡터들이 정규화돼 있어 내적=코사인
        if sim > best_sim:
            best_id, best_sim = artwork_id, sim
    return best_id, best_sim
