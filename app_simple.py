
from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import os

DB = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', '123456'),
    'database': os.getenv('DB_NAME', 'hospital_record_management_system'),
    'port': int(os.getenv('DB_PORT', '3306')),
}
PORT = int(os.getenv('PORT', '5000'))

app = Flask(__name__)
CORS(app)

def connect_db():
    return mysql.connector.connect(**DB)

def q_select(sql, params=()):
    conn = connect_db()
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def q_modify(sql, params=()):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    last_id = cur.lastrowid
    cur.close(); conn.close()
    return last_id

def call_proc(name, args=()):
    conn = connect_db()
    cur = conn.cursor()
    cur.callproc(name, args)
    conn.commit()
    cur.close(); conn.close()

def bad(msg, code=400):
    return jsonify({'ok': False, 'error': msg}), code

def ok(payload=None, code=200):
    data = {'ok': True}
    if payload is not None:
        if isinstance(payload, dict):
            data.update(payload)
        else:
            data['data'] = payload
    return jsonify(data), code

@app.get('/health')
def health():
    try:
        q_select('SELECT 1')
        return ok({'status': 'up'})
    except Error as e:
        return bad(str(e), 500)

@app.get('/stats')
def stats():
    try:
        p = q_select('SELECT COUNT(*) AS c FROM patient')[0]['c']
        d = q_select('SELECT COUNT(*) AS c FROM doctor')[0]['c']
        v = q_select('SELECT COUNT(*) AS c FROM visit')[0]['c']
        rev = q_select("SELECT COALESCE(SUM(Amount),0) AS total FROM payment WHERE Status='Paid'")[0]['total']
        return ok({'patients': p, 'doctors': d, 'visits': v, 'revenue': float(rev or 0)})
    except Error as e:
        return bad(str(e), 500)

# -------- People (ID-only lookup for login) --------
@app.get('/patients')
def patients_list():
    pid = request.args.get('id')
    name = request.args.get('name')
    try:
        if pid:
            rows = q_select('SELECT * FROM patient WHERE PatientID=%s', (pid,))
        elif name:
            rows = q_select('SELECT * FROM patient WHERE Name LIKE %s ORDER BY Name', (f'%{name}%',))
        else:
            rows = q_select('SELECT * FROM patient ORDER BY PatientID')
        return jsonify(rows)
    except Error as e:
        return bad(str(e), 500)

@app.post('/patients')
def patients_add():
    d = request.get_json(silent=True) or {}
    for k in ['Name','Age','Gender','ContactNumber']:
        if not d.get(k):
            return bad(f'Missing {k}')
    try:
        q_modify('INSERT INTO patient (Name,Age,Gender,ContactNumber) VALUES (%s,%s,%s,%s)',
                 (d['Name'], d['Age'], d['Gender'], d['ContactNumber']))
        return ok({'msg': 'Patient created'}), 201
    except Error as e:
        return bad(str(e), 500)

@app.delete('/patients/<pid>')
def patients_delete(pid):
    try:
        q_modify('DELETE FROM patient WHERE PatientID=%s', (pid,))
        return ok({'deleted': pid})
    except Error as e:
        return bad(str(e), 500)

@app.get('/doctors')
def doctors_list():
    did = request.args.get('id')
    name = request.args.get('name')
    spec = request.args.get('specialty')
    try:
        if did:
            rows = q_select('SELECT * FROM xor WHERE DoctorID=%s', (did,))
        elif name:
            rows = q_select('SELECT * FROM doctor WHERE Name LIKE %s ORDER BY Name', (f'%{name}%',))
        elif spec:
            rows = q_select('SELECT * FROM doctor WHERE Specialty LIKE %s ORDER BY Name', (f'%{spec}%',))
        else:
            rows = q_select('SELECT * FROM doctor ORDER BY DoctorID')
        return jsonify(rows)
    except Error as e:
        return bad(str(e), 500)

@app.post('/doctors')
def doctors_add():
    d = request.get_json(silent=True) or {}
    if not d.get('Name') or not d.get('Specialty'):
        return bad('Name and Specialty required')
    try:
        q_modify('INSERT INTO doctor (Name,Specialty) VALUES (%s,%s)',
                 (d['Name'], d['Specialty']))
        return ok({'msg': 'Doctor created'}), 201
    except Error as e:
        return bad(str(e), 500)

@app.get('/nurses')
def nurses_list():
    nid = request.args.get('id')
    name = request.args.get('name')
    try:
        if nid:
            rows = q_select('SELECT * FROM nurse WHERE NurseID=%s', (nid,))
        elif name:
            rows = q_select('SELECT * FROM nurse WHERE Name LIKE %s ORDER BY Name', (f'%{name}%',))
        else:
            rows = q_select('SELECT * FROM nurse ORDER BY NurseID')
        return jsonify(rows)
    except Error as e:
        return bad(str(e), 500)

