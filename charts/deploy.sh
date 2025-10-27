#!/bin/bash
# Deployment script for log pipeline

set -e

echo "Deploying Log Pipeline to Kubernetes..."

# Create namespace
kubectl apply -f namespace.yaml

# Deploy Kafka (using Helm)
echo "Deploying Kafka cluster..."
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm upgrade --install kafka ../kafka/helm \
  --namespace log-pipeline \
  --values ../kafka/helm/values.yaml \
  --wait

# Deploy ClickHouse (using Helm)
echo "Deploying ClickHouse cluster..."
helm upgrade --install clickhouse ../clickhouse/helm \
  --namespace log-pipeline \
  --values ../clickhouse/helm/values.yaml \
  --wait

# Wait for ClickHouse to be ready
echo "Waiting for ClickHouse to be ready..."
kubectl wait --for=condition=ready pod -l app=clickhouse -n log-pipeline --timeout=300s

# Initialize ClickHouse schema
echo "Initializing ClickHouse schema..."
kubectl exec -n log-pipeline clickhouse-0 -- clickhouse-client --query "$(cat ../scripts/01_create_database.sql)"
kubectl exec -n log-pipeline clickhouse-0 -- clickhouse-client --query "$(cat ../scripts/02_create_logs_table.sql)"
kubectl exec -n log-pipeline clickhouse-0 -- clickhouse-client --query "$(cat ../scripts/03_create_materialized_views.sql)"

# Deploy application services using Kustomize
echo "Deploying application services..."
kubectl apply -k .

# Wait for deployments to be ready
echo "Waiting for deployments to be ready..."
kubectl wait --for=condition=available deployment/log-ingestion-service -n log-pipeline --timeout=300s
kubectl wait --for=condition=available deployment/log-indexer -n log-pipeline --timeout=300s
kubectl wait --for=condition=available deployment/query-api -n log-pipeline --timeout=300s

echo "Deployment complete!"
echo ""
echo "Services:"
echo "  Ingestion Service: kubectl port-forward -n log-pipeline svc/log-ingestion-service 50051:50051"
echo "  Query API: kubectl port-forward -n log-pipeline svc/query-api 8000:80"
echo ""
echo "To check status:"
echo "  kubectl get pods -n log-pipeline"
echo "  kubectl get hpa -n log-pipeline"
