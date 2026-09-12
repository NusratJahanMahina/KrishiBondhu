from flask import render_template, request, redirect, url_for, session, flash
from db_connect import get_connection
import re
import time
import random


# ============================================
# HELPER FUNCTIONS
# ============================================

def generate_id():
    return int(str(int(time.time() * 1000)) + str(random.randint(10, 99)))


def get_lang():
    return session.get('language', 'bn')


def get_flash_message(bn_msg, en_msg):
    return bn_msg if get_lang() == 'bn' else en_msg


def clear_temp_session():
    temp_keys = ['temp_role', 'temp_first_name', 'temp_last_name', 'temp_phone', 'temp_username', 'temp_password']
    for key in temp_keys:
        session.pop(key, None)


def register_login_routes(app):

    @app.route('/set_language/<lang>')
    def set_language(lang):
        if lang in ['bn', 'en']:
            session['language'] = lang
        return redirect(request.referrer or url_for('index'))

    @app.route('/')
    def index():
        if 'user' in session:
            return redirect(url_for('dashboard'))
        return render_template('index.html')

    @app.route('/login-register')
    def login_register():
        if 'user' in session:
            return redirect(url_for('dashboard'))
        return render_template('login_register.html')


    # ============================================
    # LOGIN
    # ============================================

    @app.route('/login', methods=['POST'])
    def login():
        login_input = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        remember = request.form.get('remember', False)

        if not login_input or not password:
            flash(get_flash_message(
                'দয়া করে ইউজারনেম/ফোন এবং পাসওয়ার্ড দিন।',
                'Please enter username/phone and password.'
            ), 'danger')
            return redirect(url_for('login_register'))

        conn = get_connection()
        
        if conn is None:
            flash(get_flash_message(
                'ডেটাবেস সংযোগ ব্যর্থ হয়েছে।',
                'Database connection failed.'
            ), 'danger')
            return redirect(url_for('login_register'))
        
        cursor = conn.cursor()

        if re.match(r'^01[3-9]\d{8}$', login_input):
            cursor.execute("""
                SELECT person_id, first_name, last_name, role
                FROM PERSON
                WHERE login_phone = ? AND password = ?
            """, (login_input, password))
        else:
            cursor.execute("""
                SELECT person_id, first_name, last_name, role
                FROM PERSON
                WHERE username = ? AND password = ?
            """, (login_input, password))

        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            user_data = {
                'person_id': user[0],
                'first_name': user[1],
                'last_name': user[2],
                'role': user[3]
            }

            conn = get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE PERSON SET last_login = CURRENT_TIMESTAMP WHERE person_id = ?", (user[0],))
                
                # Fetch role-specific details
                if user[3] == 'ADVISOR':
                    cursor.execute("SELECT advisor_id, specialization, rating, is_available FROM ADVISOR WHERE person_id = ?", (user[0],))
                    adv = cursor.fetchone()
                    if adv:
                        user_data['advisor_id'] = adv[0]
                        user_data['specialization'] = adv[1]
                        user_data['rating'] = adv[2]
                        user_data['is_available'] = adv[3]
                elif user[3] == 'FARMER':
                    cursor.execute("SELECT farmer_code, agent_code FROM FARMER WHERE person_id = ?", (user[0],))
                    fm = cursor.fetchone()
                    if fm:
                        user_data['farmer_id'] = fm[0]
                        user_data['farmer_code'] = fm[0]
                        user_data['agent_code'] = fm[1]
                elif user[3] == 'AGENT':
                    cursor.execute("SELECT agent_code, center_code FROM FIELD_AGENT WHERE person_id = ?", (user[0],))
                    ag = cursor.fetchone()
                    if ag:
                        user_data['agent_code'] = ag[0]
                        user_data['center_code'] = ag[1]

                conn.commit()
                cursor.close()
                conn.close()

            session['user'] = user_data
            if remember:
                session.permanent = True

            flash(get_flash_message(
                f'স্বাগতম {user[1]} {user[2]}!',
                f'Welcome {user[1]} {user[2]}!'
            ), 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(get_flash_message(
                'ভুল ইউজারনেম/ফোন বা পাসওয়ার্ড।',
                'Invalid username/phone or password.'
            ), 'danger')
            return redirect(url_for('login_register'))


    # ============================================
    # REGISTRATION STEP 1
    # ============================================

    @app.route('/register/step1', methods=['GET', 'POST'])
    def register_step1():
        if 'user' in session:
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            role = request.form.get('role', '').strip().upper()
            allowed_roles = ['FARMER', 'AGENT', 'ADMIN', 'ADVISOR']
            if role not in allowed_roles:
                flash(get_flash_message(
                    'দয়া করে একটি ভূমিকা নির্বাচন করুন।',
                    'Please select a role.'
                ), 'warning')
                return redirect(url_for('register_step1'))

            session['temp_role'] = role
            return redirect(url_for('register_step2'))

        selected_role = session.get('temp_role', '')
        return render_template('register_step1.html', selected_role=selected_role)


    # ============================================
    # REGISTRATION STEP 2
    # ============================================

    @app.route('/register/step2', methods=['GET', 'POST'])
    def register_step2():
        if 'user' in session:
            return redirect(url_for('dashboard'))

        if 'temp_role' not in session:
            flash(get_flash_message(
                'দয়া করে প্রথমে ভূমিকা নির্বাচন করুন।',
                'Please select a role first.'
            ), 'warning')
            return redirect(url_for('register_step1'))

        if request.method == 'GET':
            if 'temp_first_name' not in session:
                session['temp_first_name'] = ''
            if 'temp_last_name' not in session:
                session['temp_last_name'] = ''
            if 'temp_phone' not in session:
                session['temp_phone'] = ''
            if 'temp_username' not in session:
                session['temp_username'] = ''

        if request.method == 'POST':
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            phone = request.form.get('phone', '').strip()
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            confirm_password = request.form.get('confirm_password', '').strip()
            role = request.form.get('role', '').strip().upper()

            if not all([first_name, phone, username, password, confirm_password]):
                flash(get_flash_message(
                    'সব আবশ্যক ফিল্ড পূরণ করুন।',
                    'Please fill all required fields.'
                ), 'danger')
                session['temp_first_name'] = first_name
                session['temp_last_name'] = last_name
                session['temp_phone'] = phone
                session['temp_username'] = username
                return redirect(url_for('register_step2'))

            if password != confirm_password:
                flash(get_flash_message(
                    'পাসওয়ার্ড মেলেনি।',
                    'Passwords do not match.'
                ), 'danger')
                session['temp_first_name'] = first_name
                session['temp_last_name'] = last_name
                session['temp_phone'] = phone
                session['temp_username'] = username
                return redirect(url_for('register_step2'))

            if len(password) < 4:
                flash(get_flash_message(
                    'পাসওয়ার্ড কমপক্ষে ৪ অক্ষরের হতে হবে।',
                    'Password must be at least 4 characters.'
                ), 'danger')
                session['temp_first_name'] = first_name
                session['temp_last_name'] = last_name
                session['temp_phone'] = phone
                session['temp_username'] = username
                return redirect(url_for('register_step2'))

            if not re.match(r'^01[3-9]\d{8}$', phone):
                flash(get_flash_message(
                    'দয়া করে একটি বৈধ বাংলাদেশি ফোন নম্বর দিন (01XXXXXXXXX)।',
                    'Please enter a valid Bangladesh phone number (01XXXXXXXXX).'
                ), 'danger')
                session['temp_first_name'] = first_name
                session['temp_last_name'] = last_name
                session['temp_phone'] = phone
                session['temp_username'] = username
                return redirect(url_for('register_step2'))

            session['temp_first_name'] = first_name
            session['temp_last_name'] = last_name
            session['temp_phone'] = phone
            session['temp_username'] = username
            session['temp_password'] = password
            session['temp_role'] = role

            return redirect(url_for('register_step3'))

        return render_template('register_step2.html')


    # ============================================
    # REGISTRATION STEP 3
    # ============================================

    @app.route('/register/step3', methods=['GET', 'POST'])
    def register_step3():
        if 'user' in session:
            return redirect(url_for('dashboard'))

        required = ['temp_role', 'temp_first_name', 'temp_last_name', 'temp_phone', 'temp_username', 'temp_password']
        if not all(k in session for k in required):
            flash(get_flash_message(
                'নিবন্ধন তথ্য অসম্পূর্ণ। দয়া করে আবার শুরু করুন।',
                'Registration incomplete. Please start over.'
            ), 'warning')
            return redirect(url_for('register_step1'))

        if request.method == 'POST':
            conn = None
            cursor = None
            try:
                conn = get_connection()
                if conn is None:
                    flash(get_flash_message(
                        'ডেটাবেস সংযোগ ব্যর্থ হয়েছে।',
                        'Database connection failed.'
                    ), 'danger')
                    return redirect(url_for('register_step1'))

                cursor = conn.cursor()

                cursor.execute("SELECT COUNT(*) FROM PERSON WHERE login_phone = ?", (session['temp_phone'],))
                count = cursor.fetchone()[0]
                if count > 0:
                    flash(get_flash_message(
                        'এই ফোন নম্বরটি ইতিমধ্যে ব্যবহার করা হয়েছে। দয়া করে ভিন্ন নম্বর দিন।',
                        'This phone number is already registered. Please use a different one.'
                    ), 'danger')
                    session.pop('temp_phone', None)
                    return redirect(url_for('register_step2'))

                person_id = generate_id()

                first_name = session['temp_first_name']
                last_name = session['temp_last_name']
                phone = session['temp_phone']
                username = session['temp_username']
                password = session['temp_password']
                role = session['temp_role']

                cursor.execute("""
                    INSERT INTO PERSON (person_id, first_name, last_name, login_phone, username, password, role)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    person_id,
                    first_name,
                    last_name,
                    phone,
                    username,
                    password,
                    role
                ))
                conn.commit()

                cursor.execute("""
                    INSERT INTO PHONE (person_id, phone_number, phone_type, is_primary)
                    VALUES (?, ?, 'PERSONAL', 'YES')
                """, (
                    person_id,
                    phone
                ))
                conn.commit()

                clear_temp_session()

                session['user'] = {
                    'person_id': person_id,
                    'first_name': first_name,
                    'last_name': last_name,
                    'role': role
                }
                flash(get_flash_message(
                    f'স্বাগতম {first_name}!',
                    f'Welcome {first_name}!'
                ), 'success')
                return redirect(url_for('dashboard'))

            except Exception as e:
                if conn:
                    conn.rollback()
                error_msg = str(e)
                print(f"=== DATABASE ERROR: {error_msg} ===")

                clear_temp_session()

                if 'unique constraint' in error_msg.lower():
                    if 'username' in error_msg.lower():
                        flash(get_flash_message(
                            'এই ইউজারনেমটি ইতিমধ্যে ব্যবহার করা হয়েছে।',
                            'This username is already taken.'
                        ), 'danger')
                    else:
                        flash(get_flash_message(
                            'এই তথ্যগুলো ইতিমধ্যে ব্যবহার করা হয়েছে।',
                            'This information is already registered.'
                        ), 'danger')
                else:
                    flash(get_flash_message(
                        f'ডেটাবেস ত্রুটি: {error_msg[:150]}',
                        f'Database error: {error_msg[:150]}'
                    ), 'danger')

                return redirect(url_for('register_step1'))
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()

        return render_template('register_step3.html')


    # ============================================
    # DASHBOARD (REDIRECTS TO ROLE-SPECIFIC DASHBOARDS)
    # ============================================

    @app.route('/dashboard')
    def dashboard():
        if 'user' not in session:
            flash(get_flash_message(
                'দয়া করে প্রথমে লগইন করুন।',
                'Please login first.'
            ), 'warning')
            return redirect(url_for('login_register'))

        user = session['user']
        role = user['role'].lower()

        if role == 'agent':
            return redirect(url_for('agent_dashboard'))
        if role == 'advisor':
            return redirect(url_for('advisor_dashboard'))
        if role == 'admin':
            return redirect(url_for('admin_dashboard'))

        if role == 'farmer':
            person_id = user.get('person_id')
            farmer_code = user.get('farmer_code') or user.get('farmer_id') or person_id
            
            conn = get_connection()
            farmer_data = {}
            if conn:
                cursor = conn.cursor()
                
                # 1. Fetch Farmer & Location info
                cursor.execute("""
                    SELECT 
                        F.farmer_code,
                        COALESCE(F.land_area, 3.5) as land_area,
                        F.registration_date,
                        COALESCE(C.center_name, 'আঞ্চলিক কৃষি কেন্দ্র') as center_name,
                        COALESCE(C.upazila, 'উপজেলা') as upazila,
                        COALESCE(C.district, 'জেলা') as district,
                        F.agent_code,
                        F.center_code
                    FROM FARMER F
                    LEFT JOIN IFARMER_CENTER C ON F.center_code = C.center_code
                    WHERE F.person_id = ? OR F.farmer_code = ?
                """, (person_id, farmer_code))
                f_row = cursor.fetchone()
                
                if f_row:
                    farmer_data['farmer_code'] = f_row[0]
                    farmer_data['land_area'] = f_row[1]
                    farmer_data['registration_date'] = f_row[2]
                    farmer_data['center_name'] = f_row[3]
                    farmer_data['upazila'] = f_row[4]
                    farmer_data['district'] = f_row[5]
                    agent_code = f_row[6]
                    center_code = f_row[7]
                else:
                    farmer_data['farmer_code'] = farmer_code
                    farmer_data['land_area'] = 3.5
                    farmer_data['center_name'] = 'ঢাকা কৃষি সেবা কেন্দ্র'
                    farmer_data['upazila'] = 'সদর'
                    farmer_data['district'] = 'ঢাকা'
                    agent_code = 2001
                    center_code = 101

                # 2. Fetch KYC status
                cursor.execute("SELECT identity_verified FROM KYC WHERE farmer_code = ?", (farmer_data['farmer_code'],))
                kyc_row = cursor.fetchone()
                farmer_data['kyc_status'] = kyc_row[0] if kyc_row else 'VERIFIED'

                # 3. Fetch Assigned Field Agent
                cursor.execute("""
                    SELECT 
                        FA.agent_code,
                        P.first_name,
                        P.last_name,
                        P.login_phone,
                        C.center_name
                    FROM FIELD_AGENT FA
                    JOIN PERSON P ON FA.person_id = P.person_id
                    LEFT JOIN IFARMER_CENTER C ON FA.center_code = C.center_code
                    WHERE FA.agent_code = ?
                """, (agent_code,))
                ag_row = cursor.fetchone()
                if ag_row:
                    farmer_data['agent'] = {
                        'code': ag_row[0],
                        'name': f"{ag_row[1]} {ag_row[2]}",
                        'phone': ag_row[3],
                        'center_name': ag_row[4]
                    }
                else:
                    farmer_data['agent'] = {
                        'code': 2001,
                        'name': 'করিম সাহেব',
                        'phone': '01721234567',
                        'center_name': farmer_data['center_name']
                    }

                # 4. Fetch Loans & Detailed Repayment Ledger
                cursor.execute("""
                    SELECT 
                        loan_no, 
                        loan_state, 
                        approval_date, 
                        tenure_months, 
                        COALESCE(amount, 50000) as amount, 
                        COALESCE(purpose, 'কৃষি উৎপাদন ও শস্য সুরক্ষা') as purpose, 
                        application_date
                    FROM LOAN
                    WHERE farmer_code = ?
                    ORDER BY loan_no DESC
                """, (farmer_data['farmer_code'],))
                loans = cursor.fetchall()
                farmer_data['loans'] = loans
                
                loans_detailed = []
                for l in loans:
                    l_no = l[0]
                    l_state = l[1]
                    l_appr = l[2]
                    l_tenure = l[3] or 12
                    l_principal = l[4] or 50000.0
                    l_purpose = l[5]
                    l_apply = l[6]
                    
                    l_payable = round(l_principal * (1.0 + 0.04 * (l_tenure / 12.0)), 2)
                    l_emi = round(l_payable / l_tenure)
                    
                    cursor.execute("""
                        SELECT 
                            repayment_id,
                            installment_no,
                            repayment_month,
                            repayment_date,
                            amount_paid,
                            remaining_balance,
                            payment_method,
                            transaction_ref,
                            status,
                            remarks
                        FROM LOAN_REPAYMENT
                        WHERE loan_no = ?
                        ORDER BY installment_no ASC
                    """, (l_no,))
                    reps = cursor.fetchall()
                    
                    l_total_paid = sum(r[4] for r in reps)
                    if l_state == 'CLOSED':
                        l_remaining = 0.0
                        l_prog = 100.0
                    else:
                        l_remaining = max(0.0, round(l_payable - l_total_paid, 2))
                        l_prog = min(100.0, round((l_total_paid / l_payable) * 100.0, 1)) if l_payable > 0 else 0.0
                    
                    loans_detailed.append({
                        'loan_no': l_no,
                        'state': l_state,
                        'approval_date': l_appr,
                        'application_date': l_apply,
                        'tenure_months': l_tenure,
                        'principal': l_principal,
                        'total_payable': l_payable,
                        'monthly_emi': l_emi,
                        'total_paid': l_total_paid,
                        'remaining_due': l_remaining,
                        'progress_pct': l_prog,
                        'purpose': l_purpose,
                        'repayments': reps,
                        'paid_count': len(reps)
                    })
                
                farmer_data['loans_detailed'] = loans_detailed
                farmer_data['active_loans_count'] = sum(1 for l in loans_detailed if l['state'] == 'ACTIVE')
                farmer_data['total_borrowed_amount'] = sum(l['principal'] for l in loans_detailed if l['state'] in ('ACTIVE', 'PENDING'))
                farmer_data['total_repaid_amount'] = sum(l['total_paid'] for l in loans_detailed)
                farmer_data['total_remaining_due'] = sum(l['remaining_due'] for l in loans_detailed if l['state'] == 'ACTIVE')

                # Fetch all farmer repayments history
                cursor.execute("""
                    SELECT 
                        LR.repayment_id,
                        LR.loan_no,
                        LR.installment_no,
                        LR.repayment_month,
                        LR.repayment_date,
                        LR.amount_paid,
                        LR.remaining_balance,
                        LR.payment_method,
                        LR.transaction_ref,
                        LR.status,
                        L.purpose
                    FROM LOAN_REPAYMENT LR
                    JOIN LOAN L ON LR.loan_no = L.loan_no
                    WHERE LR.farmer_code = ?
                    ORDER BY LR.repayment_date DESC, LR.repayment_id DESC
                """, (farmer_data['farmer_code'],))
                farmer_data['all_repayments'] = cursor.fetchall()

                # 5. Fetch Advisor Consultations & Prescriptions
                cursor.execute("""
                    SELECT 
                        AB.booking_id,
                        AB.scheduled_date,
                        AB.start_time,
                        AB.end_time,
                        AB.rate_type,
                        AB.total_amount,
                        AB.payment_status,
                        AB.booking_status,
                        AB.consultation_topic,
                        P.first_name,
                        P.last_name,
                        A.specialization,
                        COALESCE(A.rating, 5.0) as advisor_rating,
                        AB.notes,
                        AR.rating as my_rating,
                        AR.review as my_review,
                        AB.advisor_id
                    FROM ADVISOR_BOOKING AB
                    JOIN ADVISOR A ON AB.advisor_id = A.advisor_id
                    JOIN PERSON P ON A.person_id = P.person_id
                    LEFT JOIN ADVISOR_RATING AR ON AB.booking_id = AR.booking_id
                    WHERE AB.farmer_id = ?
                    ORDER BY AB.booking_date DESC, AB.scheduled_date DESC
                    LIMIT 8
                """, (farmer_data['farmer_code'],))
                consultations = cursor.fetchall()
                farmer_data['consultations'] = consultations
                farmer_data['upcoming_consultations'] = [c for c in consultations if c[7] in ('CONFIRMED', 'PENDING')]
                farmer_data['completed_consultations'] = [c for c in consultations if c[7] == 'COMPLETED']

                # 6. Fetch Available Inventory from local center
                cursor.execute("""
                    SELECT inventory_id, item_name, quantity, unit, price
                    FROM INVENTORY
                    WHERE agent_code = ? OR agent_code = 2001
                    LIMIT 6
                """, (agent_code,))
                farmer_data['inventory'] = cursor.fetchall()

                # 7. Fetch Top Available Advisors for quick booking
                cursor.execute("""
                    SELECT 
                        A.advisor_id,
                        P.first_name,
                        P.last_name,
                        A.specialization,
                        COALESCE(A.rating, 5.0) as rating,
                        COALESCE((SELECT amount FROM ADVISOR_RATE WHERE advisor_id = A.advisor_id AND rate_type = 'HOURLY'), 500) as hourly_rate
                    FROM ADVISOR A
                    JOIN PERSON P ON A.person_id = P.person_id
                    WHERE A.is_available = 'YES'
                    ORDER BY COALESCE(A.rating, 5.0) DESC
                    LIMIT 3
                """)
                farmer_data['top_advisors'] = cursor.fetchall()

                cursor.close()
                conn.close()

            # Static / Mock Real-Time Krishi Bazar Data
            farmer_data['market_prices'] = [
                {'crop': 'আমন ধান (Aman Paddy)', 'price': '৳ ১,৩৫০', 'unit': 'মণ (40 kg)', 'trend': 'up', 'change': '+৳ ২০'},
                {'crop': 'বোরো ধান (Boro Paddy)', 'price': '৳ ১,৪২০', 'unit': 'মণ (40 kg)', 'trend': 'stable', 'change': '০'},
                {'crop': 'আলু - ডায়মন্ড (Potato)', 'price': '৳ ৩৫', 'unit': 'কেজি (kg)', 'trend': 'down', 'change': '-৳ ২'},
                {'crop': 'সরিষা (Mustard)', 'price': '৳ ৩,৬০০', 'unit': 'মণ (40 kg)', 'trend': 'up', 'change': '+৳ ৫০'},
                {'crop': 'গম (Wheat)', 'price': '৳ ১,৬৫০', 'unit': 'মণ (40 kg)', 'trend': 'up', 'change': '+৳ ১৫'},
                {'crop': 'পেঁয়াজ - দেশি (Onion)', 'price': '৳ ৬৫', 'unit': 'কেজি (kg)', 'trend': 'down', 'change': '-৳ ৩'}
            ]

            # Weather & Agri Advisory
            farmer_data['weather'] = {
                'temp': '29°C',
                'condition': 'আংশিক মেঘলা (Partly Cloudy)',
                'humidity': '78%',
                'rain_prob': '15%',
                'wind': '12 km/h',
                'advisory': 'মাটিতে পরিমিত আর্দ্রতা রাখুন। আলু ও রবি ফসলে সেচ দেওয়ার পর সার প্রয়োগ নিশ্চিত করুন। রোগবালাই প্রতিরোধে কৃষি উপদেষ্টার পরামর্শ নিন।'
            }

            return render_template('dashboard_farmer.html', user=user, farmer=farmer_data)

        template_map = {
            'admin': 'dashboard_admin.html',
        }
        template = template_map.get(role, 'dashboard_farmer.html')
        return render_template(template, user=user)


    # ============================================
    # FARMER LOAN APPLICATION
    # ============================================

    @app.route('/farmer/loan/apply', methods=['POST'])
    def farmer_apply_loan():
        if 'user' not in session or session['user'].get('role') != 'FARMER':
            flash(get_flash_message('অনুমতি নেই। / Access denied.', 'Access denied.'), 'danger')
            return redirect(url_for('login_register'))

        user = session['user']
        person_id = user.get('person_id')
        
        conn = get_connection()
        if not conn:
            flash(get_flash_message('ডাটাবেজ সংযোগে ত্রুটি।', 'Database connection error.'), 'danger')
            return redirect(url_for('dashboard'))

        cursor = conn.cursor()
        # Find farmer_code and agent_code
        cursor.execute("SELECT farmer_code, agent_code FROM FARMER WHERE person_id = ?", (person_id,))
        f_row = cursor.fetchone()
        farmer_code = f_row[0] if f_row else user.get('farmer_code') or person_id
        agent_code = f_row[1] if f_row else 2001

        try:
            amount = float(request.form.get('amount', 50000))
        except ValueError:
            amount = 50000.0

        try:
            tenure_months = int(request.form.get('tenure_months', 12))
        except ValueError:
            tenure_months = 12

        purpose = request.form.get('purpose', 'কৃষি উৎপাদন ও শস্য সুরক্ষা').strip()
        if not purpose:
            purpose = 'কৃষি উৎপাদন ও শস্য সুরক্ষা'

        try:
            cursor.execute("""
                INSERT INTO LOAN (farmer_code, amount, purpose, loan_state, tenure_months, application_date)
                VALUES (?, ?, ?, 'PENDING', ?, CURRENT_TIMESTAMP)
            """, (farmer_code, amount, purpose, tenure_months))
            new_loan_id = cursor.lastrowid

            # 1. Notify Farmer
            cursor.execute("""
                INSERT INTO NOTIFICATION (person_id, title, message, link)
                VALUES (?, '📋 কৃষি ঋণ আবেদন জমা হয়েছে', ?, '/dashboard')
            """, (person_id, f"আপনার ৳{amount:,.0f} টাকার কৃষি ঋণ আবেদনটি (উদ্দেশ্য: {purpose}) সফলভাবে জমা হয়েছে। এটি পর্যালোচনাধীন রয়েছে।"))

            # 2. Notify Field Agent
            if agent_code:
                cursor.execute("SELECT person_id FROM FIELD_AGENT WHERE agent_code = ?", (agent_code,))
                ag_person = cursor.fetchone()
                if ag_person:
                    cursor.execute("""
                        INSERT INTO NOTIFICATION (person_id, title, message, link)
                        VALUES (?, '🔔 নতুন কৃষি ঋণ আবেদন!', ?, '/agent/dashboard')
                    """, (ag_person[0], f"কৃষক #{farmer_code} ({user.get('first_name')} {user.get('last_name')}) ৳{amount:,.0f} টাকার নতুন কৃষি ঋণ আবেদন করেছেন।"))

            # 3. Notify Admins
            cursor.execute("SELECT person_id FROM PERSON WHERE role = 'ADMIN'")
            admins = cursor.fetchall()
            for adm in admins:
                cursor.execute("""
                    INSERT INTO NOTIFICATION (person_id, title, message, link)
                    VALUES (?, '💳 নতুন ঋণ আবেদন পোর্টফোলিওতে যুক্ত হয়েছে', ?, '/admin/dashboard')
                """, (adm[0], f"কৃষক #{farmer_code} ৳{amount:,.0f} টাকার নতুন কৃষি ঋণের আবেদন করেছেন।"))

            conn.commit()
            flash(get_flash_message(
                f'আপনার ৳{amount:,.0f} টাকার কৃষি ঋণ আবেদনটি সফলভাবে জমা হয়েছে! ফিল্ড এজেন্ট ও কেন্দ্রীয় অনুমোদন প্রক্রিয়া শুরু হয়েছে।',
                f'Your loan application for ৳{amount:,.0f} has been submitted successfully and is under review!'
            ), 'success')
        except Exception as e:
            conn.rollback()
            flash(f'ত্রুটি: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

    # ============================================
    # FARMER LOAN REPAYMENT / EMI PAYMENT
    # ============================================

    @app.route('/farmer/loan/repay', methods=['POST'])
    def farmer_repay_loan():
        if 'user' not in session or session['user'].get('role') != 'FARMER':
            flash(get_flash_message('অনুমতি নেই। / Access denied.', 'Access denied.'), 'danger')
            return redirect(url_for('login_register'))

        user = session['user']
        person_id = user.get('person_id')
        
        conn = get_connection()
        if not conn:
            flash(get_flash_message('ডাটাবেজ সংযোগে ত্রুটি।', 'Database connection error.'), 'danger')
            return redirect(url_for('dashboard'))

        cursor = conn.cursor()
        try:
            loan_no = int(request.form.get('loan_no'))
            amount_paid = float(request.form.get('amount_paid', 0))
            payment_method = request.form.get('payment_method', 'bKash')
            repayment_month = request.form.get('repayment_month', 'বর্তমান মাস')
            remarks = request.form.get('remarks', 'অনলাইন কিস্তি পরিশোধ')

            if amount_paid <= 0:
                flash(get_flash_message('পরিশোধের পরিমাণ সঠিক নয়।', 'Invalid repayment amount.'), 'warning')
                return redirect(url_for('dashboard'))

            # Fetch loan details
            cursor.execute("""
                SELECT L.farmer_code, L.amount, L.tenure_months, L.loan_state
                FROM LOAN L
                WHERE L.loan_no = ?
            """, (loan_no,))
            l_row = cursor.fetchone()
            if not l_row:
                flash(get_flash_message('ঋণ হিসাব খুঁজে পাওয়া যায়নি।', 'Loan record not found.'), 'danger')
                return redirect(url_for('dashboard'))

            farmer_code, principal, tenure, loan_state = l_row
            tenure = tenure or 12
            total_payable = round(principal * (1.0 + 0.04 * (tenure / 12.0)), 2)

            # Get current total paid
            cursor.execute("SELECT COALESCE(SUM(amount_paid), 0), COUNT(*) FROM LOAN_REPAYMENT WHERE loan_no = ?", (loan_no,))
            sum_row = cursor.fetchone()
            current_total_paid = sum_row[0]
            prev_installments_count = sum_row[1]

            installment_no = prev_installments_count + 1
            new_total_paid = current_total_paid + amount_paid
            remaining_balance = max(0.0, round(total_payable - new_total_paid, 2))

            import random
            txn_prefix = 'TXN-BK' if payment_method == 'bKash' else ('TXN-NG' if payment_method == 'Nagad' else 'TXN-AG')
            txn_ref = request.form.get('transaction_ref') or f"{txn_prefix}-{random.randint(10000, 99999)}"

            interest_portion = round(amount_paid * 0.04, 2)
            principal_portion = round(amount_paid - interest_portion, 2)

            cursor.execute("""
                INSERT INTO LOAN_REPAYMENT (
                    loan_no, farmer_code, installment_no, repayment_month, repayment_date,
                    amount_paid, interest_portion, principal_portion, remaining_balance,
                    payment_method, transaction_ref, status, remarks
                ) VALUES (?, ?, ?, ?, date('now'), ?, ?, ?, ?, ?, ?, 'PAID', ?)
            """, (
                loan_no, farmer_code, installment_no, repayment_month,
                amount_paid, interest_portion, principal_portion, remaining_balance,
                payment_method, txn_ref, remarks
            ))

            # If remaining balance <= 0, mark loan as CLOSED
            if remaining_balance <= 0:
                cursor.execute("UPDATE LOAN SET loan_state = 'CLOSED' WHERE loan_no = ?", (loan_no,))

            # Send Notification to Farmer
            cursor.execute("""
                INSERT INTO NOTIFICATION (person_id, title, message, link)
                VALUES (?, '💰 কিস্তি পরিশোধ সফল হয়েছে!', ?, '/dashboard')
            """, (
                person_id, 
                f"ঋণ #{loan_no} এর {installment_no}নং কিস্তি বাবদ ৳{amount_paid:,.0f} সফলভাবে জমা হয়েছে ({payment_method}, ট্রানজেকশন: {txn_ref})। অবশিষ্ট দেনা: ৳{remaining_balance:,.0f}।"
            ))

            conn.commit()
            flash(get_flash_message(
                f'ঋণ #{loan_no} এর কিস্তি বাবদ ৳{amount_paid:,.0f} সফলভাবে জমা হয়েছে! অবশিষ্ট স্থিতি: ৳{remaining_balance:,.0f}',
                f'Installment payment of ৳{amount_paid:,.0f} for Loan #{loan_no} was successful! Remaining Balance: ৳{remaining_balance:,.0f}'
            ), 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('dashboard'))


    # ============================================
    # LOGOUT
    # ============================================

    @app.route('/logout')
    def logout():
        session.clear()
        flash(get_flash_message('আপনি লগআউট হয়েছেন।', 'You have been logged out.'), 'info')
        return redirect(url_for('login_register'))