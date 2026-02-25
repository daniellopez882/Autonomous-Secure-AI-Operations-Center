# A-SOC System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                          │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          Next.js Dashboard (Port 3000)                   │  │
│  │  • Real-time Threat Feed (WebSocket)                     │  │
│  │  • Blast Radius Visualization                            │  │
│  │  • Human-in-the-Loop Approval UI                         │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ WebSocket (ws://localhost:9002)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend (Port 9002)                │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  WebSocket Manager                       │  │
│  │  • Connection Pool                                       │  │
│  │  • Broadcast Events                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Multi-Agent Orchestrator                    │  │
│  │                                                          │  │
│  │    ┌──────────┐  ┌──────────┐  ┌──────────┐            │  │
│  │    │Telemetry │→ │Detection │→ │Supervisor│            │  │
│  │    │  Agent   │  │  Agent   │  │  Agent   │            │  │
│  │    └──────────┘  └──────────┘  └──────────┘            │  │
│  │                         │              │                │  │
│  │                         ▼              ▼                │  │
│  │    ┌──────────┐  ┌──────────┐  ┌──────────┐            │  │
│  │    │Forensics │  │ Response │  │Compliance│            │  │
│  │    │  Agent   │  │  Agent   │  │  Agent   │            │  │
│  │    └──────────┘  └──────────┘  └──────────┘            │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  PostgreSQL  │    │    Redis     │    │     OPA      │
│   (Port      │    │  (Port 6379) │    │ (Port 8181)  │
│    5432)     │    │              │    │              │
│              │    │  • Caching   │    │  • Policy    │
│  • Events    │    │  • Sessions  │    │    Engine    │
│  • Incidents │    │  • State     │    │  • Rego      │
│  • Audit Log │    │              │    │    Rules     │
└──────────────┘    └──────────────┘    └──────────────┘
```

## Agent Communication Flow

```
┌──────────────────────────────────────────────────────────────┐
│                    Threat Detection Cycle                    │
└──────────────────────────────────────────────────────────────┘

1. INGEST
   ┌─────────────┐
   │  Telemetry  │ ← CloudTrail, VPC Logs, K8s Audit
   │    Agent    │
   └──────┬──────┘
          │ ASOCMessage(ALERT)
          ▼
2. DETECT
   ┌─────────────┐
   │  Detection  │ ← LLM Analysis (OpenAI/Anthropic)
   │    Agent    │   Risk Scoring (0-100)
   └──────┬──────┘
          │ ASOCMessage(REPORT, risk_score=0.85)
          ▼
3. EVALUATE
   ┌─────────────┐
   │  Supervisor │ ← OPA Policy Query
   │    Agent    │   if risk > 0.6 → Request Approval
   └──────┬──────┘
          │ APPROVAL_REQUIRED → WebSocket → UI
          │ ⏸️  PAUSE (await permission_event)
          │ ✅ APPROVE_ACTION ← WebSocket ← User
          ▼
4. INVESTIGATE
   ┌─────────────┐
   │  Forensics  │ → Blast Radius Graph
   │    Agent    │   Attack Path Reconstruction
   └──────┬──────┘
          │ BLAST_RADIUS_UPDATE → WebSocket → UI
          ▼
5. RESPOND
   ┌─────────────┐
   │  Response   │ → IAM_REVOKE / BLOCK_IP / ISOLATE
   │    Agent    │   Slack Notification
   └──────┬──────┘
          │ ASOCMessage(COMMAND)
          ▼
6. AUDIT
   ┌─────────────┐
   │ Compliance  │ → Immutable Event Store
   │    Agent    │   SOC2/ISO 27001 Mapping
   └─────────────┘
```

## Data Flow

```
External Sources          A-SOC System              Outputs
─────────────────        ──────────────            ────────

AWS CloudTrail    ──┐
VPC Flow Logs     ──┤
K8s Audit Logs    ──┼──→  Telemetry  ──→  Detection
GuardDuty Alerts  ──┤       Agent           Agent
Custom Webhooks   ──┘                         │
                                              │
                                              ▼
                                         Risk Score
                                              │
                                              ▼
                                         Supervisor ←─── OPA
                                              │
                                              ▼
                                    Human Approval? ──→ Dashboard
                                              │
                                              ▼
                                         Forensics ──→ Graph Viz
                                              │
                                              ▼
                                         Response  ──→ AWS API
                                              │         Slack
                                              │         PagerDuty
                                              ▼
                                         Compliance ──→ S3 Bucket
                                                        EventStore
```

## Security Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Security Layers                      │
└─────────────────────────────────────────────────────────┘

1. Authentication & Authorization
   ├─ API Keys (LLM Providers)
   ├─ IAM Roles (AWS Resources)
   ├─ OPA Policies (Action Authorization)
   └─ Human-in-the-Loop (High-Risk Actions)

2. Data Protection
   ├─ TLS/SSL (All Network Traffic)
   ├─ Secrets Management (Docker Secrets, K8s Secrets)
   ├─ Encrypted Storage (PostgreSQL, S3)
   └─ Immutable Audit Logs (WORM Storage)

3. Network Security
   ├─ VPC Isolation (AWS)
   ├─ Network Policies (Kubernetes)
   ├─ Firewall Rules (Security Groups)
   └─ Rate Limiting (API Gateway)

4. Compliance
   ├─ SOC2 Type II Controls
   ├─ ISO 27001 Mapping
   ├─ GDPR Data Handling
   └─ Audit Trail Retention (7 years)
```

## Deployment Topologies

### Development
```
Local Machine
├─ Backend (Port 9002)
├─ Dashboard (Port 3000)
└─ Docker Compose (Postgres, Redis, OPA)
```

### Staging
```
AWS ECS Fargate
├─ Backend Task (2 replicas)
├─ Dashboard Task (2 replicas)
├─ RDS PostgreSQL (Multi-AZ)
├─ ElastiCache Redis (Cluster Mode)
└─ ALB (Application Load Balancer)
```

### Production
```
Kubernetes Cluster (EKS/GKE/AKS)
├─ Backend Deployment (HPA: 2-10 pods)
├─ Dashboard Deployment (HPA: 2-5 pods)
├─ PostgreSQL StatefulSet (3 replicas)
├─ Redis Cluster (6 nodes)
├─ OPA Sidecar (per pod)
├─ Ingress Controller (NGINX/Traefik)
└─ Service Mesh (Istio - Optional)
```

## Technology Stack Details

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | Next.js 14, TypeScript, Tailwind CSS | Real-time dashboard |
| **Backend** | FastAPI, Python 3.10+, Uvicorn | Async API server |
| **Orchestration** | LangGraph | Agent state machine |
| **LLM** | OpenAI GPT-4, Anthropic Claude | Threat analysis |
| **Policy** | Open Policy Agent (Rego) | Authorization |
| **Database** | PostgreSQL 15 | Persistent storage |
| **Cache** | Redis 7 | Session & state |
| **Container** | Docker, Docker Compose | Local dev |
| **Orchestration** | Kubernetes, Helm | Production |
| **CI/CD** | GitHub Actions | Automation |
| **Monitoring** | Prometheus, Grafana | Observability |
| **Logging** | ELK Stack, CloudWatch | Centralized logs |

## Scalability Considerations

### Horizontal Scaling
- **Backend**: Stateless design allows unlimited replicas
- **Database**: Read replicas for query distribution
- **Redis**: Cluster mode for distributed caching

### Performance Optimization
- **Connection Pooling**: PostgreSQL (pgbouncer)
- **Caching Strategy**: Redis for LLM response cache
- **Async Processing**: Celery for background tasks
- **CDN**: CloudFront for static assets

### High Availability
- **Multi-AZ Deployment**: Database and application
- **Health Checks**: Kubernetes liveness/readiness probes
- **Auto-Recovery**: Pod restart policies
- **Backup Strategy**: Automated daily snapshots
