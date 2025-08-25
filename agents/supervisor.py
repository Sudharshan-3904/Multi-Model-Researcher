from email import message
from typing import TypedDict
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from langgraph.prebuilt import ToolNdoe
from langgraph import StateGraph, START, END

from agents.data_agent import DataAgent
from agents.analyzer_agent import AnalyzerAgent
from storage.storage import Storage
from storage.audit import AuditLogger

from models.model_interface import ModelInterface

class SupervisorAgent:
    def __init__(self):
        print("[supervisor.py] SupervisorAgent initialized")
        self.data_agent = DataAgent()
        self.analyzer_agent = AnalyzerAgent()
        self.storage = Storage()
        self.audit = AuditLogger()
        self.model_interface = ModelInterface()

    async def handle_request(self, query, user, model_provider="Ollama", model=None):
        print(f"[supervisor.py] handle_request called with query={query}, user={user}, model_provider={model_provider}, model={model}")
        self.audit.log_action(user, 'request', {'query': query, 'model': model_provider})
        # Step 1: Collect data
        raw_data = self.data_agent.collect(query)
        self.audit.log_action('DataAgent', 'collected', {'items': len(raw_data)})
        # Step 2: Analyze data (pass model interface, model name, and provider)
        report = await self.analyzer_agent.analyze(raw_data, query, self.model_interface, model_name=model, model_provider=model_provider)
        self.audit.log_action('AnalyzerAgent', 'analyzed')
        # Step 3: Store results
        self.storage.save_report(query, report)
        self.audit.log_action('Supervisor', 'completed', {'query': query})
        print(f"[supervisor.py] handle_request returning report (first 100 chars): {report[:100]}")
        return report

class ChatState(TypedDict):
    message: list
    query: str

llm = init_chat_model(model=)
