import random
import json
from datetime import datetime, timedelta

random.seed(42)

# ── Master lists ──────────────────────────────────────────────────────────────

SUPPLIERS = [
    {"id": f"SUP-{i:03d}", "name": name, "country": country, "region": region, "tier": tier, "qualified": qualified}
    for i, (name, country, region, tier, qualified) in enumerate([
        ("BioSynth AG",           "Germany",     "Europe",       1, True),
        ("ChemCore Ltd",          "UK",           "Europe",       1, True),
        ("PharmRaw Inc",          "USA",          "North America",1, True),
        ("ActiveMol GmbH",        "Switzerland",  "Europe",       1, True),
        ("EastChem Co",           "China",        "Asia",         2, True),
        ("IndoPharma Pvt",        "India",        "Asia",         2, True),
        ("NordChem AS",           "Norway",       "Europe",       1, True),
        ("SynthEx Corp",          "USA",          "North America",1, True),
        ("MedRaw Srl",            "Italy",        "Europe",       2, True),
        ("AsiaChem Ltd",          "Japan",        "Asia",         1, True),
        ("GlobalAPI SA",          "France",       "Europe",       1, True),
        ("PrimeChem BV",          "Netherlands",  "Europe",       1, True),
        ("RawMed Inc",            "Canada",       "North America",2, True),
        ("BioBase GmbH",          "Austria",      "Europe",       2, True),
        ("SpectraChem Pvt",       "India",        "Asia",         2, False),
        ("CoreAPI Ltd",           "UK",           "Europe",       1, True),
        ("PharSource SA",         "Spain",        "Europe",       2, True),
        ("MolecuRaw Corp",        "USA",          "North America",1, True),
        ("NovaChem AS",           "Sweden",       "Europe",       1, True),
        ("PacificAPI Co",         "South Korea",  "Asia",         2, True),
    ], start=1)
]

FACILITIES = [
    {"id": f"FAC-{i:03d}", "name": name, "location": location, "country": country, "fda_registered": fda_reg}
    for i, (name, location, country, fda_reg) in enumerate([
        ("Frankfurt Manufacturing Plant",  "Frankfurt",    "Germany",     True),
        ("New Jersey API Facility",        "New Jersey",   "USA",         True),
        ("Singapore Synthesis Center",     "Singapore",    "Singapore",   True),
        ("Basel Production Unit",          "Basel",        "Switzerland", True),
        ("Mumbai Pharma Plant",            "Mumbai",       "India",       True),
        ("Lyon Sterile Facility",          "Lyon",         "France",      True),
        ("Tokyo Precision Plant",          "Tokyo",        "Japan",       True),
        ("Dublin Biologics Center",        "Dublin",       "Ireland",     True),
        ("Montreal API Plant",             "Montreal",     "Canada",      True),
        ("Barcelona Secondary Plant",      "Barcelona",    "Spain",       False),
    ], start=1)
]

INGREDIENTS = [
    {"id": f"ING-{i:03d}", "name": name, "type": ing_type, "controlled": controlled}
    for i, (name, ing_type, controlled) in enumerate([
        ("Amoxicillin Trihydrate",    "API",      True),
        ("Ibuprofen USP",             "API",      True),
        ("Metformin HCl",             "API",      True),
        ("Atorvastatin Calcium",      "API",      True),
        ("Omeprazole Magnesium",      "API",      True),
        ("Lisinopril",                "API",      True),
        ("Sertraline HCl",            "API",      True),
        ("Amlodipine Besylate",       "API",      True),
        ("Microcrystalline Cellulose","Excipient",False),
        ("Lactose Monohydrate",       "Excipient",False),
        ("Magnesium Stearate",        "Excipient",False),
        ("Povidone K30",              "Excipient",False),
        ("Hydroxypropyl Cellulose",   "Excipient",False),
        ("Croscarmellose Sodium",     "Excipient",False),
        ("Talc PhEur",                "Excipient",False),
        ("Colloidal Silicon Dioxide", "Excipient",False),
        ("Titanium Dioxide",          "Excipient",False),
        ("Hypromellose",              "Excipient",False),
        ("Purified Water",            "Solvent",  False),
        ("Ethanol 96%",               "Solvent",  False),
    ], start=1)
]

PRODUCTS = [
    {"id": f"PRD-{i:03d}", "name": name, "therapeutic_area": area}
    for i, (name, area) in enumerate([
        ("Amoxicap 500mg Capsules",   "Antibiotics"),
        ("Ibuprofen 400mg Tablets",   "Anti-inflammatory"),
        ("Metformin 850mg Tablets",   "Diabetes"),
        ("Atorvastatin 20mg Tablets", "Cardiovascular"),
        ("Omeprazole 20mg Capsules",  "Gastroenterology"),
        ("Lisinopril 10mg Tablets",   "Cardiovascular"),
        ("Sertraline 50mg Tablets",   "CNS"),
        ("Amlodipine 5mg Tablets",    "Cardiovascular"),
    ], start=1)
]

QC_PASS_DESCRIPTIONS = [
    "All critical quality attributes within specification. Visual inspection clear. Assay 99.2%. Dissolution 96% at 30min.",
    "Batch meets all release specifications. Microbial limits compliant. Moisture content 2.1%. Hardness 8.2kP.",
    "Full analytical testing completed. Identity confirmed by HPLC. Purity 99.8%. Particle size distribution normal.",
    "Release testing passed. Uniformity of dosage units compliant. Disintegration 4 minutes. No visible defects.",
    "All in-process controls met. Blend uniformity RSD 1.2%. Compression force nominal. Weight variation within limits.",
    "Sterility testing passed. Endotoxin below limit. pH 7.2. Particulate matter compliant with USP 788.",
    "Stability indicating assay passed. Related substances within limits. Karl Fischer 0.3%. Appearance normal.",
    "Certificate of analysis verified. Residual solvents compliant ICH Q3C. Heavy metals below threshold.",
]

