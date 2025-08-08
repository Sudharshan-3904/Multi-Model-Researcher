class AnalyzerAgent:
    def analyze(self, data, query, model_interface, model_name):
        # For demo: rank by citations and summarize
        sorted_data = sorted(data, key=lambda x: x['citations'], reverse=True)
        summary = '\n'.join([f"{item['title']} (Citations: {item['citations']})" for item in sorted_data])
        # Interact with selected model for further analysis
        prompt = f"Summarize the following papers for the query '{query}':\n{summary}"
        model_response = model_interface.run_model(model_name, prompt)
        return f"Top Papers:\n{summary}\n\nModel Analysis:\n{model_response}"
