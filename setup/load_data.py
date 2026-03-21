import os
import json
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

# ── Connection ────────────────────────────────────────────────────────────────

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)

# ── Load data from JSON ───────────────────────────────────────────────────────

with open("../data/pharma_data.json", "r") as f:
    data = json.load(f)

# ── Clear existing data ───────────────────────────────────────────────────────

def clear_database(tx):
    tx.run("MATCH (n) DETACH DELETE n")

# ── Constraints & Indexes ─────────────────────────────────────────────────────

def create_constraints(tx):
    constraints = [
        "CREATE CONSTRAINT supplier_id IF NOT EXISTS FOR (s:Supplier) REQUIRE s.id IS UNIQUE",
        "CREATE CONSTRAINT facility_id IF NOT EXISTS FOR (f:Facility) REQUIRE f.id IS UNIQUE",
        "CREATE CONSTRAINT ingredient_id IF NOT EXISTS FOR (i:Ingredient) REQUIRE i.id IS UNIQUE",
        "CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE",
        "CREATE CONSTRAINT batch_id IF NOT EXISTS FOR (b:Batch) REQUIRE b.id IS UNIQUE",
    ]
    for c in constraints:
        tx.run(c)

# ── Node loaders ──────────────────────────────────────────────────────────────

def load_suppliers(tx, suppliers):
    tx.run("""
        UNWIND $suppliers AS s
        MERGE (sup:Supplier {id: s.id})
        SET sup.name      = s.name,
            sup.country   = s.country,
            sup.region    = s.region,
            sup.tier      = s.tier,
            sup.qualified = s.qualified
    """, suppliers=suppliers)

def load_facilities(tx, facilities):
    tx.run("""
        UNWIND $facilities AS f
        MERGE (fac:Facility {id: f.id})
        SET fac.name           = f.name,
            fac.location       = f.location,
            fac.country        = f.country,
            fac.fda_registered = f.fda_registered
    """, facilities=facilities)

def load_ingredients(tx, ingredients):
    tx.run("""
        UNWIND $ingredients AS i
        MERGE (ing:Ingredient {id: i.id})
        SET ing.name       = i.name,
            ing.type       = i.type,
            ing.controlled = i.controlled
    """, ingredients=ingredients)

def load_products(tx, products):
    tx.run("""
        UNWIND $products AS p
        MERGE (prod:Product {id: p.id})
        SET prod.name              = p.name,
            prod.therapeutic_area  = p.therapeutic_area
    """, products=products)

def load_batches(tx, batches):
    tx.run("""
        UNWIND $batches AS b
        MERGE (bat:Batch {id: b.id})
        SET bat.product_name        = b.product_name,
            bat.manufacturing_date  = b.manufacturing_date,
            bat.expiry_date         = b.expiry_date,
            bat.batch_size_kg       = b.batch_size_kg,
            bat.qc_passed           = b.qc_passed,
            bat.qc_description      = b.qc_description,
            bat.quarter             = b.quarter,
            bat.year                = b.year,
            bat.status              = b.status
    """, batches=batches)

# ── Relationship loaders ──────────────────────────────────────────────────────

def load_batch_product_relationships(tx, batches):
    tx.run("""
        UNWIND $batches AS b
        MATCH (bat:Batch {id: b.id})
        MATCH (prod:Product {id: b.product_id})
        MERGE (bat)-[:PRODUCES]->(prod)
    """, batches=batches)

def load_batch_facility_relationships(tx, batches):
    tx.run("""
        UNWIND $batches AS b
        MATCH (bat:Batch {id: b.id})
        MATCH (fac:Facility {id: b.facility_id})
        MERGE (bat)-[:MANUFACTURED_AT]->(fac)
    """, batches=batches)

def load_ingredient_assignments(tx, assignments):
    tx.run("""
        UNWIND $assignments AS a
        MATCH (bat:Batch {id: a.batch_id})
        MATCH (ing:Ingredient {id: a.ingredient_id})
        MATCH (sup:Supplier {id: a.supplier_id})
        MERGE (bat)-[:CONTAINS {
            quantity_kg: a.quantity_kg,
            lot_number:  a.lot_number
        }]->(ing)
        MERGE (ing)-[:SUPPLIED_BY]->(sup)
    """, assignments=assignments)

# ── Verification ──────────────────────────────────────────────────────────────

def verify_load(session):
    result = session.run("""
        MATCH (n) 
        RETURN labels(n)[0] AS label, count(n) AS count
        ORDER BY label
    """)
    print("\n📊 Node counts:")
    for record in result:
        print(f"   {record['label']:<15} {record['count']}")

    result = session.run("""
        MATCH ()-[r]->()
        RETURN type(r) AS type, count(r) AS count
        ORDER BY type
    """)
    print("\n🔗 Relationship counts:")
    for record in result:
        print(f"   {record['type']:<20} {record['count']}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("🚀 Loading pharma supply chain data into AuraDB...")
    print(f"   URI: {os.getenv('NEO4J_URI')}\n")

    with driver.session(database=os.getenv("NEO4J_DATABASE", "neo4j")) as session:

        # Clear
        print("🗑️  Clearing existing data...")
        session.execute_write(clear_database)

        # Constraints
        print("📌 Creating constraints and indexes...")
        session.execute_write(create_constraints)

        # Nodes
        print("📦 Loading Suppliers...")
        session.execute_write(load_suppliers, data["suppliers"])

        print("🏭 Loading Facilities...")
        session.execute_write(load_facilities, data["facilities"])

        print("🧪 Loading Ingredients...")
        session.execute_write(load_ingredients, data["ingredients"])

        print("💊 Loading Products...")
        session.execute_write(load_products, data["products"])

        print("🔬 Loading Batches...")
        session.execute_write(load_batches, data["batches"])

        # Relationships
        print("🔗 Creating Batch → Product relationships...")
        session.execute_write(load_batch_product_relationships, data["batches"])

        print("🔗 Creating Batch → Facility relationships...")
        session.execute_write(load_batch_facility_relationships, data["batches"])

        print("🔗 Creating Batch → Ingredient → Supplier relationships...")
        session.execute_write(load_ingredient_assignments, data["assignments"])

        # Verify
        print("\n✅ Data loaded successfully!")
        verify_load(session)

    driver.close()
    print("\n🎉 Done! Your pharma knowledge graph is ready.")
    print("   Next step: run setup/create_embeddings.py")

if __name__ == "__main__":
    main()