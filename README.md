# Jigawa Northwest Senatorial District - Situation Room Portal

An election Situation Room collation and field agent reporting portal tailored specifically for **Jigawa Northwest Senatorial District**.

---

## 🏛️ District Coverage
The system includes full coverage and geographic delimitations (LGAs, Wards, and Polling Units) for the 12 local government areas of Jigawa North-West:
- **Babura**
- **Gagarawa**
- **Garki**
- **Gumel**
- **Gwiwa**
- **Kazaure**
- **Maigatari**
- **Ringim**
- **Roni**
- **Taura**
- **Yankwashi**
- **Sule Tankarkar**

---

## 🔐 Role-Based Access Control (Admin Protection)

Per your strict protocol, **only verified Situation Room Admins** can:
1. **Add / Record Form EC8A Results**:
   - Unauthorized result submissions from unauthenticated users are blocked (`HTTP 401 Unauthorized`).
   - Every submitted electoral box result is stamped with the authenticated admin's identity (`submitted_by_admin`).
2. **Accredit & Add Party Agents**:
   - Only Admins can register new party agents to assigned polling units across the 12 LGAs.
   - Public self-registration is locked down.
3. **Admin Management & Directory**:
   - Inspect accredited agents per LGA, Ward, and PU code.
   - Quick one-click "Enter Result" for any accredited agent.
   - Remove or update agents.

### Default Admin Credentials:
- **Username:** `admin`
- **Password:** `admin123`

---

## ⚡ Core Features

1. **Live Situation Room Command Center**:
   - Total polling units reporting count
   - Real-time BVAS accredited voter metrics
   - Valid vs rejected ballots audit
   - Dynamic party standings leaderboard (APC, PDP, NNPP, LP, ADC, PRP, Others) with leading vote counts and progress percentages
   - LGA collation breakdown table
   - Live incoming electoral box stream with auto-refresh every 10 seconds

2. **Electoral Box Result Submission (Form EC8A - Admin Only)**:
   - Admin authentication check before unlocking the entry terminal
   - Auto-selects accredited party agents to populate Polling Unit details
   - Form fields for:
     - LGA & Ward cascading selectors
     - Polling Unit (PU) Code and Location
     - Registered Voters, BVAS Accredited Voters, Ballots Issued, Unused, Spoiled, and Rejected
     - Individual party votes with real-time automatic client-side reconciliation
     - Form EC8A snapshot image upload support
     - Admin certification remarks

3. **Automated Anti-Rigging & Audit Engine**:
   - Automatically detects **Over-Voting** (Total votes cast > Accredited voters)
   - Checks **Oversubscription** (Accredited voters > Registered voters)
   - Performs **Ballot Reconciliation Balance** (Ballots Issued vs Used + Unused + Spoiled)
   - Automatically flags suspicious polling unit entries for inspection

4. **Polling Units Database & Audit**:
   - Filter by LGA, audit status (`VERIFIED` vs `FLAGGED`), or keyword search
   - Detailed Form EC8A inspector modal with full ballot audit breakdown and recording admin stamp
   - One-click **Export to CSV** for official reporting

5. **Field Security & Incident Triage**:
   - Distress alerts: BVAS failures, ballot snatching, intimidation, late arrival of materials
   - Severity tags (`CRITICAL`, `HIGH`, `MEDIUM`) with incident logs

---

## 🚀 Running the Situation Room

```powershell
python server.py
```

Then open your browser at:
👉 **`http://localhost:8000`**

Click the **Admin Login** button at the top right (or navigate to **Add Box Result (Admin)** or **Party Agents (Admin)**) and sign in with `admin` / `admin123`.
