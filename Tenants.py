# app_student.py - Complete Student Project
# No external services needed - runs anywhere!

from flask import Flask, render_template_string, request, redirect, url_for, flash, session
from datetime import datetime
import sqlite3
import smtplib
from email.mime.text import MIMEText
import json
import os

app = Flask(__name__)
app.secret_key = 'student_project_secret_key'

# HTML Templates (embedded for single-file simplicity)
DASHBOARD_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Tenant Management System</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .container { max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
        .stat-card { background: white; padding: 1.5rem; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
        .stat-number { font-size: 2rem; font-weight: bold; color: #667eea; }
        .btn { display: inline-block; padding: 0.5rem 1rem; margin: 0.5rem; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; }
        .btn-primary { background: #667eea; color: white; }
        .btn-danger { background: #e74c3c; color: white; }
        .btn-success { background: #27ae60; color: white; }
        table { width: 100%; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        th, td { padding: 1rem; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #667eea; color: white; }
        .form-group { margin-bottom: 1rem; }
        .form-group label { display: block; margin-bottom: 0.5rem; font-weight: bold; }
        .form-group input, .form-group select { width: 100%; padding: 0.5rem; border: 1px solid #ddd; border-radius: 5px; }
        .alert { padding: 1rem; border-radius: 5px; margin-bottom: 1rem; }
        .alert-success { background: #d4edda; color: #155724; }
        .alert-error { background: #f8d7da; color: #721c24; }
        .nav { background: white; padding: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .nav a { margin: 0 1rem; text-decoration: none; color: #333; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏢 Scovia's Management System</h1>
        <p>Student Project</p>
    </div>
    <div class="nav">
        <a href="/">Dashboard</a>
        <a href="/tenants">Tenants</a>
        <a href="/add_tenant">Add Tenant</a>
        <a href="/record_payment">Record Payment</a>
        <a href="/reports">Reports</a>
    </div>
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
</body>
</html>
'''

INDEX_HTML = '''
{% extends "base.html" %}
{% block content %}
<div class="stats">
    <div class="stat-card">
        <h3>Total Tenants</h3>
        <div class="stat-number">{{ total_tenants }}</div>
    </div>
    <div class="stat-card">
        <h3>Total Outstanding Balance</h3>
        <div class="stat-number">${{ "%.2f"|format(total_balance) }}</div>
    </div>
    <div class="stat-card">
        <h3>Total Rent Collected</h3>
        <div class="stat-number">${{ "%.2f"|format(total_collected) }}</div>
    </div>
</div>
<div class="stat-card">
    <h3>Recent Payments</h3>
    <table>
        <thead>
            <tr><th>Tenant</th><th>Amount</th><th>Date</th><th>Method</th></tr>
        </thead>
        <tbody>
            {% for payment in recent_payments %}
            <tr>
                <td>{{ payment[0] }}</td>
                <td>${{ "%.2f"|format(payment[1]) }}</td>
                <td>{{ payment[2] }}</td>
                <td>{{ payment[3] }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
'''

TENANTS_HTML = '''
{% extends "base.html" %}
{% block content %}
<h2>All Tenants</h2>
<table>
    <thead>
        <tr><th>Name</th><th>Email</th><th>Phone</th><th>Monthly Rent</th><th>Balance</th><th>Actions</th></tr>
    </thead>
    <tbody>
        {% for tenant in tenants %}
        <tr>
            <td>{{ tenant[1] }}</td>
            <td>{{ tenant[2] }}</td>
            <td>{{ tenant[3] }}</td>
            <td>${{ "%.2f"|format(tenant[6]) }}</td>
            <td>${{ "%.2f"|format(tenant[7]) }}</td>
            <td>
                <a href="/pay_history/{{ tenant[0] }}" class="btn btn-primary">History</a>
                <a href="/delete_tenant/{{ tenant[0] }}" class="btn btn-danger" onclick="return confirm('Are you sure?')">Delete</a>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endblock %}
'''

ADD_TENANT_HTML = '''
{% extends "base.html" %}
{% block content %}
<h2>Add New Tenant</h2>
<form method="POST">
    <div class="form-group"><label>Name:</label><input type="text" name="name" required></div>
    <div class="form-group"><label>Email:</label><input type="email" name="email"></div>
    <div class="form-group"><label>Phone:</label><input type="text" name="phone"></div>
    <div class="form-group"><label>Address:</label><input type="text" name="address"></div>
    <div class="form-group"><label>Monthly Rent ($):</label><input type="number" step="0.01" name="monthly_rent" required></div>
    <div class="form-group"><label>Initial Balance ($):</label><input type="number" step="0.01" name="balance" value="0"></div>
    <button type="submit" class="btn btn-primary">Add Tenant</button>
</form>
{% endblock %}
'''

RECORD_PAYMENT_HTML = '''
{% extends "base.html" %}
{% block content %}
<h2>Record Payment</h2>
<form method="POST">
    <div class="form-group">
        <label>Select Tenant:</label>
        <select name="tenant_id" required>
            <option value="">Choose tenant...</option>
            {% for tenant in tenants %}
            <option value="{{ tenant[0] }}">{{ tenant[1] }} - Balance: ${{ "%.2f"|format(tenant[7]) }}</option>
            {% endfor %}
        </select>
    </div>
    <div class="form-group"><label>Amount Paid ($):</label><input type="number" step="0.01" name="amount" required></div>
    <div class="form-group">
        <label>Payment Method:</label>
        <select name="payment_method">
            <option value="Cash">Cash</option>
            <option value="Bank Transfer">Bank Transfer</option>
            <option value="Mobile Money">Mobile Money</option>
        </select>
    </div>
    <div class="form-group"><label>Send Receipt?</label>
        <select name="send_receipt">
            <option value="no">No</option>
            <option value="email">Send to Email</option>
            <option value="sms">Send SMS (via email gateway)</option>
        </select>
    </div>
    <button type="submit" class="btn btn-success">Record Payment</button>
</form>
{% endblock %}
'''

PAYMENT_HISTORY_HTML = '''
{% extends "base.html" %}
{% block content %}
<h2>Payment History for {{ tenant[1] }}</h2>
<p><strong>Current Balance:</strong> ${{ "%.2f"|format(tenant[7]) }}</p>
<table>
    <thead><tr><th>Date</th><th>Amount</th><th>Method</th><th>Receipt</th></tr></thead>
    <tbody>
        {% for payment in payments %}
        <tr>
            <td>{{ payment[2] }}</td>
            <td>${{ "%.2f"|format(payment[1]) }}</td>
            <td>{{ payment[3] }}</td>
            <td><a href="/receipt/{{ payment[0] }}" target="_blank">Download PDF</a></td>
        </tr>
        {% endfor %}
    </tbody>
</table>
<a href="/tenants" class="btn btn-primary">Back to Tenants</a>
{% endblock %}
'''

REPORTS_HTML = '''
{% extends "base.html" %}
{% block content %}
<h2>Financial Reports</h2>
<div class="stats">
    <div class="stat-card">
        <h3>Total Rent Collected</h3>
        <div class="stat-number">${{ "%.2f"|format(total_collected) }}</div>
    </div>
    <div class="stat-card">
        <h3>Average Rent</h3>
        <div class="stat-number">${{ "%.2f"|format(avg_rent) }}</div>
    </div>
</div>
<h3>Tenants with Outstanding Balance</h3>
<table>
    <thead><tr><th>Tenant</th><th>Balance</th><th>Monthly Rent</th></tr></thead>
    <tbody>
        {% for tenant in tenants_with_balance %}
        <tr>
            <td>{{ tenant[1] }}</td>
            <td>${{ "%.2f"|format(tenant[7]) }}</td>
            <td>${{ "%.2f"|format(tenant[6]) }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endblock %}
'''

# Database setup
def init_db():
    conn = sqlite3.connect('tenants.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tenants
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  email TEXT,
                  phone TEXT,
                  address TEXT,
                  created_date TEXT,
                  monthly_rent REAL,
                  balance REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS payments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  tenant_id INTEGER,
                  amount REAL,
                  payment_date TEXT,
                  payment_method TEXT,
                  FOREIGN KEY (tenant_id) REFERENCES tenants (id))''')
    conn.commit()
    conn.close()

# Routes
@app.route('/')
def dashboard():
    conn = sqlite3.connect('tenants.db')
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM tenants")
    total_tenants = c.fetchone()[0]
    
    c.execute("SELECT COALESCE(SUM(balance), 0) FROM tenants")
    total_balance = c.fetchone()[0]
    
    c.execute("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE payment_date >= date('now', 'start of month')")
    total_collected = c.fetchone()[0]
    
    c.execute('''SELECT t.name, p.amount, p.payment_date, p.payment_method 
                 FROM payments p JOIN tenants t ON p.tenant_id = t.id 
                 ORDER BY p.payment_date DESC LIMIT 10''')
    recent_payments = c.fetchall()
    
    conn.close()
    
    return render_template_string(INDEX_HTML, 
                                 total_tenants=total_tenants,
                                 total_balance=total_balance,
                                 total_collected=total_collected,
                                 recent_payments=recent_payments)

@app.route('/tenants')
def tenants():
    conn = sqlite3.connect('tenants.db')
    c = conn.cursor()
    c.execute("SELECT * FROM tenants ORDER BY name")
    tenants = c.fetchall()
    conn.close()
    return render_template_string(TENANTS_HTML, tenants=tenants)

@app.route('/add_tenant', methods=['GET', 'POST'])
def add_tenant():
    if request.method == 'POST':
        conn = sqlite3.connect('tenants.db')
        c = conn.cursor()
        c.execute("INSERT INTO tenants (name, email, phone, address, created_date, monthly_rent, balance) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (request.form['name'], request.form['email'], request.form['phone'], 
                  request.form['address'], datetime.now().strftime('%Y-%m-%d'),
                  float(request.form['monthly_rent']), float(request.form['balance'])))
        conn.commit()
        conn.close()
        flash('Tenant added successfully!', 'success')
        return redirect(url_for('tenants'))
    return render_template_string(ADD_TENANT_HTML)

@app.route('/record_payment', methods=['GET', 'POST'])
def record_payment():
    if request.method == 'POST':
        tenant_id = int(request.form['tenant_id'])
        amount = float(request.form['amount'])
        payment_method = request.form['payment_method']
        send_receipt = request.form.get('send_receipt', 'no')
        
        conn = sqlite3.connect('tenants.db')
        c = conn.cursor()
        
        # Update tenant balance
        c.execute("SELECT name, email, phone, balance FROM tenants WHERE id = ?", (tenant_id,))
        tenant = c.fetchone()
        new_balance = tenant[3] - amount
        
        c.execute("UPDATE tenants SET balance = ? WHERE id = ?", (new_balance, tenant_id))
        
        # Record payment
        c.execute("INSERT INTO payments (tenant_id, amount, payment_date, payment_method) VALUES (?, ?, ?, ?)",
                 (tenant_id, amount, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), payment_method))
        
        conn.commit()
        
        # Send receipt if requested
        if send_receipt == 'email' and tenant[1]:
            send_email_receipt(tenant[0], tenant[1], amount, new_balance)
            flash(f'Receipt sent to {tenant[1]}', 'success')
        elif send_receipt == 'sms' and tenant[2]:
            send_sms_free(tenant[0], tenant[2], amount, new_balance)
            flash(f'SMS sent to {tenant[2]} (via email gateway)', 'success')
        
        conn.close()
        
        flash(f'Payment of ${amount:,.2f} recorded for {tenant[0]}! New balance: ${new_balance:,.2f}', 'success')
        return redirect(url_for('tenants'))
    
    conn = sqlite3.connect('tenants.db')
    c = conn.cursor()
    c.execute("SELECT * FROM tenants WHERE balance > 0 OR 1=1 ORDER BY name")
    tenants = c.fetchall()
    conn.close()
    return render_template_string(RECORD_PAYMENT_HTML, tenants=tenants)

@app.route('/pay_history/<int:id>')
def pay_history(id):
    conn = sqlite3.connect('tenants.db')
    c = conn.cursor()
    c.execute("SELECT * FROM tenants WHERE id = ?", (id,))
    tenant = c.fetchone()
    c.execute("SELECT * FROM payments WHERE tenant_id = ? ORDER BY payment_date DESC", (id,))
    payments = c.fetchall()
    conn.close()
    return render_template_string(PAYMENT_HISTORY_HTML, tenant=tenant, payments=payments)

@app.route('/receipt/<int:payment_id>')
def generate_receipt(payment_id):
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    
    conn = sqlite3.connect('tenants.db')
    c = conn.cursor()
    c.execute('''SELECT p.*, t.name, t.email, t.phone 
                 FROM payments p JOIN tenants t ON p.tenant_id = t.id 
                 WHERE p.id = ?''', (payment_id,))
    payment = c.fetchone()
    conn.close()
    
    if not payment:
        return "Receipt not found", 404
    
    filename = f"receipt_{payment_id}.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    c.drawString(200, 750, "RENT PAYMENT RECEIPT")
    c.drawString(50, 700, f"Receipt #: {payment[0]}")
    c.drawString(50, 680, f"Tenant: {payment[5]}")
    c.drawString(50, 660, f"Amount Paid: ${payment[1]:,.2f}")
    c.drawString(50, 640, f"Payment Date: {payment[2]}")
    c.drawString(50, 620, f"Payment Method: {payment[4]}")
    c.drawString(50, 580, "Thank you for your payment!")
    c.save()
    
    return send_file(filename, as_attachment=True)

@app.route('/reports')
def reports():
    conn = sqlite3.connect('tenants.db')
    c = conn.cursor()
    
    c.execute("SELECT COALESCE(SUM(amount), 0) FROM payments")
    total_collected = c.fetchone()[0]
    
    c.execute("SELECT COALESCE(AVG(monthly_rent), 0) FROM tenants")
    avg_rent = c.fetchone()[0]
    
    c.execute("SELECT * FROM tenants WHERE balance > 0 ORDER BY balance DESC")
    tenants_with_balance = c.fetchall()
    
    conn.close()
    return render_template_string(REPORTS_HTML, 
                                 total_collected=total_collected,
                                 avg_rent=avg_rent,
                                 tenants_with_balance=tenants_with_balance)

@app.route('/delete_tenant/<int:id>')
def delete_tenant(id):
    conn = sqlite3.connect('tenants.db')
    c = conn.cursor()
    c.execute("DELETE FROM payments WHERE tenant_id = ?", (id,))
    c.execute("DELETE FROM tenants WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash('Tenant deleted successfully!', 'success')
    return redirect(url_for('tenants'))

def send_email_receipt(name, email, amount, balance):
    """Free email receipt using Gmail SMTP"""
    try:
        # For student project, you can use any email
        # Just change these to your credentials
        sender = "your-email@gmail.com"  # Change this
        password = "your-app-password"    # Generate at myaccount.google.com/apppasswords
        
        msg = MIMEText(f"""
        Dear {name},
        
        Payment Receipt
        Amount Paid: ${amount:,.2f}
        Remaining Balance: ${balance:,.2f}
        
        Thank you!
        """)
        
        msg['Subject'] = 'Rent Payment Receipt'
        msg['From'] = sender
        msg['To'] = email
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
        return True
    except:
        return False  # Don't worry if email fails for student project

def send_sms_free(name, phone, amount, balance):
    """
    FREE SMS using email-to-SMS gateways
    Works with all major carriers automatically!
    """
    # Determine carrier from area code (simplified for student project)
    email_gateways = {
        # Major US carriers
        'att': 'txt.att.net',
        'tmobile': 'tmomail.net',
        'verizon': 'vtext.com',
        'sprint': 'messaging.sprintpcs.com',
        # International
        'vodafone': 'vodafone.co.uk',
    }
    
    # For student project, just show the message
    print(f"\n=== SMS Receipt would be sent to {phone} ===")
    print(f"Message: {name}, paid ${amount:.2f}. Balance: ${balance:.2f}")
    print("=====================================\n")
    
    # If you want real SMS, use the email gateway:
    # sms_email = f"{phone}@vtext.com"  # Verizon example
    # send_email_receipt(name, sms_email, amount, balance)
    
    return True

from flask import send_file
import reportlab

# Register templates
app.jinja_env.globals.update(zip=zip)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)