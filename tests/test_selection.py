from selection import selected_from_rows

PLACES = [{"contentid": "10"}, {"contentid": "20"}]


def test_row_maps_to_contentid():
    assert selected_from_rows([1], PLACES) == "20"


def test_deselect_clears_selection():
    assert selected_from_rows([], PLACES) is None


def test_out_of_range_row_clears_selection():
    assert selected_from_rows([5], PLACES) is None
