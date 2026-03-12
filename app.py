from flask import Flask, request, jsonify, render_template, send_from_directory
import pandas as pd
import json
import os
import re

app = Flask(__name__)

LEARNED_RULES_FILE = "learned_rules.json"

# ─────────────────────────────────────────────
# DEFAULT KEYWORD CATEGORIES
# ─────────────────────────────────────────────
DEFAULT_RULES = {
    "ZOMATO": "Food",
    "SWIGGY": "Food",
    "BLINKIT": "Groceries",
    "BIGBASKET": "Groceries",
    "DMART": "Groceries",
    "ZEPTO": "Groceries",
    "UBER": "Travel",
    "OLA": "Travel",
    "RAPIDO": "Travel",
    "IRCTC": "Travel",
    "MAKEMYTRIP": "Travel",
    "AMAZON": "Shopping",
    "FLIPKART": "Shopping",
    "MYNTRA": "Shopping",
    "MEESHO": "Shopping",
    "NETFLIX": "Entertainment",
    "HOTSTAR": "Entertainment",
    "SPOTIFY": "Entertainment",
    "YOUTUBE": "Entertainment",
    "BOOKMYSHOW": "Entertainment",
    "AIRTEL": "Bills",
    "JIO": "Bills",
    "BSNL": "Bills",
    "ELECTRICITY": "Bills",
    "BESCOM": "Bills",
    "TATA": "Bills",
    "LIC": "Insurance",
    "SBI": "Transfer",
    "HDFC": "Transfer",
    "ICICI": "Transfer",
    "SALARY": "Income",
    "NEFT": "Transfer",
    "IMPS": "Transfer",
    "ATM": "Cash",
}

# ─────────────────────────────────────────────
# LEARNED RULES - persisted to JSON
# ─────────────────────────────────────────────
def load_learned_rules():
    if os.path.exists(LEARNED_RULES_FILE):
        with open(LEARNED_RULES_FILE, "r") as f:
            return json.load(f)
    return {}

def save_learned_rules(rules):
    with open(LEARNED_RULES_FILE, "w") as f:
        json.dump(rules, f, indent=2)

# ─────────────────────────────────────────────
# EXTRACT CLEAN MERCHANT NAME FROM MESSY UPI
# Examples:
#   UPI/ZOMATO@PAYTM/1234  → ZOMATO
#   UPI-OLA-CABS-XXXXX     → OLA CABS
#   NEFT/SURESH KUMAR/...  → SURESH KUMAR
# ─────────────────────────────────────────────
def extract_merchant(description: str) -> str:
    desc = description.upper().strip()

    # Remove common UPI prefixes
    desc = re.sub(r"^(UPI[-/]?|NEFT[-/]?|IMPS[-/]?|RTGS[-/]?)", "", desc)

    # Take only the part before first slash or @ or hyphen (after prefix removed)
    parts = re.split(r"[@/]", desc)
    merchant = parts[0].strip()

    # Remove trailing digits and special chars
    merchant = re.sub(r"[-_\d]+$", "", merchant).strip()

    return merchant if merchant else desc

# ─────────────────────────────────────────────
# CATEGORIZE ONE TRANSACTION
# Priority: learned rules → default keyword rules → Uncategorized
# ─────────────────────────────────────────────
def categorize(description: str, learned: dict) -> str:
    merchant = extract_merchant(description)

    # 1. Check exact learned rule
    if merchant in learned:
        return learned[merchant]

    # 2. Check if any learned key is contained in merchant
    for key, cat in learned.items():
        if key in merchant:
            return cat

    # 3. Check default keyword rules
    for keyword, cat in DEFAULT_RULES.items():
        if keyword in merchant:
            return cat

    # 4. Fallback
    return "Uncategorized"

# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    filename = file.filename.lower()

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(file)
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file)
        else:
            return jsonify({"error": "Only CSV or Excel files supported"}), 400
    except Exception as e:
        return jsonify({"error": f"Could not read file: {str(e)}"}), 400

    # ── Normalize column names ──
    df.columns = [c.strip().lower() for c in df.columns]

    # Try to detect date, description, amount columns
    col_map = {}
    for col in df.columns:
        if any(x in col for x in ["date", "dt", "txn date", "transaction date"]):
            col_map["date"] = col
        elif any(x in col for x in ["desc", "narration", "particulars", "details", "transaction", "remarks"]):
            col_map["description"] = col
        elif any(x in col for x in ["amount", "debit", "credit", "amt", "withdrawal", "deposit"]):
            if "amount" not in col_map:
                col_map["amount"] = col

    if len(col_map) < 2:
        # Fallback: use first 3 columns
        cols = list(df.columns)
        col_map = {
            "date": cols[0] if len(cols) > 0 else None,
            "description": cols[1] if len(cols) > 1 else None,
            "amount": cols[2] if len(cols) > 2 else None,
        }

    learned = load_learned_rules()
    transactions = []

    for _, row in df.iterrows():
        try:
            date = str(row.get(col_map.get("date", ""), "")).strip()
            desc = str(row.get(col_map.get("description", ""), "")).strip()
            amt_raw = row.get(col_map.get("amount", ""), 0)

            # Clean amount
            if isinstance(amt_raw, str):
                amt_raw = amt_raw.replace(",", "").replace("₹", "").replace(" ", "")
                try:
                    amt = float(amt_raw)
                except:
                    amt = 0.0
            else:
                amt = float(amt_raw) if pd.notna(amt_raw) else 0.0

            if desc and desc.lower() not in ["nan", ""]:
                merchant = extract_merchant(desc)
                category = categorize(desc, learned)
                transactions.append({
                    "date": date,
                    "description": desc,
                    "merchant": merchant,
                    "amount": round(amt, 2),
                    "category": category,
                })
        except Exception:
            continue

    if not transactions:
        return jsonify({"error": "No valid transactions found. Check your column names."}), 400

    # ── Summary by category ──
    summary = {}
    for t in transactions:
        if t["amount"] < 0:  # only spending
            cat = t["category"]
            summary[cat] = round(summary.get(cat, 0) + abs(t["amount"]), 2)

    return jsonify({
        "transactions": transactions,
        "summary": summary,
        "total_transactions": len(transactions),
        "columns_detected": col_map,
    })


@app.route("/learn", methods=["POST"])
def learn():
    """
    User corrects a transaction category.
    We save the merchant → category mapping so it's remembered forever.
    """
    data = request.json
    merchant = data.get("merchant", "").upper().strip()
    category = data.get("category", "").strip()

    if not merchant or not category:
        return jsonify({"error": "merchant and category required"}), 400

    learned = load_learned_rules()
    learned[merchant] = category
    save_learned_rules(learned)

    return jsonify({
        "status": "learned",
        "merchant": merchant,
        "category": category,
        "total_rules": len(learned)
    })


@app.route("/learned-rules", methods=["GET"])
def get_learned_rules():
    return jsonify(load_learned_rules())


@app.route("/categories", methods=["GET"])
def get_categories():
    all_cats = sorted(set(list(DEFAULT_RULES.values()) + [
        "Food", "Travel", "Shopping", "Entertainment", "Bills",
        "Rent", "Salary", "Income", "Insurance", "Groceries",
        "Healthcare", "Education", "Transfer", "Cash", "Uncategorized", "Other"
    ]))
    return jsonify(all_cats)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
