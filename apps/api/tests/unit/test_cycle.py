import json
from collections import Counter
from datetime import date

import pytest

from app import config
from app.domain.cycle import (
    essay_kind_for,
    next_topic,
    weeks_since,
    CycleError,
    SlotInput,
    TemplateInput,
    generate_week,
    select_template,
    suggest_topic,
    week_index,
    week_start_of,
)

DATA = config.DATA_DIR / "ciclo-inicial.json"
PLAN_START, PLAN_END = date(2026, 10, 9), date(2026, 12, 11)


def initial_template() -> TemplateInput:
    raw = json.loads(DATA.read_text(encoding="utf-8"))
    slots = tuple(
        SlotInput(s["code"], s["weekday"], s["window"], s["minutes"], s["purpose"]) for s in raw["slots"]
    )
    return TemplateInput(date.fromisoformat(raw["template"]["effective_from"]), slots)


def test_partial_first_week_has_only_friday_blocks():
    occ = generate_week(initial_template(), date(2026, 10, 5), PLAN_START, PLAN_END)
    assert [o.cycle_slot_code for o in occ] == ["S13", "S14", "S15"]
    assert {o.planned_on for o in occ} == {date(2026, 10, 9)}
    assert [o.window for o in occ] == ["before", "middle", "after"]


def test_full_week_has_15_blocks_and_purpose_split():
    tpl = initial_template()
    occ = generate_week(tpl, date(2026, 10, 12), PLAN_START, PLAN_END)
    assert len(occ) == 15
    assert min(o.planned_on for o in occ) == date(2026, 10, 12)
    assert max(o.planned_on for o in occ) == date(2026, 10, 16)
    by_code = {s.code: s for s in tpl.slots}
    minutes = Counter()
    for o in occ:
        minutes[by_code[o.cycle_slot_code].purpose] += by_code[o.cycle_slot_code].minutes
    assert minutes == {"specific": 420, "basic": 180, "complementary": 180, "essay": 120}


def test_last_week_ends_on_plan_end():
    occ = generate_week(initial_template(), date(2026, 12, 7), PLAN_START, PLAN_END)
    assert len(occ) == 15
    assert max(o.planned_on for o in occ) == date(2026, 12, 11)


@pytest.mark.parametrize(
    ("week_start", "message"),
    [(date(2026, 10, 13), "segunda-feira"), (date(2026, 12, 14), "fora do período")],
)
def test_invalid_weeks(week_start, message):
    with pytest.raises(CycleError, match=message):
        generate_week(initial_template(), week_start, PLAN_START, PLAN_END)


def test_select_template_ignores_future_templates():
    old = TemplateInput(date(2026, 10, 5), ())
    new = TemplateInput(date(2026, 10, 26), ())
    assert select_template([old, new], date(2026, 10, 19)) is old
    assert select_template([old, new], date(2026, 10, 26)) is new
    with pytest.raises(CycleError):
        select_template([new], date(2026, 10, 19))


def test_week_helpers_and_topic_suggestion():
    assert week_start_of(date(2026, 10, 9)) == date(2026, 10, 5)
    assert week_index(date(2026, 10, 5), PLAN_START) == 0
    assert week_index(date(2026, 10, 12), PLAN_START) == 1
    assert suggest_topic("alternate_subjects", ["B01.01", "B02.01"], 1) == "B01.01"
    assert suggest_topic("alternate_subjects", ["B01.01", "B02.01"], 2) == "B02.01"
    assert suggest_topic("rotate_subjects", ["B01.01", "B02.01", "B03.01", "B04.01"], 3) == "B03.01"
    s12 = ["E04.01", "E04.02", "E01.04", "E02.04"]
    assert suggest_topic("alternate_delivery_and_interfaces_ai", s12, 1) == "E04.01"
    assert suggest_topic("alternate_delivery_and_interfaces_ai", s12, 2) == "E01.04"
    assert suggest_topic("choose_topic", ["E01.02", "E01.03"], 5) == "E01.02"
    assert suggest_topic("technical_case", [], 1) is None


def test_weeks_since_template_start():
    assert weeks_since(date(2026, 10, 26), date(2026, 10, 26)) == 0
    assert weeks_since(date(2026, 11, 9), date(2026, 10, 26)) == 2


def test_next_topic_rotation_starts_at_week_subject():
    topics = {"E01": ["E01.01", "E01.02"], "E03": ["E03.01", "E03.02"]}
    assert next_topic(["E01", "E03"], 0, topics, set()) == "E01.01"
    assert next_topic(["E01", "E03"], 1, topics, {"E03.01"}) == "E03.02"


def test_next_topic_skips_exhausted_subject():
    topics = {"E01": ["E01.01"], "E03": ["E03.01"]}
    assert next_topic(["E01", "E03"], 0, topics, {"E01.01"}) == "E03.01"
    assert next_topic(["E01", "E03"], 0, topics, {"E01.01", "E03.01"}) is None


def test_alternate_essay_by_week():
    assert essay_kind_for("alternate_essay", 0) == "complementary"
    assert essay_kind_for("alternate_essay", 1) == "technical_case"
    assert essay_kind_for("technical_case", 4) == "technical_case"
    assert essay_kind_for("choose_topic", 0) is None
