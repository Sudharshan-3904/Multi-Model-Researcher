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

        try:
            response = requests.get(f"{self.ollama_url}/tags")
            if response.status_code == 200:
                ollama_available = True
                models_data = response.json()
                print(models_data)
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
            "ollama": ["llama3.2"],
            "lmstudio": [
                "openai/gpt-oss-20b",
                "google/gemma-3-12b",
            ]
        }

        # Try to find the first preferred model that's available
        for model in preferred_models.get(host_type, []):
            if model in available_models:
                return model

        # If no preferred model is available, return the first available model
        return available_models[0] 
    

if __name__ == '__main__':
    detector = ModelDetector()
    ollama_available, lmstudio_available, ollama_models, lmstudio_models = detector.detect_available_models()

    print(f"Ollama Available: {ollama_available}, Models: {ollama_models}")
    print(f"LM Studio Available: {lmstudio_available}, Models: {lmstudio_models}")

    if ollama_available:
        default_ollama_model = detector.get_default_model("ollama", ollama_models)
        print(f"Default Ollama Model: {default_ollama_model}")

    if lmstudio_available:
        default_lmstudio_model = detector.get_default_model("lmstudio", lmstudio_models)
        print(f"Default LM Studio Model: {default_lmstudio_model}")