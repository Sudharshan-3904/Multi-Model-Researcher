# Multi-Model-Researcher

## 🧠 Overview

Multi-Model-Researcher is a modular, multi-agent research automation platform designed for deep analysis, summarization, and reporting using multiple LLM providers. It orchestrates agents to collect, analyze, and synthesize information from scholarly sources and web APIs, producing well-structured, auditable research reports.

---

## 🚀 Features

- **Agent-based architecture**: Supervisor, Data Collector, Analyzer, Formatter, and Storage agents
- **Multi-provider LLM support**: Integrates with Ollama, LM Studio, and more
- **Streamlit dashboard**: User-friendly interface for research queries and provider management
- **FastAPI backend**: MCP server for agent orchestration and API endpoints
- **Audit logging**: Tracks all actions for compliance and traceability
- **Pluggable data sources**: Supports arXiv, web scraping, and custom APIs
- **Secure storage**: Results and audit logs saved for review and compliance

---

## 🏗️ Architecture

See `Architecture.md` for a detailed diagram and component breakdown.

**Main Components:**

- **Supervisor Agent**: Orchestrates the workflow, manages agent interactions
- **Data Agent**: Collects raw data from APIs (e.g., arXiv)
- **Analyzer Agent**: Summarizes and synthesizes collected data using LLMs
- **Formatter Agent**: Formats analysis into structured markdown reports
- **Storage & Audit**: Persists results and logs all actions

---

## 📦 Directory Structure

```
Multi-Model-Researcher/
├── app.py                # Streamlit UI
├── server.py             # FastAPI MCP server
├── src/
│   ├── research_handler.py   # Main agent pipeline & orchestration
│   └── storage/
│       ├── storage.py        # Result storage
│       └── audit.py          # Audit logging
├── models/
│   ├── model_interface.py    # LLM provider/model abstraction
│   └── provider_utils.py     # Provider/model discovery
├── extras/               # Experimental/combined model code
├── legacy_code/          # Previous agent implementations
├── logs/                 # Debug and audit logs
├── results/              # Saved research reports
├── requirements.txt      # Python dependencies
├── pyproject.toml        # Project metadata
├── Architecture.md       # System architecture & workflow
└── README.md             # Project documentation
```

---

## ⚡ Quickstart

1. **Install dependencies**

    ```bash
    pip install -r requirements.txt

 ```

2. **Start MCP server**
 ```bash
 uvicorn server:app --reload
 ```

3. **Launch Streamlit dashboard**

 ```bash
 streamlit run app.py
 ```

4. **Query research**

- Use the dashboard or POST to `/research` endpoint:

   ```bash
   curl -X POST http://localhost:8000/research -H "Content-Type: application/json" -d '{"query": "Quantum computing", "user": "alice", "model_provider": "Ollama", "model": "llama2"}'
   ```

---

## 🛠️ Technology Stack

- Python 3.12+
- FastAPI, Streamlit, LangChain, LangGraph
- Ollama, LM Studio (local LLMs)
- BeautifulSoup4, Requests

---

## 🔒 Security & Audit

- All agent actions are logged in `audit.log`
- Reports are saved in `results/`
- API keys managed via `.env` (see dashboard)

---

## 📚 Example Workflow

1. User submits a research query (e.g., "Quantum finance roadmap")
2. Supervisor agent orchestrates:

- Data agent collects papers from arXiv
- Analyzer agent summarizes and ranks articles
- Formatter agent creates a markdown report
- Storage agent saves the report and logs actions

3. User receives a well-structured, auditable document

---

## 📝 Contributing

Pull requests and issues are welcome! See `Architecture.md` for design guidelines.

---

## 📄 License

MIT License
