#!/bin/bash
# Deploy observability stack

set -e

echo "Deploying Observability Stack..."

# Add Helm repositories
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Deploy Prometheus
echo "Deploying Prometheus..."
helm upgrade --install prometheus prometheus-community/prometheus \
  --namespace log-pipeline \
  --values prometheus/values.yaml \
  --wait

# Deploy Grafana
echo "Deploying Grafana..."
helm upgrade --install grafana grafana/grafana \
  --namespace log-pipeline \
  --values grafana/values.yaml \
  --wait

# Deploy OpenTelemetry Collector
echo "Deploying OpenTelemetry Collector..."
kubectl apply -f opentelemetry/deployment.yaml

echo "Observability stack deployed successfully!"
echo ""
echo "Access Grafana:"
echo "  kubectl port-forward -n log-pipeline svc/grafana 3000:80"
echo "  Username: admin"
echo "  Password: changeme"
echo ""
echo "Access Prometheus:"
echo "  kubectl port-forward -n log-pipeline svc/prometheus-server 9090:80"
