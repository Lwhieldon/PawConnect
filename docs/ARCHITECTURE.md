# PawConnect AI - System Architecture

## Overview

PawConnect AI is a multi-agent system built on Google Cloud Platform that uses orchestrated AI agents to match pets with potential adopters.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         User Interface                       │
│              (Web App / Mobile App / Voice)                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   Dialogflow CX Agent                        │
│              (Conversational Interface)                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              PawConnect Main Agent (Orchestrator)            │
│                    (Cloud Run Service)                       │
└─────────┬────────────┬───────────┬───────────┬──────────────┘
          │            │           │           │
    ┌─────▼───┐  ┌────▼───┐  ┌────▼────┐ ┌───▼────────┐
    │ Pet     │  │ Recom- │  │ Vision  │ │ Workflow   │
    │ Search  │  │ mend   │  │ Agent   │ │ Agent      │
    │ Agent   │  │ Agent  │  │         │ │            │
    └────┬────┘  └────┬───┘  └────┬────┘ └───┬────────┘
         │            │           │           │
         ▼            ▼           ▼           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Google Cloud Services                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │RescueGrps│ │Vertex AI │ │ Vision   │ │Firestore │      │
│  │   API    │ │  Model   │ │   API    │ │   DB     │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│  ┌──────────┐ ┌──────────┐                                 │
│  │  Redis   │ │ Pub/Sub  │                                 │
│  │ (Cache)  │ │(Analytics)│                                │
│  └──────────┘ └──────────┘                                 │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Main Orchestrator Agent

**Location**: `pawconnect_ai/agent.py`

**Responsibilities**:
- Route user requests to appropriate sub-agents
- Maintain conversation context
- Aggregate results from multiple agents
- Handle error recovery and fallbacks

**Technology**:
- Python 3.11+
- FastAPI for REST endpoints
- Async/await for concurrent operations

### 2. Sub-Agents

#### Pet Search Agent
- **File**: `pawconnect_ai/sub_agents/pet_search_agent.py`
- **Function**: Query RescueGroups API for available pets
- **Features**:
  - Location-based search
  - Filter by pet attributes
  - Caching for performance
  - Rate limiting

#### Recommendation Agent
- **File**: `pawconnect_ai/sub_agents/recommendation_agent.py`
- **Function**: ML-based pet matching
- **Model**: TensorFlow/Keras hybrid recommendation system
- **Factors**:
  - Lifestyle compatibility (40%)
  - Personality match (30%)
  - Practical constraints (20%)
  - Urgency weighting (10%)

#### Conversation Agent
- **File**: `pawconnect_ai/sub_agents/conversation_agent.py`
- **Function**: Natural language understanding
- **Integration**: Dialogflow CX
- **Features**:
  - Intent detection
  - Entity extraction
  - Context management
  - Multi-turn conversations

#### Vision Agent
- **File**: `pawconnect_ai/sub_agents/vision_agent.py`
- **Function**: Image analysis
- **APIs**: Google Cloud Vision + Custom models
- **Capabilities**:
  - Breed identification
  - Age estimation
  - Health markers detection
  - Behavioral cues

#### Workflow Agent
- **File**: `pawconnect_ai/sub_agents/workflow_agent.py`
- **Function**: Application processing
- **Workflows**:
  - Adoption applications
  - Visit scheduling
  - Background checks
  - Status notifications

### 3. Data Layer

#### Firestore
- **Collections**:
  - `users`: User profiles and preferences (location, species, housing, experience)
  - `sessions`: Conversation history with timestamped events
  - `applications`: Adoption applications (future)
- **Implementation**: `pawconnect_ai/utils/api_clients.py` - GoogleCloudClient
- **Features**:
  - Automatic preference tracking on every webhook call
  - Event-based conversation history
  - Session persistence across conversations
- **See**: [GCP_INTEGRATIONS.md](./GCP_INTEGRATIONS.md) for detailed schema

#### Cloud Memorystore (Redis)
- **Purpose**: Caching RescueGroups API responses
- **TTL**: Configurable (default 1 hour via `CACHE_TTL`)
- **Cache Keys**:
  - `pawconnect:pet_search:<hash>` - Search results by parameters
  - `pawconnect:pet_details:<hash>` - Individual pet details by ID
- **Implementation**: `pawconnect_ai/utils/api_clients.py`
- **Benefits**: Reduces API calls by 60-80%, improves response times from 600ms to 150ms
- **See**: [GCP_INTEGRATIONS.md](./GCP_INTEGRATIONS.md) for configuration

#### Cloud Storage
- **Buckets**:
  - `model-artifacts`: ML models
  - `pet-images`: Cached pet photos
  - `build-artifacts`: CI/CD outputs

### 4. Communication Layer

#### Pub/Sub Topics
- **Primary Topic**: `pawconnect` (configurable via `PUBSUB_TOPIC_PREFIX`)
- **Event Types**:
  - `pet_search`: User searches for pets
  - `pet_recommendations`: User requests recommendations
  - `pet_details_view`: User views specific pet details
  - `visit_scheduled`: User schedules shelter visit
  - `application_started`: User starts adoption application
- **Implementation**: `pawconnect_ai/dialogflow_webhook.py` - publish_analytics()
- **Message Format**: JSON with event_type, timestamp, and data payload
- **Use Cases**: Real-time analytics, monitoring, downstream data processing
- **See**: [GCP_INTEGRATIONS.md](./GCP_INTEGRATIONS.md) for message schemas

