from email import message
from typing import TypedDict

from agents.data_collector import DataAgent
from agents.summarizer import Summarizer
from agents.analyzer import Analyzer
from agents.formatter import Formatter
from agents.report_maker import ReportMaker
from storage.storage import Storage
from storage.audit import AuditLogger
from models.model_interface import ModelInterface

class SupervisorAgent:
    def __init__(self):
        print("[supervisor.py] SupervisorAgent initialized")
        self.data_agent = DataAgent()
        self.storage = Storage()
        self.audit = AuditLogger()
        self.model_interface = ModelInterface()
        self.analyzer = Analyzer()
        self.formatter = Formatter()
        self.report_maker = ReportMaker()

    async def handle_request(self, query, user, model_provider="Ollama", model=None, chat_title="Untitled"):
        print(f"[supervisor.py] handle_request called with query={query}, user={user}, model_provider={model_provider}, model={model}, chat_title={chat_title}")
        self.audit.log_action(user, 'request', {'query': query, 'model': model_provider, 'chat_title': chat_title})
        # Step 1: Data Collector
        raw_data = self.data_agent.collect(query)
        self.audit.log_action('DataAgent', 'collected', {'items': len(raw_data)})

        # Step 2: Summarizer
        summarizer = Summarizer(self.model_interface, model, model_provider)
        summaries = []
        import asyncio
        async def summarize_one(item):
            title = item.get('title', 'No Title')
            citations = item.get('citations', 0)
            url = item.get('url', '')
            import requests
            from bs4 import BeautifulSoup
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    html = response.text
                    soup = BeautifulSoup(html, 'html.parser')
                    text = soup.get_text(separator=' ', strip=True)
                    summary = await summarizer.summarize(text, query)
                    return f"- {title} (Citations: {citations})\n{summary}"
                else:
                    return f"- {title} (Citations: {citations})\n[Failed to retrieve article]"
            except Exception as e:
                return f"- {title} (Citations: {citations})\n[Error retrieving or summarizing article: {e}]"

        summaries = await asyncio.gather(*(summarize_one(item) for item in raw_data))
        # Step 3: Analyzer
        analysis = self.analyzer.analyze("\n\n".join(summaries))
        self.audit.log_action('Analyzer', 'analyzed')
        # Step 4: Formatter
        formatted = self.formatter.format(analysis, chat_title, query, model_provider, model)
        # Step 5: Report Maker
        report = self.report_maker.make_report(formatted)
        # Store results
        self.storage.save_report(query, report)
        self.audit.log_action('Supervisor', 'completed', {'query': query})
        print(f"[supervisor.py] handle_request returning report (first 100 chars): {report[:100]}")
        return report
