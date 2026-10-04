import sqlite3
import os
import json
import hashlib
import secrets
from datetime import datetime
from data_reference import LGAS_DATA, PARTIES

DB_FILE = os.path.join(os.path.dirname(__file__), "situation_room.db")

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode('utf-8')).hexdigest()

def generate_token() -> str:
    return secrets.token_hex(24)

def init_db():
    conn = get_db()
    c = conn.cursor()

    # 0. Admins table
    c.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT DEFAULT 'COLLATOR_ADMIN', -- 'SUPER_ADMIN', 'COLLATOR_ADMIN'
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Active admin sessions
    c.execute("""
    CREATE TABLE IF NOT EXISTS admin_sessions (
        token TEXT PRIMARY KEY,
        admin_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(admin_id) REFERENCES admins(id)
    )
    """)
    
    # 1. Agents table (party agents assigned to polling units)
    c.execute("""
    CREATE TABLE IF NOT EXISTS agents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        pin_hash TEXT NOT NULL,
        party TEXT NOT NULL,
        lga TEXT NOT NULL,
        ward TEXT NOT NULL,
        pu_code TEXT NOT NULL,
        pu_name TEXT NOT NULL,
        is_verified INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 2. Results table (submitted per polling unit/electoral box)
    c.execute("""
    CREATE TABLE IF NOT EXISTS pu_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lga TEXT NOT NULL,
        ward TEXT NOT NULL,
        pu_code TEXT NOT NULL,
        pu_name TEXT NOT NULL,
        registered_voters INTEGER DEFAULT 0,
        accredited_voters INTEGER DEFAULT 0,
        ballots_issued INTEGER DEFAULT 0,
        unused_ballots INTEGER DEFAULT 0,
        spoiled_ballots INTEGER DEFAULT 0,
        rejected_ballots INTEGER DEFAULT 0,
        valid_votes INTEGER DEFAULT 0,
        total_votes INTEGER DEFAULT 0,
        
        -- Party breakdown
        apc_votes INTEGER DEFAULT 0,
        pdp_votes INTEGER DEFAULT 0,
        nnpp_votes INTEGER DEFAULT 0,
        lp_votes INTEGER DEFAULT 0,
        adc_votes INTEGER DEFAULT 0,
        prp_votes INTEGER DEFAULT 0,
        other_votes INTEGER DEFAULT 0,
        
        -- Meta
        agent_id INTEGER,
        agent_name TEXT NOT NULL,
        agent_phone TEXT NOT NULL,
        agent_party TEXT NOT NULL,
        ec8a_photo TEXT,
        incident_report TEXT,
        status TEXT DEFAULT 'VERIFIED', -- 'PENDING', 'VERIFIED', 'FLAGGED'
        flags TEXT, -- JSON string of anomalies if any
        submitted_by_admin TEXT DEFAULT 'admin',
        submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(pu_code)
    )
    """)
    
    # 3. Incidents / Distress Calls
    c.execute("""
    CREATE TABLE IF NOT EXISTS incidents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lga TEXT NOT NULL,
        ward TEXT NOT NULL,
        pu_code TEXT NOT NULL,
        agent_name TEXT NOT NULL,
        agent_phone TEXT NOT NULL,
        incident_type TEXT NOT NULL, -- 'VIOLENCE', 'BVAS_FAILURE', 'BALLOT_SNATCHING', 'VOTER_INTIMIDATION', 'LATE_ARRIVAL'
        severity TEXT DEFAULT 'MEDIUM', -- 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
        description TEXT NOT NULL,
        status TEXT DEFAULT 'OPEN', -- 'OPEN', 'INVESTIGATING', 'RESOLVED'
        reported_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 4. Situation Room Announcements / Directives
    c.execute("""
    CREATE TABLE IF NOT EXISTS broadcasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        priority TEXT DEFAULT 'NORMAL', -- 'NORMAL', 'URGENT', 'ALERT'
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Default situation room admin
    c.execute("SELECT COUNT(*) as cnt FROM admins")
    if c.fetchone()["cnt"] == 0:
        c.execute("""
            INSERT INTO admins (username, password_hash, full_name, role)
            VALUES (?, ?, ?, ?)
        """, ("admin", hash_pin("admin123"), "Situation Room Returning Officer", "SUPER_ADMIN"))

    # Seed mock agents and some initial results if empty
    c.execute("SELECT COUNT(*) as cnt FROM agents")
    if c.fetchone()["cnt"] == 0:
        seed_data(c)

    conn.commit()
    conn.close()

def seed_data(c):
    # ADC Polling Unit Agents across Jigawa Northwest Senatorial District
    sample_agents = [
        ("08031112233", "Ibrahim Danladi", "1234", "ADC", "Babura", "Babura", "BBR-01-001", "Kofar Fada Primary School"),
        ("08032223344", "Usman Haruna", "1234", "ADC", "Babura", "Batali", "BBR-02-004", "Batali Dispensary Square"),
        ("08033334455", "Mustapha Sani", "1234", "ADC", "Gumel", "Baikary", "GML-01-002", "Baikary Central Pri. Sch."),
        ("08034445566", "Aminu Balarabe", "1234", "ADC", "Gumel", "Galagamma", "GML-04-001", "Emir Palace Front Gate"),
        ("08035556677", "Aliyu Kazaure", "1234", "ADC", "Kazaure", "Kanti", "KZR-06-003", "Kanti Market Polling Unit"),
        ("08036667788", "Kabiru Ringim", "1234", "ADC", "Ringim", "Ringim", "RNG-06-001", "Ringim Model School"),
        ("08037778899", "Bello Taura", "1234", "ADC", "Taura", "Gujungu", "TRA-04-002", "Gujungu Central Area"),
        ("08038889900", "Zaharaddeen Garki", "1234", "ADC", "Garki", "Garki", "GRK-03-001", "Garki District Office Square"),
        ("08039990011", "Salisu Roni", "1234", "ADC", "Roni", "Roni", "RON-07-001", "Roni Town Hall PU"),
        ("08030001122", "Murtala Yankwashi", "1234", "ADC", "Yankwashi", "Karkarna", "YKW-05-001", "Karkarna Health Clinic"),
        ("08031234567", "Suleiman Gagarawa", "1234", "ADC", "Gagarawa", "Gagarawa", "GGR-01-001", "Gagarawa Secretariat Square"),
        ("08032345678", "Hamisu Maigatari", "1234", "ADC", "Maigatari", "Border Area", "MGT-08-001", "Maigatari Border Post PU"),
    ]

    for phone, name, pin, party, lga, ward, pu_code, pu_name in sample_agents:
        c.execute("""
            INSERT INTO agents (phone, full_name, pin_hash, party, lga, ward, pu_code, pu_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (phone, name, hash_pin(pin), party, lga, ward, pu_code, pu_name))

    # Preload sample polling unit results brought in by ADC agents covering all parties
    sample_results = [
        ("Babura", "Babura", "BBR-01-001", "Kofar Fada Primary School", 750, 480, 500, 20, 0, 10, 470, 480, 245, 140, 75, 4, 32, 4, 0, "Ibrahim Danladi", "08031112233", "ADC", "Collation completed peacefully. Result declared and signed by all party agents.", "VERIFIED", "[]"),
        ("Gumel", "Galagamma", "GML-04-001", "Emir Palace Front Gate", 820, 560, 580, 20, 0, 15, 545, 560, 290, 185, 60, 3, 45, 2, 0, "Aminu Balarabe", "08034445566", "ADC", "Heavy turnout, smooth accreditation with BVAS.", "VERIFIED", "[]"),
        ("Kazaure", "Kanti", "KZR-06-003", "Kanti Market Polling Unit", 680, 420, 450, 30, 0, 8, 412, 420, 215, 110, 80, 2, 38, 2, 0, "Aliyu Kazaure", "08035556677", "ADC", "Completed in good time.", "VERIFIED", "[]"),
        ("Ringim", "Ringim", "RNG-06-001", "Ringim Model School", 950, 610, 650, 40, 0, 12, 598, 610, 270, 260, 58, 5, 28, 2, 0, "Kabiru Ringim", "08036667788", "ADC", "Tight contest. High voter engagement recorded on Form EC8A.", "VERIFIED", "[]"),
        ("Taura", "Gujungu", "TRA-04-002", "Gujungu Central Area", 720, 490, 520, 30, 0, 14, 476, 490, 210, 170, 85, 6, 25, 3, 0, "Bello Taura", "08037778899", "ADC", "Smooth counting and reconciliation.", "VERIFIED", "[]"),
        ("Garki", "Garki", "GRK-03-001", "Garki District Office Square", 640, 390, 410, 20, 0, 9, 381, 390, 195, 130, 48, 4, 30, 3, 0, "Zaharaddeen Garki", "08038889900", "ADC", "All party agents signed form EC8A.", "VERIFIED", "[]")
    ]

    for res in sample_results:
        c.execute("""
            INSERT INTO pu_results (
                lga, ward, pu_code, pu_name, registered_voters, accredited_voters,
                ballots_issued, unused_ballots, spoiled_ballots, rejected_ballots,
                valid_votes, total_votes, apc_votes, pdp_votes, nnpp_votes, lp_votes,
                adc_votes, prp_votes, other_votes, agent_name, agent_phone,
                agent_party, incident_report, status, flags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, res)

    # Preload sample broadcasts
    c.execute("""
        INSERT INTO broadcasts (title, content, priority)
        VALUES 
        ('Situation Room Activated', 'Jigawa Northwest Senatorial District collation situation room is live. Authorized Admin Collators can enter authenticated EC8A results.', 'ALERT'),
        ('BVAS Battery Advisory', 'Any polling units reporting low BVAS power in Babura or Maigatari border areas should contact the LGA Field Operations Officer on 08020000001.', 'NORMAL')
    """)

    # Preload sample incident
    c.execute("""
        INSERT INTO incidents (lga, ward, pu_code, agent_name, agent_phone, incident_type, severity, description, status)
        VALUES ('Maigatari', 'Border Area', 'MGT-08-001', 'Hamisu Maigatari', '08032345678', 'BVAS_FAILURE', 'MEDIUM', 'BVAS facial verification slow in intense sunlight. INEC technician alerted.', 'INVESTIGATING')
    """)

if __name__ == "__main__":
    init_db()
    print("Database and Admin schema initialized successfully.")
