from pydantic import BaseModel
from typing import Dict

class LLM(BaseModel):
    """LLM base model"""
    name: str
    """Name/identifier of the model."""
    max_output_tokens: int
    """Maximum output tokens allowed."""
    temperature: float | None
    """Temperature of the model."""
    openrouter_name: str | None = None
    """OpenRouter model ID."""

gemini20flash = LLM(name="gemini-2.0-flash",
                    max_output_tokens=8192,
                    temperature=0.7,
                    openrouter_name="google/gemini-2.0-flash-exp:free")
"""`gemini-2.0-flash` model."""

gemini25flash = LLM(name="gemini-2.5-flash",
                    max_output_tokens=65536,
                    temperature=0.7,
                    openrouter_name="google/gemini-2.0-flash-exp:free")
"""`gemini-2.5-flash` model."""

gemini25pro = LLM(name="gemini-2.5-pro",
                  max_output_tokens=65536,
                  temperature=0.7,
                  openrouter_name="google/gemini-2.0-pro-exp-02-05:free")
"""`gemini-2.5-pro` model."""

o3mini = LLM(name="o3-mini-2025-01-31",
             max_output_tokens=100000,
             temperature=None,
             openrouter_name="openai/o3-mini")
"""`o3-mini` model."""

gpt4o = LLM(name="gpt-4o-2024-11-20",
            max_output_tokens=16384,
            temperature=0.5,
            openrouter_name="openai/gpt-4o")
"""`gpt-4o` model."""

gpt41 = LLM(name="gpt-4.1-2025-04-14",
            max_output_tokens=16384,
            temperature=0.5,
            openrouter_name="openai/gpt-4-turbo")
"""`gpt-4.1` model."""

gpt41mini = LLM(name="gpt-4.1-mini",
                max_output_tokens=16384,
                temperature=0.5,
                openrouter_name="openai/gpt-4-turbo-preview")
"""`gpt-4.1-mini` model."""

gpt4omini = LLM(name="gpt-4o-mini-2024-07-18",
                max_output_tokens=16384,
                temperature=0.5,
                openrouter_name="openai/gpt-4o-mini")
"""`gpt-4o-mini` model."""

gpt45 = LLM(name="gpt-4.5-preview-2025-02-27",
            max_output_tokens=16384,
            temperature=0.5,
            openrouter_name="openai/gpt-4.5-preview")
"""`gpt-4.5-preview` model."""

gpt5 = LLM(name="gpt-5",
           max_output_tokens=128000,
           temperature=None,
           openrouter_name="openai/gpt-5")
"""`gpt-5` model """

gpt5mini = LLM(name="gpt-5-mini",
               max_output_tokens=128000,
               temperature=None,
               openrouter_name="openai/gpt-5")
"""`gpt-5-mini` model."""

claude37sonnet = LLM(name="claude-3-7-sonnet-20250219",
                     max_output_tokens=64000,
                     temperature=0,
                     openrouter_name="anthropic/claude-3.7-sonnet")
"""`claude-3-7-sonnet` model."""

claude4opus = LLM(name="claude-opus-4-20250514",
                   max_output_tokens=32000,
                   temperature=0,
                   openrouter_name="anthropic/claude-3-opus")
"""`claude-4-Opus` model."""

claude41opus = LLM(name="claude-opus-4-1-20250805",
                   max_output_tokens=32000,
                   temperature=0,
                   openrouter_name="anthropic/claude-3-opus")
"""`claude-4.1-Opus` model."""

models : Dict[str, LLM] = {
                            "gemini-2.0-flash" : gemini20flash,
                            "gemini-2.5-flash" : gemini25flash,
                            "gemini-2.5-pro" : gemini25pro,
                            "o3-mini" : o3mini,
                            "gpt-4o" : gpt4o,
                            "gpt-4.1" : gpt41,
                            "gpt-4.1-mini" : gpt41mini,
                            "gpt-4o-mini" : gpt4omini,
                            "gpt-4.5" : gpt45,
                            "gpt-5" : gpt5,
                            "gpt-5-mini" : gpt5mini,
                            "claude-3.7-sonnet" : claude37sonnet,
                            "claude-4-opus" : claude4opus,
                            "claude-4.1-opus" : claude41opus,
                           }
"""Dictionary with the available models."""
