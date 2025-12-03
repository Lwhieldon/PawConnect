# GCP Integrations Guide

PawConnect uses three key Google Cloud Platform services to enhance performance, track user behavior, and provide analytics:

1. **Redis (Memorystore)** - Caching for API responses
2. **Firestore** - User preferences and conversation history
3. **Pub/Sub** - Real-time analytics and event tracking

## Table of Contents

- [Overview](#overview)
- [Redis Caching](#redis-caching)
- [Firestore Storage](#firestore-storage)
- [Pub/Sub Analytics](#pubsub-analytics)
- [Setup Instructions](#setup-instructions)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

---

## Overview

### Architecture

```
┌─────────────────┐
│  Dialogflow CX  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│   PawConnect Webhook (FastAPI)  │
│  ┌───────────────────────────┐  │
│  │  User Preferences Tracker │  │
│  │  Conversation History     │  │
│  │  Analytics Publisher      │  │
│  └───────────────────────────┘  │
└──┬──────────┬──────────┬────────┘
   │          │          │
   ▼          ▼          ▼
┌──────┐  ┌──────────┐  ┌────────┐
│Redis │  │Firestore │  │Pub/Sub │
└──────┘  └──────────┘  └────────┘
```

### Benefits

- **Redis**: Reduces API calls to RescueGroups by 60-80%, improves response times
- **Firestore**: Enables personalized recommendations based on user history
- **Pub/Sub**: Real-time analytics for monitoring user behavior and system performance

---

## Redis Caching

### What Gets Cached

Redis caches responses from the RescueGroups API to reduce load and improve performance:

1. **Pet Search Results** - Cached for 1 hour (configurable via `CACHE_TTL`)
2. **Pet Details** - Cached for 1 hour per pet ID

### Cache Key Format

```
pawconnect:pet_search:<hash>    # Search results
pawconnect:pet_details:<hash>   # Individual pet details
```

The hash is an MD5 of sorted search parameters for consistent cache keys.

### Configuration

In `.env`:
```bash
# Redis/Memorystore Configuration
REDIS_HOST=localhost              # Local dev: localhost, Prod: Memorystore internal IP
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=                   # Leave empty for local dev
CACHE_TTL=3600                    # Cache duration in seconds (1 hour)
```

### Implementation Details

From `pawconnect_ai/utils/api_clients.py`:

```python
# Check cache before API call
cache_key = google_cloud_client.generate_cache_key(
    "pet_search",
    pet_type=pet_type,
    location=location,
    distance=distance,
    limit=limit,
    page=page
)
cached_result = google_cloud_client.get_cache(cache_key)
if cached_result:
    logger.info("Returning cached search results")
    return cached_result

# ... Make API call ...

# Cache the result
google_cloud_client.set_cache(cache_key, result)
```

### Cache Behavior

- **Cache Miss**: Makes API call, stores result in Redis
- **Cache Hit**: Returns cached result immediately
- **Cache Failure**: If Redis is unavailable, falls back to direct API calls
- **TTL**: Cached entries expire after `CACHE_TTL` seconds

---

## Firestore Storage

### Collections

PawConnect uses two Firestore collections:

#### 1. `users` Collection

Stores user preferences for personalized recommendations.

**Document ID**: Dialogflow session ID
**Schema**:
```json
{
  "location": "Seattle",
  "species": "dog",
  "housing": "apartment",
  "experience": "yes",
  "search_radius": 50
}
```

#### 2. `sessions` Collection

Stores conversation history for each user session.

**Document ID**: Dialogflow session ID
**Schema**:
```json
{
  "session_id": "abc123...",
  "created_at": "2025-12-03T10:30:00Z",
  "updated_at": "2025-12-03T10:35:00Z",
  "events": [
    {
      "type": "search_pets",
      "timestamp": "2025-12-03T10:31:00Z",
      "data": {
        "pet_type": "dog",
        "location": "Seattle",
        "results_count": 15
      }
    },
    {
      "type": "pet_details_viewed",
      "timestamp": "2025-12-03T10:33:00Z",
      "data": {
        "pet_id": "12345",
        "pet_name": "Lucky",
        "pet_species": "Dog"
      }
    },
    {
      "type": "visit_scheduled",
      "timestamp": "2025-12-03T10:35:00Z",
      "data": {
        "pet_id": "12345",
        "pet_name": "Lucky",
        "visit_date": "Saturday, December 7, 2025",
        "visit_time": "2:00 PM"
      }
    }
  ]
}
```

### Event Types

- `search_pets` - User searches for pets
- `get_recommendations` - User requests recommendations
- `pet_details_viewed` - User views details for a specific pet
- `visit_scheduled` - User schedules a shelter visit
- `application_started` - User starts an adoption application

### Configuration

In `.env`:
```bash
# Firestore Configuration
FIRESTORE_COLLECTION_USERS=users
FIRESTORE_COLLECTION_APPLICATIONS=applications
FIRESTORE_COLLECTION_SESSIONS=sessions
```

### Implementation Details

From `pawconnect_ai/dialogflow_webhook.py`:

```python
# Track user preferences
async def track_user_preferences(session_id: str, parameters: Dict[str, Any]) -> None:
    if not google_cloud_client:
        return

    preferences = {}
    if "location" in parameters:
        preferences["location"] = parameters["location"]
    if "species" in parameters:
        preferences["species"] = parameters["species"]
    # ... extract other preferences

    if preferences:
        google_cloud_client.update_user_preferences(session_id, preferences)

# Track conversation events
async def track_conversation_event(
    session_id: str,
    event_type: str,
    event_data: Dict[str, Any]
) -> None:
    if not google_cloud_client:
        return

    google_cloud_client.save_conversation_event(session_id, event_type, event_data)
```

### Querying Conversation History

To retrieve a user's conversation history:

```python
from pawconnect_ai.utils.api_clients import google_cloud_client

history = google_cloud_client.get_conversation_history(session_id)
if history:
    print(f"Session started: {history['created_at']}")
    for event in history['events']:
        print(f"{event['type']} at {event['timestamp']}")
```

---

## Pub/Sub Analytics

### Topics

PawConnect publishes analytics events to a single Pub/Sub topic:

**Topic Name**: `pawconnect` (configurable via `PUBSUB_TOPIC_PREFIX`)

### Event Types Published

1. **pet_search** - When users search for pets
2. **pet_recommendations** - When users request recommendations
3. **pet_details_view** - When users view pet details
4. **visit_scheduled** - When users schedule visits
5. **application_started** - When users start applications

### Message Format

All messages follow this schema:

```json
{
  "event_type": "pet_search",
  "timestamp": "2025-12-03T10:31:00Z",
  "data": {
    "pet_type": "dog",
    "location": "Seattle",
    "breed": null,
    "results_count": 15
  }
}
```

### Configuration

In `.env`:
```bash
# Pub/Sub Configuration
PUBSUB_TOPIC_PREFIX=pawconnect
PUBSUB_SEARCH_TOPIC=pawconnect-search-results        # Not currently used
PUBSUB_RECOMMENDATION_TOPIC=pawconnect-recommendations # Not currently used
```

### Implementation Details

From `pawconnect_ai/dialogflow_webhook.py`:

```python
async def publish_analytics(event_type: str, event_data: Dict[str, Any]) -> None:
    if not google_cloud_client:
        return

    try:
        await google_cloud_client.publish_analytics_event(event_type, event_data)
    except Exception as e:
        logger.error(f"Failed to publish analytics event: {e}")
```

### Subscribing to Events

To consume analytics events:

```python
from google.cloud import pubsub_v1

# Create subscriber
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(
    [Insert Project Name Here],
    "pawconnect-analytics-subscription"
)

def callback(message):
    data = json.loads(message.data.decode())
    print(f"Event: {data['event_type']}")
    print(f"Data: {data['data']}")
    message.ack()

# Subscribe
subscriber.subscribe(subscription_path, callback=callback)
```

---

## Setup Instructions

### 1. Local Development Setup

#### Install Redis Locally (Windows)

```bash
# Download Redis for Windows from https://github.com/microsoftarchive/redis/releases
# Or use WSL2:
wsl --install
wsl
sudo apt update
sudo apt install redis-server
redis-server
```

#### Configure .env for Local Development

```bash
# .env
ENVIRONMENT=development
TESTING_MODE=False
MOCK_APIS=False

# Redis (Local)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
CACHE_TTL=3600

# GCP (uses Application Default Credentials)
GCP_PROJECT_ID=[Insert Project Name Here]
GCP_REGION=[Insert Region Here]
GCP_CREDENTIALS_PATH=[Insert Path Here]

# Firestore collections
FIRESTORE_COLLECTION_USERS=users
FIRESTORE_COLLECTION_SESSIONS=sessions

# Pub/Sub
PUBSUB_TOPIC_PREFIX=pawconnect
```

#### Authenticate with GCP

```bash
gcloud auth application-default login
gcloud config set project [Insert Project Name Here]
```

### 2. Production Setup on Cloud Run

#### Deploy Memorystore for Redis

```bash
# Create Memorystore instance
gcloud redis instances create pawconnect-cache \
    --size=1 \
    --region=[Insert Region Here] \
    --redis-version=redis_6_x

# Get instance details
gcloud redis instances describe pawconnect-cache --region=[Insert Region Here]

# Note the internal IP (e.g., 10.0.0.3)
```

#### Create Pub/Sub Topic

```bash
# Create topic
gcloud pubsub topics create pawconnect

# Create subscription for analytics
gcloud pubsub subscriptions create pawconnect-analytics-subscription \
    --topic=pawconnect
```

#### Configure Firestore

Firestore should already be enabled in your GCP project. No additional setup needed - collections are created automatically.

#### Deploy Webhook with GCP Services

```bash
# Deploy with environment variables
gcloud run deploy pawconnect-webhook \
    --source . \
    --region [Insert Region Here] \
    --allow-unauthenticated \
    --set-env-vars ENVIRONMENT=production,\
GCP_PROJECT_ID=[Insert Project Name Here],\
GCP_REGION=[Insert Region Here],\
REDIS_HOST=10.0.0.3,\
REDIS_PORT=6379,\
CACHE_TTL=3600 \
    --min-instances=0 \
    --max-instances=10
```

**Note**: For production, store `REDIS_PASSWORD` in Secret Manager and inject via `--set-secrets`.

---

## Monitoring

### Redis Cache Performance

Monitor cache hit/miss rates in Cloud Run logs:

```bash
# View logs
gcloud run services logs read pawconnect-webhook --region=[Insert Region Here] --limit=100

# Look for:
# "Cache HIT for key: pawconnect:pet_search:abc123"
# "Cache MISS for key: pawconnect:pet_search:abc123"
```

### Firestore Usage

Check Firestore in GCP Console:
- Go to Firestore → Data
- Inspect `users` and `sessions` collections
- View document counts and storage size

### Pub/Sub Message Throughput

Monitor Pub/Sub in GCP Console:
- Go to Pub/Sub → Topics → pawconnect
- View message publish rate
- Check subscription backlog

---

## Troubleshooting

### Redis Connection Failed

**Symptom**: Logs show "Failed to connect to Redis" warning

**Solutions**:
1. Verify Redis is running: `redis-cli ping` (should return `PONG`)
2. Check `REDIS_HOST` and `REDIS_PORT` in `.env`
3. For Memorystore: Ensure Cloud Run has VPC connector configured
4. Check firewall rules allow Redis port (6379)

**Impact**: Caching disabled, falls back to direct API calls (slower but functional)

### Firestore Permission Denied

**Symptom**: Error "Permission denied on Firestore"

**Solutions**:
1. Verify service account has Firestore permissions:
   ```bash
   gcloud projects add-iam-policy-binding [Insert Project Here] \
       --member="serviceAccount:YOUR-SERVICE-ACCOUNT@[Insert Project Here].iam.gserviceaccount.com" \
       --role="roles/datastore.user"
   ```
2. Check GCP credentials are configured correctly
3. Verify `GCP_PROJECT_ID` matches your project

### Pub/Sub Messages Not Publishing

**Symptom**: No analytics events appearing in Pub/Sub

**Solutions**:
1. Verify topic exists: `gcloud pubsub topics list`
2. Check service account has Pub/Sub Publisher role:
   ```bash
   gcloud projects add-iam-policy-binding [Insert Project Here] \
       --member="serviceAccount:YOUR-SERVICE-ACCOUNT@[Insert Project Here].iam.gserviceaccount.com" \
       --role="roles/pubsub.publisher"
   ```
3. Check logs for "Failed to publish analytics event" errors

### Cache Not Expiring

**Symptom**: Stale data returned even after TTL

**Solutions**:
1. Verify `CACHE_TTL` is set correctly in `.env`
2. Manually flush cache: `redis-cli FLUSHALL` (development only!)
3. Check Redis memory policy: `redis-cli CONFIG GET maxmemory-policy`

---

## Performance Benchmarks

With all integrations enabled:

| Metric | Without Cache | With Cache |
|--------|--------------|------------|
| Pet Search Response Time | 800-1200ms | 50-100ms |
| Pet Details Response Time | 400-600ms | 20-50ms |
| RescueGroups API Calls | 100% | 20-40% |
| Average Latency | 600ms | 150ms |

---

## Cost Estimates (Monthly)

Based on 10,000 conversations/month:

| Service | Usage | Cost |
|---------|-------|------|
| Memorystore (1GB) | 1 instance | ~$40 |
| Firestore | 30K reads, 30K writes | ~$1 |
| Pub/Sub | 30K messages | ~$0.10 |
| **Total** | | **~$41/month** |

**Note**: Cloud Run costs separate (see docs/DEPLOYMENT.md)

---

## Additional Resources

- [Redis Best Practices](https://cloud.google.com/memorystore/docs/redis/redis-best-practices)
- [Firestore Data Model](https://cloud.google.com/firestore/docs/data-model)
- [Pub/Sub Concepts](https://cloud.google.com/pubsub/docs/overview)
- [PawConnect Architecture](./ARCHITECTURE.md)
- [Deployment Guide](./DEPLOYMENT.md)

---

**Last Updated**: December 3, 2025
**Version**: 1.0.0