QC_FAIL_DESCRIPTIONS = [
    "Out of specification result for assay: 94.1% against limit of NLT 98.0%. Potential degradation observed during stability study.",
    "Unusual crystalline deposits identified during visual inspection of active pharmaceutical ingredient. Foreign particulate matter suspected.",
    "Microbial contamination detected during environmental monitoring. Total aerobic count exceeded specification by 2 log units.",
    "Dissolution failure at 45-minute timepoint: 67% dissolved against specification of NLT 80%. Coating defect suspected.",
    "Related substances out of specification. Unknown impurity at RRT 0.85 exceeds 0.15% limit. Root cause under investigation.",
    "Particle size distribution outside specification. D90 value 285 microns against limit of NMT 250 microns. Milling issue suspected.",
    "pH drift observed in liquid formulation. Measured 5.1 against specification of 6.0-7.0. Buffer capacity insufficient.",
    "Residual solvent ethanol exceeds ICH Q3C limit. Measured 4200 ppm against limit of 5000 ppm — borderline non-compliant.",
    "Blend non-uniformity detected. RSD 4.8% against limit of NMT 3.0%. Inadequate mixing time identified as root cause.",
    "Endotoxin level above specification: 0.35 EU/mL against limit of NMT 0.25 EU/mL. Pyrogen contamination suspected.",
    "Color variation observed across tablet batch. Coating solution concentration inconsistent. Visual defect rate 3.2%.",
    "Moisture content out of specification: 5.8% against limit of NMT 4.0%. Humidity excursion during processing suspected.",
]

# ── Helper functions ──────────────────────────────────────────────────────────

def random_date(start_year=2023, end_year=2025):
    start = datetime(start_year, 1, 1)
    end   = datetime(end_year, 12, 31)
    return (start + timedelta(days=random.randint(0, (end - start).days))).strftime("%Y-%m-%d")

def generate_batches(n=200):
    batches = []
    for i in range(1, n + 1):
        product     = random.choice(PRODUCTS)
        facility    = random.choice(FACILITIES)
        mfg_date    = random_date()
        exp_date    = (datetime.strptime(mfg_date, "%Y-%m-%d") + timedelta(days=random.choice([365*2, 365*3]))).strftime("%Y-%m-%d")
        qc_passed   = random.random() > 0.25          # 75% pass rate
        qc_desc     = random.choice(QC_PASS_DESCRIPTIONS if qc_passed else QC_FAIL_DESCRIPTIONS)
        qc_desc     = qc_desc + f" Batch size: {random.choice([100, 200, 500, 1000])}kg. Operator: OP-{random.randint(10,99)}."
        quarter     = f"Q{(datetime.strptime(mfg_date, '%Y-%m-%d').month - 1) // 3 + 1}"
        year        = datetime.strptime(mfg_date, "%Y-%m-%d").year

        batches.append({
            "id":               f"BATCH-{i:04d}",
            "product_id":       product["id"],
            "product_name":     product["name"],
            "facility_id":      facility["id"],
            "manufacturing_date": mfg_date,
            "expiry_date":      exp_date,
            "batch_size_kg":    random.choice([100, 200, 500, 1000]),
            "qc_passed":        qc_passed,
            "qc_description":   qc_desc,
            "quarter":          quarter,
            "year":             year,
            "status":           "RELEASED" if qc_passed else random.choice(["REJECTED", "UNDER_INVESTIGATION"]),
        })
    return batches

def assign_ingredients_to_batches(batches):
    """Each batch uses 3-6 ingredients, each sourced from a supplier."""
    assignments = []
    for batch in batches:
        n_ingredients = random.randint(3, 6)
        selected      = random.sample(INGREDIENTS, n_ingredients)
        for ing in selected:
            supplier = random.choice(SUPPLIERS)
            assignments.append({
                "batch_id":      batch["id"],
                "ingredient_id": ing["id"],
                "supplier_id":   supplier["id"],
                "quantity_kg":   round(random.uniform(1.0, 50.0), 2),
                "lot_number":    f"LOT-{random.randint(10000, 99999)}",
            })
    return assignments

# ── Main ──────────────────────────────────────────────────────────────────────

def generate_all():
    batches     = generate_batches(200)
    assignments = assign_ingredients_to_batches(batches)

    data = {
        "suppliers":   SUPPLIERS,
        "facilities":  FACILITIES,
        "ingredients": INGREDIENTS,
        "products":    PRODUCTS,
        "batches":     batches,
        "assignments": assignments,
    }

    with open("./pharma_data.json", "w") as f:
        json.dump(data, f, indent=2)

    # Summary
    print("✅ Synthetic pharma data generated successfully!")
    print(f"   Suppliers:   {len(SUPPLIERS)}")
    print(f"   Facilities:  {len(FACILITIES)}")
    print(f"   Ingredients: {len(INGREDIENTS)}")
    print(f"   Products:    {len(PRODUCTS)}")
    print(f"   Batches:     {len(batches)}")
    print(f"   Assignments: {len(assignments)}")
    passed = sum(1 for b in batches if b["qc_passed"])
    print(f"   QC Pass rate: {passed}/{len(batches)} ({passed/len(batches)*100:.0f}%)")
    print(f"\n   Saved to: data/pharma_data.json")

if __name__ == "__main__":
    generate_all()