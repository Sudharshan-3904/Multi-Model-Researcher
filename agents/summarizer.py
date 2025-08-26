class Summarizer:
    def __init__(self, model_interface, model_name, model_provider):
        self.model_interface = model_interface
        self.model_name = model_name
        self.model_provider = model_provider

    def summarize(self, text, query):
        prompt = f"Summarize the following article in a short paragraph for the query: '{query}'.\n\nArticle:\n{text}"
        return self.model_interface.summarize(prompt, model_name=self.model_name, model_provider=self.model_provider)
