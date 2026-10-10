import copy
import uuid

import pytest

from app.guidance import content


def theme(id, kind="complementary"):
    lines, points = (30, 30) if kind == "complementary" else (60, 70)
    return {"id": id, "titulo": f"Tema {id}", "topic_ids": ["C04.01"], "linhas": lines,
            "texto_motivador": "Texto.", "comando": "Redija um texto dissertativo.",
            "aspectos": [{"texto": "Aspecto", "valor": points}],
            "espelho": {"texto_padrao": "Padrão.", "quesitos": [{"id": "2.1", "texto": "Q", "conceitos": ["0", "1"]}]},
            "fontes": [{"titulo": "Edital", "url": "https://www.in.gov.br/"}], "semelhante_a": None}


@pytest.fixture
def temas(monkeypatch):
    data = copy.deepcopy(content.guidance())
    data["temas"] = {"complementary": [theme("D1"), theme("D2"), theme("D3")],
                     "technical_case": [theme("C1", "technical_case")]}
    data["subitens"] = {"C04.01": ["1.1 Formulação de perguntas"]}
    monkeypatch.setattr(content, "guidance", lambda: data)
    return data


def week(client, start):
    items = client.post("/api/v1/plans/current/weeks", json={"week_start": start}).json()["items"]
    return {i["slot"]["code"]: i for i in items}


def guidance(client, occ):
    return client.get(f"/api/v1/occurrences/{occ['id']}/guidance")


def essay_session(client, occ):
    body = {"id": str(uuid.uuid4()), "occurrence_id": occ["id"], "studied_on": "2026-10-09",
            "duration_minutes": 60, "activity": "essay", "essay_kind": "complementary", "topic_ids": []}
    assert client.post("/api/v1/sessions", json=body).status_code == 201


def test_s13_first_week_has_note_topic_and_subitems(client, temas):
    g = guidance(client, week(client, "2026-10-05")["S13"]).json()
    assert g["roteiro"]["titulo"] == "Complementares + revisão da semana"
    assert g["nota"].startswith("Semana parcial")
    assert g["topic"] == {"id": "C04.01", "title": g["topic"]["title"], "subitens": ["1.1 Formulação de perguntas"]}
    assert (g["tema"], g["next_theme_id"], g["lembretes"]) == (None, None, [])


def test_s13_full_week_has_no_note(client, temas):
    assert guidance(client, week(client, "2026-10-12")["S13"]).json()["nota"] is None


def test_essay_rotation_and_swap(client, temas):
    s14 = week(client, "2026-10-05")["S14"]
    g = guidance(client, s14).json()
    assert (g["tema"]["id"], g["next_theme_id"]) == ("D1", "D2")
    assert g["lembretes"][0].startswith("Até 30 linhas")
    assert guidance(client, week(client, "2026-10-12")["S14"]).json()["tema"]["id"] == "D2"
    r = client.patch(f"/api/v1/occurrences/{s14['id']}", json={"version": s14["version"], "theme_id": "D3"})
    assert r.status_code == 200
    assert guidance(client, s14).json()["tema"]["id"] == "D3"


def test_theme_is_fixed_after_session(client, temas):
    s14 = week(client, "2026-10-05")["S14"]
    swapped = client.patch(f"/api/v1/occurrences/{s14['id']}", json={"version": s14["version"], "theme_id": "D2"}).json()
    essay_session(client, s14)
    g = guidance(client, s14).json()
    assert (g["tema"]["id"], g["next_theme_id"]) == ("D2", None)
    locked = client.patch(f"/api/v1/occurrences/{s14['id']}", json={"version": swapped["version"], "theme_id": "D3"})
    assert locked.json()["error"]["code"] == "theme_locked"
    assert guidance(client, week(client, "2026-10-12")["S14"]).json()["tema"]["id"] == "D3"


def test_session_pins_default_theme(client, temas):
    s14 = week(client, "2026-10-05")["S14"]
    essay_session(client, s14)
    temas["temas"]["complementary"].insert(0, theme("D0"))
    assert guidance(client, s14).json()["tema"]["id"] == "D1"


def test_unknown_theme_and_theme_on_theory_block(client, temas):
    w = week(client, "2026-10-05")
    bad = client.patch(f"/api/v1/occurrences/{w['S14']['id']}", json={"version": w["S14"]["version"], "theme_id": "C1"})
    assert bad.json()["error"]["code"] == "unknown_theme"
    theory = client.patch(f"/api/v1/occurrences/{w['S13']['id']}", json={"version": w["S13"]["version"], "theme_id": "D1"})
    assert theory.json()["error"]["code"] == "unknown_theme"


def test_guidance_without_themes(client, temas):
    temas["temas"] = {"complementary": [], "technical_case": []}
    g = guidance(client, week(client, "2026-10-05")["S15"]).json()
    assert g["roteiro"]["titulo"].startswith("Situação-problema (Q2)")
    assert (g["tema"], g["next_theme_id"]) == (None, None)
    assert g["lembretes"][0].startswith("Até 60 linhas")


def test_guidance_does_not_write_and_404(client, temas):
    s14 = week(client, "2026-10-05")["S14"]
    guidance(client, s14)
    again = client.get("/api/v1/occurrences", params={"from": "2026-10-09", "to": "2026-10-09"}).json()["items"]
    assert next(o for o in again if o["id"] == s14["id"])["version"] == s14["version"]
    assert client.get(f"/api/v1/occurrences/{uuid.uuid4()}/guidance").status_code == 404
