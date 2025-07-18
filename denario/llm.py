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

gemini25flash = LLM(name="gemini-2.5-flash-preview-04-17",
                    max_output_tokens=65536,
                    temperature=0.7)
"""`gemini-2.5-flash` model."""

#gemini25pro = LLM(name="gemini-2.5-pro-preview-05-06",
#                  max_output_tokens=65536,
#                  temperature=0.7)
#"""`gemini-2.5-pro` model."""

gemini25pro = LLM(name="gemini-2.5-pro-preview-06-05",
                  max_output_tokens=65536,
                  temperature=0.7)
"""`gemini-2.5-pro` model."""

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

gpt4omini = LLM(name="gpt-4o-mini-2024-07-18",
                max_output_tokens=16384,
                temperature=0.5)
"""`gpt-4o-mini` model."""

gpt45 = LLM(name="gpt-4.5-preview-2025-02-27",
            max_output_tokens=16384,
            temperature=0.5)
"""`gpt-4.5-preview` model."""

claude37sonnet = LLM(name="claude-3-7-sonnet-20250219",
                     max_output_tokens=64000,
                     temperature=0)
"""`claude-3-7-sonnet` model."""

models : Dict[str, LLM] = {
                            "gemini-2.0-flash" : gemini20flash,
                            "gemini-2.5-flash" : gemini25flash,
                            "gemini-2.5-pro" : gemini25pro,
                            "o3-mini" : o3mini,
                            "gpt-4o" : gpt4o,
                            "gpt-4.1" : gpt41,
                            "gpt-4o-mini" : gpt4omini,
                            "gpt-4.5" : gpt45,
                            "claude-3.7-sonnet" : claude37sonnet,
                           }
"""Dictionary with the available models."""
