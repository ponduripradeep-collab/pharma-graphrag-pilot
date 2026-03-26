import streamlit as st


st.set_page_config(page_title="About • Pharma Supply Chain GraphRAG Agent", layout="wide")

NEO4J_GREEN = "#00B04F"

st.markdown(
    f"""
<style>
    :root {{
        --neo4j-green: {NEO4J_GREEN};
        --bg: #0b0f14;
        --panel: #111827;
        --panel-border: #1f2937;
        --text: #E8EAED;
        --muted: #9CA3AF;
    }}

    html, body, .stApp {{
        background-color: var(--bg);
        color: var(--text);
    }}

    .neo4j-subtitle {{
        color: var(--muted);
        margin-top: -14px;
        margin-bottom: 18px;
        font-size: 0.98rem;
    }}

    .panel {{
        background: var(--panel);
        border: 1px solid var(--panel-border);
        border-radius: 12px;
        padding: 16px;
    }}

    .tag {{
        display: inline-block;
        border: 1px solid var(--panel-border);
        background: rgba(0, 176, 79, 0.10);
        color: var(--text);
        padding: 0.18rem 0.55rem;
        border-radius: 999px;
        font-weight: 700;
        font-size: 0.82rem;
        margin-right: 0.35rem;
        margin-bottom: 0.35rem;
    }}
</style>
""",
    unsafe_allow_html=True,
)


st.title("What this app does")
st.markdown(
    "<div class='neo4j-subtitle'>A Neo4j + LangChain GraphRAG demo for pharmaceutical supply chain investigations.</div>",
    unsafe_allow_html=True,
)

st.markdown("<div class='panel'>", unsafe_allow_html=True)
st.markdown(
    """
This app lets you ask natural-language questions about a **pharmaceutical supply chain knowledge graph**.
Instead of only retrieving “similar text”, it combines:

- **Graph traversal (Neo4j)** for traceability across suppliers → ingredients → batches → facilities
- **Vector similarity search** for finding batches with similar QC / contamination narratives
- **LLM-powered analytics** for ad-hoc counts, filters, and aggregations
"""
)
st.markdown("</div>", unsafe_allow_html=True)


st.subheader("Links")
st.markdown(
    """
- Source code: [github.com/ponduripradeep-collab/pharma-graphrag-pilot](https://github.com/ponduripradeep-collab/pharma-graphrag-pilot)
- Article: [What a 90,000-bottle drug recall reveals about GraphRAG](https://www.linkedin.com/pulse/what-90000-bottle-drug-recall-reveals-graphrag-pradeep-ponduri-b4o2c/?trackingId=jybLtso7RxuFdgcpYMaiLA%3D%3D)
"""
)


st.subheader("How answers are generated (backend)")
st.markdown("<div class='panel'>", unsafe_allow_html=True)
st.markdown(
    """
Each question is **routed to one of three tools**:

- **`SUPPLIER_IMPACT`**: a templated Cypher query that traces which batches contain ingredients supplied by a given supplier.
- **`CONTAMINATION_SEARCH`**: vector search over batch QC descriptions to find similar failure patterns, then graph lookups to pull suppliers, facilities, and ingredients for each match.
- **`AGGREGATION`**: Text2Cypher (LLM-generated Cypher) for analytics questions like “how many”, “group by”, and time/region filtering.

The routing + tool execution runs as a small workflow: **classify → retrieve → generate**.
"""
)
st.markdown("</div>", unsafe_allow_html=True)


st.subheader("What I built behind the scenes")
left, right = st.columns([1, 1])

with left:
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.markdown(
        """
**Knowledge graph design (Neo4j)**

- Nodes: `Batch`, `Supplier`, `Facility`, `Ingredient`, `Product`
- Relationships:
  - `(Batch)-[:CONTAINS]->(Ingredient)`
  - `(Ingredient)-[:SUPPLIED_BY]->(Supplier)`
  - `(Batch)-[:MANUFACTURED_AT]->(Facility)`
  - `(Batch)-[:PRODUCES]->(Product)`

This structure supports real traceability questions (e.g., supplier recalls) by requiring multi-hop traversal.
"""
    )
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.markdown(
        """
**Vector search + embeddings**

- Embedded each batch’s QC narrative (`qc_description`) into a vector stored on `Batch` nodes.
- Created a Neo4j vector index used for semantic similarity queries.
- After retrieving similar batches, the app pulls **graph context** (suppliers, ingredients, facility) to explain why those results matter.
"""
    )
    st.markdown("</div>", unsafe_allow_html=True)


st.subheader("Key implementation files")
st.markdown("<div class='panel'>", unsafe_allow_html=True)
st.markdown(
    """
- **Agent (routing + tools)**: `agent/pharma_agent.py`
- **Data generation**: `data/generate_data.py`
- **Load graph into Neo4j**: `setup/load_data.py`
- **Create embeddings + vector index**: `setup/create_embeddings.py`
- **Streamlit UI**: `streamlit_app.py` + `pages/01_About.py`
"""
)
st.markdown("</div>", unsafe_allow_html=True)


st.subheader("Tech stack")
st.markdown("<div class='panel'>", unsafe_allow_html=True)
st.markdown(
    """
<span class="tag">Neo4j</span>
<span class="tag">LangChain</span>
<span class="tag">LangGraph</span>
<span class="tag">OpenAI</span>
<span class="tag">Streamlit</span>
""",
    unsafe_allow_html=True,
)
st.markdown(
    """
- **Neo4j** stores the supply chain graph and supports Cypher + vector indexes.
- **LangChain** provides Neo4j integration and LLM utilities.
- **LangGraph** orchestrates the agent workflow (router + retrieval + response generation).
- **Streamlit** provides the UI.
"""
)
st.markdown("</div>", unsafe_allow_html=True)


st.subheader("Configuration (runtime)")
st.markdown("<div class='panel'>", unsafe_allow_html=True)
st.markdown(
    """
The agent reads credentials from a `.env` file in the repo root:

- `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`
- `OPENAI_API_KEY`
"""
)
st.markdown("</div>", unsafe_allow_html=True)

