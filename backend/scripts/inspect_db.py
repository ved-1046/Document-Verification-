import sqlite3
import json

conn = sqlite3.connect("file:backend/docuverify.db?mode=ro", uri=True)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 1. Get all table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
tables = [row["name"] for row in cursor.fetchall()]

schema_info = {
    "total_tables": len(tables),
    "tables": {}
}

for table in tables:
    cursor.execute(f"PRAGMA table_info({table});")
    columns = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute(f"PRAGMA foreign_key_list({table});")
    fks = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute(f"SELECT COUNT(*) as count FROM {table};")
    row_count = cursor.fetchone()["count"]

    # Sample rows (sanitized)
    cursor.execute(f"SELECT * FROM {table} ORDER BY 1 DESC LIMIT 3;")
    sample_rows = []
    for r in cursor.fetchall():
        row_dict = dict(r)
        # Sanitize sensitive fields
        if "password_hash" in row_dict:
            row_dict["password_hash"] = "[REDACTED_BCRYPT_HASH]"
        if "email" in row_dict and row_dict["email"]:
            parts = row_dict["email"].split("@")
            row_dict["email"] = f"{parts[0][:3]}***@{parts[1]}"
        sample_rows.append(row_dict)
    
    schema_info["tables"][table] = {
        "column_count": len(columns),
        "row_count": row_count,
        "columns": columns,
        "foreign_keys": fks,
        "sample_records": sample_rows
    }

conn.close()

with open("backend/scripts/db_inspection_result.json", "w", encoding="utf-8") as f:
    json.dump(schema_info, f, indent=2, default=str)

print("DB Inspection completed successfully!")
print(f"Total tables: {len(tables)}")
for t in tables:
    print(f"- {t}: {schema_info['tables'][t]['column_count']} columns, {schema_info['tables'][t]['row_count']} rows")
