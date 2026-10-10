from datetime import date

from app.domain.mission import (
    DayFacts,
    ItemState,
    MissionItemInput,
    OccRef,
    build_mission,
    is_complete,
    item_state,
    mission_kind,
    optional_done,
)

FRI = date(2026, 10, 9)


def occ(i: str, window: str, status: str = "pending") -> OccRef:
    return OccRef(i, status, FRI, window)


def test_weekday_mission_has_blocks_in_window_order_and_checkout():
    items = build_mission(FRI, [occ("c", "after"), occ("a", "before"), occ("b", "middle", "completed")])
    assert [(i.kind, i.ref_id, i.required) for i in items] == [
        ("block", "a", True), ("block", "b", True), ("block", "c", True), ("checkout", None, False),
    ]
    assert [i.position for i in items] == [0, 1, 2, 3]


def test_question_goal_adds_optional_item():
    items = build_mission(FRI, [], question_goal=20)
    assert [(i.kind, i.target, i.required) for i in items] == [("questions", 20, False), ("checkout", None, False)]


def test_kind():
    assert mission_kind(FRI) == "weekday"
    assert mission_kind(date(2026, 10, 10)) == "free"


def test_block_states():
    block = MissionItemInput(0, "block", True, ref_id="o1")
    base = {"occurrence_status": {"o1": "pending"}, "occurrence_planned_on": {"o1": FRI}}
    assert item_state(block, DayFacts(FRI, **base)).state == "pending"
    done = DayFacts(FRI, occurrence_status={"o1": "completed"}, occurrence_planned_on={"o1": FRI},
                    occurrence_completed_on={"o1": FRI})
    assert item_state(block, done).state == "done"
    late = DayFacts(FRI, occurrence_status={"o1": "completed"}, occurrence_planned_on={"o1": FRI},
                    occurrence_completed_on={"o1": date(2026, 10, 12)})
    assert item_state(block, late).state == "pending"
    moved = DayFacts(FRI, occurrence_status={"o1": "pending"}, occurrence_planned_on={"o1": date(2026, 10, 12)})
    assert item_state(block, moved) == ItemState("not_applicable", "rescheduled")
    skipped = DayFacts(FRI, occurrence_status={"o1": "skipped"}, occurrence_planned_on={"o1": FRI})
    assert item_state(block, skipped) == ItemState("not_applicable", "skipped")
    manual = MissionItemInput(0, "block", True, ref_id="o1", na_reason="Intermediário indisponível")
    assert item_state(manual, DayFacts(FRI, **base)).state == "not_applicable"


def test_checkout_and_questions_states():
    assert item_state(MissionItemInput(0, "checkout", False), DayFacts(FRI, checkout_saved=True)).state == "done"
    q = MissionItemInput(0, "questions", False, target=20)
    assert item_state(q, DayFacts(FRI, question_items=19)).state == "pending"
    assert item_state(q, DayFacts(FRI, question_items=20)).state == "done"


def test_completion_rules():
    done, na, pending = ItemState("done"), ItemState("not_applicable", "x"), ItemState("pending")
    assert not is_complete([(True, na), (True, na)])
    assert is_complete([(True, done), (True, na), (False, pending)])
    assert not is_complete([(True, done), (True, pending)])
    assert not is_complete([(False, done)])
    assert optional_done([(True, done), (False, done), (False, pending)]) == 1


def test_completed_block_counts_even_if_marked_not_applicable():
    item = MissionItemInput(0, "block", True, ref_id="o1", na_reason="Não se aplica hoje")
    facts = DayFacts(FRI, occurrence_status={"o1": "completed"}, occurrence_planned_on={"o1": FRI},
                     occurrence_completed_on={"o1": FRI})
    assert item_state(item, facts).state == "done"
