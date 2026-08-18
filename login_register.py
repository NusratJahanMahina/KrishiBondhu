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
                WHERE login_phone = :1 AND password = :2
            """, (login_input, password))
        else:
            cursor.execute("""
                SELECT person_id, first_name, last_name, role
                FROM PERSON
                WHERE username = :1 AND password = :2
            """, (login_input, password))

        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session['user'] = {
                'person_id': user[0],
                'first_name': user[1],
                'last_name': user[2],
                'role': user[3]
            }
            if remember:
                session.permanent = True

            conn = get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE PERSON SET last_login = SYSDATE WHERE person_id = :1", (user[0],))
                conn.commit()
                cursor.close()
                conn.close()

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

                cursor.execute("SELECT COUNT(*) FROM PERSON WHERE login_phone = :1", (session['temp_phone'],))
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
                    VALUES (:1, :2, :3, :4, :5, :6, :7)
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
                    VALUES (:1, :2, 'PERSONAL', 'YES')
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

        template_map = {
            'farmer': 'farmer/dashboard.html',
            'admin': 'dashboard_admin.html',
            'advisor': 'dashboard_advisor.html'
        }
        template = template_map.get(role, 'dashboard_farmer.html')
        return render_template(template, user=user)


    # ============================================
    # LOGOUT
    # ============================================

    @app.route('/logout')
    def logout():
        session.clear()
        flash(get_flash_message('আপনি লগআউট হয়েছেন।', 'You have been logged out.'), 'info')
        return redirect(url_for('login_register'))