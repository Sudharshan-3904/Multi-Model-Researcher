import requests

class ModelInterface:
    def __init__(self):
        # For demo: hardcode available models
        self.models = ["Ollama", "LM Studio"]

    def list_models(self):
        return self.models

    def run_model(self, model_name, prompt):
        # Demo: mock response
        if model_name == "Ollama":
            # Example: call Ollama local server
            # resp = requests.post("http://localhost:11434/api/generate", json={"prompt": prompt})
            # return resp.json().get("response", "")
            return f"[Ollama] Response to: {prompt}"
        elif model_name == "LM Studio":
            # Example: call LM Studio API
            # resp = requests.post("http://localhost:1234/v1/completions", json={"prompt": prompt})
            # return resp.json().get("choices", [{}])[0].get("text", "")
            return f"[LM Studio] Response to: {prompt}"
        else:
            return "Model not supported."
