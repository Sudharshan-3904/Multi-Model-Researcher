
print("[provider_utils.py] Loading provider_utils module...")
import os
import requests
import ollama
from .model_interface import ModelInterface


MIObj = ModelInterface()
def get_env_providers():
    env_path = os.path.join(os.path.dirname(__file__), '../.env')
    print(f"[provider_utils.py] Reading providers from env: {env_path}")
    providers = {}
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip() and '=' in line:
                    k, v = line.strip().split('=', 1)
                    if k.endswith('_API_KEY'):
                        providers[k.replace('_API_KEY', '')] = v
    print(f"[provider_utils.py] Providers found: {providers}")
    # return providers
    return {'Ollama': '', 'LM Studio': ''} 

def query_all_models():
    print("[provider_utils.py] query_all_models called")
    providers = get_env_providers()
    all_models = {}
    # Always include LM Studio as an option
    provider_keys = set([p.upper() for p in providers.keys()])
    provider_keys.add('LM STUDIO')
    provider_keys.add('OLLAMA')

    all_models['LM STUDIO'] = MIObj.get_lmStudio_models()
    all_models['OLLAMA'] = MIObj.get_ollama_models()

    # for provider in provider_keys:
    #     print(f"[provider_utils.py] Querying models for provider: {provider}")
    #     if provider == 'OLLAMA':
    #         try:
    #             models_response = ollama.list()
    #             print(f"[provider_utils.py] ollama.list() response: {models_response}")
    #             if isinstance(models_response, dict) and 'models' in models_response:
    #                 all_models[provider] = [m['name'] for m in models_response['models']]
    #             else:
    #                 all_models[provider] = []
    #         except Exception as e:
    #             print(f"[provider_utils.py] Error fetching Ollama models: {e}")
    #             all_models[provider] = []
    #     elif provider == 'LM STUDIO':
    #         # Placeholder: In real use, query LM Studio API
    #         all_models[provider] = ['LMStudio-Model-1', 'LMStudio-Model-2']
    #     else:
    #         all_models[provider] = []
    #     print(f"[provider_utils.py] Models for {provider}: {all_models[provider]}")
    print(f"[provider_utils.py] All models: {all_models}")
    return all_models
