import requests
import json
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

class ModelDetector:
    def __init__(self):
        self.ollama_url = "http://localhost:11434/api"
        self.lmstudio_url = "http://localhost:1234/v1"

    def detect_available_models(self) -> Tuple[bool, bool, List[str], List[str]]:
        """
        Detect available models from both Ollama and LM Studio.
        Returns: (ollama_available, lmstudio_available, ollama_models, lmstudio_models)
        """
        ollama_available = False
        lmstudio_available = False
        ollama_models = []
        lmstudio_models = []

        # Check Ollama
        try:
            response = requests.get(f"{self.ollama_url}/tags")
            if response.status_code == 200:
                ollama_available = True
                models_data = response.json()
                ollama_models = [model['name'] for model in models_data.get('models', [])]
                logger.info(f"Found Ollama models: {ollama_models}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Ollama not available: {str(e)}")

        # Check LM Studio
        try:
            response = requests.get(f"{self.lmstudio_url}/models")
            if response.status_code == 200:
                lmstudio_available = True
                models_data = response.json()
                lmstudio_models = [model['id'] for model in models_data.get('data', [])]
                logger.info(f"Found LM Studio models: {lmstudio_models}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"LM Studio not available: {str(e)}")

        return ollama_available, lmstudio_available, ollama_models, lmstudio_models

    def get_default_model(self, host_type: str, available_models: List[str]) -> str:
        """Get the default model based on availability and host type."""
        if not available_models:
            return ""

        # Preferred models in order of preference
        preferred_models = {
            "ollama": ["mistral", "llama2", "codellama", "phi"],
            "lmstudio": [
                "TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
                "TheBloke/Llama-2-7B-Chat-GGUF",
                "TheBloke/Phi-2-GGUF"
            ]
        }

        # Try to find the first preferred model that's available
        for model in preferred_models.get(host_type, []):
            if model in available_models:
                return model

        # If no preferred model is available, return the first available model
        return available_models[0] 