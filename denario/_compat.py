"""Compatibility helpers for third-party dependencies."""

from __future__ import annotations

import importlib


def patch_mistralai_for_cmbagent() -> None:
    """Expose legacy top-level Mistral symbols expected by ``cmbagent``.

    ``cmbagent`` imports ``Mistral`` and ``DocumentURLChunk`` from the top-level
    ``mistralai`` module, while newer ``mistralai`` releases place them under
    nested modules. Patch those attributes in when needed so Denario keeps
    working across both layouts.
    """

    try:
        mistralai = importlib.import_module("mistralai")
    except Exception:
        return

    try:
        if not hasattr(mistralai, "Mistral"):
            mistral_sdk = importlib.import_module("mistralai.client.sdk")
            mistralai.Mistral = mistral_sdk.Mistral

        if not hasattr(mistralai, "DocumentURLChunk"):
            document_module = importlib.import_module(
                "mistralai.client.models.documenturlchunk"
            )
            mistralai.DocumentURLChunk = document_module.DocumentURLChunk
    except Exception:
        # Leave the environment unchanged if the dependency moves again;
        # downstream imports will surface the real error in that case.
        return
