from dotenv import load_dotenv

import os
from langchain_neo4j import Neo4jVector
from langchain_openai import OpenAIEmbeddings
from langchain_neo4j import Neo4jGraph

load_dotenv()

graph = Neo4jGraph(
    url=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USERNAME"),
    password=os.getenv("NEO4J_PASSWORD"),
    database=os.getenv("NEO4J_DATABASE", "neo4j"),
    enhanced_schema=False
)


embedding_model = OpenAIEmbeddings(
    model="text-embedding-ada-002",
    api_key=os.getenv("OPENAI_API_KEY")
)


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

results = vector_store.similarity_search_with_score(
    "crystalline deposits in active pharmaceutical ingredient", k=3
)

for doc, score in results:
    print(f"Score: {score}")
    print(f"Metadata: {doc.metadata}")
    print(f"Content: {doc.page_content[:100]}")
    print()