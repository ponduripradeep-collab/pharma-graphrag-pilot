# Pharma GraphRAG Pilot

A pilot project demonstrating Graph-based Retrieval-Augmented Generation (GraphRAG) for pharmaceutical supply chain use cases using Neo4j AuraDB.

## Why GraphRAG?

Plain RAG retrieves text chunks by semantic similarity — it finds what *sounds like* your question.
GraphRAG goes further: after finding similar nodes, it traverses relationships to pull in connected
structured context. For pharmaceutical supply chain, this means:

- "Which batches are at risk from this supplier?" requires 3-hop graph traversal —
  impossible with plain RAG
- Contamination investigations need both semantic similarity (find similar failures)
  AND graph context (which suppliers, facilities, ingredients are connected)
- Regulatory traceability requires complete lineage — not just similar text chunks

This pilot demonstrates all three patterns on a realistic pharma dataset.

## Overview

This project builds a pharmaceutical supply chain knowledge graph in Neo4j and provides an intelligent agent that answers natural language questions using three retrieval strategies:

- **Supplier impact analysis** — templated Cypher queries to trace which batches are at risk from a supplier recall
- **Contamination similarity search** — vector search over QC descriptions to find batches with similar failure patterns
- **Aggregation / analytics** — Text2Cypher (LLM-generated Cypher) for ad-hoc counting, grouping, and filtering

## Tech Stack

- **Neo4j AuraDB** — hosted graph database
- **LangGraph** — agent workflow orchestration (classify → retrieve → generate)
- **LangChain** — Neo4j integration, vector store, GraphCypherQAChain
- **OpenAI** — `gpt-4o-mini` for routing and generation, `text-embedding-ada-002` for QC embeddings

## Graph Schema

**Nodes**

| Label | Key Properties |
|-------|---------------|
| `Batch` | `id`, `product_name`, `qc_passed`, `status`, `manufacturing_date`, `quarter`, `year`, `batch_size_kg`, `qc_description`, `qcEmbedding` (vector) |
| `Supplier` | `id`, `name`, `country`, `region`, `tier`, `qualified` |
| `Facility` | `id`, `name`, `location`, `country`, `fda_registered` |
| `Ingredient` | `id`, `name`, `type` (API/Excipient/Solvent), `controlled` |
| `Product` | `id`, `name`, `therapeutic_area` |

**Relationships**

```
(Batch)-[:CONTAINS {quantity_kg, lot_number}]->(Ingredient)
(Ingredient)-[:SUPPLIED_BY]->(Supplier)
(Batch)-[:MANUFACTURED_AT]->(Facility)
(Batch)-[:PRODUCES]->(Product)
```

> Note: There is no direct Batch→Supplier relationship. Always traverse via Ingredient.

## Project Structure

```
pharma-graphrag-pilot/
├── .env                          # AuraDB + OpenAI credentials (see below)
├── requirements.txt              # Python dependencies
├── data/
│   ├── generate_data.py          # Generates synthetic pharma_data.json (200 batches)
│   └── pharma_data.json          # Generated synthetic dataset
├── setup/
│   ├── load_data.py              # Loads nodes and relationships into Neo4j
│   ├── create_embeddings.py      # Generates QC embeddings and creates vector index
│   └── pharma_data.json          # Copy of data used by setup scripts
├── agent/
│   └── pharma_agent.py           # LangGraph agent with 3 retrieval tools
├── testing/
│   └── similarity_pattern_test.py # Standalone vector similarity search test
└── README.md
```

## Environment Variables

Create a `.env` file in the project root:

```env
NEO4J_URI=neo4j+s://<your-aura-instance>.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<your-password>
NEO4J_DATABASE=neo4j
OPENAI_API_KEY=sk-...
```

## Getting Started

**1. Install dependencies**

```bash
pip install -r requirements.txt
```

**2. Generate synthetic data**

```bash
cd data
python generate_data.py
# Outputs: data/pharma_data.json (20 suppliers, 10 facilities, 20 ingredients, 8 products, 200 batches)
```

**3. Load data into Neo4j**

```bash
cd setup
python load_data.py
```

**4. Create embeddings and vector index**

```bash
cd setup
python create_embeddings.py
# Embeds qc_description for all 200 Batch nodes using text-embedding-ada-002
# Creates a cosine vector index named 'batchQCEmbeddings'
```

**5. Run the agent**

```bash
cd agent
python pharma_agent.py
```

## Example Questions

```python
from agent.pharma_agent import ask

# Supplier impact (Cypher template)
ask("Which batches are at risk if supplier BioSynth AG is recalled?")

# Contamination similarity (vector search + graph traversal)
ask("Find batches with similar contamination patterns to crystalline deposits in active pharmaceutical ingredient")

# Aggregation (Text2Cypher)
ask("How many batches failed QC from European suppliers in 2023?")
```

## License

MIT
