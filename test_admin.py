import urllib.request
import json
import time

def test_admin_flow():
    # 1. Test unauthorized result submit (must fail)
    unauth_req = urllib.request.Request(
        'http://localhost:8000/api/results/submit',
        data=json.dumps({'pu_code':'X'}).encode('utf-8'),
        headers={'Content-Type':'application/json'}
    )
    try:
        urllib.request.urlopen(unauth_req)
        print("FAIL: Unauthorized submit succeeded")
    except urllib.error.HTTPError as e:
        print(f"PASS: Unauthorized submit rejected with HTTP {e.code}")

    # 2. Login admin
    login_data = json.dumps({'username':'admin','password':'admin123'}).encode('utf-8')
    login_req = urllib.request.Request(
        'http://localhost:8000/api/admin/login',
        data=login_data,
        headers={'Content-Type':'application/json'}
    )
    with urllib.request.urlopen(login_req) as res:
        login_resp = json.loads(res.read().decode())
        token = login_resp['token']
        print(f"PASS: Admin login authenticated. Admin: {login_resp['admin']['username']}")

    # 3. Add party agent as Admin with a unique phone
    unique_phone = f"080{int(time.time()) % 100000000:08d}"
    agent_data = json.dumps({
        'phone': unique_phone,
        'full_name': 'Malam Sani Babura',
        'pin': '1234',
        'party': 'APC',
        'lga': 'Babura',
        'ward': 'Babura',
        'pu_code': f'BBR-01-{unique_phone[-3:]}',
        'pu_name': 'Babura Central Gate PU'
    }).encode('utf-8')
    agent_req = urllib.request.Request(
        'http://localhost:8000/api/admin/agent/add',
        data=agent_data,
        headers={'Content-Type':'application/json', 'Authorization': f'Bearer {token}'}
    )
    with urllib.request.urlopen(agent_req) as res:
        agent_resp = json.loads(res.read().decode())
        print(f"PASS: Agent accredited: {agent_resp['message']}")

    # 4. Submit result as Admin
    result_data = json.dumps({
        'pu_code': f'BBR-01-{unique_phone[-3:]}',
        'pu_name': 'Babura Central Gate PU',
        'lga': 'Babura',
        'ward': 'Babura',
        'registered_voters': 500,
        'accredited_voters': 320,
        'ballots_issued': 350,
        'unused_ballots': 30,
        'spoiled_ballots': 0,
        'rejected_ballots': 5,
        'apc_votes': 210,
        'pdp_votes': 80,
        'nnpp_votes': 25,
        'lp_votes': 0,
        'adc_votes': 0,
        'prp_votes': 0,
        'other_votes': 0,
        'agent_name': 'Malam Sani Babura',
        'agent_phone': unique_phone,
        'agent_party': 'APC',
        'incident_report': 'Certified count by Situation Room Admin'
    }).encode('utf-8')
    result_req = urllib.request.Request(
        'http://localhost:8000/api/results/submit',
        data=result_data,
        headers={'Content-Type':'application/json', 'Authorization': f'Bearer {token}'}
    )
    with urllib.request.urlopen(result_req) as res:
        result_resp = json.loads(res.read().decode())
        print(f"PASS: Result registered: {result_resp['message']}")

if __name__ == '__main__':
    test_admin_flow()
