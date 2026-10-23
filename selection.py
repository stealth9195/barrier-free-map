"""결과 표의 선택 행을 장소 contentid 로 바꾼다."""


def selected_from_rows(rows, places):
    if rows and 0 <= rows[0] < len(places):
        return places[rows[0]]["contentid"]
    return None
