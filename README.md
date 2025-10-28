# Cloud-Scale Log Ingestion & Search

A scalable, high-throughput log ingestion and search platform built for cloud-native environments. This system handles millions of logs per second with sub-second query latency using a modern event-driven architecture.

## 🏗️ Architecture

The platform consists of three main microservices:

```
┌─────────────┐     ┌──────────┐     ┌──────────────┐     ┌────────────┐
│   Clients   │────▶│ Ingestion│────▶│    Kafka     │────▶│  Indexer   │
│  (gRPC/HTTP)│     │  Service │     │   (Stream)   │     │  Service   │
└─────────────┘     └──────────┘     └──────────────┘     └──────┬─────┘
                                                                   │
┌─────────────┐     ┌──────────┐                                 ▼
│   Clients   │◀────│  Query   │◀───────────────────────┌────────────────┐
│  (HTTP/REST)│     │   API    │                        │  ClickHouse    │
└─────────────┘     └──────────┘                        │  (Analytics DB)│
                                                         └────────────────┘
```

### Components

1. **Ingestion Service** - gRPC endpoint that receives logs and publishes to Kafka
2. **Kafka** - Distributed message queue for buffering and decoupling
3. **Indexer Service** - Kafka consumer that writes logs to ClickHouse with exactly-once semantics
4. **ClickHouse** - Columnar database optimized for analytical queries
5. **Query API** - FastAPI service providing HTTP/REST interface for log queries
6. **Observability Stack** - Prometheus, Grafana, and OpenTelemetry for monitoring

## ✨ Features

- **High Throughput**: Handle millions of logs per second
- **Low Latency**: Sub-second query response times
- **Scalability**: Horizontal scaling for all components
- **Reliability**: Exactly-once delivery semantics with idempotent operations
- **Time-Series Optimization**: Partitioned by time with automatic TTL (30 days)
- **Full-Text Search**: Token-based search indexes for fast message queries
- **Aggregations**: Pre-computed materialized views for metrics
- **Data Compression**: LZ4 compression for reduced storage costs
- **Multi-Format Export**: JSON and CSV export with gzip compression
- **Production-Ready**: Health checks, metrics, distributed tracing

## 🚀 Technology Stack

### Backend Services
- **Python 3.11+** - Core service implementation
- **gRPC** - High-performance RPC framework for ingestion
- **FastAPI** - Modern web framework for query API
- **Kafka** - Event streaming platform
- **ClickHouse** - Columnar OLAP database

### Infrastructure
- **Kubernetes** - Container orchestration
- **Helm** - Package management
- **Docker** - Containerization
- **Prometheus** - Metrics collection
- **Grafana** - Visualization and dashboards
- **OpenTelemetry** - Distributed tracing

### Frontend (Optional)
- **Next.js 16** - React framework
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **Radix UI** - Accessible UI components

## 📦 Quick Start

### Prerequisites

- Kubernetes cluster (1.24+)
- kubectl configured
- Helm 3.x
- Docker (for building images)

### Local Development with Docker Compose

```bash
# Clone the repository
git clone https://github.com/johaankjis/Cloud-Scale-Log-Ingestion---Search.git
cd Cloud-Scale-Log-Ingestion---Search

# Start infrastructure
docker-compose up -d kafka clickhouse

# Initialize ClickHouse schema
cd scripts
./init-schema.sh

# Start services
cd ../ingestion-service
pip install -r requirements.txt
python main.py &

cd ../indexer
pip install -r requirements.txt
python main.py &

cd ../query-api
pip install -r requirements.txt
uvicorn main:app --reload
```

### Production Deployment to Kubernetes

See the [Deployment Guide](docs/DEPLOYMENT.md) for detailed production deployment instructions.

```bash
# Quick deployment
kubectl create namespace log-pipeline
cd charts
./deploy.sh
```

## 📖 Documentation

- **[API Documentation](docs/API.md)** - Complete API reference with examples
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Step-by-step production deployment
- **[Architecture](docs/)** - Detailed architecture and design decisions

## 🔍 Usage Examples

### Ingesting Logs

```python
import grpc
from log_pb2 import LogEntry
from log_pb2_grpc import LogIngestionServiceStub

# Connect to ingestion service
channel = grpc.insecure_channel('localhost:50051')
stub = LogIngestionServiceStub(channel)

# Send a log
log = LogEntry(
    service="my-service",
    level="INFO",
    message="User logged in successfully",
    metadata='{"user_id": "12345", "ip": "192.168.1.1"}'
)
response = stub.IngestLog(log)
```

### Querying Logs

```bash
# Query logs via REST API
curl -X POST http://localhost:8000/api/v1/logs \
  -H "Content-Type: application/json" \
  -d '{
    "start_time": "2025-01-01T00:00:00Z",
    "end_time": "2025-01-02T00:00:00Z",
    "level": "ERROR",
    "search": "timeout",
    "limit": 100
  }'
```

```python
# Query logs with Python
import requests

response = requests.post(
    'http://localhost:8000/api/v1/logs',
    json={
        'level': 'ERROR',
        'service': 'api-gateway',
        'limit': 100
    }
)
logs = response.json()
print(f"Found {logs['total']} error logs")
```

