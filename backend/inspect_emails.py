import sqlite3
import json

def inspect():
    conn = sqlite3.connect('hiring_agent.db')
    cursor = conn.cursor()
    cursor.execute('SELECT full_name, email, phone, raw_json FROM candidates')
    rows = cursor.fetchall()
    print("CANDIDATES IN DB:")
    for name, email, phone, raw_json_str in rows:
        data = json.loads(raw_json_str)
        raw_data = data.get("metadata", {}).get("raw_data", {})
        print(f"\n======================================")
        print(f"Name: {name}")
        print(f"  DB email column: '{email}'")
        print(f"  DB phone column: '{phone}'")
        print(f"  raw_json email:  '{data.get('basic_info', {}).get('email')}'")
        print(f"  raw_data email:  '{raw_data.get('email')}'")
        print(f"  raw_data personal_emails: {raw_data.get('personal_emails')}")

if __name__ == "__main__":
    inspect()
