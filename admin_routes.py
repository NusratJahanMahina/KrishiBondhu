from flask import render_template, request, redirect, url_for, session, flash, jsonify
from db_connect import get_connection
from datetime import datetime

def register_admin_routes(app):

    @app.route('/admin/dashboard')
    def admin_dashboard():
        """Executive Admin Command Center and System Oversight Dashboard"""
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            flash('প্রশাসক হিসেবে প্রবেশাধিকার সংরক্ষিত। / Admin access required.', 'danger')
            return redirect(url_for('login_register'))

        user = session['user']
        admin_data = {
            'total_farmers': 0,
            'total_agents': 0,
            'total_advisors': 0,
            'total_centers': 0,
            'total_loans': 0,
            'active_loans': 0,
            'total_consultations': 0,
            'total_inventory': 0
        }
        centers = []
        users_list = []
        advisors_list = []
        loans_list = []
        inventory_list = []
        posts = []
        all_agents = []

        try:
            conn = get_connection()
            cursor = conn.cursor()

            # 1. High-Level Metrics
            cursor.execute("SELECT COUNT(*) FROM FARMER")
            admin_data['total_farmers'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM FIELD_AGENT")
            admin_data['total_agents'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM ADVISOR")
            admin_data['total_advisors'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM IFARMER_CENTER")
            admin_data['total_centers'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*), SUM(CASE WHEN loan_state = 'ACTIVE' THEN 1 ELSE 0 END) FROM LOAN")
            l_row = cursor.fetchone()
            admin_data['total_loans'] = l_row[0] if l_row else 0
            admin_data['active_loans'] = l_row[1] if l_row and l_row[1] else 0

            cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM LOAN WHERE loan_state IN ('ACTIVE', 'PENDING', 'CLOSED')")
            admin_data['total_disbursed_amount'] = cursor.fetchone()[0] or 0

            cursor.execute("SELECT COALESCE(SUM(amount_paid), 0) FROM LOAN_REPAYMENT")
            admin_data['total_repaid_amount'] = cursor.fetchone()[0] or 0

            admin_data['total_outstanding_due'] = max(0, admin_data['total_disbursed_amount'] - admin_data['total_repaid_amount'])

            cursor.execute("SELECT COUNT(*) FROM ADVISOR_BOOKING")
            admin_data['total_consultations'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM INVENTORY")
            admin_data['total_inventory'] = cursor.fetchone()[0]

            # 2. Centers Management (with assigned agent names)
            cursor.execute("""
                SELECT 
                    c.center_code,
                    c.center_name,
                    c.upazila,
                    c.district,
                    (SELECT COUNT(*) FROM FIELD_AGENT fa WHERE fa.center_code = c.center_code) AS agent_count,
                    (SELECT COUNT(*) FROM FARMER f WHERE f.center_code = c.center_code) AS farmer_count,
                    (SELECT GROUP_CONCAT(p.first_name || ' ' || p.last_name, ', ') 
                     FROM FIELD_AGENT fa JOIN PERSON p ON fa.person_id = p.person_id 
                     WHERE fa.center_code = c.center_code) AS agent_names
                FROM IFARMER_CENTER c
                ORDER BY c.center_code ASC
            """)
            centers = cursor.fetchall()

            # 3. All Agents List (for center assignment dropdown)
            cursor.execute("""
                SELECT fa.agent_code, p.first_name || ' ' || p.last_name, fa.center_code
                FROM FIELD_AGENT fa
                JOIN PERSON p ON fa.person_id = p.person_id
                ORDER BY fa.agent_code ASC
            """)
            all_agents = cursor.fetchall()

            # 4. All Users Directory
            cursor.execute("""
                SELECT 
                    p.person_id,
                    p.first_name || ' ' || p.last_name AS full_name,
                    p.username,
                    p.login_phone,
                    p.role,
                    p.created_at
                FROM PERSON p
                ORDER BY p.person_id DESC
            """)
            users_list = cursor.fetchall()

            # 5. Advisors Directory
            cursor.execute("""
                SELECT 
                    a.advisor_id,
                    p.first_name || ' ' || p.last_name AS name,
                    p.login_phone,
                    a.specialization,
                    a.qualification,
                    COALESCE(a.rating, 5.0) as rating,
                    a.total_bookings,
                    COALESCE(a.is_available, 'YES') AS is_available,
                    a.experience_years,
                    a.bio
                FROM ADVISOR a
                JOIN PERSON p ON a.person_id = p.person_id
                ORDER BY a.rating DESC
            """)
            advisors_list = cursor.fetchall()

            # 6. Loans Portfolio & Repayments
            cursor.execute("""
                SELECT 
                    l.loan_no,
                    l.farmer_code,
                    p.first_name || ' ' || p.last_name AS farmer_name,
                    COALESCE(l.amount, 50000) AS amount,
                    l.loan_state,
                    l.approval_date,
                    l.tenure_months,
                    l.application_date,
                    COALESCE(l.purpose, 'কৃষি উৎপাদন ও শস্য সুরক্ষা') AS purpose,
                    (SELECT COALESCE(SUM(amount_paid), 0) FROM LOAN_REPAYMENT WHERE loan_no = l.loan_no) AS total_repaid,
                    (SELECT COUNT(*) FROM LOAN_REPAYMENT WHERE loan_no = l.loan_no) AS repayment_count
                FROM LOAN l
                JOIN FARMER f ON l.farmer_code = f.farmer_code
                JOIN PERSON p ON f.person_id = p.person_id
                ORDER BY l.loan_no DESC
            """)
            loans_list = cursor.fetchall()

            # 6b. System-wide Repayments
            cursor.execute("""
                SELECT 
                    lr.repayment_id,
                    lr.loan_no,
                    p.first_name || ' ' || p.last_name AS farmer_name,
                    lr.installment_no,
                    lr.repayment_month,
                    lr.repayment_date,
                    lr.amount_paid,
                    lr.remaining_balance,
                    lr.payment_method,
                    lr.transaction_ref,
                    lr.status,
                    l.purpose
                FROM LOAN_REPAYMENT lr
                JOIN LOAN l ON lr.loan_no = l.loan_no
                JOIN FARMER f ON lr.farmer_code = f.farmer_code
                JOIN PERSON p ON f.person_id = p.person_id
                ORDER BY lr.repayment_date DESC, lr.repayment_id DESC
            """)
            repayments_list = cursor.fetchall()

            # 7. Inventory Items
            cursor.execute("""
                SELECT 
                    i.inventory_id,
                    i.agent_code,
                    i.item_name,
                    i.quantity,
                    i.unit,
                    i.price
                FROM INVENTORY i
                ORDER BY i.inventory_id ASC
            """)
            inventory_list = cursor.fetchall()

            # 8. Announcements / Posts
            cursor.execute("""
                SELECT 
                    post_id,
                    title,
                    content,
                    post_date
                FROM COMMUNITY_POST
                ORDER BY post_date DESC
            """)
            posts = cursor.fetchall()

            conn.close()
        except Exception as e:
            print(f"Admin dashboard error: {e}")

        return render_template('dashboard_admin.html',
                               user=user,
                               admin_data=admin_data,
                               centers=centers,
                               all_agents=all_agents,
                               users_list=users_list,
                               advisors_list=advisors_list,
                               loans_list=loans_list,
                               repayments_list=repayments_list,
                               inventory_list=inventory_list,
                               posts=posts)


    # ==========================================
    # 1. CENTER OPERATIONS
    # ==========================================

    @app.route('/admin/center/add', methods=['POST'])
    def admin_add_center():
        """Add new iFarmer Center"""
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        center_name = request.form.get('center_name', '').strip()
        upazila = request.form.get('upazila', '').strip()
        district = request.form.get('district', '').strip()

        if not center_name or not upazila or not district:
            flash('সেন্টারের নাম, উপজেলা এবং জেলা আবশ্যক।', 'warning')
            return redirect(url_for('admin_dashboard'))

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO IFARMER_CENTER (center_name, upazila, district)
                VALUES (?, ?, ?)
            """, (center_name, upazila, district))
            conn.commit()
            conn.close()
            flash(f'নতুন সেন্টার "{center_name}" সফলভাবে যুক্ত হয়েছে!', 'success')
        except Exception as e:
            flash(f'ত্রুটি: {str(e)}', 'danger')

        return redirect(url_for('admin_dashboard'))


    @app.route('/admin/center/<int:center_code>/edit', methods=['POST'])
    def admin_edit_center(center_code):
        """Edit an existing iFarmer Center"""
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        center_name = request.form.get('center_name', '').strip()
        upazila = request.form.get('upazila', '').strip()
        district = request.form.get('district', '').strip()

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE IFARMER_CENTER
                SET center_name = ?, upazila = ?, district = ?
                WHERE center_code = ?
            """, (center_name, upazila, district, center_code))
            conn.commit()
            conn.close()
            flash(f'সেন্টার #{center_code} এর তথ্য সফলভাবে আপডেট করা হয়েছে!', 'success')
        except Exception as e:
            flash(f'ত্রুটি: {str(e)}', 'danger')

        return redirect(url_for('admin_dashboard'))


    @app.route('/admin/center/<int:center_code>/delete', methods=['POST'])
    def admin_delete_center(center_code):
        """Delete an iFarmer Center"""
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        try:
            conn = get_connection()
            cursor = conn.cursor()
            # Update agents and farmers assigned to this center to NULL or default 101
            cursor.execute("UPDATE FIELD_AGENT SET center_code = 101 WHERE center_code = ?", (center_code,))
            cursor.execute("UPDATE FARMER SET center_code = 101 WHERE center_code = ?", (center_code,))
            cursor.execute("DELETE FROM IFARMER_CENTER WHERE center_code = ?", (center_code,))
            conn.commit()
            conn.close()
            flash(f'সেন্টার #{center_code} সফলভাবে মুছে ফেলা হয়েছে।', 'info')
        except Exception as e:
            flash(f'ত্রুটি: {str(e)}', 'danger')

        return redirect(url_for('admin_dashboard'))


    @app.route('/admin/center/<int:center_code>/assign-agent', methods=['POST'])
    def admin_assign_agent(center_code):
        """Assign or reassign a Field Agent to a Center"""
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        agent_code = request.form.get('agent_code')
        if not agent_code:
            flash('অনুগ্রহ করে একজন ফিল্ড এজেন্ট নির্বাচন করুন।', 'warning')
            return redirect(url_for('admin_dashboard'))

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE FIELD_AGENT
                SET center_code = ?
                WHERE agent_code = ?
            """, (center_code, agent_code))
            conn.commit()
            conn.close()
            flash(f'ফিল্ড এজেন্ট #{agent_code} কে সফলভাবে এই সেন্টারে দায়িত্ব দেওয়া হয়েছে!', 'success')
        except Exception as e:
            flash(f'ত্রুটি: {str(e)}', 'danger')

        return redirect(url_for('admin_dashboard'))


    # ==========================================
    # 2. USER MANAGEMENT
    # ==========================================

    @app.route('/admin/user/create', methods=['POST'])
    def admin_create_user():
        """Create a new user account with selected role"""
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', 'password123').strip()
        login_phone = request.form.get('login_phone', '').strip()
        role = request.form.get('role', 'FARMER').strip().upper()

        if not first_name or not username or not login_phone:
            flash('নাম, ইউজারনেম এবং মোবাইল নম্বর আবশ্যক।', 'warning')
            return redirect(url_for('admin_dashboard'))

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO PERSON (first_name, last_name, username, password, login_phone, role)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (first_name, last_name, username, password, login_phone, role))
            new_person_id = cursor.lastrowid

            # Initialize role-specific table entries
            if role == 'FARMER':
                cursor.execute("""
                    INSERT INTO FARMER (person_id, agent_code, center_code, land_area)
                    VALUES (?, 2001, 101, 2.5)
                """, (new_person_id,))
            elif role == 'AGENT':
                cursor.execute("""
                    INSERT INTO FIELD_AGENT (person_id, center_code, is_active)
                    VALUES (?, 101, 'YES')
                """, (new_person_id,))
            elif role == 'ADVISOR':
                cursor.execute("""
                    INSERT INTO ADVISOR (person_id, specialization, qualification, rating, is_available)
                    VALUES (?, 'সাধারণ কৃষি ও উদ্ভিদ রোগ বিশেষজ্ঞ', 'বিএসসি ইন এগ্রিকালচার', 5.0, 'YES')
                """, (new_person_id,))

            conn.commit()
            conn.close()
            flash(f'নতুন ব্যবহারকারী "{username}" ({role}) সফলভাবে তৈরি হয়েছে!', 'success')
        except Exception as e:
            flash(f'ত্রুটি: {str(e)}', 'danger')

        return redirect(url_for('admin_dashboard'))


    @app.route('/admin/user/<int:person_id>/update-role', methods=['POST'])
    def admin_update_user_role(person_id):
        """Update role of a user"""
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        new_role = request.form.get('role', 'FARMER').strip().upper()

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE PERSON SET role = ? WHERE person_id = ?", (new_role, person_id))
            conn.commit()
            conn.close()
            flash(f'ব্যবহারকারী #{person_id} এর ভূমিকা পরিবর্তন করে "{new_role}" করা হয়েছে।', 'success')
        except Exception as e:
            flash(f'ত্রুটি: {str(e)}', 'danger')

        return redirect(url_for('admin_dashboard'))


    @app.route('/admin/user/<int:person_id>/delete', methods=['POST'])
    def admin_delete_user(person_id):
        """Delete a user account"""
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        if person_id == session['user'].get('person_id'):
            flash('আপনি আপনার নিজের অ্যাডমিন অ্যাকাউন্ট মুছতে পারবেন না!', 'danger')
            return redirect(url_for('admin_dashboard'))

        try:
            conn = get_connection()
            cursor = conn.cursor()
            # Clean up child relations
            cursor.execute("DELETE FROM FARMER WHERE person_id = ?", (person_id,))
            cursor.execute("DELETE FROM FIELD_AGENT WHERE person_id = ?", (person_id,))
            cursor.execute("DELETE FROM ADVISOR WHERE person_id = ?", (person_id,))
            cursor.execute("DELETE FROM NOTIFICATION WHERE person_id = ?", (person_id,))
            cursor.execute("DELETE FROM PERSON WHERE person_id = ?", (person_id,))
            conn.commit()
            conn.close()
            flash(f'ব্যবহারকারী #{person_id} সফলভাবে মুছে ফেলা হয়েছে।', 'info')
        except Exception as e:
            flash(f'ত্রুটি: {str(e)}', 'danger')

        return redirect(url_for('admin_dashboard'))


    # ==========================================
    # 3. LOAN ACTIONS (Approve / Reject / Close)
    # ==========================================

    @app.route('/admin/loan/<int:loan_no>/approve', methods=['POST'])
    def admin_approve_loan(loan_no):
        """Approve agricultural loan and notify farmer"""
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        try:
            conn = get_connection()
            cursor = conn.cursor()
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                UPDATE LOAN 
                SET loan_state = 'ACTIVE', approval_date = ?
                WHERE loan_no = ?
            """, (now_str, loan_no))

            # Fetch farmer's person_id to send notification
            cursor.execute("""
                SELECT f.person_id, p.first_name, l.tenure_months
                FROM LOAN l
                JOIN FARMER f ON l.farmer_code = f.farmer_code
                JOIN PERSON p ON f.person_id = p.person_id
                WHERE l.loan_no = ?
            """, (loan_no,))
            row = cursor.fetchone()
            if row:
                person_id, farmer_name, tenure = row[0], row[1], row[2]
                msg = f"অভিনন্দন {farmer_name}! আপনার কৃষি ঋণ #{loan_no} (মেয়াদ: {tenure} মাস) কেন্দ্রীয়ভাবে অনুমোদিত হয়েছে।"
                cursor.execute("""
                    INSERT INTO NOTIFICATION (person_id, title, message, link)
                    VALUES (?, '✅ কৃষি ঋণ অনুমোদিত হয়েছে!', ?, '/dashboard')
                """, (person_id, msg))

            conn.commit()
            conn.close()
            flash(f'ঋণ #{loan_no} সফলভাবে অনুমোদিত হয়েছে এবং কৃষককে অবহিত করা হয়েছে!', 'success')
        except Exception as e:
            flash(f'ত্রুটি: {str(e)}', 'danger')

        return redirect(url_for('admin_dashboard'))


    @app.route('/admin/loan/<int:loan_no>/reject', methods=['POST'])
    def admin_reject_loan(loan_no):
        """Reject agricultural loan"""
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE LOAN SET loan_state = 'REJECTED' WHERE loan_no = ?", (loan_no,))

            cursor.execute("""
                SELECT f.person_id, p.first_name
                FROM LOAN l
                JOIN FARMER f ON l.farmer_code = f.farmer_code
                JOIN PERSON p ON f.person_id = p.person_id
                WHERE l.loan_no = ?
            """, (loan_no,))
            row = cursor.fetchone()
            if row:
                cursor.execute("""
                    INSERT INTO NOTIFICATION (person_id, title, message, link)
                    VALUES (?, '❌ কৃষি ঋণ আবেদন বাতিল', 'দুঃখিত, আপনার ঋণ আবেদনটি প্রশাসনিক পর্যালোচনার পর বাতিল করা হয়েছে। বিস্তারিত জানতে ফিল্ড এজেন্টের সাথে যোগাযোগ করুন।', '/dashboard')
                """, (row[0],))

            conn.commit()
            conn.close()
            flash(f'ঋণ আবেদন #{loan_no} বাতিল করা হয়েছে।', 'warning')
        except Exception as e:
            flash(f'ত্রুটি: {str(e)}', 'danger')

        return redirect(url_for('admin_dashboard'))


    @app.route('/admin/loan/<int:loan_no>/close', methods=['POST'])
    def admin_close_loan(loan_no):
        """Mark loan as CLOSED/REPAID"""
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE LOAN SET loan_state = 'CLOSED' WHERE loan_no = ?", (loan_no,))
            conn.commit()
            conn.close()
            flash(f'ঋণ #{loan_no} সফলভাবে পরিশোধিত হিসেবে চিহ্নিত করা হয়েছে!', 'success')
        except Exception as e:
            flash(f'ত্রুটি: {str(e)}', 'danger')

        return redirect(url_for('admin_dashboard'))


    # ==========================================
    # 4. ADVISOR MANAGEMENT
    # ==========================================

    @app.route('/admin/advisor/<int:advisor_id>/toggle-status', methods=['POST'])
    def admin_toggle_advisor_status(advisor_id):
        """Toggle Advisor availability (YES / NO)"""
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE ADVISOR 
                SET is_available = CASE WHEN is_available = 'YES' THEN 'NO' ELSE 'YES' END
                WHERE advisor_id = ?
            """, (advisor_id,))
            conn.commit()
            conn.close()
            flash(f'উপদেষ্টা #{advisor_id} এর প্রাপ্যতা স্থিতি সফলভাবে পরিবর্তন করা হয়েছে!', 'success')
        except Exception as e:
            flash(f'ত্রুটি: {str(e)}', 'danger')

        return redirect(url_for('admin_dashboard'))


    @app.route('/admin/advisor/<int:advisor_id>/edit', methods=['POST'])
    def admin_edit_advisor(advisor_id):
        """Edit advisor details and qualification"""
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        specialization = request.form.get('specialization', '').strip()
        qualification = request.form.get('qualification', '').strip()
        experience_years = int(request.form.get('experience_years', '5'))
        bio = request.form.get('bio', '').strip()

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE ADVISOR
                SET specialization = ?, qualification = ?, experience_years = ?, bio = ?
                WHERE advisor_id = ?
            """, (specialization, qualification, experience_years, bio, advisor_id))
            conn.commit()
            conn.close()
            flash(f'উপদেষ্টা #{advisor_id} এর প্রোফাইল তথ্য আপডেট করা হয়েছে!', 'success')
        except Exception as e:
            flash(f'ত্রুটি: {str(e)}', 'danger')

        return redirect(url_for('admin_dashboard'))


    # ==========================================
    # 5. INVENTORY OPERATIONS
    # ==========================================

    @app.route('/admin/inventory/add', methods=['POST'])
    def admin_add_inventory():
        """Add seed or fertilizer to inventory"""
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        agent_code = request.form.get('agent_code', '2001')
        item_name = request.form.get('item_name', '').strip()
        quantity = int(request.form.get('quantity', '50'))
        unit = request.form.get('unit', 'কেজি').strip()
        price = float(request.form.get('price', '500'))

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO INVENTORY (agent_code, item_name, quantity, unit, price)
                VALUES (?, ?, ?, ?, ?)
            """, (agent_code, item_name, quantity, unit, price))
            conn.commit()
            conn.close()
            flash(f'পণ্য "{item_name}" সফলভাবে মজুদে যুক্ত করা হয়েছে!', 'success')
        except Exception as e:
            flash(f'ত্রুটি: {str(e)}', 'danger')

        return redirect(url_for('admin_dashboard'))


    @app.route('/admin/inventory/<int:inventory_id>/update', methods=['POST'])
    def admin_update_inventory(inventory_id):
        """Update inventory stock quantity and price"""
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        quantity = int(request.form.get('quantity', '0'))
        price = float(request.form.get('price', '0'))

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE INVENTORY
                SET quantity = ?, price = ?
                WHERE inventory_id = ?
            """, (quantity, price, inventory_id))
            conn.commit()
            conn.close()
            flash(f'ইনভেন্টরি আইটেম #{inventory_id} সফলভাবে আপডেট করা হয়েছে!', 'success')
        except Exception as e:
            flash(f'ত্রুটি: {str(e)}', 'danger')

        return redirect(url_for('admin_dashboard'))


    @app.route('/admin/inventory/<int:inventory_id>/delete', methods=['POST'])
    def admin_delete_inventory(inventory_id):
        """Delete an inventory item"""
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM INVENTORY WHERE inventory_id = ?", (inventory_id,))
            conn.commit()
            conn.close()
            flash(f'ইনভেন্টরি আইটেম #{inventory_id} মুছে ফেলা হয়েছে।', 'info')
        except Exception as e:
            flash(f'ত্রুটি: {str(e)}', 'danger')

        return redirect(url_for('admin_dashboard'))


    # ==========================================
    # 6. ANNOUNCEMENTS & BROADCAST NOTIFICATIONS
    # ==========================================

    @app.route('/admin/post/create', methods=['POST'])
    def admin_create_post():
        """Create official announcement and broadcast to all users bell"""
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        user_id = session['user'].get('person_id', 4001)
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        broadcast_bell = request.form.get('broadcast_bell') == 'on'

        if not content:
            flash('নোটিশের বিবরণ আবশ্যক।', 'warning')
            return redirect(url_for('admin_dashboard'))

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO COMMUNITY_POST (author_id, title, content)
                VALUES (?, ?, ?)
            """, (user_id, title or 'জরুরী নোটিশ', content))

            if broadcast_bell:
                # Insert notifications for all active persons
                cursor.execute("SELECT person_id FROM PERSON")
                all_person_ids = cursor.fetchall()
                for p in all_person_ids:
                    cursor.execute("""
                        INSERT INTO NOTIFICATION (person_id, title, message, link)
                        VALUES (?, ?, ?, '/dashboard')
                    """, (p[0], f"📢 {title or 'জরুরী নোটিশ'}", content))

            conn.commit()
            conn.close()
            flash('অফিসিয়াল নোটিশ সফলভাবে জারি এবং সম্প্রচার করা হয়েছে!', 'success')
        except Exception as e:
            flash(f'ত্রুটি: {str(e)}', 'danger')

        return redirect(url_for('admin_dashboard'))


    @app.route('/admin/post/<int:post_id>/delete', methods=['POST'])
    def admin_delete_post(post_id):
        """Delete announcement"""
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM COMMUNITY_POST WHERE post_id = ?", (post_id,))
            conn.commit()
            conn.close()
            flash('নোটিশ সফলভাবে মুছে ফেলা হয়েছে।', 'info')
        except Exception as e:
            flash(f'ত্রুটি: {str(e)}', 'danger')

        return redirect(url_for('admin_dashboard'))
