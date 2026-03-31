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

def _split_into_batch_blocks(answer: str) -> tuple[list[str], list[list[str]]]:
    """
    Splits agent output into:
    - header lines (before the first 'Batch ...' line)
    - batch blocks (each starts at a line whose left-stripped text begins with 'Batch ')

    Each batch block includes all lines until the next batch header line.
    """
    if not answer:
        return [], []

    lines = answer.splitlines()
    start_indices: list[int] = []
    for i, line in enumerate(lines):
        if line.lstrip().startswith("Batch "):
            start_indices.append(i)

    if not start_indices:
        return lines, []

    header = lines[: start_indices[0]]
    blocks: list[list[str]] = []
    for idx, start_i in enumerate(start_indices):
        end_i = start_indices[idx + 1] if idx + 1 < len(start_indices) else len(lines)
        blocks.append(lines[start_i:end_i])
    return header, blocks

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

    .ask-section-subtitle {{
        color: var(--muted);
        font-size: 0.88rem;
        opacity: 0.88;
        margin-top: -6px;
        margin-bottom: 10px;
        line-height: 1.45;
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

    pending_q = st.session_state.get("_pending_ask")

    st.subheader("Ask a question")
    st.markdown(
        "<div class='ask-section-subtitle'>Best for: supplier recall impact, contamination pattern search, "
        "and supply chain analytics</div>",
        unsafe_allow_html=True,
    )
    st.caption("Pick an example or type your own question.")

    cols = st.columns(3)
    for i, ex in enumerate(example_questions):
        if cols[i].button(ex, key=f"ex_{i}", disabled=bool(pending_q)):
            st.session_state["question"] = ex

    custom_question = st.text_input(
        "Custom question",
        value=pending_q or st.session_state["question"],
        disabled=bool(pending_q),
    )
    if not pending_q:
        st.session_state["question"] = custom_question

    ask_col, _ = st.columns([1, 3])
    with ask_col:
        ask_submit = st.button("Ask", type="primary", disabled=bool(pending_q))

    if pending_q:
        with st.spinner("GraphRAG is working..."):
            start = time.perf_counter()
            result = ask(pending_q)
            elapsed = time.perf_counter() - start

        tool = str(result.get("tool") or "AGGREGATION")
        st.session_state["last_tool"] = tool
        # For contamination search, use the raw tool output (has correct PASS/FAIL + similarity scores)
        if tool == "CONTAMINATION_SEARCH":
            st.session_state["last_answer"] = result.get("context") or result.get("answer") or ""
        else:
            st.session_state["last_answer"] = result.get("answer") or ""
        st.session_state["last_elapsed"] = elapsed
        del st.session_state["_pending_ask"]
        st.rerun()

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

        # Pagination / load-more for batch-heavy responses
        show_load_more_tools = {"SUPPLIER_IMPACT", "CONTAMINATION_SEARCH"}
        last_tool = str(st.session_state["last_tool"]).strip().upper()
        last_answer = st.session_state["last_answer"]

        header, batch_blocks = _split_into_batch_blocks(last_answer)
        initial_blocks_shown = 5

        if last_tool in show_load_more_tools and batch_blocks:
            shown = int(st.session_state.get("_shown_batch_blocks", initial_blocks_shown))
            shown = max(1, min(shown, len(batch_blocks)))

            displayed_lines = header + [ln for block in batch_blocks[:shown] for ln in block]
            displayed_answer = "\n".join(displayed_lines)
            st.markdown(_format_answer_for_display(displayed_answer))

            if shown < len(batch_blocks):
                st.caption(f"Showing {shown} of {len(batch_blocks)} batches")
                if st.button("Load more batches"):
                    st.session_state["_shown_batch_blocks"] = shown + 5
                    st.rerun()
        else:
            st.markdown(_format_answer_for_display(last_answer))

        st.caption(f"Response time: {st.session_state['last_elapsed']:.2f} seconds")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Enter a question and click `Ask` to see the answer.")

    if ask_submit and custom_question.strip() and not pending_q:
        st.session_state["_pending_ask"] = custom_question.strip()
        st.session_state["question"] = custom_question.strip()
        st.session_state["last_tool"] = None
        st.session_state["last_answer"] = ""
        st.session_state["last_elapsed"] = None
        st.session_state["_shown_batch_blocks"] = 5
        st.rerun()


pg = st.navigation(
    [
        st.Page(render_home, title="Pharma GraphRAG", default=True),
        st.Page("pages/01_About.py", title="About"),
    ],
    position="sidebar",
)
pg.run()

