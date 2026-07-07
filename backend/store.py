"""작품 정보와 사용자 프로필 저장소.

지금은 코드 안 예시 데이터다(메모리에만 있어 서버 재시작하면 초기화).
나중에 실제 DB로 교체한다.
웹사이트가 저장한 작품이 여기(ARTWORKS)로 들어온다.
구조는 shared/schema.json 및 PROJECT_OVERVIEW.md 4번을 따른다.
"""

import itertools

# 작품 딕셔너리. artwork_id -> Artwork 구조.
ARTWORKS = {
    "art-001": {
        "id": "art-001",
        "image_url": "https://example.com/artworks/art-001.jpg",
        "title": "서 있는 남자",
        "artist": "김조각",
        "material": "대리석",
        "size": "높이 180cm",
        "year": "1998",
        "description": "",  # 작가 설명 없음. 백엔드가 사진과 기본 정보로 생성.
    },
    "art-002": {
        "id": "art-002",
        "image_url": "https://example.com/artworks/art-002.jpg",
        "title": "붉은 들판",
        "artist": "이화가",
        "material": "캔버스에 유채",
        "size": "130x97cm",
        "year": "2015",
        "description": (
            "지평선까지 이어지는 붉은 양귀비 밭을 그렸다. "
            "화면 위쪽 3분의 1은 흐린 하늘이고, 아래는 온통 붉은 꽃으로 채웠다."
        ),  # 작가가 직접 쓴 설명. 있으면 리라이터가 우선 참고.
    },
}

# 사용자 프로필 딕셔너리. user_id -> UserProfile 구조.
# 두 사용자의 onset을 다르게 둬서 색 설명 차이를 확인할 수 있게 한다.
PROFILES = {
    "user-blind": {
        "user_id": "user-blind",
        "onset": "congenital",  # 선천맹
        "interest": "역사",
        "length": "medium",
    },
    "user-low": {
        "user_id": "user-low",
        "onset": "acquired",  # 중도실명
        "interest": "회화",
        "length": "medium",
    },
    "user-unknown": {
        "user_id": "user-unknown",
        "onset": "unknown",  # 불명. 색 이름은 쓰되 중립적으로.
        "interest": "",
        "length": "short",  # 길이 규칙 차이도 확인 가능.
    },
}


# 새 작품 id 부여용 카운터. art-001, art-002가 이미 있으니 3부터.
# 나중에 DB로 옮기면 DB의 자동 증가 키가 이 역할을 한다.
_id_counter = itertools.count(3)

# 작품 필드 순서(Artwork 구조). 저장 시 이 필드만 받는다.
_ARTWORK_FIELDS = ["image_url", "title", "artist", "material", "size", "year", "description"]


def get_artwork(artwork_id):
    """artwork_id로 작품 조회. 없으면 None."""
    return ARTWORKS.get(artwork_id)


def get_profile(user_id):
    """user_id로 프로필 조회. 없으면 None."""
    return PROFILES.get(user_id)


def add_artwork(data: dict) -> dict:
    """작품을 저장하고 저장된 Artwork를 반환한다. id는 백엔드가 자동 부여.

    웹사이트 입력 페이지가 POST /artworks로 부른다.
    """
    artwork_id = f"art-{next(_id_counter):03d}"
    artwork = {"id": artwork_id}
    for field in _ARTWORK_FIELDS:
        artwork[field] = data.get(field, "") or ""
    ARTWORKS[artwork_id] = artwork
    return artwork


def list_artworks() -> list:
    """저장된 작품 전체를 리스트로 반환한다."""
    return list(ARTWORKS.values())
