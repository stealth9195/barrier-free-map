"""관광타입 코드와 무장애 상세 필드 라벨 (무장애여행 활용매뉴얼 v4.3 기준)."""

CONTENT_TYPES = {
    "12": "관광지",
    "14": "문화시설",
    "15": "행사/공연/축제",
    "28": "레포츠",
    "32": "숙박",
    "38": "쇼핑",
    "39": "음식점",
}

BARRIER_GROUPS = [
    ("지체장애", [
        ("parking", "주차"),
        ("publictransport", "대중교통"),
        ("route", "접근로"),
        ("ticketoffice", "매표소"),
        ("promotion", "홍보물"),
        ("wheelchair", "휠체어"),
        ("exit", "출입통로"),
        ("elevator", "엘리베이터"),
        ("restroom", "화장실"),
        ("auditorium", "관람석"),
        ("room", "객실"),
        ("handicapetc", "지체장애 기타 상세"),
    ]),
    ("시각장애", [
        ("braileblock", "점자블록"),
        ("helpdog", "보조견 동반"),
        ("guidehuman", "안내요원"),
        ("audioguide", "오디오 가이드"),
        ("bigprint", "큰 활자 홍보물"),
        ("brailepromotion", "점자 홍보물 및 점자표지판"),
        ("guidesystem", "유도 안내 설비"),
        ("blindhandicapetc", "시각장애 기타상세"),
    ]),
    ("청각장애", [
        ("signguide", "수화 안내"),
        ("videoguide", "자막 비디오 가이드 및 영상 자막 안내"),
        ("hearingroom", "객실"),
        ("hearinghandicapetc", "청각장애 기타상세"),
    ]),
    ("영유아가족", [
        ("stroller", "유모차"),
        ("lactationroom", "수유실"),
        ("babysparechair", "유아용 보조의자"),
        ("infantsfamilyetc", "영유아가족 기타상세"),
    ]),
]

# 목록 필터용 편의시설 칩 (자주 쓰는 10개)
FACILITY_CHIPS = [
    ("parking", "주차"),
    ("publictransport", "대중교통"),
    ("route", "접근로"),
    ("exit", "출입통로"),
    ("elevator", "엘리베이터"),
    ("restroom", "화장실"),
    ("wheelchair", "휠체어 대여"),
    ("braileblock", "점자블록"),
    ("stroller", "유모차"),
    ("lactationroom", "수유실"),
]
