import sqlite3

conn = sqlite3.connect("situation_room.db")
c = conn.cursor()

# Check columns
c.execute("PRAGMA table_info(pu_results)")
cols = [r[1] for r in c.fetchall()]
print("Current pu_results columns:", cols)

if "submitted_by_admin" not in cols:
    c.execute("ALTER TABLE pu_results ADD COLUMN submitted_by_admin TEXT DEFAULT 'admin'")
    conn.commit()
    print("Added submitted_by_admin column successfully.")
else:
    print("submitted_by_admin already exists.")

conn.close()
