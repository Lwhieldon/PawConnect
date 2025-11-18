# PawConnect AI - API Documentation

## Overview

The PawConnect API provides endpoints for pet search, recommendations, scheduling, and application processing.

**Base URL**: `https://pawconnect-main-agent-XXXXX.run.app`
**Authentication**: API Key (for production) or Session-based (for web interface)
**Format**: JSON

## Endpoints

### Health Check

```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-11-18T10:00:00Z"
}
```

---

### Search Pets

```http
POST /api/search
```

**Request Body**:
```json
{
  "pet_type": "dog",
  "location": "Seattle, WA",
  "distance": 50,
  "size": "medium",
  "age": "adult",
  "limit": 20
}
```

**Response**:
```json
{
  "pets": [
    {
      "pet_id": "rg_12345",
      "name": "Max",
      "species": "dog",
      "breed": "Labrador Retriever",
      "age": "adult",
      "size": "large",
      "gender": "male",
      "shelter": {
        "name": "Seattle Animal Shelter",
        "city": "Seattle",
        "state": "WA"
      },
      "photos": ["https://..."]
    }
  ],
  "total_results": 45,
  "page": 1
}
```

---

### Get Recommendations

```http
POST /api/recommendations
```

**Request Body**:
```json
{
  "user_profile": {
    "preferences": {
      "pet_type": "dog",
      "home_type": "apartment",
      "has_yard": false,
      "activity_level": "high",
      "experience_level": "first_time"
    }
  },
  "top_k": 10
}
```

**Response**:
```json
{
  "recommendations": [
    {
      "pet": { /* Pet object */ },
      "overall_score": 0.87,
      "match_explanation": "Max is an excellent match...",
      "key_factors": ["Good with children", "Low maintenance"]
    }
  ]
}
```

---

### Schedule Visit

```http
POST /api/visit/schedule
```

**Request Body**:
```json
{
  "user_id": "user_123",
  "pet_id": "rg_12345",
  "preferred_date": "2025-11-20",
  "preferred_time": "14:00"
}
```

**Response**:
```json
{
  "visit_id": "visit_789",
  "status": "scheduled",
  "confirmation_email_sent": true
}
```

---

### Submit Application

```http
POST /api/application/submit
```

**Request Body**:
```json
{
  "user_id": "user_123",
  "pet_id": "rg_12345",
  "application_type": "adoption",
  "form_data": {
    "first_name": "John",
    "last_name": "Doe",
    /* Additional fields */
  }
}
```

**Response**:
```json
{
  "application_id": "app_456",
  "status": "submitted",
  "next_steps": ["Background check", "Home assessment"]
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Pet type is required",
    "details": {}
  }
}
```

**Error Codes**:
- `INVALID_REQUEST` - Malformed or missing required fields
- `NOT_FOUND` - Resource not found
- `UNAUTHORIZED` - Authentication required
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `INTERNAL_ERROR` - Server error

---

## Rate Limits

- **Free tier**: 100 requests/hour
- **Authenticated**: 1000 requests/hour
- **Enterprise**: Custom limits

---

## Webhooks

For Dialogflow CX integration:

**Endpoint**: `/webhook/dialogflow`
**Method**: POST

See [DIALOGFLOW_SETUP.md](./DIALOGFLOW_SETUP.md) for details.

---

## SDK Examples

### Python

```python
from pawconnect_ai.agent import PawConnectMainAgent

agent = PawConnectMainAgent()
pets = await agent.search_pets(
    pet_type="dog",
    location="Seattle, WA"
)
```

### cURL

```bash
curl -X POST https://pawconnect-api.run.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"pet_type":"dog","location":"Seattle, WA"}'
```

---

For more information, see the [README](../README.md).
