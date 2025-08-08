import requests

class DataAgent:
    def collect(self, query):
        # For demo: fetch arXiv papers via API (mocked)
        # In real: use plugins for PDF, HTML, API, etc.
        # Here, just return a mock list
        return [
            {'title': 'Quantum Finance Paper 1', 'citations': 120, 'url': 'https://arxiv.org/abs/1234.5678'},
            {'title': 'Quantum Finance Paper 2', 'citations': 95, 'url': 'https://arxiv.org/abs/2345.6789'}
        ]
