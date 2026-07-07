"""규칙 보정기 — 증류 교사 출력을 화면해설 규칙에 맞게 결정론적으로 다듬는다.

증류(distillation) 교사가 유창한 초안을 내도, notes.md 6절에서 봤듯 선천맹 색 규칙·
길이·인사말투는 자주 어긋난다. 이 모듈은 그 초안을 학습용 '정답(target)'으로 쓰기 전에
규칙에 맞게 자동 손질하고, 자동으로 못 고치는 것은 감수 플래그로 남긴다.

원칙 (BACKEND_SPEC 4번 + eval_local.py 감지기와 동일한 규칙):
- congenital(선천맹): 색 이름을 뺀다. 관형형 색(예: "파란 원피스")은 색 형용사만 지우고
  명사는 남긴다. 서술형 색(예: "배경은 노란색이다")처럼 문장 구조로 얽혀 자동 제거가
  위험한 경우는 남은 색을 지우지 않고 needs_human 플래그만 세운다.
- acquired / unknown: 색은 그대로 둔다.
- 인사말·예고("안녕하세요", "설명드리겠습니다" 등)로 시작하면 그 구절을 떼어낸다.
- 길이 규칙을 넘기면 뒤 문장을 잘라 상한에 맞춘다.
- 안전 정보가 raw에 없는데 붙은 '안전' 문장은 오적용이므로 그 문장을 뺀다.

이 보정기는 '교사 출력 → 규칙 준수 정답'을 만드는 자동 단계일 뿐, 마지막엔 사람이 감수한다
(TECH_PLAN 3.4 "사람이 감수한다. 양보다 질"). 자동으로 확신 못 하는 항목은 반드시
needs_human=True 로 표시해 감수 큐로 보낸다.
"""

import re

# 관형형 색 형용사(뒤에 명사가 붙는 형태). 지우면 명사만 남아 문장이 자연스럽다.
# 예: "파란 원피스" -> "원피스", "짙은 파랑 하늘" 등은 아래 표준형만 처리.
ADNOMINAL_COLORS = [
    "빨간", "빨간색", "붉은", "새빨간", "불그스름한",
    "파란", "파란색", "새파란", "짙은 파란", "푸른", "시퍼런",
    "노란", "노란색", "샛노란",
    "주황", "주황색", "주홍",
    "초록", "초록색", "녹색", "연두", "연둣빛", "푸르른",
    "보라", "보라색", "자주색", "자줏빛",  # '자주' 단독은 부사와 동형이라 제외(내용 훼손 방지).
    "분홍", "분홍색", "핑크",
    "하얀", "하얀색", "흰", "새하얀",
    "검은", "검은색", "까만", "새까만",
    "회색", "잿빛",
    "갈색", "밤색", "고동색",
    "남색", "청색", "적색", "황색",
]
# 길게 먼저 매칭하도록 정렬(부분 매칭 방지).
ADNOMINAL_COLORS.sort(key=len, reverse=True)

# 서술형/명사형 색 — 자동 제거가 위험. 남으면 needs_human.
# '자주'는 부사와 동형이라 오탐 → 자주색/자줏빛만. (eval_local.COLOR_RE와 정렬 유지.)
RESIDUAL_COLOR_RE = re.compile(
    r"빨강|빨간|빨갛|붉|파랑|파란|파랗|노랑|노란|노랗|주황|초록|녹색|연두|청록|보라"
    r"|자주색|자줏빛|분홍|핑크|하양|하얀|흰|검정|검은|까만|회색|잿빛|갈색|밤색|남색"
    r"|청색|적색|황색|백색|흑색|은색|금색|색깔|빛깔"
)

GREETING_RE = re.compile(
    r"^\s*(안녕하세요[^.!?]*[.!?]?\s*|여러분[^.!?]*[.!?]?\s*"
    r"|[^.!?]*설명(을)?\s*드리겠습니다[.!?]?\s*"
    r"|[^.!?]*소개(를)?\s*(해\s*)?드리겠습니다[.!?]?\s*"
    r"|[^.!?]*화면\s*해설을 통해[^.!?]*[.!?]?\s*"
    r"|지금부터[^.!?]*[.!?]?\s*)"
)

# eval_local.SAFETY_CUES 와 반드시 같은 목록 유지(생성기/채점기 판정 일치).
SAFETY_CUES = ["열차", "선로", "횡단보도", "신호", "뜨겁", "뜨거", "계단", "차도",
               "승강장", "턱", "웅덩이", "공사", "장애물"]
