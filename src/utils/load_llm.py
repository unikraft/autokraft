import getpass
import os
from typing import Optional
from langchain.chat_models import init_chat_model


class LLMLoader:
    """
    A class to handle LLM model loading and configuration.
    """
    
    def __init__(self, model_name: str = "llama-3.3-70b-versatile", model_provider: str = "groq", temperature: float = 0.05):
        """
        Initialize LLMLoader.
        
        Args:
            model_name: Name of the model to load (default: "llama-3.1-8b-instant")
            model_provider: Provider for the model (default: "groq")
            temperature: Controls randomness in responses (0.0-1.0, default: 0.7)
        """
        self.model_name = model_name
        self.model_provider = model_provider
        self.temperature = temperature
        self._model = None
        self._setup_api_key()
    
    def _setup_api_key(self) -> None:
        """
        Setup API key for the model provider.
        """
        if self.model_provider.lower() == "groq":
            if not os.environ.get("GROQ_API_KEY"):
                os.environ["GROQ_API_KEY"] = getpass.getpass("Enter API key for Groq: ")
        # Add other providers as needed
    
    def get_model(self):
        """
        Get the initialized model instance.
        
        Returns:
            Initialized chat model
        """
        if self._model is None:
            self._model = init_chat_model(
                self.model_name, 
                model_provider=self.model_provider,
                temperature=self.temperature
            )
        
        return self._model
    
    def reload_model(self):
        """
        Reload the model (useful if you want to reinitialize).
        
        Returns:
            Newly initialized chat model
        """
        self._model = init_chat_model(
            self.model_name, 
            model_provider=self.model_provider,
            temperature=self.temperature
        )
        return self._model
    
    def change_model(self, model_name: str, model_provider: Optional[str] = None, temperature: Optional[float] = None):
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
        Default Groq Llama3 model
    """
    loader = LLMLoader(temperature=temperature)
    return loader.get_model()


if __name__ == "__main__":
    llm_loader = LLMLoader()
    model = llm_loader.get_model()
    print(f"Loaded model: {llm_loader.model_name} from {llm_loader.model_provider}")
