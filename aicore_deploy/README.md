# Supply Chain AI Agent — SAP AI Core Deployment Guide

## Architecture

```
User Question
     │
     ▼
Flask API (/v1/predict)
     │
     ▼
AI Agent Logic (agent.py)
     │
     ▼
Neo4j AuraDB (Graph queries)
     │
     ▼
Answer returned as JSON
```

---

## Files

| File | Description |
|------|-------------|
| `agent.py` | Flask app — AI agent + Neo4j query logic |
| `requirements.txt` | Python dependencies |
| `Dockerfile` | Container image definition |
| `serving_template.yaml` | SAP AI Core serving template |

---

## Step 1: Build & Push Docker Image

```bash
# Login to your Docker registry
docker login <YOUR_DOCKER_REGISTRY>

# Build image
docker build -t <YOUR_DOCKER_REGISTRY>/supply-chain-agent:latest .

# Push image
docker push <YOUR_DOCKER_REGISTRY>/supply-chain-agent:latest
```

---

## Step 2: Register Neo4j Secret in AI Launchpad (No Code Needed)

1. Open **SAP AI Launchpad**
2. Go to **Administration** → **Generic Secrets**
3. Click **Create** and fill in:
   - **Name:** `neo4j-secret`
   - **Resource Group:** `default`
   - Key-value pairs:

| Key | Value |
|-----|-------|
| `NEO4J_URI` | `neo4j+s://59d34f34.databases.neo4j.io` |
| `NEO4J_USERNAME` | `neo4j` |
| `NEO4J_PASSWORD` | *(your password)* |

4. Click **Create**

> The secret is automatically mounted into the container at `/run/secrets/neo4j-secret/` — no credentials in code or config files.

---

## Step 3: Register Docker Registry Secret in AI Core

In AI Launchpad → Administration → Docker Registry Secrets:
- Name: `docker-registry-secret`
- Server: your registry URL
- Username / Password: your credentials

---

## Step 4: Sync Serving Template

Put `serving_template.yaml` in your AI Core GitHub repository sync folder, or apply via API:

```bash
curl -X POST <AICORE_API>/v1/lm/servingConfigurations \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "supply-chain-agent-config",
    "executableId": "supply-chain-agent-serving",
    "scenarioId": "supply-chain-agent"
  }'
```

---

## Step 5: Create Deployment

```bash
curl -X POST <AICORE_API>/v1/lm/deployments \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"configurationId": "<config-id-from-step-4>"}'
```

---

## Step 6: Test the Deployed Agent

Once deployment status is `RUNNING`, call the endpoint:

```bash
curl -X POST <DEPLOYMENT_URL>/v1/predict \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the top products?"}'
```

Expected response:
```json
{
  "question": "What are the top products?",
  "answer": "Top ordered products:\n1. Field & Stream ..."
}
```

---

## Supported Questions

| Question | Description |
|----------|-------------|
| `What are the top products?` | Top 5 most ordered products |
| `Show late deliveries` | Orders with late delivery status |
| `Show products from supplier Fan Shop` | Products from a specific supplier |
| `Graph summary` | Node counts by label |
| `Show orders for customer 12345` | All orders for a customer ID |