SAFETY_SENT_RE = re.compile(r"[^.!?]*안전[^.!?]*[.!?]")

LEN_MAX = {"short": 2, "medium": 4, "long": 5}


def _split_sentences(text):
    # 문장 부호 기준으로 나누되 부호를 살려서 되붙일 수 있게 한다.
    parts = re.findall(r"[^.!?]*[.!?]", text)
    tail = re.sub(r"[^.!?]*[.!?]", "", text).strip()
    if tail:
        parts.append(tail)
    return [p.strip() for p in parts if p.strip()]


def strip_greeting(text):
    prev = None
    out = text
    # 인사말이 겹쳐 붙는 경우가 있어 반복 제거.
    while out != prev:
        prev = out
        out = GREETING_RE.sub("", out, count=1).lstrip()
    return out


def strip_misapplied_safety(text, raw):
    """raw에 안전 단서가 없는데 output에 붙은 '안전' 문장을 뺀다."""
    if any(cue in raw for cue in SAFETY_CUES):
        return text  # raw에 안전 단서 있음 → 안전 언급 정당, 건드리지 않음.
    return SAFETY_SENT_RE.sub("", text).strip()


def remove_adnominal_colors(text):
    """관형형 색 형용사를 지운다. '파란 원피스'->'원피스'. 명사는 보존."""
    out = text
    for c in ADNOMINAL_COLORS:
        # 색 + 공백(들) 을 통째로 제거. 뒤 명사만 남는다.
        out = re.sub(rf"{re.escape(c)}\s+", "", out)
        # '색으로', '빛으로' 같은 꼬리 없이 홀로 남은 경우도 정리.
        out = re.sub(rf"{re.escape(c)}(?=[,.\s])", "", out)
    # 색 제거로 생긴 이중 공백 정리.
    out = re.sub(r"\s{2,}", " ", out).strip()
    return out


def trim_length(text, length):
    limit = LEN_MAX.get(length, 4)
    sents = _split_sentences(text)
    if len(sents) <= limit:
        return text
    return " ".join(sents[:limit])


def repair(draft, raw, profile):
    """교사 초안(draft)을 규칙에 맞게 손질. 반환: (target, meta).

    meta.needs_human: 자동으로 규칙을 완전히 못 맞춰 사람 감수가 필요하면 True.
    meta.notes: 무엇을 고쳤는지/왜 감수가 필요한지.
    """
    onset = profile.get("onset", "unknown")
    length = profile.get("length", "medium")
    notes = []
    needs_human = False

    out = draft.strip()

    before = out
    out = strip_greeting(out)
    if out != before:
        notes.append("인사말/예고 제거")

    before = out
    out = strip_misapplied_safety(out, raw)
    if out != before:
        notes.append("안전문구 오적용 제거")

    if onset == "congenital":
        before = out
        out = remove_adnominal_colors(out)
        if out != before:
            notes.append("관형형 색 이름 제거")
        # 남은 색(서술형/명사형)은 자동 제거가 위험 → 감수로.
        if RESIDUAL_COLOR_RE.search(out):
            needs_human = True
            notes.append("서술형 색 잔존 — 사람 감수 필요")

    before = out
    out = trim_length(out, length)
    if out != before:
        notes.append(f"길이 상한({LEN_MAX.get(length,4)}문장)으로 절단")

    # 절단이 문장을 어색하게 끊었을 수 있으니 아주 짧아지면 감수로.
    if len(out) < 10:
        needs_human = True
        notes.append("보정 후 너무 짧음 — 감수 필요")

    return out, {"needs_human": needs_human, "notes": notes}


if __name__ == "__main__":
    # 손시험.
    samples = [
        ("안녕하세요 여러분. 파란 원피스를 입은 여자가 노란 배경 앞에 앉아 있습니다. 안전하게 감상하세요.",
         "파란 원피스를 입은 여자가 노란 배경 앞에 앉아 있다.",
         {"onset": "congenital", "length": "medium"}),
        ("배경은 노란색이고 여자는 파란색 원피스를 입고 있습니다.",
         "노란 배경에 파란 원피스", {"onset": "congenital", "length": "medium"}),
    ]
    for draft, raw, prof in samples:
        t, m = repair(draft, raw, prof)
        print("IN :", draft)
        print("OUT:", t)
        print("MET:", m)
        print()
