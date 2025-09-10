# **Multi-Model-Researcher: Modular Multi-Agent Research Automation**

---

## 🧠 **Architecture Overview (Implemented)**

### **High-Level Components (Actual Implementation)**

```diagram
┌─────────────────────────────┐
│      Streamlit Dashboard    │
│   (app.py, user interface)  │
└─────────────┬───────────────┘
        │
      ┌───────▼─────────┐
      │ FastAPI MCP API │
      │   (server.py)   │
      └───────┬─────────┘
        │
      ┌───────▼─────────────┐
      │  Agent Orchestrator │
      │ (research_handler.py)│
      └───────┬─────────────┘
        │
 ┌────────────▼─────────────┐
 │   Data Agent (arXiv, web)│
 └────────────┬─────────────┘
        │
 ┌────────────▼─────────────┐
 │ Analyzer/Summarizer Agent│
 └────────────┬─────────────┘
        │
 ┌────────────▼─────────────┐
 │ Formatter Agent          │
 └────────────┬─────────────┘
        │
 ┌────────────▼─────────────┐
 │ Storage & Audit (results,│
 │ audit.log, storage.py)   │
 └──────────────────────────┘
```

---

## 🧩 **Component Descriptions**

### 1. **Supervisor/Orchestrator (research_handler.py)**

- **Coordinates**: Data collection, analysis, formatting, and storage agents
- **Implements**: Iterative agent workflow using LangGraph and LangChain
- **Logs**: All actions via AuditLogger

---

### 2. **Data Agent (Collector, research_handler.py)**

- **Collects**: Papers and abstracts from arXiv (via requests, XML parsing)
- **Extensible**: Can be extended for other APIs and web sources

---

### 3. **Analyzer/Summarizer Agent (research_handler.py)**

- **Summarizes**: Each article using LLMs (Ollama, LM Studio)
- **Analyzes**: Synthesizes summaries into detailed reports
- **Formats**: Final output as markdown via Formatter agent

---

### 4. **Storage & Audit (src/storage/)**

- **Stores**: Results in `results/` as text files
- **Logs**: All agent actions in `audit.log`
- **Simple file-based**: Can be extended for DBs or cloud storage

---

### 5. **Authentication & Audit Layer (src/storage/audit.py)**

- **Tracks**: All research actions, queries, and agent steps
- **API keys**: Managed via `.env` and dashboard

---

## 🔒 **Security & Compliance (Implemented)**

| Feature           | Implementation Details                              |
| ----------------- | --------------------------------------------------- |
| Access Control    | API keys via .env, dashboard registration           |
| Audit Trail       | All actions logged in audit.log                     |
| Data Provenance   | Each step logged with timestamp and agent identity  |
| Confidentiality   | Local file storage, can be extended for encryption  |
| Sandbox Execution | Python process isolation, extensible for Docker/VMs |

---

## ⚙️ **Technology Stack (Actual)**

| Layer          | Tools/Frameworks                            |
| -------------- | ------------------------------------------- |
| MCP + Agents   | Python (FastAPI, LangChain, LangGraph)      |
| NLP & Analysis | Ollama, LM Studio, LangChain                |
| Storage        | Local file system, extensible for DBs       |
| Orchestration  | LangGraph, FastAPI                          |
| Interface      | Streamlit                                   |
| Auth/Audit     | File-based logging, .env API key management |

---

## 🔁 **Example Workflow (Actual)**

1. **User Request**: Enter query in Streamlit dashboard or POST to `/research` API
2. **Supervisor/Orchestrator**:

- Calls Data Agent to fetch papers from arXiv
- Summarizes each article using LLM (Ollama/LM Studio)
- Analyzes and synthesizes summaries into a detailed report
- Formats report as markdown
- Stores result and logs all actions

3. **User receives**: Well-structured, auditable document

---

## ✅ **Benefits (Actual)**

- **Scalability**: Modular agent design, easy to extend
- **Auditability**: All steps logged, results saved
- **Modularity**: Agents and providers can be upgraded independently
- **Security**: API key management, audit trail, local storage

---
