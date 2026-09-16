# =========================================================
# MERGED MODULE — admin_routes.py
# =========================================================
# Base logic (Oracle schema, community posts, audit, KYC list): You + Noor
# UI structure & tab navigation refactored with input from: Rafi (admin module)
# Oracle DBMS conversion: You
#
# CHANGES FROM ORIGINAL:
# - All SQL converted to Oracle bind syntax (:1, :2, ...)
# - NVL() replaces COALESCE(), SYSDATE replaces datetime('now')
# - Loan approvals call the APPROVE_LOAN stored procedure
#   (checks FARMER_ELIGIBILITY_VIEW before approving)
# - Community post creation preserved — mandatory write operation
# - LISTAGG replaces GROUP_CONCAT for agent name lists
# - /admin/farmer/<farmer_code>/manage: KYC writes use datetime columns correctly
# - Removed SQLite-only constructs (IF NOT EXISTS, ?, etc.)
# - Center/loan/inventory IDs treated as VARCHAR2 (Oracle schema)
# =========================================================

from flask import render_template, request, redirect, url_for, session, flash, jsonify
from db_connect import get_connection
from datetime import datetime
from cte_analytics_queries import (
    get_regional_center_ranking_cte,
    get_farmer_credit_risk_tiering_cte,
    get_advisor_revenue_matrix_cte,
    get_recursive_loan_schedule_cte
)
from search_queries import (
    search_farmers, search_advisors, search_loans,
    search_inventory, search_centers
)


def get_lang():
    return session.get('language', 'bn')


def get_flash_message(bn_msg, en_msg):
    return bn_msg if get_lang() == 'bn' else en_msg


def _next_center_code(cursor):
    """Generate next center code like C-001, C-002 ..."""
    cursor.execute("""
        SELECT 'C-' || LPAD(
            NVL(MAX(TO_NUMBER(REGEXP_SUBSTR(center_code, '[0-9]+'))), 100) + 1,
            3, '0')
        FROM IFARMER_CENTER
    """)
    return cursor.fetchone()[0]


def _next_post_id(cursor):
    """Generate next post id like POST-<timestamp>"""
    cursor.execute("SELECT 'POST-' || TO_CHAR(SYSDATE, 'YYYYMMDDHH24MISS') FROM DUAL")
    return cursor.fetchone()[0]


