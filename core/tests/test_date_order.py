from datetime import datetime

import pytest

from lovelm.errors import DateOrderAmbiguous, InconsistentDates, UnrecognizedFormat
from lovelm.parse import parse_chat


def android(*dates_and_times: str) -> str:
    return "".join(f"{dt} - {'Rohan' if i % 2 == 0 else 'Tara'}: msg {i}\n"
                   for i, dt in enumerate(dates_and_times))


def test_day_over_12_in_first_field_means_day_first():
    chat = parse_chat(android("03/04/24, 10:00", "04/04/24, 10:00", "25/04/24, 10:00"))
    assert chat.meta.date_order == "DMY"


def test_day_over_12_in_second_field_means_month_first():
    chat = parse_chat(android("03/04/24, 10:00", "04/25/24, 10:00"))
    assert chat.meta.date_order == "MDY"
    assert chat.messages[0].ts == datetime(2024, 3, 4, 10, 0)


def test_both_fields_over_12_is_inconsistent():
    with pytest.raises(InconsistentDates):
        parse_chat(android("13/05/24, 10:00", "05/13/24, 10:00"))


def test_ambiguous_dates_are_resolved_by_time_order():
    # Day-first reads Mar 10, 11, 12 then Apr 1, 2: in order. Month-first jumps Dec 3 -> Jan 4.
    chat = parse_chat(android("10/03/24, 10:00", "11/03/24, 10:00", "12/03/24, 10:00",
                              "01/04/24, 10:00", "02/04/24, 10:00"))
    assert chat.meta.date_order == "DMY"
    assert chat.messages[3].ts == datetime(2024, 4, 1, 10, 0)


def test_ambiguous_dates_resolved_towards_month_first():
    chat = parse_chat(android("03/10/24, 10:00", "03/11/24, 10:00", "03/12/24, 10:00",
                              "04/01/24, 10:00", "04/02/24, 10:00"))
    assert chat.meta.date_order == "MDY"
    assert chat.messages[3].ts == datetime(2024, 4, 1, 10, 0)


def test_truly_ambiguous_raises_with_both_readings():
    with pytest.raises(DateOrderAmbiguous) as err:
        parse_chat(android("03/04/24, 10:00", "05/04/24, 10:00", "07/04/24, 10:00"))
    assert err.value.code == "date_order_ambiguous"
    assert err.value.data["sample"] == (3, 4, 24)
    assert err.value.data["as_dmy"] == "2024-04-03"
    assert err.value.data["as_mdy"] == "2024-03-04"


def test_override_settles_the_ambiguity():
    text = android("03/04/24, 10:00", "05/04/24, 10:00", "07/04/24, 10:00")
    assert parse_chat(text, date_order="DMY").messages[0].ts == datetime(2024, 4, 3, 10, 0)
    assert parse_chat(text, date_order="MDY").messages[0].ts == datetime(2024, 3, 4, 10, 0)


def test_identical_readings_need_no_question():
    # 05/05/24 is the same instant either way, so do not bother the user.
    chat = parse_chat(android("05/05/24, 10:00", "05/05/24, 11:00", "05/05/24, 12:00"))
    assert chat.meta.date_order == "DMY"


def test_impossible_dates_are_dropped_with_a_warning():
    chat = parse_chat(android("13/01/24, 10:00", "31/02/24, 10:00", "14/01/24, 10:00"))
    assert len(chat.messages) == 2
    assert "dropped_invalid_dates:1" in chat.warnings


def test_bad_override_value_is_rejected():
    with pytest.raises(ValueError):
        parse_chat(android("13/01/24, 10:00"), date_order="XYZ")


def test_unrecognized_files_are_rejected():
    for text in ["", "hello world\nthis is not a chat\nat all\n", "1,2,3\n4,5,6\n"]:
        with pytest.raises(UnrecognizedFormat):
            parse_chat(text)
