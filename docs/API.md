# Query API Documentation

## Base URL

\`\`\`
http://logs-api.example.com
\`\`\`

## Authentication

Currently, the API does not require authentication. In production, implement:
- API keys
- OAuth 2.0
- JWT tokens

## Endpoints

### Health Check

Check API health and dependencies.

**Endpoint**: `GET /health`

**Response**:
\`\`\`json
{
  "status": "healthy",
  "clickhouse": "connected"
}
\`\`\`

### Query Logs

Query logs with filtering and pagination.

**Endpoint**: `POST /api/v1/logs`

**Request Body**:
\`\`\`json
{
  "start_time": "2025-01-01T00:00:00Z",
  "end_time": "2025-01-02T00:00:00Z",
  "service": "api-gateway",
  "level": "ERROR",
  "search": "timeout",
  "limit": 1000,
  "offset": 0
}
\`\`\`

**Parameters**:
- `start_time` (optional): Start time for query range (ISO 8601)
- `end_time` (optional): End time for query range (ISO 8601)
- `service` (optional): Filter by service name
- `level` (optional): Filter by log level (DEBUG, INFO, WARN, ERROR)
- `search` (optional): Full-text search in message
- `limit` (optional): Maximum results (1-10000, default: 1000)
- `offset` (optional): Pagination offset (default: 0)

**Response**:
\`\`\`json
{
  "total": 5432,
  "limit": 1000,
  "offset": 0,
  "logs": [
    {
      "timestamp": "2025-01-01T12:34:56.789Z",
      "service": "api-gateway",
      "level": "ERROR",
      "message": "Request timeout after 30s",
      "metadata": {
        "request_id": "req-123456",
        "user_id": "user-789",
        "endpoint": "/api/v1/users"
      }
    }
  ],
  "query_time_ms": 245.67
}
\`\`\`

### Get Aggregations

Get aggregated log counts by service and level.

**Endpoint**: `GET /api/v1/logs/aggregate`

**Query Parameters**:
- `start_time` (optional): Start time (ISO 8601)
- `end_time` (optional): End time (ISO 8601)
- `service` (optional): Filter by service

**Response**:
\`\`\`json
[
  {
    "service": "api-gateway",
    "level": "ERROR",
    "count": 1234,
    "hour": "2025-01-01T12:00:00Z"
  }
]
\`\`\`

### Get Recent Errors

Get recent error logs.

**Endpoint**: `GET /api/v1/logs/errors`

**Query Parameters**:
- `start_time` (optional): Start time (ISO 8601)
- `end_time` (optional): End time (ISO 8601)
- `service` (optional): Filter by service
- `limit` (optional): Maximum results (1-1000, default: 100)

**Response**:
\`\`\`json
[
  {
    "timestamp": "2025-01-01T12:34:56.789Z",
    "service": "payment-service",
    "message": "Payment processing failed",
    "metadata": {
      "transaction_id": "txn-456",
      "error_code": "INSUFFICIENT_FUNDS"
    }
  }
]
\`\`\`

### Export Logs

Export logs in JSON or CSV format with gzip compression.

**Endpoint**: `GET /api/v1/logs/export`

**Query Parameters**:
- `start_time` (optional): Start time (ISO 8601)
- `end_time` (optional): End time (ISO 8601)
- `service` (optional): Filter by service
- `format` (optional): Export format (json or csv, default: json)

**Response**: Gzip-compressed file download

## Rate Limiting

Current implementation does not include rate limiting. Recommended for production:
- 1000 requests per minute per IP
- 10000 requests per hour per API key

## Error Responses

### 400 Bad Request
\`\`\`json
{
  "detail": "Invalid query parameters"
}
\`\`\`

### 500 Internal Server Error
\`\`\`json
{
  "detail": "Database connection failed"
}
\`\`\`

### 503 Service Unavailable
\`\`\`json
{
  "detail": "Service unavailable"
}
\`\`\`

## Examples

### Python

\`\`\`python
import requests
from datetime import datetime, timedelta

# Query logs
response = requests.post(
    'http://logs-api.example.com/api/v1/logs',
    json={
        'start_time': (datetime.now() - timedelta(hours=1)).isoformat(),
        'level': 'ERROR',
        'limit': 100
    }
)

logs = response.json()
print(f"Found {logs['total']} errors")
\`\`\`

### cURL

\`\`\`bash
# Query logs
curl -X POST http://logs-api.example.com/api/v1/logs \
  -H "Content-Type: application/json" \
  -d '{
    "level": "ERROR",
    "limit": 10
  }'

# Export logs
curl -X GET "http://logs-api.example.com/api/v1/logs/export?format=json&service=api-gateway" \
  -o logs-export.json.gz
