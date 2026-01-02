"""
RFP Intelligence - Base Agent Configuration

Provides LLM abstraction layer supporting multiple providers (OpenAI, Anthropic, Gemini).
"""

import os
from typing import Optional
from crewai import LLM

from config.settings import settings, LLMProvider


def get_llm(
    provider: Optional[LLMProvider] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None
) -> LLM:
    """
    Get an LLM instance for the specified or configured provider.
    
    Args:
        provider: Override the configured provider
        model: Override the configured model
        temperature: Override the configured temperature
        
    Returns:
        Configured LLM instance for CrewAI
    """
    provider = provider or settings.llm_provider
    model = model or settings.default_model
    temperature = temperature if temperature is not None else settings.llm_temperature
    
    # Set API key in environment (CrewAI reads from env)
    if provider == LLMProvider.OPENAI:
        if settings.openai_api_key:
            os.environ["OPENAI_API_KEY"] = settings.openai_api_key
        return LLM(
            model=f"openai/{model}" if not model.startswith("openai/") else model,
            temperature=temperature
        )
    
    elif provider == LLMProvider.ANTHROPIC:
        if settings.anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key
        return LLM(
            model=f"anthropic/{model}" if not model.startswith("anthropic/") else model,
            temperature=temperature
        )
    
    elif provider == LLMProvider.GEMINI:
        if settings.google_api_key:
            os.environ["GOOGLE_API_KEY"] = settings.google_api_key
        return LLM(
            model=f"gemini/{model}" if not model.startswith("gemini/") else model,
            temperature=temperature
        )
    
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


# Default LLM instance using configured settings
default_llm = None

def get_default_llm() -> LLM:
    """Get the default LLM instance (lazy initialization)."""
    global default_llm
    if default_llm is None:
        default_llm = get_llm()
    return default_llm


# Common agent configurations
AGENT_VERBOSE = True

# Output validation helpers
def validate_json_output(output: str, required_keys: list[str]) -> dict:
    """
    Validate and parse JSON output from an agent.
    
    Args:
        output: Raw output string from agent
        required_keys: Keys that must be present in the output
        
    Returns:
        Parsed JSON dict
        
    Raises:
        ValueError: If output is not valid JSON or missing required keys
    """
    import json
    
    # Try to extract JSON from the output
    try:
        # Handle cases where agent wraps JSON in markdown code blocks
        if "```json" in output:
            start = output.find("```json") + 7
            end = output.find("```", start)
            output = output[start:end].strip()
        elif "```" in output:
            start = output.find("```") + 3
            end = output.find("```", start)
            output = output[start:end].strip()
        
        data = json.loads(output)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON output: {e}")
    
    # Check required keys
    missing = [key for key in required_keys if key not in data]
    if missing:
        raise ValueError(f"Missing required keys in output: {missing}")
    
    return data
