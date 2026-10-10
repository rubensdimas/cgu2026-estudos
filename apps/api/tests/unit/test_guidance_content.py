import copy
import json

from app import config
from app.guidance import content


def catalog_topic_ids() -> set[str]:
    catalog = json.loads((config.DATA_DIR / "catalogo-edital.json").read_text(encoding="utf-8"))
    return {t["id"] for s in catalog["subjects"] for t in s["topics"]}


def theme(id, kind="complementary"):
    lines, points = (30, 30) if kind == "complementary" else (60, 70)
    return {"id": id, "titulo": "T", "topic_ids": ["C04.01"], "linhas": lines, "texto_motivador": "x",
            "comando": "Redija.", "aspectos": [{"texto": "a", "valor": points}],
            "espelho": {"texto_padrao": "p", "quesitos": [{"id": "2.1", "texto": "q", "conceitos": ["0", "1"]}]},
            "fontes": [{"titulo": "Edital", "url": "https://www.in.gov.br/"}], "semelhante_a": None}


def test_real_file_is_valid():
    assert content.validate(content.guidance(), catalog_topic_ids()) == []


def test_validator_catches_wrong_minutes_and_points():
    data = copy.deepcopy(content.guidance())
    data["roteiros_por_atividade"]["theory"][0]["passos"][0]["minutos"] += 1
    bad = theme("D1")
    bad["aspectos"][0]["valor"] = 25
    data["temas"]["complementary"] = [bad, theme("D1")]
    problems = content.validate(data, catalog_topic_ids())
    assert any("theory" in p and "61" in p for p in problems)
    assert any("D1" in p and "30" in p for p in problems)
    assert any("duplicado" in p for p in problems)


def test_validator_catches_unknown_topic_and_bad_url():
    data = copy.deepcopy(content.guidance())
    data["materiais"]["Z99.99"] = [{"titulo": "x", "url": "http://exemplo", "nota": ""}]
    problems = content.validate(data, catalog_topic_ids())
    assert any("Z99.99" in p for p in problems)
    assert any("https" in p for p in problems)


NEXT_TWO_WEEKS = {"B01.01", "B02.01", "B03.01", "B04.01", "C01.01", "C02.01", "C03.01", "C04.01", "C05.01",
                  "E01.01", "E01.02", "E01.04", "E02.01", "E03.01", "E04.01"}


def test_every_topic_has_subitems():
    data = content.guidance()
    assert set(data["subitens"]) == catalog_topic_ids()
    assert all(data["subitens"][t] for t in data["subitens"])


def test_next_two_weeks_have_materials():
    assert NEXT_TWO_WEEKS <= set(content.guidance()["materiais"])


def test_enough_themes_until_exam():
    temas = content.guidance()["temas"]
    assert len(temas["complementary"]) >= 10
    assert len(temas["technical_case"]) >= 10
    subjects = {t.split(".")[0] for th in temas["complementary"] for t in th["topic_ids"]}
    assert subjects == {"C01", "C02", "C03", "C04", "C05"}