@app.post('/nurses')
def nurses_add():
    d = request.get_json(silent=True) or {}
    if not d.get('Name'):
        return bad('Name required')
    try:
        q_modify('INSERT INTO nurse (Name) VALUES (%s)', (d['Name'],))
        return ok({'msg': 'Nurse created'}), 201
    except Error as e:
        return bad(str(e), 500)

# -------- Clinical & billing --------
@app.get('/visits')
def visits_list():
    pid = request.args.get('patientId')
    did = request.args.get('doctorId')
    where, params = [], []
    base = '''
        SELECT v.VisitID, v.VisitDate, v.Diagnosis,
               p.PatientID, p.Name AS PatientName,
               d.DoctorID, d.Name AS DoctorName
        FROM visit v
        JOIN patient p ON p.PatientID=v.PatientID
        JOIN doctor  d ON d.DoctorID=v.DoctorID
    '''
    if pid:
        where.append('p.PatientID=%s'); params.append(pid)
    if did:
        where.append('d.DoctorID=%s'); params.append(did)
    if where:
        base += ' WHERE ' + ' AND '.join(where)
    base += ' ORDER BY v.VisitDate DESC'
    try:
        rows = q_select(base, tuple(params))
        return jsonify(rows)
    except Error as e:
        return bad(str(e), 500)

@app.post('/visits')
def visits_add():
    d = request.get_json(silent=True) or {}
    for k in ['PatientID','DoctorID','VisitDate']:
        if not d.get(k):
            return bad(f'Missing {k}')
    try:
        q_modify('INSERT INTO visit (PatientID,DoctorID,VisitDate,Diagnosis) VALUES (%s,%s,%s,%s)',
                 (d['PatientID'], d['DoctorID'], d['VisitDate'], d.get('Diagnosis','')))
        return ok({'msg':'Visit created'}), 201
    except Error as e:
        return bad(str(e), 500)

@app.patch('/visits/<int:visit_id>/diagnosis')
def update_visit_diagnosis(visit_id):
    d = request.get_json(silent=True) or {}
    new_dx = (d.get('Diagnosis') or '').strip()
    if new_dx == '':
        return bad('Diagnosis cannot be empty')
    try:
        q_modify('UPDATE visit SET Diagnosis=%s WHERE VisitID=%s', (new_dx, visit_id))
        return ok({'VisitID': visit_id, 'Diagnosis': new_dx})
    except Error as e:
        return bad(str(e), 500)

@app.get('/treatments')
def treatments_list():
    vid = request.args.get('visitId')
    pid = request.args.get('patientId')
    where, params = [], []
    base = '''
      SELECT t.TreatmentID, t.VisitID, t.Notes,
             m.MedicationID, m.Name AS MedicationName, m.Dosage,
             v.PatientID, v.DoctorID, v.VisitDate
      FROM treatment t
      LEFT JOIN medication m ON m.MedicationID=t.MedicationID
      JOIN visit v ON v.VisitID=t.VisitID
    '''
    if vid:
        where.append('t.VisitID=%s'); params.append(vid)
    if pid:
        where.append('v.PatientID=%s'); params.append(pid)
    if where:
        base += ' WHERE ' + ' AND '.join(where)
    base += ' ORDER BY t.TreatmentID DESC'
    try:
        rows = q_select(base, tuple(params))
        return jsonify(rows)
    except Error as e:
        return bad(str(e), 500)

@app.post('/treatments')
def treatments_add():
    d = request.get_json(silent=True) or {}
    if not d.get('VisitID'):
        return bad('Missing VisitID')
    try:
        q_modify('INSERT INTO treatment (VisitID,MedicationID,Notes) VALUES (%s,%s,%s)',
                 (d['VisitID'], d.get('MedicationID'), d.get('Notes')))
        return ok({'msg':'Treatment created'}), 201
    except Error as e:
        return bad(str(e), 500)

@app.get('/medications')
def meds_list():
    name = request.args.get('name')
    try:
        if name:
            rows = q_select('SELECT * FROM medication WHERE Name LIKE %s ORDER BY Name', (f'%{name}%',))
        else:
            rows = q_select('SELECT * FROM medication ORDER BY MedicationID')
        return jsonify(rows)
    except Error as e:
        return bad(str(e), 500)

@app.post('/medications')
def meds_add():
    d = request.get_json(silent=True) or {}
    if not d.get('Name') or not d.get('Dosage'):
        return bad('Name and Dosage required')
    try:
        q_modify('INSERT INTO medication (Name,Dosage) VALUES (%s,%s)', (d['Name'], d['Dosage']))
        return ok({'msg':'Medication created'}), 201
    except Error as e:
        return bad(str(e), 500)

@app.get('/payments')
def payments_list():
    pid = request.args.get('patientId')
    base = '''
        SELECT pay.PaymentID, pay.PatientID, p.Name AS PatientName, pay.VisitID,
               pay.Amount, pay.Status, pay.PaidOn
        FROM payment pay JOIN patient p ON p.PatientID=pay.PatientID
    '''
    params = []
    if pid:
        base += ' WHERE pay.PatientID=%s'; params.append(pid)
    base += ' ORDER BY COALESCE(pay.PaidOn, "1970-01-01") DESC, pay.PaymentID DESC'
    try:
        rows = q_select(base, tuple(params))
        return jsonify(rows)
    except Error as e:
        return bad(str(e), 500)

