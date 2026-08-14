import sqlite3
import json

def inspect():
    conn = sqlite3.connect('hiring_agent.db')
    cursor = conn.cursor()
    cursor.execute('SELECT full_name, raw_json FROM candidates WHERE full_name IN ("Jacob Berg", "Julia Trull")')
    rows = cursor.fetchall()
    print("KEYS AND PERSONA VALUES IN DB FOR JACOB & JULIA:")
    for name, raw_json_str in rows:
        data = json.loads(raw_json_str)
        raw_data = data.get("metadata", {}).get("raw_data", {})
        print(f"\n======================================")
        print(f"Name: {name}")
        print(f"  raw_data seniority: {raw_data.get('seniority')}")
        print(f"  raw_data keys: {list(raw_data.keys())}")
        # Let's inspect the entire raw_data dict's keys and values related to seniority/persona
        for k, v in raw_data.items():
            if 'seniority' in k or 'persona' in k:
                print(f"    {k}: {v}")
        print(f"  raw_json profile_details keys: {list(data.keys())}")
        print(f"  raw_json basic_info: {data.get('basic_info')}")
        print(f"  engineered_features in raw_json: {data.get('metadata', {}).get('raw_data', {}).get('engineered_features')}")

if __name__ == "__main__":
    inspect()
