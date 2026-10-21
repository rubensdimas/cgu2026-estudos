import json
from types import SimpleNamespace

import pytest

from app import config
from app.flashcards.ai import AiError, OpenAiGenerator, get_generator
from app.flashcards.domain import Context

CTX = Context(subject="Transparência", topic_id="C02.01", topic="Acesso à informação",
              subitems=["1.1 Transparência ativa e passiva.", "1.2 Sigilos."], materials=[], studied="LAI")


class FakeClient:
    def __init__(self, output_text=None, error=None):
        self.kwargs, self.output_text, self.error = None, output_text, error
        self.responses = SimpleNamespace(create=self.create)

    def create(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return SimpleNamespace(output_text=self.output_text)


def output(*subitems):
    cards = [{"categoria": "conceito", "subitem": s, "frente": "P?", "verso": "R."} for s in subitems]
    return json.dumps({"origem": "o", "foco": "f", "prioridades": [], "cards": cards})


def test_openai_generator_sends_schema_prompt_and_model():
    client = FakeClient(output("1.1", "9.9"))
    batch = OpenAiGenerator("key", "m", client=client)(CTX)
    assert client.kwargs["model"] == "m"
    assert client.kwargs["text"]["format"]["strict"] is True
    assert "CEBRASPE" in client.kwargs["instructions"]
    assert "Acesso à informação" in client.kwargs["input"]
    assert [c.subitem for c in batch.cards] == ["1.1"]


@pytest.mark.parametrize("client", [FakeClient(error=RuntimeError("boom")), FakeClient("não é json"), FakeClient(None)])
def test_openai_generator_wraps_failures(client):
    with pytest.raises(AiError):
        OpenAiGenerator("key", "m", client=client)(CTX)


def test_get_generator_is_none_without_key(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")
    assert get_generator() is None


def test_real_client_does_not_retry_past_the_time_limit(monkeypatch):
    import openai

    created = {}
    monkeypatch.setattr(openai, "OpenAI", lambda **kw: created.update(kw) or FakeClient(output("1.1")))
    OpenAiGenerator("key", "m")(CTX)
    assert created["max_retries"] == 0
