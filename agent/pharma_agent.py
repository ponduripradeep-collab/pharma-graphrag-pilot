import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

from langchain_neo4j import Neo4jGraph, Neo4jVector
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_neo4j import GraphCypherQAChain
from langgraph.graph import START, StateGraph
from langchain_core.messages import HumanMessage, AIMessage
from typing_extensions import List, TypedDict

# ── Connections ───────────────────────────────────────────────────────────────

graph = Neo4jGraph(
    url=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USERNAME"),
    password=os.getenv("NEO4J_PASSWORD"),
    database=os.getenv("NEO4J_DATABASE", "neo4j"),
    enhanced_schema=False
)

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY")
)

embedding_model = OpenAIEmbeddings(
    model="text-embedding-ada-002",
    api_key=os.getenv("OPENAI_API_KEY")
)

# ── Vector store ──────────────────────────────────────────────────────────────

vector_store = Neo4jVector.from_existing_index(
    embedding_model,
    graph=graph,
    index_name="batchQCEmbeddings",
    embedding_node_property="qcEmbedding",
    text_node_property="qc_description",
    retrieval_query="""
        RETURN node.qc_description AS text,
               score,
               {
                   id: node.id,
                   product_name: node.product_name,
                   qc_passed: node.qc_passed,
                   status: node.status,
                   manufacturing_date: node.manufacturing_date,
                   year: node.year
               } AS metadata
    """
)

# ── Tool 1: Supplier impact (Cypher template) ─────────────────────────────────

SUPPLIER_IMPACT_QUERY = """
MATCH (s:Supplier {name: $supplier_name})
<-[:SUPPLIED_BY]-(i:Ingredient)
<-[:CONTAINS]-(b:Batch)
-[:MANUFACTURED_AT]->(f:Facility)
RETURN 
    b.id AS batch_id,
    b.status AS status,
    b.qc_passed AS qc_passed,
    b.product_name AS product,
    b.manufacturing_date AS mfg_date,
    i.name AS ingredient,
    f.name AS facility
ORDER BY b.manufacturing_date DESC
"""

def supplier_impact_tool(supplier_name: str) -> str:
    """Find all batches at risk if a supplier is recalled."""
    with graph._driver.session(database=os.getenv("NEO4J_DATABASE", "neo4j")) as session:
        result = session.run(SUPPLIER_IMPACT_QUERY, supplier_name=supplier_name)
        records = result.data()

    if not records:
        return f"No batches found for supplier '{supplier_name}'. Check the supplier name."

    lines = [f"Supplier recall impact analysis for: {supplier_name}",
             f"Total affected batches: {len(records)}\n"]

    for r in records:
        status = "✅ PASS" if r["qc_passed"] else "❌ FAIL"
        lines.append(
            f"  Batch {r['batch_id']} [{status}] — {r['product']} "
            f"| Ingredient: {r['ingredient']} "
            f"| Facility: {r['facility']} "
            f"| Date: {r['mfg_date']}"
        )
    return "\n".join(lines)

# ── Tool 2: Contamination similarity (Vector + Graph retrieval) ───────────────

GRAPH_CONTEXT_QUERY = """
MATCH (b:Batch {id: $batch_id})
OPTIONAL MATCH (b)-[:CONTAINS]->(i:Ingredient)-[:SUPPLIED_BY]->(s:Supplier)
OPTIONAL MATCH (b)-[:MANUFACTURED_AT]->(f:Facility)
RETURN 
    b.id AS batch_id,
    b.status AS status,
    b.qc_passed AS qc_passed,
    b.product_name AS product,
    b.manufacturing_date AS mfg_date,
    b.qc_description AS qc_description,
    collect(DISTINCT i.name) AS ingredients,
    collect(DISTINCT s.name) AS suppliers,
    f.name AS facility
"""

def contamination_similarity_tool(query: str, k: int = 3) -> str:
    """Find batches with similar contamination patterns using vector search + graph context."""
    # Step 1: Vector similarity search
    similar_docs = vector_store.similarity_search_with_score(query, k=k)

    if not similar_docs:
        return "No similar batches found."

    lines = [f"Similar contamination patterns for: '{query}'\n"]

    # Step 2: Graph traversal for each similar batch
    with graph._driver.session(database=os.getenv("NEO4J_DATABASE", "neo4j")) as session:
        for doc, score in similar_docs:
            batch_id = doc.metadata.get("id")
            if not batch_id:
                continue

            result = session.run(GRAPH_CONTEXT_QUERY, batch_id=batch_id)
            record = result.single()

            if record:
                status = "✅ PASS" if record["qc_passed"] else "❌ FAIL"
                lines.append(f"Batch {record['batch_id']} [{status}] — similarity score: {score:.4f}")
                lines.append(f"  Product: {record['product']}")
                lines.append(f"  Facility: {record['facility']}")
                lines.append(f"  Suppliers: {', '.join(record['suppliers'])}")
                lines.append(f"  Ingredients: {', '.join(record['ingredients'][:3])}")
                lines.append(f"  QC Note: {record['qc_description'][:120]}...")
                lines.append("")

    return "\n".join(lines)

# ── Tool 3: Aggregation (Text2Cypher) ─────────────────────────────────────────

