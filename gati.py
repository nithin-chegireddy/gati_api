import pandas as pd
import time
import json
import requests
import os
from flask import Flask, jsonify

# ============================================================
# FIXED OUTPUT JSON DIRECTORY (Dashboard Folder)
# ============================================================
DATA_DIR = r"data"
os.makedirs(DATA_DIR, exist_ok=True)

# Output JSON file paths
GATI_JSON = os.path.join(DATA_DIR, "gati_output.json")

# ============================================================
# INPUT EXCEL
# ============================================================
INPUT_EXCEL = os.path.join(DATA_DIR, "COMBINED_INPUTS.xlsx")
df = pd.read_excel(INPUT_EXCEL)

gati_list = df.iloc[:, 1].dropna().astype(str).tolist()

# ============================================================
# GATI API (no changes)
# ============================================================
def run_gati(gati_list):
    print("\n===== RUNNING GATI TRACKING =====")

    HEADERS = {
        "Referer": "https://www.allcargogati.com/track-shipment",
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json"
    }

    API_URL = "https://admin.allcargogati.com/api/track-shipment"

    all_rows = []

    for docket in gati_list:

        # FIX 1: Remove ".0" and convert to int string
        try:
            clean_docket = str(int(float(docket)))
        except:
            clean_docket = docket.strip()

        payload = {
            "requid": "GWEB0001",
            "authorization": "rNi40TfnQr92qoKD",
            "docketNo": clean_docket
        }

        latest_block = ""
        previous_status = ""

        try:
            resp = requests.post(API_URL, json=payload, headers=HEADERS, timeout=15)
            data = resp.json()

            if "data" in data and data["data"]:
                details = data["data"].get("details", [])

                if details:
                    transit = details[0].get("TRANSIT_DTLS", [])

                    if len(transit) > 0:
                        t = transit[0]
                        latest_block = (
                            f"Date: {t.get('intransitDate','')}, "
                            f"Time: {t.get('intransitTime','')}, "
                            f"Loc: {t.get('intransitLocation','')}, "
                            f"Status: {t.get('intransitStatus','')}"
                        )

                    if len(transit) > 1:
                        p = transit[1]
                        previous_status = (
                            f"{p.get('intransitStatus','')} "
                            f"{p.get('intransitDate','')} {p.get('intransitTime','')}"
                        )

            all_rows.append({
                "Docket_Number": clean_docket,
                "Latest_Update": latest_block,
                "Previous_Status": previous_status
            })

        except Exception as e:
            all_rows.append({
                "Docket_Number": clean_docket,
                "Error": str(e)
            })

    # SAVE JSON
    with open(GATI_JSON, "w", encoding="utf-8") as f:
        json.dump(all_rows, f, indent=4, ensure_ascii=False)

    print("✅ GATI JSON SAVED:", GATI_JSON)


# ============================================================
# FLASK API
# ============================================================
app = Flask(__name__)

@app.route("/run_gati")
def api_run_gati():
    run_gati(gati_list)
    return jsonify({"status": "success", "message": "GATI scraping completed"})


@app.route("/get_gati")
def get_gati_json():
    if os.path.exists(GATI_JSON):
        with open(GATI_JSON, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify([])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
