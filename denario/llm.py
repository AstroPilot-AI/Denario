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

gemini20flash = LLM(name="gemini-2.0-flash",
                    max_output_tokens=8192,
                    temperature=0.7)
"""`gemini-2.0-flash` model."""

gemini25flash = LLM(name="gemini-2.5-flash",
                    max_output_tokens=65536,
                    temperature=0.7)
"""`gemini-2.5-flash` model."""

gemini25pro = LLM(name="gemini-2.5-pro",
                  max_output_tokens=65536,
                  temperature=0.7)
"""`gemini-2.5-pro` model."""

gemini3propreview = LLM(name="gemini-3-pro-preview",
                        max_output_tokens=65536,
                        temperature=0.7)
"""`gemini-3-pro-preview` model."""

gemini3flashpreview = LLM(name="gemini-3-flash-preview",
                          max_output_tokens=65536,
                          temperature=0.7)
"""`gemini-3-flash-preview` model."""

o3mini = LLM(name="o3-mini-2025-01-31",
             max_output_tokens=100000,
             temperature=None)
"""`o3-mini` model."""

gpt4o = LLM(name="gpt-4o-2024-11-20",
            max_output_tokens=16384,
            temperature=0.5)
"""`gpt-4o` model."""

gpt41 = LLM(name="gpt-4.1-2025-04-14",
            max_output_tokens=16384,
            temperature=0.5)
"""`gpt-4.1` model."""

gpt41mini = LLM(name="gpt-4.1-mini",
                max_output_tokens=16384,
                temperature=0.5)
"""`gpt-4.1-mini` model."""

gpt4omini = LLM(name="gpt-4o-mini-2024-07-18",
                max_output_tokens=16384,
                temperature=0.5)
"""`gpt-4o-mini` model."""

gpt45 = LLM(name="gpt-4.5-preview-2025-02-27",
            max_output_tokens=16384,
            temperature=0.5)
"""`gpt-4.5-preview` model."""

gpt5 = LLM(name="gpt-5",
           max_output_tokens=128000,
           temperature=None)
"""`gpt-5` model """

gpt52 = LLM(name="gpt-5.2",
            max_output_tokens=128000,
            temperature=None)
"""`gpt-5.2` model."""

gpt52pro = LLM(name="gpt-5.2-pro",
               max_output_tokens=128000,
               temperature=None)
"""`gpt-5.2-pro` model."""

gpt5mini = LLM(name="gpt-5-mini",
               max_output_tokens=128000,
               temperature=None)
"""`gpt-5-mini` model."""

claude37sonnet = LLM(name="claude-3-7-sonnet-20250219",
                     max_output_tokens=64000,
                     temperature=0)
"""`claude-3-7-sonnet` model."""

claude4opus = LLM(name="claude-opus-4-20250514",
                   max_output_tokens=32000,
                   temperature=0)
"""`claude-4-Opus` model."""

claude41opus = LLM(name="claude-opus-4-1-20250805",
                   max_output_tokens=32000,
                   temperature=0)
"""`claude-4.1-Opus` model."""

claude45sonnet = LLM(name="claude-sonnet-4-5",
                     max_output_tokens=64000,
                     temperature=0)
"""`claude-4.5-Sonnet` model."""

claude45sonnet_20250929 = LLM(name="claude-sonnet-4-5-20250929",
                              max_output_tokens=64000,
                              temperature=0)
"""`claude-4.5-Sonnet` snapshot model."""

claude45haiku = LLM(name="claude-haiku-4-5",
                    max_output_tokens=64000,
                    temperature=0)
"""`claude-4.5-Haiku` model."""

claude45haiku_20251001 = LLM(name="claude-haiku-4-5-20251001",
                             max_output_tokens=64000,
                             temperature=0)
"""`claude-4.5-Haiku` snapshot model."""

claude45opus = LLM(name="claude-opus-4-5",
                   max_output_tokens=64000,
                   temperature=0)
"""`claude-4.5-Opus` model."""

claude45opus_20251101 = LLM(name="claude-opus-4-5-20251101",
                            max_output_tokens=64000,
                            temperature=0)
"""`claude-4.5-Opus` snapshot model."""

models : Dict[str, LLM] = {
                            "gemini-2.0-flash" : gemini20flash,
                            "gemini-2.5-flash" : gemini25flash,
                            "gemini-2.5-pro" : gemini25pro,
                            "gemini-3-pro" : gemini3propreview,
                            "gemini-3-pro-preview" : gemini3propreview,
                            "gemini-3-flash" : gemini3flashpreview,
                            "gemini-3-flash-preview" : gemini3flashpreview,
                            "o3-mini" : o3mini,
                            "gpt-4o" : gpt4o,
                            "gpt-4.1" : gpt41,
                            "gpt-4.1-mini" : gpt41mini,
                            "gpt-4o-mini" : gpt4omini,
                            "gpt-4.5" : gpt45,
                            "gpt-5" : gpt5,
                            "gpt-5.2" : gpt52,
                            "gpt-5.2-pro" : gpt52pro,
                            "gpt-5-mini" : gpt5mini,
                            "claude-3.7-sonnet" : claude37sonnet,
                            "claude-4-opus" : claude4opus,
                            "claude-4.1-opus" : claude41opus,
                            "claude-4.5-sonnet" : claude45sonnet,
                            "claude-4.5-sonnet-20250929" : claude45sonnet_20250929,
                            "claude-4.5-haiku" : claude45haiku,
                            "claude-4.5-haiku-20251001" : claude45haiku_20251001,
                            "claude-4.5-opus" : claude45opus,
                            "claude-4.5-opus-20251101" : claude45opus_20251101,
                           }
"""Dictionary with the available models."""