CYPHER_PROMPT = PromptTemplate(
    input_variables=["schema", "question"],
    template="""You are an expert Neo4j Cypher query generator for a pharmaceutical supply chain knowledge graph.

Graph schema:
Nodes: Batch, Supplier, Facility, Ingredient, Product
Relationships: 
  (Batch)-[:CONTAINS]->(Ingredient)
  (Ingredient)-[:SUPPLIED_BY]->(Supplier)
  (Batch)-[:MANUFACTURED_AT]->(Facility)
  (Batch)-[:PRODUCES]->(Product)

Key properties:
- Batch: id, product_name, qc_passed, status, quarter, year, batch_size_kg
- Supplier: name, country, region
- Facility: name, location, country, fda_registered
- Ingredient: name, type, controlled
- Product: name, therapeutic_area

IMPORTANT: There is NO direct relationship between Batch and Supplier.
To find supplier of a batch you MUST traverse: (Batch)-[:CONTAINS]->(Ingredient)-[:SUPPLIED_BY]->(Supplier)

Important node properties:
- Batch: id, product_name, qc_passed (boolean), status, manufacturing_date, quarter, year, batch_size_kg
- Supplier: name, country, region (Europe/Asia/North America), tier
- Facility: name, location, country, fda_registered
- Ingredient: name, type (API/Excipient/Solvent), controlled
- Product: name, therapeutic_area

Generate a Cypher query to answer: {question}

Rules:
- Use MATCH and RETURN, never DELETE or CREATE
- For regional queries use supplier.region property
- For time queries use batch.quarter and batch.year properties
- Always return meaningful column names
- Limit results to 20 unless asked for all

Cypher query (no explanation, just the query):"""
)
llm_mini = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY")
)
text2cypher_chain = GraphCypherQAChain.from_llm(
    llm=llm_mini,
    graph=graph,
    cypher_prompt=CYPHER_PROMPT,
    verbose=False,
    allow_dangerous_requests=True
)

def aggregation_tool(question: str) -> str:
    try:
        cypher = llm_mini.invoke(
            CYPHER_PROMPT.format(question=question)
        ).content.strip()
        cypher = cypher.replace("```cypher", "").replace("```", "").strip()
        print(f"   Generated Cypher: {cypher}")
        result = graph.query(cypher)
        
        answer = llm_mini.invoke(
            f"Question: {question}\nData: {result}\nAnswer concisely:"
        ).content
        return answer
    except Exception as e:
        return f"Error: {str(e)}"

# ── Agent router ──────────────────────────────────────────────────────────────

ROUTER_PROMPT = """You are a pharmaceutical supply chain assistant.
Classify the user question into exactly one category:

SUPPLIER_IMPACT - questions about which batches are affected by a specific supplier recall or risk
CONTAMINATION_SEARCH - questions about finding batches with similar contamination or QC failure patterns  
AGGREGATION - questions involving counting, grouping, statistics, or filtering across multiple batches

Question: {question}

Respond with ONLY one word: SUPPLIER_IMPACT, CONTAMINATION_SEARCH, or AGGREGATION"""

def route_question(question: str) -> str:
    """Use LLM to route question to the right tool."""
    response = llm.invoke(ROUTER_PROMPT.format(question=question))
    route = response.content.strip().upper()
    if route not in ["SUPPLIER_IMPACT", "CONTAMINATION_SEARCH", "AGGREGATION"]:
        return "AGGREGATION"
    return route

# ── Agent state & workflow ────────────────────────────────────────────────────

class AgentState(TypedDict):
    question: str
    route: str
    context: str
    answer: str
    chat_history: List

ANSWER_PROMPT = PromptTemplate.from_template("""You are a pharmaceutical supply chain expert assistant.
Answer the question based on the retrieved context.
Be specific, cite batch IDs and supplier names where relevant.
If the context shows quality failures, highlight the risk clearly.

Context:
{context}

Question: {question}

Answer:""")

def classify(state: AgentState):
    route = route_question(state["question"])
    print(f"\n🔀 Routing to: {route}")
    return {"route": route}

def retrieve(state: AgentState):
    question = state["question"]
    route = state["route"]

    if route == "SUPPLIER_IMPACT":
        # Extract supplier name from question
        extract_prompt = f"Extract only the supplier company name from this question, nothing else: {question}"
        supplier_name = llm.invoke(extract_prompt).content.strip()
        print(f"🏭 Supplier identified: {supplier_name}")
        context = supplier_impact_tool(supplier_name)

    elif route == "CONTAMINATION_SEARCH":
        print(f"🔍 Running vector similarity search...")
        context = contamination_similarity_tool(question)
        print(f"\n📋 Context being passed to generate:\n{context}\n")

    else:
        print(f"📊 Running Text2Cypher aggregation...")
        context = aggregation_tool(question)

    return {"context": context}

def generate(state: AgentState):
    messages = ANSWER_PROMPT.invoke({
        "question": state["question"],
        "context": state["context"]
    })
    response = llm.invoke(messages)
    return {"answer": response.content}

# Build workflow
workflow = StateGraph(AgentState)
workflow.add_sequence([classify, retrieve, generate])
workflow.add_edge(START, "classify")
app = workflow.compile()

# ── Run agent ─────────────────────────────────────────────────────────────────

def ask(question: str) -> str:
    """Ask the pharma supply chain agent a question."""
    print(f"\n{'='*60}")
    print(f"Question: {question}")
    print('='*60)

    response = app.invoke({
        "question": question,
        "route": "",
        "context": "",
        "answer": "",
        "chat_history": []
    })

    print(f"\n💊 Answer:\n{response['answer']}")
    return response["answer"]

# ── Demo ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 Pharma Supply Chain GraphRAG Agent")
    print("   Powered by Neo4j + LangChain + OpenAI\n")

    # # Demo question 1 — Cypher template
    # ask("Which batches are at risk if supplier BioSynth AG is recalled?")

    # Demo question 2 — Vector similarity + graph retrieval
    ask("Find batches with similar contamination patterns to crystalline deposits in active pharmaceutical ingredient")

    # # Demo question 3 — Text2Cypher aggregation
    # ask("How many batches failed QC from European suppliers in 2023?")