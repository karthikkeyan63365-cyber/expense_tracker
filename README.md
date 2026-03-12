# 💸 Smart Expense Tracker

A Python + Flask web app that reads your bank statement and auto-categorizes transactions — and **learns from your corrections**.

---

## 📁 Project Structure

```
expense_tracker/
├── app.py               ← Flask backend (all logic here)
├── requirements.txt     ← Python dependencies
├── learned_rules.json   ← Auto-created when you save corrections
└── templates/
    └── index.html       ← Full frontend (charts, table, learning UI)
```

---

## ⚡ Setup & Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
python app.py

# 3. Open browser
http://localhost:5000
```

---

## 🧠 How the Learning Works

When you upload a statement and see a transaction like:

```
SURESH TRANSFER  →  Uncategorized
```

You change it to **Rent** in the dropdown → click **Save & Learn**.

The system saves: `SURESH → Rent` in `learned_rules.json`

Next upload, any transaction with **SURESH** in the description is automatically tagged as **Rent**. Forever. ✅

---

## 🗂️ Supported Bank Statement Formats

The app auto-detects columns. Works with most CSV/Excel exports:

| Bank | Format |
|------|--------|
| SBI | CSV export |
| HDFC | Excel/CSV |
| ICICI | CSV |
| Google Pay | CSV |
| PhonePe | CSV |
| Any UPI app | CSV |

Your columns just need to have: **Date**, **Description/Narration**, **Amount/Debit**

---

## 🔧 Messy UPI Descriptions

The app handles messy formats like:
```
UPI/ZOMATO@PAYTM/12345678  →  extracted as: ZOMATO  →  Food
UPI-UBER-INDIA-XXXXX       →  extracted as: UBER    →  Travel
NEFT/SURESH KUMAR/ABC      →  extracted as: SURESH KUMAR → learned rule
```

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web dashboard |
| `/upload` | POST | Upload CSV/Excel file |
| `/learn` | POST | Save a merchant → category rule |
| `/learned-rules` | GET | See all learned rules |
| `/categories` | GET | Get all available categories |

---

## 🚀 Future Improvements

- [ ] Monthly trend charts
- [ ] Budget limits per category
- [ ] Export corrected data to CSV
- [ ] Multiple bank account support
- [ ] Deploy on Render / Railway (free hosting)
