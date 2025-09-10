from urllib import response
import requests
import json
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

class ModelDetector:
    def __init__(self):
        self.ollama_url = "http://localhost:11434/api"
        self.lmstudio_url = "http://localhost:1234/v1"
        print("[ModelDetector] Initialized with Ollama and LM Studio URLs")

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
                print(f"[ModelDetector] Found Ollama models: {ollama_models}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Ollama not available: {str(e)}")
            print(f"[ModelDetector] Ollama not available: {str(e)}")

        # Check LM Studio
        try:
            response = requests.get(f"{self.lmstudio_url}/models")
            if response.status_code == 200:
                lmstudio_available = True
                models_data = response.json()
                lmstudio_models = [model['id'] for model in models_data.get('data', [])]
                logger.info(f"Found LM Studio models: {lmstudio_models}")
                print(f"[ModelDetector] Found LM Studio models: {lmstudio_models}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"LM Studio not available: {str(e)}")
            print(f"[ModelDetector] LM Studio not available: {str(e)}")

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

class ModelInterface:
    def __init__(self):
        print("[ModelInterface] Initialized")
        self.model_providers = ["Ollama", "LM Studio"]
        self.detector = ModelDetector()

    def get_ollama_models(self):
        print("[ModelInterface] get_ollama_models called")
        ollama_available, _, ollama_models, _ = self.detector.detect_available_models()
        if ollama_available:
            return ollama_models
        return []

    def get_lmStudio_models(self):
        print("[ModelInterface] get_lmStudio_models called")
        _, lmstudio_available, _, lmstudio_models = self.detector.detect_available_models()
        if lmstudio_available:
            return lmstudio_models
        return []

    def list_models(self, provider: str = "Ollama") -> list:
        print(f"[ModelInterface] list_models called for provider: {provider}")
        if provider == 'Ollama':
            return self.get_ollama_models()
        elif provider == 'LM Studio':
            return self.get_lmStudio_models()
        else:
            return []


    async def run_model(self, model_name, prompt, model_provider="LM_Studio"):
        print(f"[ModelInterface] run_model called for provider: {model_provider}, model: {model_name}")
        response_text = ""
        try:
            if model_provider.lower() == "ollama":
                url = f"http://localhost:11434/api/generate"
                payload = {"model": model_name, "prompt": prompt}
                resp = requests.post(url, json=payload, timeout=30)
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        with open('.\\logs\\debug_response_ollama.json', 'w') as f:
                            json.dump(data, f, indent=2)
                        response_text = data.get("response", "")
                    except Exception as e:
                        response_text = f"[Ollama JSON Error] {e}"
                else:
                    response_text = f"[Ollama Error] Status: {resp.status_code}"
            elif model_provider.lower() == "lm studio" or model_provider.lower() == "lmstudio" or model_provider.lower() == "lm_studio":
                url = f"http://localhost:1234/v1/completions"
                payload = {"model": model_name, "prompt": prompt, "max_tokens": 20000}
                resp = requests.post(url, json=payload, timeout=30)
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        with open('.\\logs\\debug_response_lm_studio.json', 'w') as f:
                            json.dump(data, f, indent=2)
                        # OpenAI compatible: choices[0].text
                        response_text = data.get("choices", [{}])[0].get("text", "")
                    except Exception as e:
                        response_text = f"[LM Studio JSON Error] {e}"
                else:
                    response_text = f"[LM Studio Error] Status: {resp.status_code}"
            else:
                response_text = f"[Error] Unknown provider: {model_provider}"
        except Exception as e:
            response_text = f"[Exception] {e}"
        return response_text

    def summarize(self, prompt, model_name="", model_provider="Ollama"):
        print(f"[ModelInterface] summarize called with provider: {model_provider}, model: {model_name}")
        return self.run_model(model_name=model_name, prompt=prompt, model_provider=model_provider)
