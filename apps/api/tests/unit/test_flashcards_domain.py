from app.flashcards.domain import Context, load_prompt, parse_batch, subitem_code, user_input

SUBITEMS = [
    "1.1 Transparência ativa e passiva; finalidade de pedidos e recursos.",
    "1.2 Distinção conceitual entre informação classificada, sigilos previstos em lei e informação pessoal.",
]


def ctx(**over):
    base = dict(subject="Transparência", topic_id="C02.01", topic="Acesso à informação", subitems=SUBITEMS,
                materials=[], studied="")
    base.update(over)
    return Context(**base)


def card(subitem, front="Pergunta?", back="Resposta.", category="conceito"):
    return {"categoria": category, "subitem": subitem, "frente": front, "verso": back}


def test_subitem_code_takes_leading_number():
    assert subitem_code("1.2 Distinção conceitual") == "1.2"


def test_user_input_lists_subitems_and_omits_empty_materials():
    text = user_input(ctx())
    assert "1.1 Transparência" in text and "1.2 Distinção" in text
    assert "Materiais sugeridos" not in text
    assert "Não informado" in text
    with_material = user_input(ctx(materials=[{"titulo": "LAI", "nota": "Arts. 3º a 8º."}], studied="Prazos"))
    assert "Materiais sugeridos" in with_material and "Arts. 3º a 8º." in with_material
    assert "Prazos" in with_material


def test_parse_batch_keeps_valid_and_drops_out_of_scope():
    raw = {"origem": "o", "foco": "f", "prioridades": [], "cards": [
        card("1.2."), card("Subitem 1.1"), card("3.4"), card("1.1", front=" "), card("1.1", category="outra"),
    ]}
    batch = parse_batch(raw, ctx())
    assert [c.subitem for c in batch.cards] == ["1.2", "1.1"]


def test_parse_batch_caps_at_ten_cards_and_three_priorities():
    raw = {"origem": "o", "foco": "f", "prioridades": ["a", "b", "c", "d", "e"], "cards": [card("1.1")] * 12}
    batch = parse_batch(raw, ctx())
    assert len(batch.cards) == 10
    assert batch.priorities == ["a", "b", "c"]


def test_prompt_mentions_cebraspe_and_scope():
    prompt = load_prompt()
    assert "CEBRASPE" in prompt and "subitens" in prompt