**Pattern**: Event-driven architecture for async processing and analytics

### 5. ML Pipeline

```
┌────────────┐    ┌────────────┐    ┌────────────┐
│  Training  │───▶│  Vertex AI │───▶│   Model    │
│    Data    │    │  Training  │    │  Registry  │
└────────────┘    └────────────┘    └────────────┘
                                           │
                                           ▼
                                    ┌────────────┐
                                    │ Prediction │
                                    │  Endpoint  │
                                    └────────────┘
```

**Model**:
- Input: User features (20 dims) + Pet features (30 dims)
- Architecture: Embedding + Dense layers
- Output: Compatibility score (0-1)
- Metrics: Precision@5, Recall@10, NDCG

## Data Flow

### Search Flow

```
User Query
    ↓
Dialogflow CX (Intent: search_pets)
    ↓
Main Agent
    ↓
Pet Search Agent
    ↓
RescueGroups API
    ↓
Parse & Format Results
    ↓
Return to User
```

### Recommendation Flow

```
User Preferences
    ↓
Main Agent
    ↓
Pet Search Agent (Get available pets)
    ↓
Recommendation Agent
    ↓
Vertex AI Model Prediction
    ↓
Rank & Filter Results
    ↓
Return Top-K Matches
```

### Application Flow

```
Submit Application
    ↓
Workflow Agent
    ↓
Store in Firestore
    ↓
Trigger Background Check
    ↓
Schedule Home Assessment
    ↓
Send Notifications
    ↓
Update Status
```

## Security

### Authentication
- **User Auth**: Firebase Authentication
- **Service Auth**: Service Account keys
- **API Auth**: API keys + OAuth 2.0

### Data Protection
- **Encryption at rest**: GCP default
- **Encryption in transit**: TLS 1.3
- **PII Handling**: Compliance with data regulations
- **Secrets**: Secret Manager for API keys

### IAM Policies
- Principle of least privilege
- Service-specific service accounts
- Regular access reviews

## Scalability

### Horizontal Scaling
- Cloud Run auto-scales based on traffic
- Min instances: 1 (production), 0 (dev)
- Max instances: 10 (configurable)
- Concurrency: 80 requests/instance

### Caching Strategy
- Redis for frequent queries
- CDN for static assets
- Browser caching for images

### Rate Limiting
- Per-user limits (Firestore tracking)
- Per-IP limits (Cloud Armor)
- Graceful degradation on quota exhaustion

## Monitoring

### Metrics
- **Application**:
  - Request latency (p50, p95, p99)
  - Error rates
  - Recommendation quality (CTR, adoption rate)
- **Infrastructure**:
  - CPU/Memory usage
  - Cold start latency
  - API quota usage

### Logging
- **Cloud Logging** for centralized logs
- **Structured logging** with JSON format
- **Log levels**: DEBUG, INFO, WARNING, ERROR
- **Retention**: 30 days (configurable)

### Alerting
- High error rate (>5%)
- High latency (p95 >2s)
- API quota near limit (>90%)
- Model drift detected

## Disaster Recovery

### Backup Strategy
- Firestore: Daily automated backups
- Cloud Storage: Versioning enabled
- Secrets: Encrypted backups

### RPO/RTO
- **RPO** (Recovery Point Objective): 24 hours
- **RTO** (Recovery Time Objective): 4 hours

### Incident Response
1. Detect (monitoring alerts)
2. Assess (check dashboards)
3. Mitigate (rollback or scale)
4. Communicate (status page)
5. Post-mortem (lessons learned)

## Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| API Response Time (p95) | <800ms | ~650ms |
| Vision Analysis (p95) | <1.2s | ~1.1s |
| Recommendation Latency (p95) | <500ms | ~450ms |
| Availability | 99.9% | 99.95% |
| Error Rate | <1% | ~0.3% |

## Future Enhancements

1. **GraphQL API**: More flexible querying
2. **WebSocket Support**: Real-time updates
3. **Multi-region Deployment**: Global availability
4. **Advanced ML**: Deep learning for recommendations
5. **AR Integration**: Virtual pet meet-and-greets
6. **Mobile SDKs**: Native iOS/Android apps

## Technology Stack

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Async**: asyncio, aiohttp

### ML/AI
- **Training**: TensorFlow, Keras
- **Serving**: Vertex AI
- **Vision**: Cloud Vision API
- **NLP**: Dialogflow CX

### Infrastructure
- **Compute**: Cloud Run
- **Storage**: Firestore, Cloud Storage
- **Messaging**: Pub/Sub
- **Caching**: Memorystore (Redis)

### DevOps
- **CI/CD**: Cloud Build
- **IaC**: Terraform
- **Monitoring**: Cloud Monitoring
- **Logging**: Cloud Logging

## Cost Analysis

**Monthly Cost Estimate** (moderate traffic):
- Cloud Run: $50-100
- Dialogflow CX: $100-200
- Vertex AI: $50-150
- Firestore: $20-50
- Other services: $30-50
- **Total**: ~$250-550/month

---

For deployment instructions, see [DEPLOYMENT.md](./DEPLOYMENT.md).
For API details, see [API.md](./API.md).
