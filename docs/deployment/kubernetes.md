# Kubernetes Deployment

## Quick Start

```bash
kubectl apply -k k8s/
```

## Manual Setup

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Create ConfigMap
kubectl apply -f k8s/configmap.yaml

# Create PVC
kubectl apply -f k8s/pvc.yaml

# Create secrets (replace with your keys)
kubectl create secret generic model-canary-secrets \
  --from-literal=openai-api-key=sk-... \
  --from-literal=anthropic-api-key=sk-ant-... \
  -n model-canary

# Deploy
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml
```
