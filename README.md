

# 🏥 CarePlus: Hospital Record & Billing Management System

**CarePlus** is a full-stack DBMS application designed to streamline hospital operations, including patient registration, clinical visit tracking, treatment logging, and financial management. It features a role-based access control system for Doctors, Nurses, Patients, and Accountants.

---

## ✨ Key Features

### 🛠️ Role-Based Functionality
* **Doctors/Nurses:** Manage patient records, log clinical visits, update diagnoses in real-time, and prescribe treatments.
* **Patients:** View a personalized dashboard including medical history, upcoming visits, and pending payments.
* **Accountants:** Access financial analytics and manage billing/payment status.

### 📊 Clinical & Financial Management
* **Dynamic Analytics:** View reports on "Visits by Doctor" and "Revenue by Payment Status."
* **Database Triggers:** Automated ID generation (e.g., `P097`) and payment updates using stored procedures.
* **Integrated Billing:** Track payments from "Pending" to "Paid" with historical logging.

### 💻 Modern Tech Stack
* **Backend:** Python (Flask)
* **Database:** MySQL with `mysql-connector-python`
* **Frontend:** HTML5, CSS3 (Modern Dark UI), and Vanilla JavaScript
* **API:** RESTful endpoints with CORS support for seamless integration

---

## 🚀 Getting Started

### 1. Database Setup
Ensure you have a MySQL server running. Create a database named `hospital_record_management_system` and configure your tables. 
*Default credentials in `app_simple.py`:*
- **Host:** localhost
- **User:** root
- **Password:** 123456

### 2. Backend Installation
```bash
# Install dependencies
pip install flask flask-cors mysql-connector-python

# Run the API
python app_simple.py
```
*The API will start on `http://localhost:5000`.*

### 3. Launch the Frontend
Simply open `front.html` in any modern web browser. The frontend is configured to communicate with the local Flask server.

---

## 🛠️ API Architecture

The system relies on a clean REST API structure:

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/stats` | `GET` | Returns totals for patients, doctors, and revenue. |
| `/patients` | `POST` | Registers a new patient in the system. |
| `/visits` | `PATCH` | Updates a visit diagnosis via `VisitID`. |
| `/payments` | `PATCH` | Marks a payment as 'Paid' via a stored procedure. |
| `/analytics/revenue_by_status` | `GET` | Aggregates revenue data for financial reporting. |

---

## 📸 Interface Preview
* **Dark-themed UI:** Designed for low-light clinical environments.
* **Interactive Tables:** Inline editing for diagnoses and status-based badges for payments.
* **Responsive Sidebar:** Dynamic navigation that changes based on your logged-in role.

---

## 👨‍💻 Author
**Harsh Anant Datar** *B.Tech Computer Science & Engineering | MIT ADT University*

---

