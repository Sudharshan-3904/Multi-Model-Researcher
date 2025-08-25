class AnalyzerAgent:
    def analyze(self, data, query, model_interface, model_name):
        print(f"[analyzer_agent.py] analyze called with query={query}, model_name={model_name}")
        # For demo: rank by citations and summarize
        sorted_data = sorted(data, key=lambda x: x['citations'], reverse=True)
        summary = '\n'.join([f"{item['title']} (Citations: {item['citations']})" for item in sorted_data])
        print(f"[analyzer_agent.py] Data summary: {summary}")
        # Interact with selected model for further analysis
        prompt = f"Summarize the following papers for the query '{query}':\n{summary}"
        model_response = model_interface.run_model(model_name, prompt)
        print(f"[analyzer_agent.py] Model response: {model_response}")
        return f"Top Papers:\n{summary}\n\nModel Analysis:\n{model_response}"
