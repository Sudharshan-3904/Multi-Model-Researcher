import requests

class DataAgent:
    def collect(self, query):
        """
        Searches arXiv for papers matching the query and returns a list of dicts with title, citations (mocked), and url.
        """
        print(f"[data_agent.py] collect called with query={query}")
        data = []
        try:
            url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results=3"
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(resp.text)
                for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                    title = entry.find('{http://www.w3.org/2005/Atom}title').text.strip()
                    link = entry.find('{http://www.w3.org/2005/Atom}id').text.strip()
                    import random
                    citations = random.randint(50, 200)
                    data.append({'title': title, 'citations': citations, 'url': link})
            else:
                print(f"[data_agent.py] arXiv API error: {resp.status_code}")
        except Exception as e:
            print(f"[data_agent.py] Exception: {e}")
        print(f"[data_agent.py] Returning data: {data}")
        return data
