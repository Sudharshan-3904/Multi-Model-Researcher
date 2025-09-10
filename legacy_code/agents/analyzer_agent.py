import requests

class AnalyzerAgent:
    async def analyze(self, data, query, model_interface, model_name, model_provider):
        print(f"[analyzer_agent.py] analyze called with query={query}, model_name={model_name}")
        from bs4 import BeautifulSoup

        summary = ""

        for item in data:
            title = item.get('title', 'No Title')
            citations = item.get('citations', 0)
            url = item.get('url', '')

            summary += f"- {title} (Citations: {citations})\n"
            try:
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    html = response.text
                    soup = BeautifulSoup(html, 'html.parser')
                    text = soup.get_text(separator=' ', strip=True)
                    prompt = f"Summarize the following article in a short paragraph for the query: '{query}'.\n\nArticle:\n{text[:5000]}"
                    article_summary = await model_interface.summarize(prompt, model_name=model_name, model_provider=model_provider)
                    summary += article_summary.strip() + "\n\n"
                else:
                    summary += "[Failed to retrieve article]\n\n"
            except Exception as e:
                summary += f"[Error retrieving or summarizing article: {e}]\n\n"

        print(f"[analyzer_agent.py] Summary Generated. Returning Report.")
        return summary if summary else "No data to analyze."
