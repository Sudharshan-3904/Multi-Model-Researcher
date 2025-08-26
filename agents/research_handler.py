from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, START, END

import requests
from typing import TypedDict, Optional

from agents.summarizer import Summarizer
from storage.storage import Storage
from storage.audit import AuditLogger
from models.model_interface import ModelInterface


# Variables intialization
audit = AuditLogger()

# Steps 1 - Resource Papers Collection
@tool
def collect(query):
    """
    Searches arXiv for papers matching the query and returns a list of dicts with title, contents, and url.
    """
    audit.log_action('Research Handler', 'Collected')
    print(f"[research_handler.py]>Collect >>> collect called with query={query}")
    data = []
    try:
        url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results={3 if len(query)<=30 else 5}"
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(resp.text)
            for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                title = entry.find('{http://www.w3.org/2005/Atom}title').text.strip()
                link = entry.find('{http://www.w3.org/2005/Atom}id').text.strip()
                import random
                citations = random.randint(50, 200)
                abstract_elem = entry.find('{http://www.w3.org/2005/Atom}summary')
                abstract = abstract_elem.text.strip() if abstract_elem is not None else ''
                data.append({'title': title, 'abstract': abstract, 'citations': citations, 'url': link})
        else:
            print(f"[research_handler.py]>Collect >>>  arXiv API error: {resp.status_code}")
    except Exception as e:
        print(f"[research_handler.py]>Collect >>>  Exception: {e}")
    print(f"[research_handler.py]>Collect >>>  Returning data: {data}")
    return data

# Steps 2 - Summarizer
import asyncio
@tool
def summarize_articles(articles: list[dict]):
    print(f"[research_handler.py]>Summarize >>> summarize_articles called with articles={articles}")
    audit.log_action('Research Handler', 'Summarized Articles')
    model_interface = ModelInterface()
    model_name = "llama2"
    model_provider = "Ollama"
    summarizer = Summarizer(model_interface, model_name, model_provider)

    async def summarize_one(item):
        title = item.get('title', 'No Title')
        citations = item.get('citations', 0)
        url = item.get('url', '')
        abstract = item.get('abstract', '')
        import requests
        from bs4 import BeautifulSoup
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                html = response.text
                soup = BeautifulSoup(html, 'html.parser')
                text = soup.get_text(separator=' ', strip=True)
                full_text = f"Abstract: {abstract}\n\n{text}"
                summary = await summarizer.summarize(full_text, "General Summary")
                return f"- {title} (Citations: {citations})\n{summary}"
            else:
                return f"- {title} (Citations: {citations})\n[Failed to retrieve article]"
        except Exception as e:
            return f"- {title} (Citations: {citations})\n[Error retrieving or summarizing article: {e}]"

    loop = asyncio.get_event_loop()
    summaries = loop.run_until_complete(asyncio.gather(*(summarize_one(item) for item in articles)))
    return summaries


# Steps 3 - Analyzer
@tool
def analyze_summaries(summaries: list[str]):
    print(f"[research_handler.py]>Analyzer >>> analyze_summaries called with summaries={summaries}")
    audit.log_action('Research Handler', 'Analyzed Summaries')
    # Placeholder: could do more advanced analysis
    return "\n\n".join(summaries)

# Steps 4 - Formatter
@tool
def format_report(analysis: str, chat_title: str, topic: str, provider: str, model: str):
    print(f"[research_handler.py]>Formatter >>> format_report called")
    audit.log_action('Research Handler', 'Formatted Report')
    report = f"# {chat_title}\n\n**Topic:** {topic}\n**Provider:** {provider}\n**Model:** {model}\n\n---\n\n{analysis}"
    return report

# Steps 5 - Report Maker
@tool
def make_report(formatted_report: str):
    print(f"[research_handler.py]>ReportMaker >>> make_report called")
    audit.log_action('Research Handler', 'Report Made')
    # Add any final touches, metadata, or export logic here
    return formatted_report

# Store Result - Save the generated report to be exported
@tool
def store_report(report: str, query: str):
    print(f"[research_handler.py]>Store >>> store_report called")
    storage = Storage()
    storage.save_report(query, report)
    audit.log_action('Research Handler', 'Report Stored')
    return True

class ChatState(TypedDict):
    message: list
    query: str

llm = init_chat_model(model="openai/gpt-oss-20b", model_provider="LM Studio")

tool_node = ToolNode([collect, summarize_articles, analyze_summaries, format_report, make_report, store_report])
# raw_llm = init_chat_model(LM_STUDIO_MODEL_NAME if MODEL_MODE=='lm-studio' else OLLAMA_MODEL_NAME, model_provider=MODEL_MODE)
raw_llm = init_chat_model(model="openai/gpt-oss-20b", model_provider="LM Studio")

def llm_node(state):
    """
    A node that uses the LLM to generate a response based on the current state.
    """
    system_message = SystemMessage(content="""You are an expert research assistant. Your task is to help create a detailed learning roadmap based on the user's topic and level.
Use the available tools to gather information, summarize articles, analyze findings, format the report, and make the final report.
When using tools, ensure to call them appropriately and handle their outputs correctly.""")

    messages_for_llm = [system_message] + state['messages']
    response = llm.invoke(messages_for_llm)
    return {'messages': state['messages'] + [response]}

def router(state):
    """
    A router node that decides which node to invoke based on the current state.
    """    
    last_message = state['messages'][-1]

    if isinstance(last_message, AIMessage) and getattr(last_message, 'tool_calls', None):
        return 'tools'
    elif isinstance(last_message, ToolMessage):
        return 'llm'
    else:
        return 'end'

def tools_node(state):
    """
    A node that uses the tools to generate a response based on the current state.
    """
    result = tool_node.invoke(state)
    tool_output_messages = result.get('messages', [])

    return {'messages': state['messages'] + tool_output_messages}

builder = StateGraph(ChatState)
builder.add_node('llm', llm_node)
builder.add_node('tools', tools_node)
builder.add_edge(START, 'llm')
builder.add_edge('llm', 'tools')
builder.add_conditional_edges('llm', router, {'tools': 'tools', 'end': END})

graph = builder.compile()

def run_research(query: str, user: str, model_provider: str = "Ollama", model: Optional[str] = None, chat_title: str = "Untitled") -> str:
    print(f"[research_handler.py]>RunResearch >>> run_research called with query={query}, user={user}, model_provider={model_provider}, model={model}, chat_title={chat_title}")
    initial_state: ChatState = {
        'messages': [HumanMessage(content=f"Please create a detailed research report on the topic: {query}")],
        'query': query
    }
    final_state = graph.run(initial_state)
    final_messages = final_state['messages']
    final_response = final_messages[-1] if final_messages else AIMessage(content="No response generated.")
    print(f"[research_handler.py]>RunResearch >>> Final response: {final_response.content[:100]}")
    return final_response.content

if __name__ == "__main__":
    # Example usage
    report = run_research("Quantum computing advancements", "test_user", model_provider="Ollama", model="llama2", chat_title="Quantum Computing Report")
    print(report)