import os
from typing import Optional

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

DEFAULT_PROVIDER = "groq"
DEFAULT_MODEL = "openai/gpt-oss-120b"


def _pick(value: Optional[str], env_name: str, default: str) -> str:
    """
    Return the first of value and the env_name variable that is not blank, stripped,
    or default when both are unset, empty or whitespace only.
    """
    for candidate in (value, os.environ.get(env_name)):
        if candidate and candidate.strip():
            return candidate.strip()
    return default


class LLMLoader:
    """
    A class to handle LLM model loading and configuration.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        model_provider: Optional[str] = None,
        temperature: float = 0.05,
    ):
        """
        Initialize LLMLoader.

        Args:
            model_name: Name of the model to load. Precedence: this argument, then
                AUTOKRAFT_LLM_MODEL (environment or .env), then DEFAULT_MODEL.
            model_provider: Provider for the model. Precedence: this argument, then
                AUTOKRAFT_LLM_PROVIDER (environment or .env), then DEFAULT_PROVIDER.
            temperature: Controls randomness in responses (0.0-1.0, default: 0.05)
        """
        load_dotenv()
        self.model_name = _pick(model_name, "AUTOKRAFT_LLM_MODEL", DEFAULT_MODEL)
        self.model_provider = _pick(
            model_provider, "AUTOKRAFT_LLM_PROVIDER", DEFAULT_PROVIDER
        ).lower()
        self.temperature = temperature
        self._model = None
        self._setup_api_key()

    def _setup_api_key(self) -> None:
        """
        Check that the API key of the model provider is set in the environment.
        """
        if self.model_provider.lower() == "groq":
            api_key = os.environ.get("GROQ_API_KEY")
            if not api_key:
                raise ValueError(
                    "GROQ_API_KEY not found in environment variables. "
                    "Please add GROQ_API_KEY=your_api_key to your .env file"
                )
        # Add other providers as needed
        elif self.model_provider.lower() == "openai":
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY not found in environment variables. "
                    "Please add OPENAI_API_KEY=your_api_key to your .env file"
                )

    def get_model(self):
        """
        Get the initialized model instance.

        Returns:
            Initialized chat model
        """
        if self._model is None:
            self._model = init_chat_model(
                self.model_name, model_provider=self.model_provider, temperature=self.temperature
            )

        return self._model

    def reload_model(self):
        """
        Reload the model (useful if you want to reinitialize).

        Returns:
            Newly initialized chat model
        """
        self._model = init_chat_model(
            self.model_name, model_provider=self.model_provider, temperature=self.temperature
        )
        return self._model

    def change_model(
        self,
        model_name: str,
        model_provider: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """
        Change to a different model.

        Args:
            model_name: New model name
            model_provider: New model provider (optional, keeps current if not provided)
            temperature: New temperature setting (optional, keeps current if not provided)

        Returns:
            Newly initialized chat model
        """
        self.model_name = model_name
        if model_provider:
            self.model_provider = model_provider
            self._setup_api_key()
        if temperature is not None:
            self.temperature = temperature

        return self.reload_model()

    def set_temperature(self, temperature: float):
        """
        Set a new temperature and reload the model.

        Args:
            temperature: New temperature value (0.0-1.0)

        Returns:
            Reloaded model with new temperature
        """
        if not 0.0 <= temperature <= 1.0:
            raise ValueError("Temperature must be between 0.0 and 1.0")

        self.temperature = temperature
        return self.reload_model()


def get_default_model(temperature: float = 0.7):
    """
    Get default model instance quickly.

    Args:
        temperature: Temperature setting for the model (default: 0.7)

    Returns:
        Model selected by LLMLoader from the environment or the defaults
    """
    loader = LLMLoader(temperature=temperature)
    return loader.get_model()


if __name__ == "__main__":
    llm_loader = LLMLoader()
    model = llm_loader.get_model()
    print(f"Loaded model: {llm_loader.model_name} from {llm_loader.model_provider}")