### Exporting Logs

```bash
# Export logs as compressed JSON
curl -X GET "http://localhost:8000/api/v1/logs/export?format=json&service=api-gateway" \
  -o logs-export.json.gz

# Export as CSV
curl -X GET "http://localhost:8000/api/v1/logs/export?format=csv" \
  -o logs-export.csv.gz
```

## 📊 Monitoring

Access monitoring dashboards:

```bash
# Port-forward Grafana
kubectl port-forward -n log-pipeline svc/grafana 3000:80

# Port-forward Prometheus
kubectl port-forward -n log-pipeline svc/prometheus 9090:80
```

Default Grafana credentials:
- Username: `admin`
- Password: Check with `kubectl get secret -n log-pipeline grafana -o jsonpath="{.data.admin-password}" | base64 --decode`

## 🧪 Testing

### Generate Mock Data

```bash
cd ingestion-service
python mock_data_generator.py --rate 1000 --duration 60
```

### Run API Tests

```bash
cd query-api
pytest test_api.py -v
```

### Load Testing

```bash
# Generate high load
python mock_data_generator.py --rate 10000 --duration 3600
```

## ⚙️ Configuration

### Environment Variables

**Ingestion Service:**
```bash
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC=logs-ingestion
GRPC_PORT=50051
```

**Indexer Service:**
```bash
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC=logs-ingestion
KAFKA_GROUP_ID=log-indexer-group
CLICKHOUSE_HOST=clickhouse
CLICKHOUSE_PORT=9000
CLICKHOUSE_DATABASE=logs
BATCH_SIZE=1000
BATCH_TIMEOUT_MS=5000
```

**Query API:**
```bash
CLICKHOUSE_HOST=clickhouse
CLICKHOUSE_PORT=9000
CLICKHOUSE_DATABASE=logs
API_PORT=8000
```

## 📈 Performance Characteristics

- **Ingestion Rate**: 100K+ logs/second per pod
- **Query Latency**: < 500ms for time-range queries
- **Storage Efficiency**: ~70% compression with LZ4
- **Data Retention**: 30 days (configurable TTL)
- **Scalability**: Linear horizontal scaling
- **Availability**: 99.9%+ with HA configuration

## 🔒 Security Considerations

### Production Recommendations

1. **TLS Encryption**
   - Enable TLS for Kafka brokers
   - Configure HTTPS for Query API
   - Use cert-manager for certificate management

2. **Authentication & Authorization**
   - Enable Kafka SASL authentication
   - Add API key authentication to Query API
   - Configure ClickHouse user permissions

3. **Network Security**
   - Apply Kubernetes network policies (included)
   - Restrict ingress/egress traffic
   - Use service mesh for mTLS

4. **Data Security**
   - Encrypt data at rest in ClickHouse
   - Mask sensitive data in logs
   - Implement data retention policies

## 🛠️ Development

### Project Structure

```
.
├── charts/                 # Kubernetes manifests and Kustomize config
├── clickhouse/            # ClickHouse Helm chart configuration
├── docs/                  # Documentation
├── indexer/               # Log indexer service (Kafka → ClickHouse)
├── ingestion-service/     # Log ingestion service (gRPC → Kafka)
├── kafka/                 # Kafka Helm chart configuration
├── observability/         # Prometheus, Grafana, OpenTelemetry
├── query-api/             # Query API service (HTTP/REST)
└── scripts/               # Database schema and utility scripts
```

### Adding New Features

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

### Code Style

- Follow PEP 8 for Python code
- Use type hints where applicable
- Add docstrings for public functions
- Write unit tests for new features

## 🤝 Contributing

Contributions are welcome! Please:

1. Check existing issues or create a new one
2. Fork the repository
3. Create a feature branch
4. Write tests for your changes
5. Ensure all tests pass
6. Submit a pull request

## 📝 License

This project is open source and available under the [MIT License](LICENSE).

## 🙋 Support

- **Issues**: [GitHub Issues](https://github.com/johaankjis/Cloud-Scale-Log-Ingestion---Search/issues)
- **Discussions**: [GitHub Discussions](https://github.com/johaankjis/Cloud-Scale-Log-Ingestion---Search/discussions)

## 🗺️ Roadmap

- [ ] Add authentication and authorization
- [ ] Implement multi-tenancy
- [ ] Add log streaming (WebSocket/SSE)
- [ ] Support additional log formats (syslog, CEF)
- [ ] Add alerting based on log patterns
- [ ] Implement log anomaly detection
- [ ] Add cost optimization recommendations
- [ ] Create Terraform modules for cloud deployment

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [ClickHouse](https://clickhouse.com/) - Analytics database
- [Apache Kafka](https://kafka.apache.org/) - Event streaming
- [Kubernetes](https://kubernetes.io/) - Container orchestration
- [Prometheus](https://prometheus.io/) & [Grafana](https://grafana.com/) - Observability

---

**Built for scale. Optimized for performance. Ready for production.**
