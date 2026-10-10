from datetime import date

from app.domain.guidance import ThemeRef, next_theme, pick_variant, resolve_themes

IDS = ["D1", "D2", "D3"]


def ref(occ, week, stored=None, session=False):
    return ThemeRef(occ, week, stored, session)


def test_each_week_gets_its_theme_in_rotation():
    got = resolve_themes(IDS, [ref("a", 0), ref("b", 1), ref("c", 2), ref("d", 3)])
    assert got == {"a": "D1", "b": "D2", "c": "D3", "d": "D1"}


def test_stored_theme_wins():
    assert resolve_themes(IDS, [ref("a", 0, stored="D3")]) == {"a": "D3"}


def test_theme_done_in_earlier_week_is_skipped():
    got = resolve_themes(IDS, [ref("a", 0, stored="D2", session=True), ref("b", 1)])
    assert got == {"a": "D2", "b": "D3"}


def test_theme_without_session_is_not_done():
    got = resolve_themes(IDS, [ref("a", 0, stored="D2"), ref("b", 1)])
    assert got == {"a": "D2", "b": "D2"}


def test_removed_stored_theme_falls_back_to_rotation():
    assert resolve_themes(IDS, [ref("a", 1, stored="X9")]) == {"a": "D2"}


def test_no_themes_resolves_to_none():
    assert resolve_themes([], [ref("a", 0)]) == {"a": None}


def test_all_done_repeats_week_theme():
    refs = [ref("a", 0, session=True), ref("b", 1, session=True), ref("c", 2, session=True), ref("d", 3)]
    assert resolve_themes(IDS, refs)["d"] == "D1"


def test_next_theme_skips_done_and_wraps():
    assert next_theme(IDS, "D1", {"D2"}) == "D3"
    assert next_theme(IDS, "D3", set()) == "D1"
    assert next_theme(IDS, "D1", {"D2", "D3"}) is None
    assert next_theme(["D1"], "D1", set()) is None


def test_pick_variant_by_date():
    variants = [{"ate": "2026-11-22", "titulo": "Reduzido", "passos": []},
                {"ate": None, "titulo": "Completo", "passos": []}]
    assert pick_variant(variants, date(2026, 11, 22))["titulo"] == "Reduzido"
    assert pick_variant(variants, date(2026, 11, 23))["titulo"] == "Completo"
