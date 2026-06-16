"""OpenRouter configuration builder for cmbagent compatibility.

This module provides utilities to build cmbagent-compatible LLM configurations
that route all API calls through OpenRouter, avoiding the need for native
provider SDKs (like Google Vertex AI).
"""
import os
from typing import Optional

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Map internal model names to OpenRouter model IDs
MODEL_TO_OPENROUTER = {
    # Gemini models
    "gemini-3-pro-preview": "google/gemini-3-pro-preview",
    "gemini-3-flash-preview": "google/gemini-3-flash-preview",
    "gemini-2.5-pro": "google/gemini-2.5-pro-preview-05-06",
    "gemini-2.5-flash": "google/gemini-2.5-flash-preview-05-20",
    # OpenAI models
    "gpt-4o": "openai/gpt-4o",
    "gpt-4o-2024-11-20": "openai/gpt-4o-2024-11-20",
    "gpt-4.1": "openai/gpt-4.1",
    "gpt-4.1-2025-04-14": "openai/gpt-4.1-2025-04-14",
    "o3-mini": "openai/o3-mini",
    "o3-mini-2025-01-31": "openai/o3-mini-2025-01-31",
    # Claude models
    "claude-3-opus": "anthropic/claude-3-opus",
    "claude-3-sonnet": "anthropic/claude-3-sonnet",
    "claude-3-7-sonnet-20250219": "anthropic/claude-3.7-sonnet",
}


def get_openrouter_model_id(model: str) -> str:
    """Convert internal model name to OpenRouter model ID.
    
    Args:
        model: Internal model name (e.g., "gemini-3-pro-preview")
        
    Returns:
        OpenRouter model ID (e.g., "google/gemini-3-pro-preview")
    """
    if "/" in model:
        return model  # Already in OpenRouter format
    return MODEL_TO_OPENROUTER.get(model, f"openai/{model}")


def build_openrouter_config(model: str, api_key: Optional[str] = None) -> dict:
    """Build cmbagent-compatible config for OpenRouter.
    
    Args:
        model: Model name (internal or OpenRouter format)
        api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
        
    Returns:
        Config dict compatible with cmbagent's agent_llm_configs
    """
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    openrouter_model = get_openrouter_model_id(model)
    
    config = {
        "model": openrouter_model,
        "api_key": key,
        "api_type": "openai",
        "base_url": OPENROUTER_BASE_URL,
    }
    
    # Add reasoning_effort for o3 models
    if "o3" in model:
        config["reasoning_effort"] = "medium"
    
    return config


def build_agent_llm_configs(
    engineer_model: str,
    researcher_model: str,
    planner_model: str,
    plan_reviewer_model: str,
    orchestration_model: str,
    formatter_model: str,
    api_key: Optional[str] = None,
) -> dict:
    """Build complete agent_llm_configs dict for cmbagent.
    
    This creates configs for all agents used by cmbagent, routing them
    through OpenRouter.
    
    Args:
        engineer_model: Model for engineer agent
        researcher_model: Model for researcher agent
        planner_model: Model for planner agent
        plan_reviewer_model: Model for plan reviewer agent
        orchestration_model: Model for control/orchestration agents
        formatter_model: Model for response formatter agents
        api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
        
    Returns:
        Dict mapping agent names to their LLM configs
    """
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    
    return {
        # Main agents
        "engineer": build_openrouter_config(engineer_model, key),
        "researcher": build_openrouter_config(researcher_model, key),
        "planner": build_openrouter_config(planner_model, key),
        "plan_reviewer": build_openrouter_config(plan_reviewer_model, key),
        "control": build_openrouter_config(orchestration_model, key),
        "idea_maker": build_openrouter_config(orchestration_model, key),
        "idea_hater": build_openrouter_config(orchestration_model, key),
        "camb_context": build_openrouter_config(orchestration_model, key),
        "plot_judge": build_openrouter_config(formatter_model, key),
        # Formatters
        "engineer_response_formatter": build_openrouter_config(formatter_model, key),
        "researcher_response_formatter": build_openrouter_config(formatter_model, key),
        "executor_response_formatter": build_openrouter_config(formatter_model, key),
        "planner_response_formatter": build_openrouter_config(formatter_model, key),
        "reviewer_response_formatter": build_openrouter_config(formatter_model, key),
        "idea_maker_response_formatter": build_openrouter_config(formatter_model, key),
        "idea_hater_response_formatter": build_openrouter_config(formatter_model, key),
        "summarizer_response_formatter": build_openrouter_config(formatter_model, key),
        # Other agents
        "task_improver": build_openrouter_config(formatter_model, key),
        "task_recorder": build_openrouter_config(orchestration_model, key),
        "summarizer": build_openrouter_config(orchestration_model, key),
        "perplexity": build_openrouter_config(formatter_model, key),
        "aas_keyword_finder": build_openrouter_config(formatter_model, key),
        "plot_debugger": build_openrouter_config(orchestration_model, key),
    }


def build_cmbagent_api_keys(openrouter_key: Optional[str] = None) -> dict:
    """Build api_keys dict for cmbagent using OpenRouter.
    
    CMBAgent expects a dict with OPENAI, GEMINI, ANTHROPIC keys.
    We map OpenRouter key to all of them since agent_llm_configs 
    will override the actual usage.
    
    Args:
        openrouter_key: OpenRouter API key (defaults to env var)
        
    Returns:
        Dict compatible with cmbagent's api_keys parameter
    """
    key = openrouter_key or os.getenv("OPENROUTER_API_KEY")
    
    return {
        "OPENAI": key,
        "GEMINI": key,
        "ANTHROPIC": key,
        "MISTRAL": key,
    }
