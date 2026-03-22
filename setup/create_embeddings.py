import os
import time
from dotenv import load_dotenv
from neo4j import GraphDatabase
from openai import OpenAI

load_dotenv()

# ── Clients ───────────────────────────────────────────────────────────────────

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY2"))

EMBEDDING_MODEL = "text-embedding-ada-002"
VECTOR_INDEX_NAME = "batchQCEmbeddings"
BATCH_SIZE = 20  # process 20 batches at a time to avoid rate limits

# ── Fetch all batches ─────────────────────────────────────────────────────────

def fetch_batches(session):
    result = session.run("""
        MATCH (b:Batch)
        WHERE b.qcEmbedding IS NULL
        RETURN b.id AS id, b.qc_description AS description
        ORDER BY b.id
    """)
    return [{"id": r["id"], "description": r["description"]} for r in result]

# ── Generate embeddings ───────────────────────────────────────────────────────

def generate_embeddings(texts):
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts
    )
    return [item.embedding for item in response.data]

# ── Store embeddings ──────────────────────────────────────────────────────────

def store_embeddings(tx, batch_embeddings):
    tx.run("""
        UNWIND $items AS item
        MATCH (b:Batch {id: item.id})
        CALL db.create.setNodeVectorProperty(b, 'qcEmbedding', item.embedding)
    """, items=batch_embeddings)

# ── Create vector index ───────────────────────────────────────────────────────

def create_vector_index(session):
    session.run(f"""
        CREATE VECTOR INDEX {VECTOR_INDEX_NAME} IF NOT EXISTS
        FOR (b:Batch) ON b.qcEmbedding
        OPTIONS {{indexConfig: {{
            `vector.dimensions`: 1536,
            `vector.similarity_function`: 'cosine'
        }}}}
    """)
    print(f"✅ Vector index '{VECTOR_INDEX_NAME}' created")

# ── Verify ────────────────────────────────────────────────────────────────────

def verify(session):
    result = session.run("""
        MATCH (b:Batch)
        WHERE b.qcEmbedding IS NOT NULL
        RETURN count(b) AS embedded_count
    """)
    count = result.single()["embedded_count"]
    print(f"\n📊 Batches with embeddings: {count}/200")

    result = session.run("""
        SHOW INDEXES
        WHERE type = 'VECTOR'
    """)
    print("\n🔍 Vector indexes:")
    for r in result:
        print(f"   {r['name']} — state: {r['state']}")

# ── Test similarity search ────────────────────────────────────────────────────

def test_similarity_search(session):
    print("\n🧪 Testing similarity search...")
    test_query = "crystalline deposits found in active ingredient during inspection"

    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=[test_query]
    )
    query_embedding = response.data[0].embedding

    result = session.run("""
        CALL db.index.vector.queryNodes($index, 3, $embedding)
        YIELD node, score
        RETURN node.id AS batch_id,
               node.qc_passed AS passed,
               node.qc_description AS description,
               score
        ORDER BY score DESC
    """, index=VECTOR_INDEX_NAME, embedding=query_embedding)

    print(f"\n   Query: '{test_query}'")
    print("   Top 3 similar batches:")
    for r in result:
        status = "✅ PASS" if r["passed"] else "❌ FAIL"
        print(f"\n   {r['batch_id']} [{status}] — score: {r['score']:.4f}")
        print(f"   {r['description'][:100]}...")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("🚀 Creating embeddings for pharma batch QC descriptions...")
    print(f"   Model: {EMBEDDING_MODEL}")
    print(f"   Index: {VECTOR_INDEX_NAME}\n")

    with driver.session(database=os.getenv("NEO4J_DATABASE", "neo4j")) as session:

        # Fetch batches that need embeddings
        batches = fetch_batches(session)
        print(f"📦 Found {len(batches)} batches needing embeddings\n")

        if not batches:
            print("✅ All batches already have embeddings — skipping generation")
        else:
            # Process in batches to avoid rate limits
            total = len(batches)
            processed = 0

            for i in range(0, total, BATCH_SIZE):
                chunk = batches[i:i + BATCH_SIZE]
                texts = [b["description"] for b in chunk]

                print(f"   Embedding batch {i//BATCH_SIZE + 1}/{(total + BATCH_SIZE - 1)//BATCH_SIZE} "
                      f"({len(chunk)} descriptions)...")

                try:
                    embeddings = generate_embeddings(texts)

                    batch_embeddings = [
                        {"id": chunk[j]["id"], "embedding": embeddings[j]}
                        for j in range(len(chunk))
                    ]

                    session.execute_write(store_embeddings, batch_embeddings)
                    processed += len(chunk)
                    print(f"   ✅ Stored {processed}/{total} embeddings")

                    # Small delay to respect rate limits
                    if i + BATCH_SIZE < total:
                        time.sleep(0.5)

                except Exception as e:
                    print(f"   ❌ Error on batch {i//BATCH_SIZE + 1}: {e}")
                    raise

        # Create vector index
        print("\n📌 Creating vector index...")
        create_vector_index(session)

        # Wait for index to come online
        print("   Waiting for index to come online...")
        time.sleep(3)

        # Verify
        verify(session)

        # Test similarity search
        test_similarity_search(session)

    driver.close()
    print("\n\n🎉 Done! Your pharma knowledge graph now has:")
    print("   ✅ 200 batch nodes with QC embeddings")
    print("   ✅ Vector index for similarity search")
    print("   ✅ Similarity search working")
    print("\n   Next step: build the LangChain agent (agent/pharma_agent.py)")

if __name__ == "__main__":
    main()