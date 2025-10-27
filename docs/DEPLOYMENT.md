# Deployment Guide

## Prerequisites

### Infrastructure Requirements

- **Kubernetes Cluster**: 1.24 or higher
- **Node Requirements**:
  - Minimum 3 nodes
  - 8 CPU cores per node
  - 32 GB RAM per node
  - 500 GB SSD storage per node
- **Helm**: Version 3.x
- **kubectl**: Configured with cluster access

### Network Requirements

- Ingress controller (nginx recommended)
- Load balancer support
- DNS configuration for external access

## Step-by-Step Deployment

### 1. Prepare the Cluster

\`\`\`bash
# Create namespace
kubectl create namespace log-pipeline

# Label namespace for monitoring
kubectl label namespace log-pipeline monitoring=enabled
\`\`\`

### 2. Deploy Kafka Cluster

\`\`\`bash
cd kafka/helm

# Review and customize values
vim values.yaml

# Deploy Kafka
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

helm install kafka bitnami/kafka \
  --namespace log-pipeline \
  --values values.yaml \
  --wait \
  --timeout 10m

# Verify Kafka is running
kubectl get pods -n log-pipeline -l app.kubernetes.io/name=kafka
\`\`\`

### 3. Deploy ClickHouse Cluster

\`\`\`bash
cd clickhouse/helm

# Review and customize values
vim values.yaml

# Deploy ClickHouse
helm install clickhouse bitnami/clickhouse \
  --namespace log-pipeline \
  --values values.yaml \
  --wait \
  --timeout 10m

# Wait for ClickHouse to be ready
kubectl wait --for=condition=ready pod -l app=clickhouse \
  -n log-pipeline --timeout=300s
\`\`\`

### 4. Initialize ClickHouse Schema

\`\`\`bash
cd scripts

# Create database
kubectl exec -n log-pipeline clickhouse-0 -- \
  clickhouse-client --query "$(cat 01_create_database.sql)"

# Create tables
kubectl exec -n log-pipeline clickhouse-0 -- \
  clickhouse-client --query "$(cat 02_create_logs_table.sql)"

# Create materialized views
kubectl exec -n log-pipeline clickhouse-0 -- \
  clickhouse-client --query "$(cat 03_create_materialized_views.sql)"

# Verify schema
kubectl exec -n log-pipeline clickhouse-0 -- \
  clickhouse-client --query "SHOW TABLES FROM logs"
\`\`\`

### 5. Build and Push Docker Images

\`\`\`bash
# Build ingestion service
cd ingestion-service
docker build -t <registry>/log-ingestion-service:v1.0.0 .
docker push <registry>/log-ingestion-service:v1.0.0

# Build indexer service
cd ../indexer
docker build -t <registry>/log-indexer:v1.0.0 .
docker push <registry>/log-indexer:v1.0.0

# Build query API
cd ../query-api
docker build -t <registry>/query-api:v1.0.0 .
docker push <registry>/query-api:v1.0.0
\`\`\`

### 6. Deploy Application Services

\`\`\`bash
cd charts

# Update image references in kustomization.yaml
vim kustomization.yaml

# Deploy using Kustomize
kubectl apply -k .

# Verify deployments
kubectl get deployments -n log-pipeline
kubectl get pods -n log-pipeline
kubectl get hpa -n log-pipeline
\`\`\`

### 7. Deploy Observability Stack

\`\`\`bash
cd observability

# Deploy Prometheus and Grafana
./deploy-observability.sh

# Verify observability stack
kubectl get pods -n log-pipeline -l app=prometheus
kubectl get pods -n log-pipeline -l app=grafana
\`\`\`

### 8. Configure Ingress

\`\`\`bash
# Update ingress hostname
vim charts/query-api/deployment.yaml

# Apply ingress
kubectl apply -f charts/query-api/deployment.yaml

# Get ingress IP
kubectl get ingress -n log-pipeline
\`\`\`

## Post-Deployment Verification

### Health Checks

\`\`\`bash
# Check all pods are running
kubectl get pods -n log-pipeline

# Check service endpoints
kubectl get svc -n log-pipeline

# Test ingestion service
kubectl port-forward -n log-pipeline svc/log-ingestion-service 50051:50051

# Test query API
kubectl port-forward -n log-pipeline svc/query-api 8000:80
curl http://localhost:8000/health
\`\`\`

### Load Testing

\`\`\`bash
# Generate test load
kubectl exec -n log-pipeline deploy/log-ingestion-service -- \
  python mock_data_generator.py --rate 10000 --duration 3600

# Monitor metrics
kubectl port-forward -n log-pipeline svc/grafana 3000:80
# Open http://localhost:3000
\`\`\`

## Production Considerations

### Security

1. **Enable TLS**:
   - Configure TLS for Kafka
   - Enable HTTPS for Query API
   - Use cert-manager for certificate management

2. **Authentication**:
   - Enable Kafka SASL authentication
   - Add API authentication to Query API
   - Configure ClickHouse user permissions

3. **Network Policies**:
   - Apply network policies (already included)
   - Restrict ingress/egress traffic
   - Use service mesh for mTLS

### High Availability

1. **Multi-AZ Deployment**:
   - Spread pods across availability zones
   - Use pod anti-affinity rules
   - Configure topology spread constraints

2. **Backup and Recovery**:
   - Enable ClickHouse backups to S3
   - Backup Kafka topics
   - Document recovery procedures

### Monitoring and Alerting

1. **Configure Alertmanager**:
   - Set up notification channels (Slack, PagerDuty)
   - Define escalation policies
   - Test alert routing

2. **Custom Dashboards**:
   - Create team-specific dashboards
   - Set up SLO tracking
   - Configure anomaly detection

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues and solutions.