def register_admin_routes(app):

    # ==========================================
    # 1. ADMIN DASHBOARD
    # ==========================================
    @app.route('/admin/dashboard')
    def admin_dashboard():
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            flash(get_flash_message('প্রশাসক হিসেবে প্রবেশাধিকার সংরক্ষিত।',
                                    'Admin access required.'), 'danger')
            return redirect(url_for('login_register'))

        user = session['user']
        admin_data = {
            'total_farmers': 0, 'total_agents': 0, 'total_advisors': 0,
            'total_centers': 0, 'total_loans': 0, 'active_loans': 0,
            'total_consultations': 0, 'total_inventory': 0,
            'total_disbursed_amount': 0, 'total_repaid_amount': 0,
            'total_outstanding_due': 0,
        }
        centers, users_list, advisors_list = [], [], []
        loans_list, repayments_list, inventory_list = [], [], []
        posts, all_agents = [], []

        conn = get_connection()
        if conn:
            cursor = conn.cursor()
            try:
                # --- High-level KPIs ---
                cursor.execute("SELECT COUNT(*) FROM FARMER")
                admin_data['total_farmers'] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM FIELD_AGENT")
                admin_data['total_agents'] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM ADVISOR")
                admin_data['total_advisors'] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM IFARMER_CENTER")
                admin_data['total_centers'] = cursor.fetchone()[0]

                cursor.execute("""
                    SELECT COUNT(*),
                           NVL(SUM(CASE WHEN loan_state = 'ACTIVE' THEN 1 ELSE 0 END), 0)
                    FROM LOAN
                """)
                l_row = cursor.fetchone()
                admin_data['total_loans'] = l_row[0] if l_row else 0
                admin_data['active_loans'] = l_row[1] if l_row else 0

                cursor.execute("""
                    SELECT NVL(SUM(amount), 0) FROM LOAN
                    WHERE loan_state IN ('ACTIVE','PENDING','CLOSED')
                """)
                admin_data['total_disbursed_amount'] = cursor.fetchone()[0] or 0

                cursor.execute("SELECT NVL(SUM(amount_paid), 0) FROM REPAYMENT")
                admin_data['total_repaid_amount'] = cursor.fetchone()[0] or 0
                admin_data['total_outstanding_due'] = max(
                    0,
                    admin_data['total_disbursed_amount'] - admin_data['total_repaid_amount']
                )

                cursor.execute("SELECT COUNT(*) FROM ADVISOR_BOOKING")
                admin_data['total_consultations'] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM INVENTORY")
                admin_data['total_inventory'] = cursor.fetchone()[0]

                # --- Centers with assigned agent names (LISTAGG) ---
                cursor.execute("""
                    SELECT
                        c.center_code,
                        c.center_name,
                        NVL(c.upazila, 'N/A'),
                        NVL(c.district, 'N/A'),
                        (SELECT COUNT(*) FROM FIELD_AGENT fa
                         WHERE fa.center_code = c.center_code) AS agent_count,
                        (SELECT COUNT(*) FROM FARMER f
                         WHERE f.center_code = c.center_code) AS farmer_count,
                        (SELECT LISTAGG(p.first_name || ' ' || p.last_name, ', ')
                                WITHIN GROUP (ORDER BY p.first_name)
                         FROM FIELD_AGENT fa
                         JOIN PERSON p ON fa.person_id = p.person_id
                         WHERE fa.center_code = c.center_code) AS agent_names
                    FROM IFARMER_CENTER c
                    ORDER BY c.center_code ASC
                """)
                centers = cursor.fetchall()

                # --- All agents (for center assign dropdown) ---
                cursor.execute("""
                    SELECT fa.agent_code,
                           p.first_name || ' ' || p.last_name
                    FROM FIELD_AGENT fa
                    JOIN PERSON p ON fa.person_id = p.person_id
                    ORDER BY fa.agent_code ASC
                """)
                all_agents = cursor.fetchall()

                # --- Users directory ---
                cursor.execute("""
                    SELECT p.person_id,
                           p.first_name || ' ' || p.last_name AS full_name,
                           p.username,
                           p.login_phone,
                           p.role,
                           TO_CHAR(p.created_at, 'DD-Mon-YYYY')
                    FROM PERSON p
                    ORDER BY p.person_id DESC
                """)
                users_list = cursor.fetchall()

                # --- Advisors ---
                cursor.execute("""
                    SELECT a.advisor_id,
                           p.first_name || ' ' || p.last_name AS name,
                           p.login_phone,
                           a.specialization,
                           NVL(a.qualification, 'N/A'),
                           NVL(a.rating, 5.0),
                           NVL(a.total_bookings, 0),
                           NVL(a.is_available, 'YES'),
                           NVL(a.experience_years, 0),
                           NVL(a.bio, '')
                    FROM ADVISOR a
                    JOIN PERSON p ON a.person_id = p.person_id
                    ORDER BY NVL(a.rating, 5.0) DESC
                """)
                advisors_list = cursor.fetchall()

                # --- Loans portfolio ---
                cursor.execute("""
                    SELECT
                        l.loan_no,
                        l.farmer_code,
                        p.first_name || ' ' || p.last_name AS farmer_name,
                        NVL(l.amount, 0),
                        l.loan_state,
                        TO_CHAR(l.approval_date, 'DD-Mon-YYYY'),
                        NVL(l.tenure_months, 12),
                        TO_CHAR(l.application_date, 'DD-Mon-YYYY'),
                        NVL(l.purpose, 'কৃষি উৎপাদন ও শস্য সুরক্ষা'),
                        (SELECT NVL(SUM(amount_paid), 0) FROM REPAYMENT
                         WHERE loan_no = l.loan_no),
                        (SELECT COUNT(*) FROM REPAYMENT WHERE loan_no = l.loan_no)
                    FROM LOAN l
                    JOIN FARMER f ON l.farmer_code = f.farmer_code
                    JOIN PERSON p ON f.person_id = p.person_id
                    ORDER BY l.loan_no DESC
                """)
                loans_list = cursor.fetchall()

                # --- Repayments ---
                cursor.execute("""
                    SELECT
                        r.loan_no || '-' || TO_CHAR(r.installment_no),
                        r.loan_no,
                        p.first_name || ' ' || p.last_name AS farmer_name,
                        r.installment_no,
                        TO_CHAR(r.payment_date, 'Mon-YYYY'),
                        TO_CHAR(r.payment_date, 'DD-Mon-YYYY'),
                        r.amount_paid,
                        NULL,
                        r.payment_method,
                        NULL,
                        r.payment_state,
                        NVL(l.purpose, '')
                    FROM REPAYMENT r
                    JOIN LOAN l ON r.loan_no = l.loan_no
                    JOIN FARMER f ON l.farmer_code = f.farmer_code
                    JOIN PERSON p ON f.person_id = p.person_id
                    ORDER BY r.payment_date DESC, r.installment_no DESC
                """)
                repayments_list = cursor.fetchall()

                # --- Inventory ---
                cursor.execute("""
                    SELECT i.inventory_id,
                           i.center_code,
                           i.name,
                           NVL(i.quantity, 0),
                           NVL(i.unit, 'unit'),
                           NVL(i.price_per_unit, 0)
                    FROM INVENTORY i
                    ORDER BY i.inventory_id ASC
                """)
                inventory_list = cursor.fetchall()

                # --- Community posts ---
                cursor.execute("""
                    SELECT post_id,
                           NVL(title, 'জরুরী নোটিশ'),
                           content,
                           TO_CHAR(post_date, 'DD-Mon-YYYY')
                    FROM COMMUNITY_POST
                    ORDER BY post_date DESC
                """)
                posts = cursor.fetchall()

            except Exception as e:
                print(f"Admin dashboard error: {e}")
                import traceback; traceback.print_exc()
            finally:
                cursor.close()
                conn.close()

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
    # 2. CENTER OPERATIONS
    # ==========================================
    @app.route('/admin/center/add', methods=['POST'])
    def admin_add_center():
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        center_name = request.form.get('center_name', '').strip()
        upazila     = request.form.get('upazila', '').strip()
        district    = request.form.get('district', '').strip()

        if not center_name or not upazila or not district:
            flash('সেন্টারের নাম, উপজেলা এবং জেলা আবশ্যক।', 'warning')
            return redirect(url_for('admin_dashboard'))

        conn = get_connection()
        cursor = conn.cursor()
        try:
            new_code = _next_center_code(cursor)
            cursor.execute("""
                INSERT INTO IFARMER_CENTER
                    (center_code, center_name, upazila, district, center_state)
                VALUES (:1, :2, :3, :4, 'ACTIVE')
            """, (new_code, center_name, upazila, district))
            conn.commit()
            flash(f'নতুন সেন্টার "{center_name}" সফলভাবে যুক্ত হয়েছে!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'ত্রুটি: {str(e)}', 'danger')
        finally:
            cursor.close(); conn.close()
        return redirect(url_for('admin_dashboard'))

    @app.route('/admin/center/<center_code>/edit', methods=['POST'])
    def admin_edit_center(center_code):
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        center_name = request.form.get('center_name', '').strip()
        upazila     = request.form.get('upazila', '').strip()
        district    = request.form.get('district', '').strip()

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE IFARMER_CENTER
                SET center_name = :1, upazila = :2, district = :3
                WHERE center_code = :4
            """, (center_name, upazila, district, center_code))
            conn.commit()
            flash(f'সেন্টার #{center_code} আপডেট হয়েছে!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'ত্রুটি: {str(e)}', 'danger')
        finally:
            cursor.close(); conn.close()
        return redirect(url_for('admin_dashboard'))

    @app.route('/admin/center/<center_code>/delete', methods=['POST'])
    def admin_delete_center(center_code):
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        conn = get_connection()
        cursor = conn.cursor()
        try:
            # Detach agents & farmers first (set to NULL, no hardcoded '101')
            cursor.execute(
                "UPDATE FIELD_AGENT SET center_code = NULL WHERE center_code = :1",
                (center_code,))
            cursor.execute(
                "UPDATE FARMER SET center_code = NULL WHERE center_code = :1",
                (center_code,))
            cursor.execute(
                "DELETE FROM IFARMER_CENTER WHERE center_code = :1",
                (center_code,))
            conn.commit()
            flash(f'সেন্টার #{center_code} মুছে ফেলা হয়েছে।', 'info')
        except Exception as e:
            conn.rollback()
            flash(f'ত্রুটি: {str(e)}', 'danger')
        finally:
            cursor.close(); conn.close()
        return redirect(url_for('admin_dashboard'))

    @app.route('/admin/center/<center_code>/assign-agent', methods=['POST'])
    def admin_assign_agent(center_code):
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        agent_code = request.form.get('agent_code')
        if not agent_code:
            flash('অনুগ্রহ করে একজন ফিল্ড এজেন্ট নির্বাচন করুন।', 'warning')
            return redirect(url_for('admin_dashboard'))

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE FIELD_AGENT
                SET center_code = :1
                WHERE agent_code = :2
            """, (center_code, agent_code))
            conn.commit()
            flash(f'ফিল্ড এজেন্ট #{agent_code} কে এই সেন্টারে দায়িত্ব দেওয়া হয়েছে!',
                  'success')
        except Exception as e:
            conn.rollback()
            flash(f'ত্রুটি: {str(e)}', 'danger')
        finally:
            cursor.close(); conn.close()
        return redirect(url_for('admin_dashboard'))

    # ==========================================
    # 3. USER MANAGEMENT
    # ==========================================
    @app.route('/admin/user/create', methods=['POST'])
    def admin_create_user():
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        first_name  = request.form.get('first_name', '').strip()
        last_name   = request.form.get('last_name', '').strip()
        username    = request.form.get('username', '').strip()
        password    = request.form.get('password', 'password123').strip()
        login_phone = request.form.get('login_phone', '').strip()
        role        = request.form.get('role', 'FARMER').strip().upper()

        if not first_name or not username or not login_phone:
            flash('নাম, ইউজারনেম এবং মোবাইল নম্বর আবশ্যক।', 'warning')
            return redirect(url_for('admin_dashboard'))

        conn = get_connection()
        cursor = conn.cursor()
        try:
            new_id_var = cursor.var(int)
            cursor.execute("""
                INSERT INTO PERSON
                    (person_id, first_name, last_name, username, password,
                     login_phone, role, gender)
                VALUES
                    (person_seq.NEXTVAL, :1, :2, :3, :4, :5, :6, 'Other')
                RETURNING person_id INTO :7
            """, (first_name, last_name, username, password,
                  login_phone, role, new_id_var))
            new_person_id = new_id_var.getvalue()[0]

            # Role-specific sub-table entry
            if role == 'FARMER':
                cursor.execute("SELECT farmer_seq.NEXTVAL FROM DUAL")
                farmer_code = 'FR-' + str(cursor.fetchone()[0]).zfill(4)
                cursor.execute("""
                    INSERT INTO FARMER (farmer_code, person_id, account_status)
                    VALUES (:1, :2, 'ACTIVE')
                """, (farmer_code, new_person_id))
            elif role == 'AGENT':
                cursor.execute("SELECT 'AG-' || LPAD(person_seq.CURRVAL, 4, '0') FROM DUAL")
                agent_code = cursor.fetchone()[0]
                cursor.execute("""
                    INSERT INTO FIELD_AGENT (agent_code, person_id, is_active)
                    VALUES (:1, :2, 'Y')
                """, (agent_code, new_person_id))
            elif role == 'ADVISOR':
                cursor.execute("""
                    INSERT INTO ADVISOR
                        (advisor_id, person_id, specialization, qualification,
                         is_available, rating, total_bookings)
                    VALUES
                        (advisor_seq.NEXTVAL, :1,
                         'সাধারণ কৃষি ও উদ্ভিদ রোগ বিশেষজ্ঞ',
                         'বিএসসি ইন এগ্রিকালচার', 'YES', 5.0, 0)
                """, (new_person_id,))

            conn.commit()
            flash(f'নতুন ব্যবহারকারী "{username}" ({role}) তৈরি হয়েছে!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'ত্রুটি: {str(e)}', 'danger')
        finally:
            cursor.close(); conn.close()
        return redirect(url_for('admin_dashboard'))

    @app.route('/admin/user/<int:person_id>/update-role', methods=['POST'])
    def admin_update_user_role(person_id):
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        new_role = request.form.get('role', 'FARMER').strip().upper()

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE PERSON SET role = :1 WHERE person_id = :2",
                (new_role, person_id))
            conn.commit()
            flash(f'ব্যবহারকারী #{person_id} এর ভূমিকা "{new_role}" করা হয়েছে।', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'ত্রুটি: {str(e)}', 'danger')
        finally:
            cursor.close(); conn.close()
        return redirect(url_for('admin_dashboard'))

    @app.route('/admin/user/<int:person_id>/delete', methods=['POST'])
    def admin_delete_user(person_id):
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        if person_id == session['user'].get('person_id'):
            flash('আপনি আপনার নিজের অ্যাকাউন্ট মুছতে পারবেন না!', 'danger')
            return redirect(url_for('admin_dashboard'))

        conn = get_connection()
        cursor = conn.cursor()
        try:
            # Clean child rows first
            cursor.execute("DELETE FROM FARMER WHERE person_id = :1", (person_id,))
            cursor.execute("DELETE FROM FIELD_AGENT WHERE person_id = :1", (person_id,))
            cursor.execute("DELETE FROM ADVISOR WHERE person_id = :1", (person_id,))
            cursor.execute("DELETE FROM NOTIFICATION WHERE person_id = :1", (person_id,))
            cursor.execute("DELETE FROM PHONE WHERE person_id = :1", (person_id,))
            cursor.execute("DELETE FROM PERSON WHERE person_id = :1", (person_id,))
            conn.commit()
            flash(f'ব্যবহারকারী #{person_id} মুছে ফেলা হয়েছে।', 'info')
        except Exception as e:
            conn.rollback()
            flash(f'ত্রুটি: {str(e)}', 'danger')
        finally:
            cursor.close(); conn.close()
        return redirect(url_for('admin_dashboard'))

    # ==========================================
    # 4. LOAN ACTIONS (via STORED PROCEDURE)
    # ==========================================
    @app.route('/admin/loan/<loan_no>/approve', methods=['POST'])
    def admin_approve_loan(loan_no):
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        admin_id = session['user'].get('person_id')

        conn = get_connection()
        cursor = conn.cursor()
        try:
            # APPROVE_LOAN validates eligibility via FARMER_ELIGIBILITY_VIEW
            cursor.callproc('APPROVE_LOAN', (loan_no, admin_id, 'APPROVE'))
            conn.commit()
            flash(f'ঋণ #{loan_no} সফলভাবে অনুমোদিত হয়েছে!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'ত্রুটি: {str(e)}', 'danger')
        finally:
            cursor.close(); conn.close()
        return redirect(url_for('admin_dashboard'))

    @app.route('/admin/loan/<loan_no>/reject', methods=['POST'])
    def admin_reject_loan(loan_no):
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        admin_id = session['user'].get('person_id')

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.callproc('APPROVE_LOAN', (loan_no, admin_id, 'REJECT'))
            conn.commit()
            flash(f'ঋণ #{loan_no} বাতিল করা হয়েছে।', 'warning')
        except Exception as e:
            conn.rollback()
            flash(f'ত্রুটি: {str(e)}', 'danger')
        finally:
            cursor.close(); conn.close()
        return redirect(url_for('admin_dashboard'))

    @app.route('/admin/loan/<loan_no>/close', methods=['POST'])
    def admin_close_loan(loan_no):
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE LOAN SET loan_state = 'CLOSED' WHERE loan_no = :1",
                (loan_no,))
            conn.commit()
            flash(f'ঋণ #{loan_no} পরিশোধিত চিহ্নিত করা হয়েছে!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'ত্রুটি: {str(e)}', 'danger')
        finally:
            cursor.close(); conn.close()
        return redirect(url_for('admin_dashboard'))

    # ==========================================
    # 5. ADVISOR MANAGEMENT
    # ==========================================
    @app.route('/admin/advisor/<int:advisor_id>/toggle-status', methods=['POST'])
    def admin_toggle_advisor_status(advisor_id):
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE ADVISOR
                SET is_available = CASE
                    WHEN is_available = 'YES' THEN 'NO' ELSE 'YES' END
                WHERE advisor_id = :1
            """, (advisor_id,))
            conn.commit()
            flash(f'উপদেষ্টা #{advisor_id} এর প্রাপ্যতা পরিবর্তিত হয়েছে!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'ত্রুটি: {str(e)}', 'danger')
        finally:
            cursor.close(); conn.close()
        return redirect(url_for('admin_dashboard'))

    @app.route('/admin/advisor/<int:advisor_id>/edit', methods=['POST'])
    def admin_edit_advisor(advisor_id):
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        specialization = request.form.get('specialization', '').strip()
        qualification  = request.form.get('qualification', '').strip()
        bio            = request.form.get('bio', '').strip()
        try:
            exp = int(request.form.get('experience_years', '5'))
        except ValueError:
            exp = 5

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE ADVISOR
                SET specialization = :1,
                    qualification = :2,
                    experience_years = :3,
                    bio = :4
                WHERE advisor_id = :5
            """, (specialization, qualification, exp, bio, advisor_id))
            conn.commit()
            flash(f'উপদেষ্টা #{advisor_id} এর প্রোফাইল আপডেট হয়েছে!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'ত্রুটি: {str(e)}', 'danger')
        finally:
            cursor.close(); conn.close()
        return redirect(url_for('admin_dashboard'))

    # ==========================================
    # 6. INVENTORY OPERATIONS
    # ==========================================
    @app.route('/admin/inventory/add', methods=['POST'])
    def admin_add_inventory():
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        agent_code = request.form.get('agent_code', '').strip()
        item_name  = request.form.get('item_name', '').strip()
        try:
            quantity = int(request.form.get('quantity', '50'))
            price    = float(request.form.get('price', '500'))
        except ValueError:
            quantity, price = 50, 500.0
        unit = request.form.get('unit', 'কেজি').strip()

        conn = get_connection()
        cursor = conn.cursor()
        try:
            # Find center via agent
            cursor.execute(
                "SELECT center_code FROM FIELD_AGENT WHERE agent_code = :1",
                (agent_code,))
            row = cursor.fetchone()
            if not row or not row[0]:
                flash('এই এজেন্টের জন্য কোনো সেন্টার নির্ধারিত নেই।', 'warning')
                return redirect(url_for('admin_dashboard'))
            center_code = row[0]

            # Generate new inventory id
            cursor.execute("""
                SELECT 'INV-' || LPAD(
                    NVL(MAX(TO_NUMBER(REGEXP_SUBSTR(inventory_id, '[0-9]+'))), 0) + 1,
                    3, '0')
                FROM INVENTORY
            """)
            new_id = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO INVENTORY
                    (inventory_id, center_code, name, quantity, unit,
                     price_per_unit, min_stock_level)
                VALUES (:1, :2, :3, :4, :5, :6, 10)
            """, (new_id, center_code, item_name, quantity, unit, price))
            conn.commit()
            flash(f'পণ্য "{item_name}" মজুদে যুক্ত হয়েছে!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'ত্রুটি: {str(e)}', 'danger')
        finally:
            cursor.close(); conn.close()
        return redirect(url_for('admin_dashboard'))

    @app.route('/admin/inventory/<inventory_id>/update', methods=['POST'])
    def admin_update_inventory(inventory_id):
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        try:
            quantity = int(request.form.get('quantity', '0'))
            price    = float(request.form.get('price', '0'))
        except ValueError:
            quantity, price = 0, 0.0

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE INVENTORY
                SET quantity = :1, price_per_unit = :2
                WHERE inventory_id = :3
            """, (quantity, price, inventory_id))
            conn.commit()
            flash(f'ইনভেন্টরি #{inventory_id} আপডেট হয়েছে!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'ত্রুটি: {str(e)}', 'danger')
        finally:
            cursor.close(); conn.close()
        return redirect(url_for('admin_dashboard'))

    @app.route('/admin/inventory/<inventory_id>/delete', methods=['POST'])
    def admin_delete_inventory(inventory_id):
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM INVENTORY WHERE inventory_id = :1",
                (inventory_id,))
            conn.commit()
            flash(f'ইনভেন্টরি #{inventory_id} মুছে ফেলা হয়েছে।', 'info')
        except Exception as e:
            conn.rollback()
            flash(f'ত্রুটি: {str(e)}', 'danger')
        finally:
            cursor.close(); conn.close()
        return redirect(url_for('admin_dashboard'))

    # ==========================================
    # 7. COMMUNITY POSTS (WRITE OPERATION)
    # ==========================================
    @app.route('/admin/post/create', methods=['POST'])
    def admin_create_post():
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        admin_id       = session['user'].get('person_id')
        title          = request.form.get('title', '').strip() or 'জরুরী নোটিশ'
        content        = request.form.get('content', '').strip()
        broadcast_bell = request.form.get('broadcast_bell') == 'on'

        if not content:
            flash('নোটিশের বিবরণ আবশ্যক।', 'warning')
            return redirect(url_for('admin_dashboard'))

        conn = get_connection()
        cursor = conn.cursor()
        try:
            post_id = _next_post_id(cursor)
            cursor.execute("""
                INSERT INTO COMMUNITY_POST (post_id, admin_id, title, content, post_date)
                VALUES (:1, :2, :3, :4, SYSDATE)
            """, (post_id, admin_id, title, content))

            if broadcast_bell:
                # Fan out notification to every person
                cursor.execute("SELECT person_id FROM PERSON")
                all_ids = [r[0] for r in cursor.fetchall()]
                for pid in all_ids:
                    cursor.execute("""
                        INSERT INTO NOTIFICATION
                            (notif_id, person_id, title, message, link,
                             is_read, created_at, notification_type)
                        VALUES
                            ('NOTIF-' || notif_seq.NEXTVAL, :1, :2, :3,
                             '/dashboard', 'NO', SYSDATE, 'ANNOUNCEMENT')
                    """, (pid, '📢 ' + title, content))

            conn.commit()
            flash('নোটিশ সফলভাবে জারি ও সম্প্রচার করা হয়েছে!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'ত্রুটি: {str(e)}', 'danger')
        finally:
            cursor.close(); conn.close()
        return redirect(url_for('admin_dashboard'))

    @app.route('/admin/post/<post_id>/delete', methods=['POST'])
    def admin_delete_post(post_id):
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM COMMUNITY_POST WHERE post_id = :1", (post_id,))
            conn.commit()
            flash('নোটিশ মুছে ফেলা হয়েছে।', 'info')
        except Exception as e:
            conn.rollback()
            flash(f'ত্রুটি: {str(e)}', 'danger')
        finally:
            cursor.close(); conn.close()
        return redirect(url_for('admin_dashboard'))

    # ==========================================
    # 8. SEARCH
    # ==========================================
    @app.route('/search')
    def search_page():
        query_term = request.args.get('q', '').strip()
        category   = request.args.get('category', 'ALL').strip().upper()

        farmers, advisors, loans, inventory, centers = [], [], [], [], []

        conn = get_connection()
        if conn:
            cursor = conn.cursor()
            try:
                if category in ['ALL', 'FARMERS']:
                    farmers = search_farmers(cursor, query_term)
                if category in ['ALL', 'ADVISORS']:
                    advisors = search_advisors(cursor, query_term)
                if category in ['ALL', 'LOANS']:
                    loans = search_loans(cursor, query_term)
                if category in ['ALL', 'INVENTORY']:
                    inventory = search_inventory(cursor, query_term)
                if category in ['ALL', 'CENTERS']:
                    centers = search_centers(cursor, query_term)
            except Exception as e:
                flash(f"অনুসন্ধান ত্রুটি: {str(e)}", "danger")
                print(f"Search error: {e}")
            finally:
                cursor.close(); conn.close()

        return render_template('search.html',
                               query_term=query_term,
                               category=category,
                               farmers=farmers,
                               advisors=advisors,
                               loans=loans,
                               inventory=inventory,
                               centers=centers)

    @app.route('/api/search')
    def api_search():
        query_term = request.args.get('q', '').strip()
        category   = request.args.get('category', 'ALL').strip().upper()
        results = {'farmers': [], 'advisors': [], 'loans': [],
                   'inventory': [], 'centers': []}

        conn = get_connection()
        if conn:
            cursor = conn.cursor()
            try:
                if category in ['ALL', 'FARMERS']:
                    results['farmers'] = search_farmers(cursor, query_term)
                if category in ['ALL', 'ADVISORS']:
                    results['advisors'] = search_advisors(cursor, query_term)
                if category in ['ALL', 'LOANS']:
                    results['loans'] = search_loans(cursor, query_term)
                if category in ['ALL', 'INVENTORY']:
                    results['inventory'] = search_inventory(cursor, query_term)
                if category in ['ALL', 'CENTERS']:
                    results['centers'] = search_centers(cursor, query_term)
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
            finally:
                cursor.close(); conn.close()
        return jsonify({'success': True, 'data': results})

    # ==========================================
    # 9. CTE ANALYTICS
    # ==========================================
    @app.route('/admin/analytics')
    @app.route('/analytics')
    def admin_analytics():
        selected_loan_no = request.args.get('loan_no')

        center_rankings = []
        farmer_risk = []
        advisor_revenue = []
        recursive_schedule = []
        all_centers = []
        all_agents = []

        conn = get_connection()
        if conn:
            cursor = conn.cursor()
            try:
                center_rankings = get_regional_center_ranking_cte(cursor)
                farmer_risk = get_farmer_credit_risk_tiering_cte(cursor, limit=50)
                advisor_revenue = get_advisor_revenue_matrix_cte(cursor)
                recursive_schedule = get_recursive_loan_schedule_cte(
                    cursor, loan_no=selected_loan_no)

                cursor.execute("""
                    SELECT center_code, center_name, upazila, district
                    FROM IFARMER_CENTER
                    ORDER BY center_code ASC
                """)
                all_centers = cursor.fetchall()

                cursor.execute("""
                    SELECT fa.agent_code,
                           p.first_name || ' ' || p.last_name,
                           fa.center_code
                    FROM FIELD_AGENT fa
                    JOIN PERSON p ON fa.person_id = p.person_id
                    ORDER BY fa.agent_code ASC
                """)
                all_agents = cursor.fetchall()

            except Exception as e:
                flash(f"CTE Analytics Error: {str(e)}", "danger")
                import traceback; traceback.print_exc()
            finally:
                cursor.close(); conn.close()

        return render_template('analytics.html',
                               center_rankings=center_rankings,
                               farmer_risk=farmer_risk,
                               advisor_revenue=advisor_revenue,
                               recursive_schedule=recursive_schedule,
                               all_centers=all_centers,
                               all_agents=all_agents,
                               selected_loan_no=selected_loan_no
                                 or (recursive_schedule[0]['loan_no']
                                     if recursive_schedule else None))

    # ==========================================
    # 10. ANALYTICS QUICK-FIX ACTIONS
    # ==========================================
    @app.route('/admin/farmer/<farmer_code>/manage', methods=['POST'])
    def admin_manage_farmer(farmer_code):
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        next_url       = request.form.get('next_url') or url_for('admin_analytics')
        new_kyc        = request.form.get('kyc_status')
        new_center     = request.form.get('center_code')
        alert_msg      = request.form.get('alert_message', '').strip()
        close_loan     = request.form.get('close_active_loan')

        conn = get_connection()
        cursor = conn.cursor()
        try:
            # 1. KYC update / insert
            if new_kyc:
                cursor.execute(
                    "SELECT kyc_id FROM KYC WHERE farmer_code = :1", (farmer_code,))
                if cursor.fetchone():
                    cursor.execute("""
                        UPDATE KYC
                        SET identity_verified = :1, verified_date = SYSDATE
                        WHERE farmer_code = :2
                    """, (new_kyc, farmer_code))
                else:
                    cursor.execute("""
                        INSERT INTO KYC
                            (kyc_id, farmer_code, agent_code,
                             nid_front_ref, nid_back_ref, land_dolil_ref,
                             land_legal_status, identity_verified, verified_date)
                        VALUES
                            ('KYC-' || TO_CHAR(kyc_seq.NEXTVAL),
                             :1,
                             (SELECT NVL(agent_code, 'AG-001') FROM FARMER
                              WHERE farmer_code = :1),
                             'nid.jpg', 'nid_b.jpg', 'land.pdf',
                             'OWNED', :2, SYSDATE)
                    """, (farmer_code, new_kyc))

            # 2. Center reassignment
            if new_center:
                cursor.execute(
                    "UPDATE FARMER SET center_code = :1 WHERE farmer_code = :2",
                    (new_center, farmer_code))

            # 3. Close active loan if requested
            if close_loan == 'YES':
                cursor.execute("""
                    UPDATE LOAN SET loan_state = 'CLOSED'
                    WHERE farmer_code = :1 AND loan_state = 'ACTIVE'
                """, (farmer_code,))

            # 4. Direct alert notification
            if alert_msg:
                cursor.execute(
                    "SELECT person_id FROM FARMER WHERE farmer_code = :1",
                    (farmer_code,))
                row = cursor.fetchone()
                if row:
                    cursor.execute("""
                        INSERT INTO NOTIFICATION
                            (notif_id, person_id, farmer_code, title, message,
                             link, is_read, created_at)
                        VALUES
                            ('NOTIF-' || notif_seq.NEXTVAL, :1, :2,
                             '⚠️ প্রশাসনিক সতর্কতা', :3, '/dashboard',
                             'NO', SYSDATE)
                    """, (row[0], farmer_code, alert_msg))

            conn.commit()
            flash(f'কৃষক #{farmer_code} আপডেট হয়েছে!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'ত্রুটি: {str(e)}', 'danger')
            import traceback; traceback.print_exc()
        finally:
            cursor.close(); conn.close()
        return redirect(next_url)

    @app.route('/admin/loan/<loan_no>/record-repayment', methods=['POST'])
    def admin_record_loan_repayment(loan_no):
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            return redirect(url_for('login_register'))

        next_url = request.form.get('next_url') or url_for('admin_analytics')
        try:
            amount_paid = float(request.form.get('amount_paid', 0))
        except ValueError:
            amount_paid = 0
        payment_method = request.form.get('payment_method', 'CASH')

        if amount_paid <= 0:
            flash('পরিশোধের পরিমাণ ০ এর বেশি হতে হবে।', 'warning')
            return redirect(next_url)

        # Oracle payment_method CHECK constraint only allows:
        # CASH, MOBILE_BANKING, BANK_TRANSFER, CHEQUE
        method_map = {
            'bKash': 'MOBILE_BANKING',
            'Nagad': 'MOBILE_BANKING',
            'Bank Transfer': 'BANK_TRANSFER',
            'Cash (Field Agent)': 'CASH',
        }
        pm = method_map.get(payment_method, payment_method)
        if pm not in ('CASH', 'MOBILE_BANKING', 'BANK_TRANSFER', 'CHEQUE'):
            pm = 'CASH'

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT NVL(MAX(installment_no), 0) + 1 FROM REPAYMENT WHERE loan_no = :1",
                (loan_no,))
            inst_no = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO REPAYMENT
                    (loan_no, installment_no, amount_paid, payment_date,
                     payment_method, payment_state)
                VALUES
                    (:1, :2, :3, SYSDATE, :4, 'PAID')
            """, (loan_no, inst_no, amount_paid, pm))
            conn.commit()
            flash(f'ঋণ #{loan_no} এর ৳{amount_paid:,.0f} কিস্তি রেকর্ড হয়েছে!',
                  'success')
        except Exception as e:
            conn.rollback()
            flash(f'ত্রুটি: {str(e)}', 'danger')
        finally:
            cursor.close(); conn.close()
        return redirect(next_url)