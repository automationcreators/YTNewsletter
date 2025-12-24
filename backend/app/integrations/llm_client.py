"""LLM client abstraction for multiple providers."""

from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass
import anthropic
import openai
from app.config import settings


@dataclass
class LLMResponse:
    """Response from LLM."""
    content: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    total_tokens: int


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        pass

    @property
    @abstractmethod
    def provider(self) -> str:
        """Get the provider name."""
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        """Get the model name."""
        pass


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or settings.anthropic_api_key
        self._model = model or "claude-sonnet-4-20250514"
        self.client = anthropic.Anthropic(api_key=self.api_key)

    @property
    def provider(self) -> str:
        return "anthropic"

    @property
    def model(self) -> str:
        return self._model

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate a response using Claude."""
        messages = [{"role": "user", "content": prompt}]

        kwargs = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": messages,
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        # Only add temperature if not using extended thinking models
        if not self._model.startswith("claude-3-5"):
            kwargs["temperature"] = temperature

        response = self.client.messages.create(**kwargs)

        return LLMResponse(
            content=response.content[0].text,
            model=self._model,
            provider="anthropic",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
        )


class OpenAIClient(BaseLLMClient):
    """OpenAI GPT client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or settings.openai_api_key
        self._model = model or "gpt-4-turbo-preview"
        self.client = openai.OpenAI(api_key=self.api_key)

    @property
    def provider(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate a response using GPT."""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        usage = response.usage

        return LLMResponse(
            content=response.choices[0].message.content,
            model=self._model,
            provider="openai",
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
        )


class LLMFactory:
    """Factory for creating LLM clients."""

    @staticmethod
    def create(
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> BaseLLMClient:
        """
        Create an LLM client.

        Args:
            provider: Provider name ("anthropic" or "openai")
            model: Model name (uses default if not specified)

        Returns:
            LLM client instance
        """
        provider = provider or settings.default_llm_provider

        if provider == "anthropic":
            return AnthropicClient(model=model)
        elif provider == "openai":
            return OpenAIClient(model=model)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

    @staticmethod
    def get_default() -> BaseLLMClient:
        """Get the default LLM client based on settings."""
        return LLMFactory.create(
            provider=settings.default_llm_provider,
            model=settings.default_llm_model,
        )


# Default client instance
default_llm_client = LLMFactory.get_default()
