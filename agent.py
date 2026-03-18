"""
Supply Chain AI Agent - SAP AI Core Deployment
Connects to Neo4j AuraDB and answers supply chain questions via a REST API.
"""

import os
import re
import json
from flask import Flask, request, jsonify
from py2neo import Graph

app = Flask(__name__)

# --- Load Neo4j credentials ---
# SAP AI Core mounts secrets as files under /run/secrets/<secret-name>/<key>
# Fallback to environment variables for local development

def load_secret(key: str, secret_name: str = "neo4j-secret") -> str:
    """Load Neo4j credentials from environment variables injected by serving_template.yaml."""
    value = os.environ.get(key)
    if value:
        return value
    raise RuntimeError(
        f"Environment variable '{key}' not found. "
        f"Ensure it is set in the serving_template.yaml env section."
    )

NEO4J_URI = load_secret("NEO4J_URI")
NEO4J_USERNAME = load_secret("NEO4J_USERNAME")
NEO4J_PASSWORD = load_secret("NEO4J_PASSWORD")

graph = Graph(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

# ─── Query Tools ────────────────────────────────────────────────────────────

def query_top_products(limit=5):
    return graph.run("""
        MATCH (o:Order)-[:CONTAINS]->(p:Product)
        RETURN p.name AS product, count(o) AS order_count
        ORDER BY order_count DESC LIMIT $limit
    """, limit=limit).data()

def query_late_orders():
    return graph.run("""
        MATCH (o:Order)
        WHERE o.status = 'Late delivery'
        RETURN o.order_id AS order_id, o.order_date AS date
        LIMIT 10
    """).data()

def query_supplier_products(name):
    return graph.run("""
        MATCH (p:Product)-[:SUPPLIED_BY]->(s:Supplier)
        WHERE toLower(s.name) CONTAINS toLower($name)
        RETURN p.name AS product, s.name AS supplier
        LIMIT 10
    """, name=name).data()

def query_graph_summary():
    return graph.run("""
        MATCH (n)
        RETURN labels(n)[0] AS label, count(n) AS count
        ORDER BY count DESC
    """).data()

def query_customer_orders(customer_id):
    return graph.run("""
        MATCH (c:Customer {customer_id: $cid})-[:PLACED]->(o:Order)
        RETURN o.order_id AS order_id, o.status AS status, o.order_date AS date
        LIMIT 10
    """, cid=customer_id).data()

# ─── Agent Logic ─────────────────────────────────────────────────────────────

def supply_chain_agent(question: str) -> str:
    q = question.lower()

    if "top" in q and "product" in q:
        data = query_top_products(5)
        lines = [f"{i+1}. {r['product']} ({r['order_count']} orders)" for i, r in enumerate(data)]
        return "Top ordered products:\n" + "\n".join(lines)

    elif "late" in q or "delayed" in q:
        data = query_late_orders()
        if not data:
            return "No late deliveries found."
        lines = [f"Order {r['order_id']} on {r['date']}" for r in data]
        return f"Late deliveries ({len(data)} found):\n" + "\n".join(lines)

    elif "supplier" in q:
        parts = q.split("supplier")
        name = parts[-1].strip().strip("?").strip() or "shop"
        data = query_supplier_products(name)
        if not data:
            return f"No products found for supplier containing '{name}'."
        lines = [f"{r['product']} → {r['supplier']}" for r in data]
        return f"Products from supplier '{name}':\n" + "\n".join(lines)

    elif "summary" in q or "how many" in q or "count" in q:
        data = query_graph_summary()
        lines = [f"{r['label']}: {r['count']} nodes" for r in data]
        return "Graph Summary:\n" + "\n".join(lines)

    elif "customer" in q:
        ids = re.findall(r'\d+', question)
        if ids:
            data = query_customer_orders(int(ids[0]))
            if not data:
                return f"No orders found for customer {ids[0]}."
            lines = [f"Order {r['order_id']} | {r['status']} | {r['date']}" for r in data]
            return f"Orders for customer {ids[0]}:\n" + "\n".join(lines)
        return "Please provide a customer ID, e.g. 'Show orders for customer 12345'."

    return ("I can answer:\n"
            "- 'What are the top products?'\n"
            "- 'Show late deliveries'\n"
            "- 'Show products from supplier Fan Shop'\n"
            "- 'Graph summary'\n"
            "- 'Show orders for customer 12345'")

# ─── Flask API Endpoints ──────────────────────────────────────────────────────

@app.route("/v1/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/v1/predict", methods=["POST"])
def predict():
    data = request.get_json()
    question = data.get("question", "")
    if not question:
        return jsonify({"error": "No question provided"}), 400
    answer = supply_chain_agent(question)
    return jsonify({"question": question, "answer": answer})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
