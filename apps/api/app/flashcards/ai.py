"""Adaptador da OpenAI (Responses API com saída estruturada). Testes trocam `get_generator` por um falso."""

import json
import logging
from typing import Protocol

from app import config
from app.flashcards.domain import OUTPUT_SCHEMA, Batch, Context, load_prompt, parse_batch, user_input

log = logging.getLogger(__name__)


class AiError(Exception):
    pass


class Generator(Protocol):
    model: str

    def __call__(self, ctx: Context) -> Batch: ...


class OpenAiGenerator:
    def __init__(self, api_key: str, model: str, client=None):
        if client is None:
            from openai import OpenAI

            client = OpenAI(api_key=api_key, max_retries=0)  # uma tentativa: o limite de 60 s é do pedido inteiro
        self.model, self._client = model, client

    def __call__(self, ctx: Context) -> Batch:
        try:
            response = self._client.responses.create(
                model=self.model,
                instructions=load_prompt(),
                input=user_input(ctx),
                text={"format": {"type": "json_schema", "name": "flashcards", "strict": True, "schema": OUTPUT_SCHEMA}},
                store=False,
                timeout=config.OPENAI_TIMEOUT,
            )
            return parse_batch(json.loads(response.output_text), ctx)
        except Exception as exc:  # SDK, recusa (texto vazio) ou JSON inválido: tudo vira falha de geração
            log.warning("flashcard generation failed: %s", type(exc).__name__)
            raise AiError from exc


def get_generator() -> Generator | None:
    if not config.OPENAI_API_KEY:
        return None
    return OpenAiGenerator(config.OPENAI_API_KEY, config.OPENAI_MODEL)
