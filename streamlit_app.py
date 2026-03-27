import time

import streamlit as st

from agent.pharma_agent import ask


st.set_page_config(page_title="Pharma GraphRAG", layout="wide")


NEO4J_GREEN = "#00B04F"

def _format_answer_for_display(answer: str) -> str:
    """
    - Truncate 'Suppliers:' lists to 3 items + 'and X more...'
    - Preserve line breaks while still allowing markdown (e.g., **bold**).
    """
    if not answer:
        return ""

    out_lines: list[str] = []
    for line in answer.splitlines():
        if "Suppliers:" in line:
            prefix, rest = line.split("Suppliers:", 1)
            suppliers = [s.strip() for s in rest.split(",") if s.strip()]
            if len(suppliers) > 3:
                shown = ", ".join(suppliers[:3])
                remaining = len(suppliers) - 3
                line = f"{prefix}Suppliers: {shown} and {remaining} more..."
        out_lines.append(line)

    # In Markdown, single newlines don't always render as line breaks.
    # Two trailing spaces forces a line break while preserving markdown styling.
    return "  \n".join(out_lines)

def _reasoning_path(tool: str | None) -> str:
    tool = (tool or "").strip().upper()
    if tool == "SUPPLIER_IMPACT":
        return "Supplier → Ingredient → Batch → Facility → Product"
    if tool == "CONTAMINATION_SEARCH":
        return "Query → Vector search (QC text) → Similar Batches → (Ingredients → Suppliers) + Facility"
    if tool == "AGGREGATION":
        return "Question → Text2Cypher → Neo4j query → Aggregated result"
    return "Question → Router → Selected tool → Result"

def render_home() -> None:
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
        margin-bottom: 22px;
        font-size: 0.98rem;
    }}

    .tool-badge {{
        display: inline-block;
        background: var(--neo4j-green);
        color: #07130b;
        font-weight: 800;
        padding: 0.25rem 0.7rem;
        border-radius: 999px;
        letter-spacing: 0.02em;
        text-transform: uppercase;
        font-size: 0.85rem;
    }}

    .reasoning-path {{
        color: var(--muted);
        margin-top: 6px;
        margin-bottom: 10px;
        font-size: 0.92rem;
    }}

    .response-panel {{
        background: var(--panel);
        border: 1px solid var(--panel-border);
        border-radius: 12px;
        padding: 16px;
    }}
</style>
""",
        unsafe_allow_html=True,
    )

    st.title("Pharma Supply Chain GraphRAG Agent")
    st.markdown(
        "<div class='neo4j-subtitle'>Uses Neo4j + LangChain to answer pharmaceutical supply chain questions.</div>",
        unsafe_allow_html=True,
    )

    # Sidebar: Knowledge graph stats
    st.sidebar.header("Knowledge Graph Stats")
    st.sidebar.metric("Total Batches", 200)
    st.sidebar.metric("Suppliers", 20)
    st.sidebar.metric("Facilities", 10)
    st.sidebar.metric("Ingredients", 20)
    st.sidebar.metric("Products", 8)

    example_questions = [
        "Which batches are at risk if supplier BioSynth AG is recalled?",
        "Find batches with similar contamination patterns to crystalline deposits in API",
        "How many batches failed QC from European suppliers in 2023?",
    ]

    if "question" not in st.session_state:
        st.session_state["question"] = ""

    st.subheader("Ask a question")
    st.caption("Pick an example or type your own question.")

    cols = st.columns(3)
    for i, ex in enumerate(example_questions):
        if cols[i].button(ex, key=f"ex_{i}"):
            st.session_state["question"] = ex

    custom_question = st.text_input("Custom question", value=st.session_state["question"])
    st.session_state["question"] = custom_question

    ask_col, _ = st.columns([1, 3])
    with ask_col:
        ask_submit = st.button("Ask", type="primary")

    if "last_tool" not in st.session_state:
        st.session_state["last_tool"] = None
    if "last_answer" not in st.session_state:
        st.session_state["last_answer"] = None
    if "last_elapsed" not in st.session_state:
        st.session_state["last_elapsed"] = None

    st.subheader("Response")
    if st.session_state["last_tool"] is not None and st.session_state["last_answer"] is not None:
        st.markdown("<div class='response-panel'>", unsafe_allow_html=True)
        st.markdown(
            f"<span class='tool-badge'>{st.session_state['last_tool']}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div class='reasoning-path'><b>Traversal</b>: {_reasoning_path(st.session_state['last_tool'])}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(_format_answer_for_display(st.session_state["last_answer"]))
        st.caption(f"Response time: {st.session_state['last_elapsed']:.2f} seconds")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Enter a question and click `Ask` to see the answer.")

    if ask_submit and custom_question.strip():
        # Clear previous response immediately so the old answer doesn't linger
        st.session_state["last_tool"] = None
        st.session_state["last_answer"] = ""
        st.session_state["last_elapsed"] = None

        with st.spinner("GraphRAG is working..."):
            start = time.perf_counter()
            result = ask(custom_question.strip())
            elapsed = time.perf_counter() - start

        st.session_state["last_tool"] = str(result.get("tool") or "AGGREGATION")
        st.session_state["last_answer"] = result.get("answer") or ""
        st.session_state["last_elapsed"] = elapsed
        st.rerun()


pg = st.navigation(
    [
        st.Page(render_home, title="Pharma GraphRAG", default=True),
        st.Page("pages/01_About.py", title="About"),
    ],
    position="sidebar",
)
pg.run()