@app.post('/payments')
def payments_add():
    d = request.get_json(silent=True) or {}
    for k in ['PatientID','Amount','Status']:
        if not d.get(k):
            return bad(f'Missing {k}')
    try:
        q_modify('INSERT INTO payment (PatientID,VisitID,Amount,Status) VALUES (%s,%s,%s,%s)',
                 (d['PatientID'], d.get('VisitID'), d['Amount'], d['Status']))
        return ok({'msg':'Payment created'}), 201
    except Error as e:
        return bad(str(e), 500)

@app.patch('/payments/<int:payid>/markPaid')
def payments_mark_paid(payid):
    try:
        call_proc('sp_mark_payment_paid', (payid,))
        return ok({'PaymentID': payid, 'Status':'Paid'})
    except Error as e:
        return bad(str(e), 500)

@app.get('/records')
def records_list():
    pid = request.args.get('patientId')
    did = request.args.get('doctorId')
    where, params = [], []
    base = '''
      SELECT r.RecordID, r.PatientID, p.Name AS PatientName,
             r.DoctorID, d.Name AS DoctorName, r.Title, r.CreatedOn
      FROM records r
      JOIN patient p ON p.PatientID=r.PatientID
      LEFT JOIN doctor d ON d.DoctorID=r.DoctorID
    '''
    if pid:
        where.append('r.PatientID=%s'); params.append(pid)
    if did:
        where.append('r.DoctorID=%s'); params.append(did)
    if where:
        base += ' WHERE ' + ' AND '.join(where)
    base += ' ORDER BY r.CreatedOn DESC'
    try:
        rows = q_select(base, tuple(params))
        return jsonify(rows)
    except Error as e:
        return bad(str(e), 500)

# -------- Analytics (joins/group by/order by) --------
@app.get('/analytics/visits_by_doctor')
def visits_by_doctor():
    try:
        rows = q_select('''
            SELECT d.DoctorID, d.Name AS DoctorName, COUNT(v.VisitID) AS VisitCount
            FROM doctor d
            LEFT JOIN visit v ON v.DoctorID=d.DoctorID
            GROUP BY d.DoctorID, d.Name
            ORDER BY VisitCount DESC, DoctorName ASC
        ''')
        return jsonify(rows)
    except Error as e:
        return bad(str(e), 500)

@app.get('/analytics/revenue_by_status')
def revenue_by_status():
    try:
        rows = q_select('''
            SELECT Status, COUNT(*) AS Payments, ROUND(SUM(Amount),2) AS TotalAmount
            FROM payment
            GROUP BY Status
            ORDER BY FIELD(Status,'Paid','Pending','Other'), TotalAmount DESC
        ''')
        return jsonify(rows)
    except Error as e:
        return bad(str(e), 500)

@app.get('/profile')
def patient_profile():
    pid = request.args.get('patientId')
    did = request.args.get('doctorId')  # optional filter
    if not pid: return bad('patientId required')
    try:
        patient = q_select('SELECT * FROM patient WHERE PatientID=%s', (pid,))
        vsql = '''
            SELECT v.VisitID, v.VisitDate, v.Diagnosis, d.DoctorID, d.Name AS DoctorName
            FROM visit v JOIN doctor d ON d.DoctorID=v.DoctorID
            WHERE v.PatientID=%s
        '''
        params = [pid]
        if did:
            vsql += ' AND d.DoctorID=%s'; params.append(did)
        vsql += ' ORDER BY v.VisitDate DESC'
        visits = q_select(vsql, tuple(params))
        treatments = q_select('''
            SELECT t.TreatmentID, t.VisitID, t.Notes, m.Name AS MedicationName, m.Dosage
            FROM treatment t LEFT JOIN medication m ON m.MedicationID=t.MedicationID
            JOIN visit v ON v.VisitID=t.VisitID
            WHERE v.PatientID=%s ORDER BY t.TreatmentID DESC
        ''', (pid,))
        recs = q_select('''
            SELECT r.RecordID, r.Title, r.CreatedOn, r.DoctorID, d.Name AS DoctorName
            FROM records r LEFT JOIN doctor d ON d.DoctorID=r.DoctorID
            WHERE r.PatientID=%s ORDER BY r.CreatedOn DESC
        ''', (pid,))
        pays = q_select('''
            SELECT PaymentID, Amount, Status, PaidOn
            FROM payment WHERE PatientID=%s ORDER BY COALESCE(PaidOn,'1970-01-01') DESC, PaymentID DESC
        ''', (pid,))
        return ok({'patient': patient[0] if patient else None,
                   'visits': visits, 'treatments': treatments,
                   'records': recs, 'payments': pays})
    except Error as e:
        return bad(str(e), 500)

if __name__ == '__main__':
    print(f"API on http://localhost:{PORT}")
    app.run(debug=True, host='0.0.0.0', port=PORT)
