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
    get_center_list,
    search_farmers,
    search_loans,
    get_center_performance_report,
    get_kyc_summary_by_center,
    get_agent_activity_report,
    get_pending_loans_view,
    get_center_summary_view,
    get_center_loan_count_function,
    get_audit_log,
    list_all_farmers,
    list_all_agents,
    list_all_centers,
    list_all_inventory,
    list_all_banks,
    list_all_kyc,
)
import time
import os
from werkzeug.utils import secure_filename

SCHEMA = "KRISHIBANDHU"
UPLOAD_FOLDER = r'C:\Users\Mahina\Downloads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def set_schema(cursor):
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
        set_schema(cursor)

        admin_row = get_admin_info(cursor, person_id)

        admin_code = admin_row[0] if admin_row else 'N/A'
        center_code = admin_row[1] if admin_row else None
        center_name = admin_row[2] if admin_row and admin_row[2] else 'All Centers'
        is_super = admin_row[3] if admin_row and admin_row[3] else 'CENTER'
        supervisor_name = admin_row[5] if admin_row and admin_row[5] else 'None'

        pending_loans = get_pending_loans(cursor, center_code, is_super == 'SUPER')

        stats_row = get_admin_stats(cursor, center_code, is_super == 'SUPER')
        stats = {
            'total_farmers': stats_row[0] if stats_row else 0,
            'kyc_verified': stats_row[1] if stats_row else 0,
            'active_loans': stats_row[2] if stats_row else 0,
            'total_disbursed': stats_row[3] if stats_row else 0,
            'repayment_rate': stats_row[4] if stats_row else 0,
            'defaulted_amount': stats_row[5] if stats_row else 0
        }

        subordinates = get_subordinates(cursor, person_id, center_code, is_super == 'SUPER')
        posts = get_community_posts(cursor)
        inventory_alerts = get_inventory_alerts(cursor, center_code, is_super == 'SUPER')
        centers = get_center_list(cursor, is_super == 'SUPER', center_code)

        cursor.close()
        conn.close()

        admin_info = [admin_code, center_code, center_name, is_super, supervisor_name]

        return render_template('dashboard_admin.html',
                               user=session['user'],
                               admin_info=admin_info,
                               is_super=is_super,
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
        set_schema(cursor)
        try:
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

    @app.route('/admin/search')
    def admin_search():
        if 'user' not in session or session['user']['role'] != 'ADMIN':
            flash('Unauthorized.', 'danger')
            return redirect(url_for('login_register'))

        keyword = request.args.get('q', '').strip()
        search_type = request.args.get('type', 'farmer')
        results = []

        if keyword:
            conn = get_connection()
            cursor = conn.cursor()
            set_schema(cursor)
            try:
                if search_type == 'loan':
                    results = search_loans(cursor, keyword)
                else:
                    results = search_farmers(cursor, keyword)
                cursor.close()
                conn.close()
            except Exception as e:
                cursor.close()
                conn.close()
                flash(f'Search error: {str(e)}', 'danger')

        return render_template('admin/admin_search.html',
                               user=session['user'],
                               keyword=keyword,
                               search_type=search_type,
                               results=results)

    @app.route('/admin/reports')
    def admin_reports():
        if 'user' not in session or session['user']['role'] != 'ADMIN':
            flash('Unauthorized.', 'danger')
            return redirect(url_for('login_register'))

        conn = get_connection()
        cursor = conn.cursor()
        set_schema(cursor)
        center_perf = []
        kyc_summary = []
        agent_activity = []
        center_summary = []
        audit_log = []

        try:
            center_perf = get_center_performance_report(cursor)
        except Exception as e:
            print(f"Report 1 error: {e}")
            conn.rollback()

        try:
            kyc_summary = get_kyc_summary_by_center(cursor)
        except Exception as e:
            print(f"Report 2 error: {e}")
            conn.rollback()

        try:
            agent_activity = get_agent_activity_report(cursor)
        except Exception as e:
            print(f"Report 3 error: {e}")
            conn.rollback()

        try:
            center_summary = get_center_summary_view(cursor)
        except Exception as e:
            print(f"Report 4 error: {e}")
            conn.rollback()

        try:
            audit_log = get_audit_log(cursor, 30)
        except Exception as e:
            print(f"Report 5 error: {e}")
            conn.rollback()

        cursor.close()
        conn.close()

        return render_template('admin/admin_reports.html',
                               user=session['user'],
                               center_perf=center_perf,
                               kyc_summary=kyc_summary,
                               agent_activity=agent_activity,
                               center_summary=center_summary,
                               audit_log=audit_log)

    # ============================================
    # 6 QUICK ACCESS LIST PAGES
    # ============================================

    @app.route('/admin/farmers')
    def admin_farmers():
        if 'user' not in session or session['user']['role'] != 'ADMIN':
            return redirect(url_for('login_register'))
        conn = get_connection()
        cursor = conn.cursor()
        set_schema(cursor)
        rows = list_all_farmers(cursor)
        cursor.close()
        conn.close()
        return render_template('admin/admin_list.html',
                               user=session['user'],
                               page_title='All Farmers',
                               page_icon='fa-users',
                               page_color='success',
                               headers=['Code', 'Name', 'Phone', 'Location', 'KYC', 'Center'],
                               rows=rows)

    @app.route('/admin/agents')
    def admin_agents():
        if 'user' not in session or session['user']['role'] != 'ADMIN':
            return redirect(url_for('login_register'))
        conn = get_connection()
        cursor = conn.cursor()
        set_schema(cursor)
        rows = list_all_agents(cursor)
        cursor.close()
        conn.close()
        return render_template('admin/admin_list.html',
                               user=session['user'],
                               page_title='All Field Agents',
                               page_icon='fa-user-tie',
                               page_color='primary',
                               headers=['Code', 'Name', 'Phone', 'Center', 'Active', 'Farmers'],
                               rows=rows)

    @app.route('/admin/centers')
    def admin_centers():
        if 'user' not in session or session['user']['role'] != 'ADMIN':
            return redirect(url_for('login_register'))
        conn = get_connection()
        cursor = conn.cursor()
        set_schema(cursor)
        rows = list_all_centers(cursor)
        cursor.close()
        conn.close()
        return render_template('admin/admin_list.html',
                               user=session['user'],
                               page_title='All Centers',
                               page_icon='fa-building',
                               page_color='success',
                               headers=['Code', 'Name', 'District', 'Upazila', 'Phone', 'State', 'Farmers'],
                               rows=rows)

    @app.route('/admin/inventory')
    def admin_inventory():
        if 'user' not in session or session['user']['role'] != 'ADMIN':
            return redirect(url_for('login_register'))
        conn = get_connection()
        cursor = conn.cursor()
        set_schema(cursor)
        rows = list_all_inventory(cursor)
        cursor.close()
        conn.close()
        return render_template('admin/admin_list.html',
                               user=session['user'],
                               page_title='Inventory',
                               page_icon='fa-warehouse',
                               page_color='warning',
                               headers=['ID', 'Name', 'Quantity', 'Price', 'Unit', 'Center', 'Location', 'Manufacturer'],
                               rows=rows)

    @app.route('/admin/banks')
    def admin_banks():
        if 'user' not in session or session['user']['role'] != 'ADMIN':
            return redirect(url_for('login_register'))
        conn = get_connection()
        cursor = conn.cursor()
        set_schema(cursor)
        rows = list_all_banks(cursor)
        cursor.close()
        conn.close()
        return render_template('admin/admin_list.html',
                               user=session['user'],
                               page_title='Partner Banks',
                               page_icon='fa-university',
                               page_color='dark',
                               headers=['Code', 'Bank Name', 'Branch', 'Contact', 'Phone', 'Email', 'Max Loan', 'State'],
                               rows=rows)

    @app.route('/admin/kyc')
    def admin_kyc():
        if 'user' not in session or session['user']['role'] != 'ADMIN':
            return redirect(url_for('login_register'))
        conn = get_connection()
        cursor = conn.cursor()
        set_schema(cursor)
        rows = list_all_kyc(cursor)
        cursor.close()
        conn.close()
        return render_template('admin/admin_list.html',
                               user=session['user'],
                               page_title='KYC Records',
                               page_icon='fa-file-alt',
                               page_color='info',
                               headers=['KYC ID', 'Farmer Code', 'Name', 'Status', 'Land Status', 'Verified Date', 'Nominee', 'Relation'],
                               rows=rows)