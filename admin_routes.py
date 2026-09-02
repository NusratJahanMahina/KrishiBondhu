from flask import render_template, request, redirect, url_for, session, flash, jsonify
from db_connect import get_connection
from admin_queries import (
    get_admin_info,
    get_pending_loans,
    get_admin_stats,
    get_subordinates,
    get_community_posts,
    get_loan_detail,
    get_inventory_alerts,
    get_center_list
)
import time
import os
from werkzeug.utils import secure_filename

SCHEMA = "KRISHIBANDHU"  # only used for INSERT and fallback
UPLOAD_FOLDER = r'C:\Users\Mahina\Downloads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def set_schema(cursor):
    """Force the session to use the KRISHIBANDHU schema."""
    cursor.execute(f"ALTER SESSION SET CURRENT_SCHEMA = {SCHEMA}")

def register_admin_routes(app):
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    @app.route('/admin/dashboard')
    def admin_dashboard():
        if 'user' not in session:
            flash('Please login first.', 'warning')
            return redirect(url_for('login_register'))
        if session['user']['role'] != 'ADMIN':
            flash('Access denied. Admins only.', 'danger')
            return redirect(url_for('login_register'))

        person_id = session['user']['person_id']
        conn = get_connection()
        cursor = conn.cursor()

        # ----- FIX: Set the schema -----
        set_schema(cursor)

        # --- 1. Get admin info ---
        admin_row = get_admin_info(cursor, person_id)
        if not admin_row:
            cursor.execute(f"""
                INSERT INTO {SCHEMA}.ADMIN (person_id, admin_code, assigned_center_code, supervisor_id, access_level)
                VALUES (:1, 'ADMIN-DEFAULT', NULL, NULL, 'SUPER')
            """, (person_id,))
            conn.commit()
            admin_row = get_admin_info(cursor, person_id)

        admin_code = admin_row[0] if admin_row else 'N/A'
        center_code = admin_row[1] if admin_row else None
        center_name = admin_row[2] if admin_row and admin_row[2] else 'All Centers'
        is_super = admin_row[3] if admin_row and admin_row[3] == 'SUPER' else 'CENTER'
        supervisor_name = admin_row[5] if admin_row and admin_row[5] else 'None'

        # --- 2. Pending loans ---
        pending_loans = get_pending_loans(cursor, center_code, is_super == 'SUPER')

        # --- 3. Stats ---
        stats_row = get_admin_stats(cursor, center_code, is_super == 'SUPER')
        stats = {
            'total_farmers': stats_row[0] if stats_row else 0,
            'kyc_verified': stats_row[1] if stats_row else 0,
            'active_loans': stats_row[2] if stats_row else 0,
            'total_disbursed': stats_row[3] if stats_row else 0,
            'repayment_rate': stats_row[4] if stats_row else 0,
            'defaulted_amount': stats_row[5] if stats_row else 0
        }

        # --- 4. Subordinates ---
        subordinates = get_subordinates(cursor, person_id, center_code, is_super == 'SUPER')

        # --- 5. Community posts ---
        posts = get_community_posts(cursor)
        print(f"[ADMIN] Found {len(posts)} posts")

        # --- 6. Inventory alerts ---
        inventory_alerts = get_inventory_alerts(cursor, center_code, is_super == 'SUPER')

        # --- 7. Centers list ---
        centers = get_center_list(cursor, is_super == 'SUPER', center_code)

        cursor.close()
        conn.close()

        admin_info = [admin_code, center_code, center_name, is_super, supervisor_name]

        return render_template('dashboard_admin.html',
                               user=session['user'],
                               admin_info=admin_info,
                               is_super=is_super == 'SUPER',
                               center_name=center_name,
                               stats=stats,
                               pending_loans=pending_loans,
                               subordinates=subordinates,
                               posts=posts,
                               inventory_alerts=inventory_alerts,
                               centers=centers)

    @app.route('/admin/approve-loan', methods=['POST'])
    def admin_approve_loan():
        if 'user' not in session or session['user']['role'] != 'ADMIN':
            flash('Unauthorized.', 'danger')
            return redirect(url_for('login_register'))

        loan_no = request.form.get('loan_no')
        action = request.form.get('action')
        admin_id = session['user']['person_id']

        conn = get_connection()
        cursor = conn.cursor()
        # ----- FIX: Set the schema -----
        set_schema(cursor)
        try:
            # Stored procedure is in KRISHIBANDHU schema
            cursor.callproc('APPROVE_LOAN', (loan_no, admin_id, action))
            conn.commit()
            flash(f'Loan {loan_no} {action}d successfully.', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('admin_dashboard'))

    @app.route('/admin/create-post', methods=['POST'])
    def admin_create_post():
        if 'user' not in session or session['user']['role'] != 'ADMIN':
            flash('Unauthorized.', 'danger')
            return redirect(url_for('login_register'))

        content = request.form.get('content')
        if not content:
            flash('Content is required.', 'danger')
            return redirect(url_for('admin_dashboard'))

        image = request.files.get('image')
        admin_id = session['user']['person_id']
        post_id = 'POST-' + str(int(time.time()))

        # --- Handle image upload ---
        image_filename = None
        if image and image.filename and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{int(time.time())}{ext}"
            full_path = os.path.join(UPLOAD_FOLDER, filename)
            image.save(full_path)
            image_filename = filename

        conn = get_connection()
        cursor = conn.cursor()
        # ----- FIX: Set the schema -----
        set_schema(cursor)
        try:
            cursor.execute(f"""
                INSERT INTO {SCHEMA}.COMMUNITY_POST (post_id, admin_id, content, post_date, image)
                VALUES (:1, :2, :3, SYSDATE, :4)
            """, (post_id, admin_id, content, image_filename))
            conn.commit()
            flash('Post created successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('admin_dashboard'))

    @app.route('/admin/loan-detail/<loan_no>')
    def admin_loan_detail(loan_no):
        if 'user' not in session or session['user']['role'] != 'ADMIN':
            return jsonify({'error': 'Unauthorized'}), 401

        conn = get_connection()
        cursor = conn.cursor()
        # ----- FIX: Set the schema -----
        set_schema(cursor)
        loan = get_loan_detail(cursor, loan_no)
        cursor.close()
        conn.close()

        if not loan:
            return jsonify({'error': 'Loan not found'}), 404

        return jsonify({
            'loan_no': loan[0],
            'amount': loan[1],
            'interest_rate': loan[2],
            'tenure_months': loan[3],
            'purpose': loan[4],
            'application_date': loan[5],
            'approval_date': loan[6],
            'disbursement_date': loan[7],
            'loan_state': loan[8],
            'farmer_code': loan[9],
            'farmer_name': loan[10],
            'phone': loan[11],
            'nid': loan[12],
            'village': loan[13],
            'upazila': loan[14],
            'district': loan[15],
            'kyc_status': loan[16],
            'land_legal_status': loan[17],
            'credit_score': loan[18]
        })