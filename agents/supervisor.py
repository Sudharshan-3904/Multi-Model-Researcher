from agents.data_agent import DataAgent
from agents.analyzer_agent import AnalyzerAgent
from storage.storage import Storage
from storage.audit import AuditLogger

from models.model_interface import ModelInterface

class SupervisorAgent:
    def __init__(self):
        self.data_agent = DataAgent()
        self.analyzer_agent = AnalyzerAgent()
        self.storage = Storage()
        self.audit = AuditLogger()
        self.model_interface = ModelInterface()

    def handle_request(self, query, user, model="Ollama"):
        self.audit.log_action(user, 'request', {'query': query, 'model': model})
        # Step 1: Collect data
        raw_data = self.data_agent.collect(query)
        self.audit.log_action('DataAgent', 'collected', {'items': len(raw_data)})
        # Step 2: Analyze data (pass model interface)
        report = self.analyzer_agent.analyze(raw_data, query, self.model_interface, model)
        self.audit.log_action('AnalyzerAgent', 'analyzed', {'summary': report[:100]})
        # Step 3: Store results
        self.storage.save_report(query, report)
        self.audit.log_action('Supervisor', 'completed', {'query': query})
        return report
