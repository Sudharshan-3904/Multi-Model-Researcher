from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, START, END

import requests
from typing import TypedDict, Optional
import xml.etree.ElementTree as ET

from storage.storage import Storage
from storage.audit import AuditLogger


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
        resp = requests.get(url, timeout=100)
        if resp.status_code == 200:
            root = ET.fromstring(resp.text)
            for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                title = entry.find('{http://www.w3.org/2005/Atom}title').text.strip() # pyright: ignore[reportOptionalMemberAccess]
                link = entry.find('{http://www.w3.org/2005/Atom}id').text.strip() # type: ignore
                import random
                citations = random.randint(50, 200)
                abstract_elem = entry.find('{http://www.w3.org/2005/Atom}summary')
                abstract = abstract_elem.text.strip() if abstract_elem is not None else '' # type: ignore
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
    """
    Summarizes a list of articles one by one returning a list of summaries.
    """
    print(f"[research_handler.py]>Summarize >>> summarize_articles called with articles={articles}")

    audit.log_action('Research Handler', 'Summarized Articles')
    from models.model_interface import ModelInterface
    import requests
    from bs4 import BeautifulSoup
    import asyncio

    model_interface = ModelInterface()
    model_name = "llama2"
    model_provider = "Ollama"

    async def summarize_one(item):
        title = item.get('title', 'No Title')
        citations = item.get('citations', 0)
        url = item.get('url', '')
        abstract = item.get('abstract', '')
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                html = response.text
                soup = BeautifulSoup(html, 'html.parser')
                text = soup.get_text(separator=' ', strip=True)
                full_text = f"Abstract: {abstract}\n\n{text}"
                # Use raw_llm with system messages for summarization
                system_message = "You are a helpful research assistant. Summarize the following article in a descriptive paragraph of about 200 words."
                prompt = f"{system_message}\n\nArticle:\n{full_text}"
                summary = await model_interface.run_model(model_name, prompt, model_provider)
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
    """
    Analyzes a list of summaries and returns a detailed report.
    """
    print(f"[research_handler.py]>Analyzer >>> analyze_summaries called with summaries={summaries}")
    audit.log_action('Research Handler', 'Analyzed Summaries')
    # Use raw_llm to analyze all summaries and provide a detailed report
    system_message = SystemMessage(content="You are an expert research analyst. Analyze the following article summaries and provide a very detailed report, covering basic observations, key findings, trends, and advanced insights. Structure the report with clear sections and actionable recommendations.")
    summaries_text = "\n\n".join(summaries)
    prompt = f"{system_message.content}\n\nSummaries:\n{summaries_text}"
    # Use raw_llm (already initialized above)
    response = raw_llm.invoke([system_message, HumanMessage(content=prompt)])
    return response.content

# Steps 4 - Formatter
@tool
def format_report(analysis: str, chat_title: str, topic: str, provider: str, model: str):
    """
    Formats the analysis into a well-structured markdown report.
    """
    print(f"[research_handler.py]>Formatter >>> format_report called")
    audit.log_action('Research Handler', 'Formatted Report')
    # Use raw_llm to analyze all summaries and provide a detailed report
    system_message = SystemMessage(content="You are an expert research documnet creator. A very detailed analysis will be given and you need to format it into a well structure markdown format.")
    prompt = f"{system_message.content}\n\n Topics: {topic}\n Analysis:\n{analysis}"
    # Use raw_llm (already initialized above)
    response = raw_llm.invoke([system_message, HumanMessage(content=prompt)])
    # response_content = "".join(response.content)

    with open('.\\logs\\debug_formatted_report.md', 'w', encoding='utf-8') as f:
        f.write(str(response.content))

    return response.content

# Store Result - Save the generated report to be exported
@tool
def store_report(report: str, query: str):
    """
    Stores the final generated report in a file or database.
    """
    print(f"[research_handler.py]>Store >>> store_report called")
    storage = Storage()
    storage.save_report(query, report)
    audit.log_action('Research Handler', 'Report Stored')
    return True

class ChatState(TypedDict):
    message: list
    query: str


# LM Studio: Use direct API calls for main LLM
class LMStudioLLM:
    def __init__(self, model="openai/gpt-oss-20b", api_url="http://localhost:1234/v1/completions"):
        self.model = model
        self.api_url = api_url

    def invoke(self, messages):
        # messages: list of SystemMessage/HumanMessage
        prompt = "\n".join([m.content for m in messages])
        payload = {
            "model": self.model,
            "prompt": prompt,
            "max_tokens": 2048
        }
        resp = requests.post(self.api_url, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            return type('LLMResponse', (), {"content": data.get("choices", [{}])[0].get("text", "")})()
        else:
            return type('LLMResponse', (), {"content": f"[LM Studio Error] Status: {resp.status_code}"})()

llm = LMStudioLLM(model="llama-3.2-3b-instruct")

tool_node = ToolNode([collect, summarize_articles, analyze_summaries, format_report, store_report])

# raw_llm: Use Ollama via LangChain
raw_llm = init_chat_model(model="llama2", model_provider="ollama")

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

def run_research(query: str, user: str, model_provider: str = "Ollama", model: Optional[str] = None, chat_title: str = "Untitled"):
    print(f"[research_handler.py]>RunResearch >>> run_research called with query={query}, user={user}, model_provider={model_provider}, model={model}, chat_title={chat_title}")
    # initial_state: ChatState = {
    #     'messages': [HumanMessage(content=f"Please create a detailed research report on the topic: {query}")], # type: ignore
    #     'query': query
    # }
    # final_state = graph.run(initial_state) # type: ignore
    # final_messages = final_state['messages']
    # final_response = final_messages[-1] if final_messages else AIMessage(content="No response generated.")
    # print(f"[research_handler.py]>RunResearch >>> Final response: {final_response.content[:100]}")

    initial_state = {
        'messages': [
            HumanMessage(content=f"Create a roadmap for the topic: {query}.")
        ],
        'query': query
    }

    max_iterations = 20
    state = initial_state
    for i in range(max_iterations):
        # Decide which node to run next
        last_message = state['messages'][-1]
        if isinstance(last_message, AIMessage) and getattr(last_message, 'tool_calls', None):
            # If the LLM suggests tool calls, run tools_node
            state = tools_node(state)
        elif isinstance(last_message, ToolMessage):
            # If a tool was just called, run llm_node
            state = llm_node(state)
        else:
            # Otherwise, run llm_node to continue the conversation
            state = llm_node(state)

        # Check for a valid response
        if state and 'messages' in state and state['messages']:
            last_message = state['messages'][-1]
            if isinstance(last_message, AIMessage):
                return str(last_message.content)
            elif isinstance(last_message, ToolMessage):
                return str(last_message.content)
            else:
                return f"Agent response: {str(last_message.content)}"
        
        return "No valid response from the agent after iterations."

if __name__ == "__main__":
    # Example usage
    report = run_research(query="Quantum computing advancements", user="test_user", model_provider="Ollama", model="llama2", chat_title="Quantum Computing Report")
    print(report)