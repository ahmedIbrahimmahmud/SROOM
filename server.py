import http.server
import socketserver
import json
import urllib.parse
import os
import sys
from datetime import datetime
from database import get_db, hash_pin, generate_token
from data_reference import LGAS_DATA, PARTIES

PORT = int(os.environ.get("PORT", 8000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class SituationRoomHandler(http.server.SimpleHTTPRequestHandler):
    def get_auth_token(self):
        auth_header = self.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            return auth_header.split('Bearer ', 1)[1].strip()
        return None

    def get_current_admin(self):
        token = self.get_auth_token()
        if not token:
            return None
        conn = get_db()
        c = conn.cursor()
        c.execute("""
            SELECT s.token, a.id, a.username, a.full_name, a.role
            FROM admin_sessions s
            JOIN admins a ON s.admin_id = a.id
            WHERE s.token = ?
        """, (token,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Static assets
        if path == "/" or path == "/index.html":
            self.serve_file(os.path.join(BASE_DIR, "index.html"), "text/html; charset=utf-8")
            return
        elif path.startswith("/static/"):
            file_path = os.path.join(BASE_DIR, path.lstrip("/"))
            if os.path.exists(file_path):
                ext = os.path.splitext(file_path)[1]
                mime_types = {
                    ".css": "text/css; charset=utf-8",
                    ".js": "application/javascript; charset=utf-8",
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".svg": "image/svg+xml"
                }
                self.serve_file(file_path, mime_types.get(ext, "application/octet-stream"))
            else:
                self.send_error(404, "File Not Found")
            return

        # API Routes
        if path == "/api/metadata":
            self.send_json({
                "district": "Jigawa Northwest Senatorial District",
                "senatorial_zone": "Jigawa North-West (Zone A)",
                "lgas": LGAS_DATA,
                "parties": PARTIES
            })
            return

        elif path == "/api/admin/check":
            admin = self.get_current_admin()
            if admin:
                self.send_json({"authenticated": True, "admin": admin})
            else:
                self.send_json({"authenticated": False})
            return

        elif path == "/api/summary":
            self.get_summary()
            return

        elif path == "/api/results":
            self.get_results(query)
            return

        elif path == "/api/incidents":
            self.get_incidents()
            return

        elif path == "/api/broadcasts":
            self.get_broadcasts()
            return

        elif path == "/api/agents":
            self.get_agents()
            return

        elif path == "/api/export/csv":
            self.export_csv()
            return

        # Default fallback
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        content_len = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_len) if content_len > 0 else b""
        
        try:
            data = json.loads(post_body.decode('utf-8')) if post_body else {}
        except Exception:
            data = {}

        if path == "/api/admin/login":
            self.admin_login(data)
        elif path == "/api/admin/logout":
            self.admin_logout()
        elif path == "/api/admin/agent/add":
            self.admin_add_agent(data)
        elif path == "/api/agent/delete":
            self.admin_delete_agent(data)
        elif path == "/api/agent/verify":
            self.verify_agent(data)
        elif path == "/api/agent/register":
            # Direct public registration disabled - only admin can add
            self.send_json({
                "success": False,
                "message": "Public agent registration is disabled. Only authorized Situation Room Admins can accredit party agents."
            }, 403)
        elif path == "/api/results/submit":
            self.submit_result(data)
        elif path == "/api/incidents/submit":
            self.submit_incident(data)
        elif path == "/api/broadcasts/submit":
            self.submit_broadcast(data)
        else:
            self.send_error(404, "Unknown API Endpoint")

    def serve_file(self, filepath, content_type):
        if not os.path.exists(filepath):
            self.send_error(404, "File Not Found")
            return
        with open(filepath, "rb") as f:
            content = f.read()
        try:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass

    def send_json(self, data, status=200):
        body = json.dumps(data).encode('utf-8')
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.end_headers()
            self.wfile.write(body)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass

    # ------------------ ADMIN AUTHENTICATION ------------------

    def admin_login(self, data):
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        if not username or not password:
            self.send_json({"success": False, "message": "Username and password required"}, 400)
            return

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM admins WHERE username = ?", (username,))
        admin = c.fetchone()

        if not admin or admin["password_hash"] != hash_pin(password):
            conn.close()
            self.send_json({"success": False, "message": "Invalid admin credentials"}, 401)
            return

        token = generate_token()
        c.execute("INSERT INTO admin_sessions (token, admin_id, username) VALUES (?, ?, ?)",
                  (token, admin["id"], admin["username"]))
        conn.commit()
        conn.close()

        self.send_json({
            "success": True,
            "message": "Admin authenticated successfully",
            "token": token,
            "admin": {
                "id": admin["id"],
                "username": admin["username"],
                "full_name": admin["full_name"],
                "role": admin["role"]
            }
        })

    def admin_logout(self):
        token = self.get_auth_token()
        if token:
            conn = get_db()
            c = conn.cursor()
            c.execute("DELETE FROM admin_sessions WHERE token = ?", (token,))
            conn.commit()
            conn.close()
        self.send_json({"success": True, "message": "Logged out successfully"})

    # ------------------ ADMIN-ONLY AGENT MANAGEMENT ------------------

    def admin_add_agent(self, data):
        admin = self.get_current_admin()
        if not admin:
            self.send_json({"success": False, "message": "Unauthorized. Situation Room Admin login required."}, 401)
            return

        phone = data.get("phone", "").strip()
        full_name = data.get("full_name", "").strip()
        pin = data.get("pin", "1234").strip()
        party = data.get("party", "ADC").strip() or "ADC"
        lga = data.get("lga", "").strip()
        ward = data.get("ward", "").strip()
        pu_code = data.get("pu_code", "").strip()
        pu_name = data.get("pu_name", "").strip()

        if not all([phone, full_name, pin, party, lga, ward, pu_code, pu_name]):
            self.send_json({"success": False, "message": "All party agent fields are required"}, 400)
            return

        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO agents (phone, full_name, pin_hash, party, lga, ward, pu_code, pu_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (phone, full_name, hash_pin(pin), party, lga, ward, pu_code, pu_name))
            conn.commit()
            agent_id = c.lastrowid
            conn.close()
            self.send_json({
                "success": True,
                "message": f"ADC Party Agent '{full_name}' successfully accredited by Admin {admin['username']}",
                "agent_id": agent_id
            })
        except Exception as e:
            conn.close()
            self.send_json({"success": False, "message": f"Could not add agent: {str(e)}"}, 400)

    def admin_delete_agent(self, data):
        admin = self.get_current_admin()
        if not admin:
            self.send_json({"success": False, "message": "Unauthorized. Admin credentials required."}, 401)
            return

        agent_id = data.get("id")
        if not agent_id:
            self.send_json({"success": False, "message": "Agent ID is required"}, 400)
            return

        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
        conn.commit()
        conn.close()
        self.send_json({"success": True, "message": "Agent record removed."})

    # ------------------ AGENT LOOKUP ------------------

    def verify_agent(self, data):
        phone = data.get("phone", "").strip()
        pin = data.get("pin", "").strip()
        if not phone:
            self.send_json({"success": False, "message": "Phone number required"}, 400)
            return

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM agents WHERE phone = ?", (phone,))
        row = c.fetchone()
        conn.close()

        if not row:
            self.send_json({"success": False, "message": "Agent with this phone number not found"}, 404)
            return

        if pin and row["pin_hash"] != hash_pin(pin):
            self.send_json({"success": False, "message": "Invalid PIN code"}, 401)
            return

        self.send_json({
            "success": True,
            "agent": {
                "id": row["id"],
                "phone": row["phone"],
                "full_name": row["full_name"],
                "party": row["party"],
                "lga": row["lga"],
                "ward": row["ward"],
                "pu_code": row["pu_code"],
                "pu_name": row["pu_name"]
            }
        })

    # ------------------ ADMIN-ONLY RESULT ENTRY ------------------

    def submit_result(self, data):
        # Enforce that ONLY authenticated Admin can enter results
        admin = self.get_current_admin()
        if not admin:
            self.send_json({
                "success": False,
                "message": "PERMISSION DENIED: Only authorized Situation Room Admins can enter or modify electoral box results."
            }, 401)
            return

        pu_code = data.get("pu_code", "").strip()
        lga = data.get("lga", "").strip()
        ward = data.get("ward", "").strip()
        pu_name = data.get("pu_name", "").strip()
        agent_name = data.get("agent_name", "").strip()
        agent_phone = data.get("agent_phone", "").strip()
        agent_party = data.get("agent_party", "ADC").strip() or "ADC"

        if not pu_code or not lga or not pu_name or not agent_phone:
            self.send_json({"success": False, "message": "Polling unit code, LGA, Name and Agent info are required"}, 400)
            return

        reg = int(data.get("registered_voters", 0) or 0)
        acc = int(data.get("accredited_voters", 0) or 0)
        issued = int(data.get("ballots_issued", 0) or 0)
        unused = int(data.get("unused_ballots", 0) or 0)
        spoiled = int(data.get("spoiled_ballots", 0) or 0)
        rejected = int(data.get("rejected_ballots", 0) or 0)

        apc = int(data.get("apc_votes", 0) or 0)
        pdp = int(data.get("pdp_votes", 0) or 0)
        nnpp = int(data.get("nnpp_votes", 0) or 0)
        lp = int(data.get("lp_votes", 0) or 0)
        adc = int(data.get("adc_votes", 0) or 0)
        prp = int(data.get("prp_votes", 0) or 0)
        other = int(data.get("other_votes", 0) or 0)

        valid_votes = apc + pdp + nnpp + lp + adc + prp + other
        total_votes = valid_votes + rejected

        # Anomaly detection & verification flags
        flags = []
        status = "VERIFIED"

        if acc > reg and reg > 0:
            flags.append(f"OVERSUBSCRIPTION: Accredited voters ({acc}) exceeds Registered voters ({reg})")
            status = "FLAGGED"

        if total_votes > acc and acc > 0:
            flags.append(f"OVER-VOTING: Total votes cast ({total_votes}) exceeds Accredited voters ({acc})")
            status = "FLAGGED"

        if issued > 0 and (total_votes + unused + spoiled) > (issued + 5):
            flags.append("BALLOT_RECONCILIATION_MISMATCH: Votes + Unused + Spoiled does not balance with Issued ballots")
            status = "FLAGGED"

        ec8a_photo = data.get("ec8a_photo", "")
        incident_report = data.get("incident_report", "").strip()

        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO pu_results (
                    lga, ward, pu_code, pu_name, registered_voters, accredited_voters,
                    ballots_issued, unused_ballots, spoiled_ballots, rejected_ballots,
                    valid_votes, total_votes, apc_votes, pdp_votes, nnpp_votes, lp_votes,
                    adc_votes, prp_votes, other_votes, agent_name, agent_phone,
                    agent_party, ec8a_photo, incident_report, status, flags, submitted_by_admin, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(pu_code) DO UPDATE SET
                    lga=excluded.lga,
                    ward=excluded.ward,
                    pu_name=excluded.pu_name,
                    registered_voters=excluded.registered_voters,
                    accredited_voters=excluded.accredited_voters,
                    ballots_issued=excluded.ballots_issued,
                    unused_ballots=excluded.unused_ballots,
                    spoiled_ballots=excluded.spoiled_ballots,
                    rejected_ballots=excluded.rejected_ballots,
                    valid_votes=excluded.valid_votes,
                    total_votes=excluded.total_votes,
                    apc_votes=excluded.apc_votes,
                    pdp_votes=excluded.pdp_votes,
                    nnpp_votes=excluded.nnpp_votes,
                    lp_votes=excluded.lp_votes,
                    adc_votes=excluded.adc_votes,
                    prp_votes=excluded.prp_votes,
                    other_votes=excluded.other_votes,
                    agent_name=excluded.agent_name,
                    agent_phone=excluded.agent_phone,
                    agent_party=excluded.agent_party,
                    ec8a_photo=CASE WHEN excluded.ec8a_photo != '' THEN excluded.ec8a_photo ELSE pu_results.ec8a_photo END,
                    incident_report=excluded.incident_report,
                    status=excluded.status,
                    flags=excluded.flags,
                    submitted_by_admin=excluded.submitted_by_admin,
                    updated_at=CURRENT_TIMESTAMP
            """, (
                lga, ward, pu_code, pu_name, reg, acc, issued, unused, spoiled, rejected,
                valid_votes, total_votes, apc, pdp, nnpp, lp, adc, prp, other,
                agent_name, agent_phone, agent_party, ec8a_photo, incident_report, status, json.dumps(flags), admin["username"]
            ))
            conn.commit()
            conn.close()

            self.send_json({
                "success": True,
                "message": f"Result for Polling Unit {pu_code} authenticated and recorded by Admin {admin['username']}.",
                "pu_code": pu_code,
                "status": status,
                "flags": flags,
                "valid_votes": valid_votes,
                "total_votes": total_votes
            })
        except Exception as e:
            conn.close()
            self.send_json({"success": False, "message": f"Submission failed: {str(e)}"}, 500)

    def submit_incident(self, data):
        conn = get_db()
        c = conn.cursor()
        c.execute("""
            INSERT INTO incidents (lga, ward, pu_code, agent_name, agent_phone, incident_type, severity, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("lga", ""),
            data.get("ward", ""),
            data.get("pu_code", ""),
            data.get("agent_name", ""),
            data.get("agent_phone", ""),
            data.get("incident_type", "OTHER"),
            data.get("severity", "MEDIUM"),
            data.get("description", "")
        ))
        conn.commit()
        inc_id = c.lastrowid
        conn.close()
        self.send_json({"success": True, "incident_id": inc_id, "message": "Incident logged into Situation Room triage queue"})

    def submit_broadcast(self, data):
        admin = self.get_current_admin()
        if not admin:
            self.send_json({"success": False, "message": "Unauthorized. Admin access required."}, 401)
            return

        conn = get_db()
        c = conn.cursor()
        c.execute("""
            INSERT INTO broadcasts (title, content, priority)
            VALUES (?, ?, ?)
        """, (
            data.get("title", "Notice"),
            data.get("content", ""),
            data.get("priority", "NORMAL")
        ))
        conn.commit()
        conn.close()
        self.send_json({"success": True, "message": "Broadcast transmitted"})

    def get_summary(self):
        conn = get_db()
        c = conn.cursor()

        # Overall district aggregates
        c.execute("""
            SELECT 
                COUNT(*) as reported_pus,
                COALESCE(SUM(registered_voters), 0) as total_registered,
                COALESCE(SUM(accredited_voters), 0) as total_accredited,
                COALESCE(SUM(valid_votes), 0) as total_valid_votes,
                COALESCE(SUM(rejected_ballots), 0) as total_rejected_votes,
                COALESCE(SUM(total_votes), 0) as total_votes_cast,
                COALESCE(SUM(apc_votes), 0) as apc_total,
                COALESCE(SUM(pdp_votes), 0) as pdp_total,
                COALESCE(SUM(nnpp_votes), 0) as nnpp_total,
                COALESCE(SUM(lp_votes), 0) as lp_total,
                COALESCE(SUM(adc_votes), 0) as adc_total,
                COALESCE(SUM(prp_votes), 0) as prp_total,
                COALESCE(SUM(other_votes), 0) as other_total,
                SUM(CASE WHEN status = 'FLAGGED' THEN 1 ELSE 0 END) as flagged_count,
                SUM(CASE WHEN status = 'VERIFIED' THEN 1 ELSE 0 END) as verified_count
            FROM pu_results
        """)
        agg = dict(c.fetchone())

        # LGA breakdowns
        c.execute("""
            SELECT 
                lga,
                COUNT(*) as reported_pus,
                COALESCE(SUM(accredited_voters), 0) as accredited,
                COALESCE(SUM(valid_votes), 0) as valid_votes,
                COALESCE(SUM(apc_votes), 0) as apc,
                COALESCE(SUM(pdp_votes), 0) as pdp,
                COALESCE(SUM(nnpp_votes), 0) as nnpp,
                COALESCE(SUM(lp_votes), 0) as lp,
                COALESCE(SUM(adc_votes), 0) as adc,
                COALESCE(SUM(prp_votes), 0) as prp,
                COALESCE(SUM(other_votes), 0) as other,
                SUM(CASE WHEN status = 'FLAGGED' THEN 1 ELSE 0 END) as flagged_pus
            FROM pu_results
            GROUP BY lga
            ORDER BY lga ASC
        """)
        lga_breakdown = [dict(row) for row in c.fetchall()]

        # Incident metrics
        c.execute("SELECT COUNT(*) as cnt FROM incidents WHERE status = 'OPEN'")
        open_incidents = c.fetchone()["cnt"]

        # Latest updates
        c.execute("SELECT * FROM pu_results ORDER BY updated_at DESC LIMIT 8")
        latest_results = [dict(row) for row in c.fetchall()]

        conn.close()

        # Calculate party standing
        party_totals = [
            {"code": "APC", "name": "All Progressives Congress", "votes": agg["apc_total"], "color": "#0284c7"},
            {"code": "PDP", "name": "Peoples Democratic Party", "votes": agg["pdp_total"], "color": "#16a34a"},
            {"code": "NNPP", "name": "New Nigeria Peoples Party", "votes": agg["nnpp_total"], "color": "#dc2626"},
            {"code": "LP", "name": "Labour Party", "votes": agg["lp_total"], "color": "#ea580c"},
            {"code": "ADC", "name": "African Democratic Congress", "votes": agg["adc_total"], "color": "#9333ea"},
            {"code": "PRP", "name": "Peoples Redemption Party", "votes": agg["prp_total"], "color": "#e11d48"},
            {"code": "OTHER", "name": "Other Parties", "votes": agg["other_total"], "color": "#64748b"}
        ]
        party_totals.sort(key=lambda x: x["votes"], reverse=True)

        total_v = agg["total_valid_votes"]
        for p in party_totals:
            p["percentage"] = round((p["votes"] / total_v * 100), 2) if total_v > 0 else 0.0

        self.send_json({
            "metrics": agg,
            "party_totals": party_totals,
            "lga_breakdown": lga_breakdown,
            "open_incidents": open_incidents,
            "latest_results": latest_results,
            "timestamp": datetime.now().isoformat()
        })

    def get_results(self, query):
        conn = get_db()
        c = conn.cursor()
        
        sql = "SELECT * FROM pu_results WHERE 1=1"
        params = []

        if "lga" in query and query["lga"][0]:
            sql += " AND lga = ?"
            params.append(query["lga"][0])
        if "status" in query and query["status"][0]:
            sql += " AND status = ?"
            params.append(query["status"][0])
        if "search" in query and query["search"][0]:
            search_str = f"%{query['search'][0]}%"
            sql += " AND (pu_code LIKE ? OR pu_name LIKE ? OR ward LIKE ? OR agent_name LIKE ?)"
            params.extend([search_str, search_str, search_str, search_str])

        sql += " ORDER BY updated_at DESC LIMIT 200"

        c.execute(sql, params)
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        self.send_json(rows)

    def get_incidents(self):
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM incidents ORDER BY reported_at DESC LIMIT 50")
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        self.send_json(rows)

    def get_broadcasts(self):
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM broadcasts ORDER BY created_at DESC LIMIT 20")
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        self.send_json(rows)

    def get_agents(self):
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, phone, full_name, party, lga, ward, pu_code, pu_name, created_at FROM agents ORDER BY id DESC")
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        self.send_json(rows)

    def export_csv(self):
        conn = get_db()
        c = conn.cursor()
        c.execute("""
            SELECT pu_code, pu_name, lga, ward, registered_voters, accredited_voters,
                   ballots_issued, unused_ballots, spoiled_ballots, rejected_ballots,
                   valid_votes, total_votes, apc_votes, pdp_votes, nnpp_votes,
                   lp_votes, adc_votes, prp_votes, other_votes, agent_name, agent_phone,
                   agent_party, status, submitted_by_admin, submitted_at
            FROM pu_results ORDER BY lga, ward, pu_code
        """)
        rows = c.fetchall()
        conn.close()

        headers = [
            "Polling Unit Code", "Polling Unit Name", "LGA", "Ward", "Registered Voters",
            "Accredited Voters", "Ballots Issued", "Unused Ballots", "Spoiled Ballots",
            "Rejected Ballots", "Valid Votes", "Total Votes", "APC", "PDP", "NNPP",
            "LP", "ADC", "PRP", "Others", "Party Agent Name", "Agent Phone", "Party", "Status", "Admin Submitter", "Timestamp"
        ]

        csv_lines = [",".join([f'"{h}"' for h in headers])]
        for r in rows:
            line = [f'"{str(val)}"' for val in r]
            csv_lines.append(",".join(line))
        csv_data = "\r\n".join(csv_lines).encode('utf-8-sig')

        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", "attachment; filename=jigawa_northwest_results.csv")
        self.send_header("Content-Length", str(len(csv_data)))
        self.end_headers()
        self.wfile.write(csv_data)

class ThreadingSituationRoomServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

def run_server():
    with ThreadingSituationRoomServer(("", PORT), SituationRoomHandler) as httpd:
        print(f"Jigawa Northwest Situation Room Server running on port {PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down situation room server.")

if __name__ == "__main__":
    run_server()
