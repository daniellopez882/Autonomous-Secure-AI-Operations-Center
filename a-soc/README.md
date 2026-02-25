# Autonomous Secure AI Operations Center (A-SOC) 🛡️

**A-SOC** is a next-generation security platform that leverages **Agentic AI** to autonomously detect, investigate, and remediate threats in cloud environments.

## 🚀 Key Features

*   **🕵️‍♂️ Multi-Agent Architecture**: Specialized agents for Telemetry, Detection, Forensics, Response, and Compliance.
*   **🧠 LLM-Powered Analysis**: Beyond static rules, using LLMs to contextualize alerts.
*   **⚡ Real-Time Streaming**: WebSocket-based event feed for live dashboard updates.
*   **🛑 Human-in-the-Loop**: Governance for high-risk actions like IAM revocation.
*   **🕸️ Blast Radius Visualization**: Interactive attack path and resource graph.
*   **📜 Immutable Audit Trail**: Cryptographically logged decisions for compliance.

---

## 🛠️ Tech Stack

### **Backend (Python)**
*   **Framework**: FastAPI
*   **Orchestration**: LangGraph
*   **AI/LLM**: OpenAI / Anthropic (via LangChain)
*   **Policy Engine**: Open Policy Agent (OPA)
*   **Database**: PostgreSQL & Redis

### **Frontend (TypeScript)**
*   **Framework**: Next.js 14
*   **Styling**: Tailwind CSS
*   **Visualization**: React Flow

---

## ⚙️ Setup & Installation

### **1. Clone the Repository**
```bash
git clone https://github.com/daniellopez882/Autonomous-Secure-AI-Operations-Center.git
cd Autonomous-Secure-AI-Operations-Center/a-soc
```

### **2. Backend Setup**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Start the API
python -m uvicorn api:app --host 0.0.0.0 --port 9001 --reload
```

### **3. Frontend Setup**
```bash
cd dashboard
npm install
npm run dev
```

---

## 📫 Contact

**Daniel Lopez**  
Email: [daniellopezorta39@gmail.com](mailto:daniellopezorta39@gmail.com)  
GitHub: [@daniellopez882](https://github.com/daniellopez882)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
