<div align="center">

# 🛡️ Autonomous Secure AI Operations Center
### **A-SOC** — Next-Generation Agentic Cybersecurity Platform

<br/>

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agent%20Orchestration-6B3FA0?style=for-the-badge&logo=langchain&logoColor=white)](https://www.langchain.com/langgraph)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](./LICENSE)

<br/>

> *"Most security tools alert you. A-SOC acts."*

**A-SOC** is a cloud-native, AI-native security operations platform that autonomously detects, investigates, and remediates threats using a coordinated fleet of specialized LLM-powered agents — with human governance built in.

[**🚀 Quick Start**](#️-installation--setup) · [**🏗️ Architecture**](#️-architecture) · [**🎮 Demo**](#-usage) · [**🚢 Deploy**](#-deployment) · [**📫 Contact**](#-contact)

---

</div>

## 📌 Overview

Traditional Security Operations Centers (SOCs) are drowning in alerts. A-SOC leverages a fleet of specialized AI agents to bridge the gap between detection and remediation, reducing MTTR and alert fatigue.

- **Multi-Agent Orchestration**: Specialized agents for Telemetry, Detection, Forensics, and Response.
- **LLM-Powered Reasoning**: Contextual analysis of alerts to eliminate false positives.
- **Real-Time Visibility**: Live WebSocket-driven dashboard for immediate threat awareness.
- **Human-in-the-Loop**: Seamless governance for high-stakes remediation actions.

---

## 🚀 Key Features

| Feature | Description |
|---|---|
| **🕵️ Multi-Agent Architecture** | Telemetry, Detection, Forensics, Response, and Compliance agents working in concert. |
| **🧠 LLM-Powered Analysis** | Contextual reasoning that understands the *why* behind security anomalies. |
| **⚡ Real-Time Streaming** | Live threat telemetry delivered via high-performance WebSockets. |
| **🛑 Human Governance** | Explicit authorization required for high-risk IAM and network changes. |
| **🕸️ Blast Radius** | Interactive visualization of attack paths and affected infrastructure. |
| **📜 Continuous Compliance** | Automated mapping of incidents to SOC2 and ISO 27001 frameworks. |
| **👮 Policy-as-Code** | OPA-driven governance ensures all actions align with corporate policy. |

---

## 🛠️ Tech Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python, FastAPI, LangGraph, LangChain, OPA (Rego) |
| **Frontend** | Next.js 14, Tailwind CSS, React Flow, WebSockets |
| **Data/Ops** | PostgreSQL, Redis, Docker Compose |

---

## 🏗️ Architecture

A-SOC utilizes a Hub-and-Spoke model where a central Supervisor agent coordinates specialist activities and enforces OPA-defined security policies.

```
┌─────────────────────────────────────────────────────────────────┐
│                       A-SOC Agent Platform                      │
│                                                                 │
│  ┌─────────────┐    ┌────────────────────────────────────────┐  │
│  │  Log Sources │    │            Agent Fleet                  │  │
│  │─────────────│    │                                        │  │
│  │ CloudTrail  │───▶│  ① TELEMETRY AGENT                     │  │
│  │ VPC Flow    │    │     Ingests & normalizes raw log data   │  │
│  │ K8s Audit   │    │              │                         │  │
│  │             │    │              ▼                         │  │
│  └─────────────┘    │  ② DETECTION AGENT                     │  │
│                     │     Analyzes anomalies                  │  │
│                     │     Assigns Risk Score (0–100)          │  │
│                     │              │                         │  │
│                     │              ▼                         │  │
│                     │  ③ SUPERVISOR AGENT  ◀── OPA Policy    │  │
│                     │     ┌────────────────────┐             │  │
│                     │     │ Risk < 70?          │             │  │
│                     │     │ YES → Auto-remediate│             │  │
│                     │     │ NO  → Human Approval│             │  │
│                     │     └────────────────────┘             │  │
│                     │          │           │                 │  │
│                     │          ▼           ▼                 │  │
│                     │  ④ FORENSICS   Human Dashboard         │  │
│                     │     AGENT      (Blast Radius +         │  │
│                     │     (Attack     Authorize Modal)        │  │
│                     │      Graph)         │                  │  │
│                     │          │          │                  │  │
│                     │          └────┬─────┘                  │  │
│                     │               ▼                        │  │
│                     │  ⑤ RESPONSE AGENT                     │  │
│                     │     Executes remediation               │  │
│                     │     (Block IP, Revoke Keys, etc.)      │  │
│                     │               │                        │  │
│                     │               ▼                        │  │
│                     │  ⑥ COMPLIANCE AGENT                   │  │
│                     │     Maps incident → SOC2 / ISO 27001  │  │
│                     │     Logs cryptographic evidence        │  │
│                     └────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Agent Responsibilities

| Agent | Role |
|---|---|
| **① Telemetry Agent** | Ingests and normalizes logs from CloudTrail, VPC Flow Logs, and Kubernetes Audit logs into a unified event schema. |
| **② Detection Agent** | Applies LLM-powered reasoning to identify anomalies, correlate events, and assign a continuous **Risk Score (0–100)**. |
| **③ Supervisor Agent** | The orchestrator. Evaluates every detection against OPA policies and routes: `score < 70` → auto-remediate, `score ≥ 70` → escalate to human. |
| **④ Forensics Agent** | Constructs the **Blast Radius** — a real-time graph of which resources have been touched, compromised, or are at risk. |
| **⑤ Response Agent** | Executes the approved remediation playbook. Actions include IP blocking, credential revocation, and quarantine. |
| **⑥ Compliance Agent** | Automatically maps every incident and action to compliance frameworks (SOC2, ISO 27001) and writes immutable, signed audit records. |

---

## 🔐 Security Design Principles

A-SOC is designed with a **defense-in-depth** philosophy applied to the platform itself:

- **Principle of Least Privilege**: Each agent only has the tool-access it needs. The Compliance Agent cannot execute remediations.
- **Immutable Audit Log**: All LLM reasoning chains and tool invocations are stored with cryptographic signatures, making them tamper-evident.
- **Human-in-the-Loop for High-Stakes Actions**: No IAM key revocation, firewall rule change, or instance termination can happen without explicit operator authorization. The system is designed to make humans the last line of defense, not the bottleneck.
- **Policy-as-Code via OPA**: Governance is not hardcoded in Python. It lives in versioned, reviewable **Rego policy files**, making it auditable and easy to update.
- **Zero Trust Agent Communication**: Inter-agent communication is mediated by the LangGraph state machine, with no direct side-channel communication between agents.

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker & Docker Compose
- OpenAI or Anthropic API Key

### Quick Start with Docker

```bash
# 1. Clone the repository
git clone https://github.com/daniellopez882/Autonomous-Secure-AI-Operations-Center.git
cd Autonomous-Secure-AI-Operations-Center/a-soc

# 2. Configure environment
cp .env.example .env
# Edit .env and add your API keys

# 3. Launch the stack
docker-compose up -d
```

- **Dashboard**: `http://localhost:3000`
- **API Docs**: `http://localhost:9001/docs`

---

### Option B: Manual Setup

#### Step 1 — Clone the Repository
```bash
git clone https://github.com/daniellopez882/Autonomous-Secure-AI-Operations-Center.git
cd Autonomous-Secure-AI-Operations-Center/a-soc
```

#### Step 2 — Backend Setup
```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate       # macOS/Linux
# venv\Scripts\activate        # Windows

# Install backend dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env — at minimum, set OPENAI_API_KEY

# Start the API server on port 9001
python -m uvicorn api:app --host 0.0.0.0 --port 9001 --reload
```

#### Step 3 — Frontend Setup
```bash
# From the project root, navigate to the dashboard
cd dashboard

# Install frontend dependencies
npm install

# Start the development server (port 3000)
npm run dev
```

#### Step 4 — Configure Environment Variables

Copy `.env.example` to `.env` and populate the following:

```bash
# --- LLM Provider (choose one) ---
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...

# --- Database ---
DATABASE_URL=postgresql://user:password@localhost:5432/asoc
REDIS_URL=redis://localhost:6379

# --- Security ---
SECRET_KEY=your-super-secret-key-here

# --- OPA Policy Engine ---
OPA_URL=http://localhost:8181
```

---

## 🎮 Usage

Once both backend and frontend are running:

1.  **Open the Dashboard** → Navigate to `http://localhost:3000`
2.  **Start a Simulation** → Click the **"Start Simulation"** button in the top right corner
3.  **Watch the Agent Fleet** → Observe the real-time log stream as each agent processes incoming threat telemetry
4.  **Review Detections** → See risk scores assigned and watch the Blast Radius graph build dynamically
5.  **Authorize a High-Risk Action** → When the **"High Risk Action Proposed"** modal appears, review the full context and Blast Radius, then click **"Authorize"** to execute the remediation

---

## 🚢 Deployment

### Production Deployment

For production environments, see the detailed [**DEPLOYMENT.md**](./DEPLOYMENT.md) guide which covers:

- **AWS ECS (Fargate)**: Scalable serverless container deployment
- **Kubernetes**: Full Helm chart manifests in [`k8s/`](./k8s/)
- **Vercel**: Frontend-only serverless deployment
- **Monitoring**: Prometheus + Grafana stack integration
- **Security Hardening**: TLS, secrets management, WAF configuration

### Cloud Platform Summary

| Platform | Backend | Frontend | Guide |
|---|---|---|---|
| **AWS ECS Fargate** | ✅ Supported | ✅ S3 + CloudFront | [DEPLOYMENT.md#aws](./DEPLOYMENT.md#aws-ecs-deployment) |
| **Kubernetes** | ✅ Any cluster | ✅ Ingress | [k8s/](./k8s/) |
| **Docker Compose** | ✅ Self-hosted | ✅ Included | `docker-compose up -d` |
| **Vercel** | ❌ | ✅ Serverless | [DEPLOYMENT.md#vercel](./DEPLOYMENT.md#vercel-dashboard-only) |

---

## 🗺️ Roadmap

- [x] Initial Multi-Agent Framework
- [x] Real-time WebSocket event streaming
- [x] Blast Radius visualization engine
- [ ] Native AWS integration (Boto3)
- [ ] Slack/Teams reporting integration
- [ ] On-prem deployment support (Llama 3)

---

## 🤝 Contributing

We welcome contributions to the A-SOC platform! Please see our contributing guidelines for details on how to get started.

---

## 📫 Contact

**Daniel Lopez**  
Email: [daniellopezorta39@gmail.com](mailto:daniellopezorta39@gmail.com)  
GitHub: [@daniellopez882](https://github.com/daniellopez882)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

<div align="center">

Built with ❤️ by **daniellopez882**

</div>
