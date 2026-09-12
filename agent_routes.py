from flask import render_template, request, redirect, url_for, session, flash, jsonify
from db_connect import get_connection
from agent_queries import (
    get_agent_code,
    get_center_code,
    get_agent_dashboard_data,
    get_my_farmers,
    get_pending_kyc_count,
    get_pending_kyc,
    get_pending_loans,
    get_agent_inventory,
    get_outreach_farmers,
    get_pending_purchases,
    get_order_detail,
    get_order_items,
    get_farmer_detail,
    get_farmer_loans,
    get_farmer_repayments,
    get_farmer_purchases,
    get_community_posts,
    get_agent_ranking,
    get_monthly_performance,
    get_followup_farmers,
    get_absorption_rate,
    get_risk_prediction,
    get_agent_verification_status,
    get_farmer_kyc_summary,
    get_agent_tasks,
)


def get_lang():
    return session.get('language', 'bn')


def get_flash_message(bn_msg, en_msg):
    return bn_msg if get_lang() == 'bn' else en_msg


def register_agent_routes(app):

    @app.route('/agent/verify-profile', methods=['GET', 'POST'])
    def agent_verify_profile():
        if 'user' not in session or session['user']['role'] != 'AGENT':
            return redirect(url_for('login_register'))

        person_id = session['user']['person_id']

        if request.method == 'POST':
            entered_agent_code = request.form.get('agent_code')
            phone = request.form.get('phone', '')
            village = request.form.get('village', '')
            upazila = request.form.get('upazila', '')
            district = request.form.get('district', '')

            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT agent_code FROM FIELD_AGENT WHERE person_id = :1", (person_id,))
                row = cursor.fetchone()

                if not row or row[0] != entered_agent_code:
                    flash('Invalid Agent Code. Please check and try again.', 'danger')
                    return redirect(url_for('agent_verify_profile'))

                cursor.execute("""
                    UPDATE PERSON
                    SET login_phone = :1, village = :2, upazila = :3, district = :4
                    WHERE person_id = :5
                """, (phone, village, upazila, district, person_id))

                cursor.execute("""
                    UPDATE FIELD_AGENT
                    SET verification_status = 'VERIFIED', verified_date = SYSDATE
                    WHERE person_id = :1
                """, (person_id,))

                conn.commit()
                flash('Agent profile verified successfully!', 'success')
                return redirect(url_for('agent_dashboard'))
            except Exception as e:
                conn.rollback()
                flash(f'Error: {str(e)}', 'danger')
            finally:
                cursor.close()
                conn.close()

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.nid, p.login_phone, p.village, p.upazila, p.district, a.agent_code
            FROM PERSON p
            JOIN FIELD_AGENT a ON a.person_id = p.person_id
            WHERE p.person_id = :1
        """, (person_id,))
        profile = cursor.fetchone()
        cursor.close()
        conn.close()

        return render_template('agent/agent_verify_profile.html',
                               user=session['user'],
                               profile=profile)


    @app.route('/agent/dashboard')
    def agent_dashboard():
        if 'user' not in session or session['user']['role'] != 'AGENT':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))

        person_id = session['user']['person_id']
        user = session['user']

        conn_check = get_connection()
        cursor_check = conn_check.cursor()
        v_status = get_agent_verification_status(cursor_check, person_id)
        cursor_check.close()
        conn_check.close()

        conn = get_connection()

        agent_data = {
            'total_farmers': 0,
            'kyc_done': 0,
            'pending_kyc': 0,
            'pending_loans': 0,
            'loans_approved': 0,
            'center_name': None,
            'upazila': None,
            'district': None,
            'agent_code': None,
            'phone': None,
            'join_date': None,
            'pending_deliveries': 0,
            'performance_score': 0,
        }
        my_farmers = []
        posts = []
        ranking = []
        monthly_performance = []
        followup_farmers = []
        absorption_rate = []
        risk_prediction = []
        tasks = []

        if conn:
            cursor = conn.cursor()
            try:
                row = get_agent_dashboard_data(cursor, person_id)

                if row:
                    agent_data['agent_code'] = row[0]
                    agent_data['center_name'] = row[1] or 'Not Assigned'
                    agent_data['upazila'] = row[2] or 'N/A'
                    agent_data['district'] = row[3] or 'N/A'
                    agent_data['working_status'] = row[4]
                    agent_data['phone'] = row[5] or 'N/A'
                    agent_data['join_date'] = row[6].strftime('%d %b %Y') if row[6] else 'N/A'
                    agent_data['total_farmers'] = row[7] or 0
                    agent_data['kyc_done'] = row[8] or 0
                    agent_data['loans_approved'] = row[9] or 0
                    agent_data['pending_loans'] = row[10] or 0
                    agent_data['pending_deliveries'] = row[11] or 0
                    agent_data['performance_score'] = row[12] or 0

                if row and row[0]:
                    center_code = get_center_code(cursor, person_id)
                    if center_code:
                        agent_data['pending_kyc'] = get_pending_kyc_count(cursor, center_code) or 0
                    my_farmers = get_my_farmers(cursor, person_id)
                    posts = get_community_posts(cursor)
                    ranking = get_agent_ranking(cursor)
                    monthly_performance = get_monthly_performance(cursor, person_id)
                    followup_farmers = get_followup_farmers(cursor, person_id)
                    absorption_rate = get_absorption_rate(cursor, person_id)
                    risk_prediction = get_risk_prediction(cursor, person_id)
                    tasks = get_agent_tasks(cursor, person_id)

                cursor.close()
                conn.close()
            except Exception as e:
                cursor.close()
                conn.close()
                print(f"Agent dashboard error: {e}")

        return render_template('dashboard_agent.html',
                               user=user,
                               agent_data=agent_data,
                               my_farmers=my_farmers,
                               posts=posts,
                               ranking=ranking,
                               monthly_performance=monthly_performance,
                               followup_farmers=followup_farmers,
                               absorption_rate=absorption_rate,
                               risk_prediction=risk_prediction,
                               v_status=v_status,
                               tasks=tasks)


    @app.route('/agent/kyc-requests')
    def agent_kyc_requests():
        if 'user' not in session or session['user']['role'] != 'AGENT':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))

        person_id = session['user']['person_id']
        conn = get_connection()
        pending_kyc_list = []
        center_code = None

        if conn:
            cursor = conn.cursor()
            try:
                center_code = get_center_code(cursor, person_id)
                if center_code:
                    pending_kyc_list = get_pending_kyc(cursor, center_code)
                cursor.close()
                conn.close()
            except Exception as e:
                cursor.close()
                conn.close()
                print(f"KYC requests error: {e}")

        return render_template('agent/agent_kyc_requests.html',
                               user=session['user'],
                               pending_kyc=pending_kyc_list,
                               center_code=center_code)


    @app.route('/agent/loan-requests')
    def agent_loan_requests():
        if 'user' not in session or session['user']['role'] != 'AGENT':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))

        person_id = session['user']['person_id']
        conn = get_connection()
        pending_loans_list = []
        center_code = None
        current_agent_code = None

        if conn:
            cursor = conn.cursor()
            try:
                center_code = get_center_code(cursor, person_id)
                current_agent_code = get_agent_code(cursor, person_id)
                if center_code:
                    pending_loans_list = get_pending_loans(cursor, center_code, current_agent_code)
                cursor.close()
                conn.close()
            except Exception as e:
                cursor.close()
                conn.close()
                print(f"Loan requests error: {e}")

        return render_template('agent/agent_loan_requests.html',
                               user=session['user'],
                               pending_loans=pending_loans_list,
                               center_code=center_code,
                               current_agent_code=current_agent_code)


    @app.route('/agent/claim-loan/<loan_no>', methods=['POST'])
    def agent_claim_loan(loan_no):
        if 'user' not in session or session['user']['role'] != 'AGENT':
            flash('Unauthorized', 'danger')
            return redirect(url_for('login_register'))

        person_id = session['user']['person_id']
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT agent_code FROM FIELD_AGENT WHERE person_id = :1", (person_id,))
            row = cursor.fetchone()
            agent_code = row[0] if row else None

            if not agent_code:
                flash('Agent profile not found.', 'danger')
                return redirect(url_for('agent_loan_requests'))

            cursor.execute("SELECT farmer_code FROM LOAN WHERE loan_no = :1", (loan_no,))
            loan_row = cursor.fetchone()
            if not loan_row:
                flash('Loan not found.', 'danger')
                return redirect(url_for('agent_loan_requests'))

            farmer_code = loan_row[0]

            cursor.execute("""
                UPDATE FARMER SET agent_code = :1
                WHERE farmer_code = :2 AND agent_code IS NULL
            """, (agent_code, farmer_code))
            conn.commit()

            if cursor.rowcount > 0:
                flash(f'Loan {loan_no} is now assigned to you.', 'success')
            else:
                flash('This loan is already handled by another agent.', 'warning')

        except Exception as e:
            conn.rollback()
            flash(f'Error claiming loan: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('agent_loan_requests'))


    @app.route('/agent/farmers')
    def agent_farmers():
        if 'user' not in session or session['user']['role'] != 'AGENT':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))

        person_id = session['user']['person_id']
        conn = get_connection()
        farmers_list = []

        if conn:
            cursor = conn.cursor()
            try:
                farmers_list = get_my_farmers(cursor, person_id)
                cursor.close()
                conn.close()
            except Exception as e:
                cursor.close()
                conn.close()
                print(f"Farmers list error: {e}")

        return render_template('agent/agent_farmers.html',
                               user=session['user'],
                               farmers=farmers_list)


    @app.route('/agent/farmer/<farmer_code>')
    def agent_farmer_detail(farmer_code):
        if 'user' not in session or session['user']['role'] != 'AGENT':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))

        conn = get_connection()
        farmer = None
        loans = []
        repayments = []
        purchases = []

        if conn:
            cursor = conn.cursor()
            try:
                farmer = get_farmer_detail(cursor, farmer_code)
                if farmer:
                    loans = get_farmer_loans(cursor, farmer_code)
                    repayments = get_farmer_repayments(cursor, farmer_code)
                    purchases = get_farmer_purchases(cursor, farmer_code)
                cursor.close()
                conn.close()
            except Exception as e:
                cursor.close()
                conn.close()
                print(f"Farmer detail error: {e}")

        if not farmer:
            flash(get_flash_message('কৃষক পাওয়া যায়নি।', 'Farmer not found.'), 'danger')
            return redirect(url_for('agent_farmers'))

        return render_template('agent/agent_farmer_detail.html',
                               user=session['user'],
                               farmer=farmer,
                               loans=loans,
                               repayments=repayments,
                               purchases=purchases)


    @app.route('/agent/purchases')
    def agent_purchases():
        if 'user' not in session or session['user']['role'] != 'AGENT':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))

        person_id = session['user']['person_id']
        conn = get_connection()
        purchases_list = []

        if conn:
            cursor = conn.cursor()
            try:
                purchases_list = get_pending_purchases(cursor, person_id)
                cursor.close()
                conn.close()
            except Exception as e:
                cursor.close()
                conn.close()
                print(f"Purchases error: {e}")

        return render_template('agent/agent_purchases.html',
                               user=session['user'],
                               purchases=purchases_list)


    @app.route('/agent/order/<purchase_id>')
    def agent_order_detail(purchase_id):
        if 'user' not in session or session['user']['role'] != 'AGENT':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))

        person_id = session['user']['person_id']
        conn = get_connection()
        order = None
        items = []

        if conn:
            cursor = conn.cursor()
            try:
                order = get_order_detail(cursor, purchase_id, person_id)
                if order:
                    items = get_order_items(cursor, purchase_id)
                cursor.close()
                conn.close()
            except Exception as e:
                cursor.close()
                conn.close()
                print(f"Order detail error: {e}")

        if not order:
            flash('Order not found or not assigned to you.', 'danger')
            return redirect(url_for('agent_purchases'))

        total = sum(item[5] for item in items) if items else 0

        payment_labels = {
            'CASH': 'Cash on Delivery',
            'LOAN_DEDUCTION': 'Deducted from Loan',
            'MOBILE_BANKING': 'Mobile Banking (Prepaid)',
            'BANK_TRANSFER': 'Bank Transfer (Prepaid)',
        }
        payment_label = payment_labels.get(order[8], order[8])

        collect_amount = total if order[8] == 'CASH' else 0

        return render_template('agent/agent_order_detail.html',
                               user=session['user'],
                               order=order,
                               items=items,
                               total=total,
                               payment_label=payment_label,
                               collect_amount=collect_amount)


    @app.route('/agent/order/<purchase_id>/mark-shipped', methods=['POST'])
    def agent_mark_shipped(purchase_id):
        if 'user' not in session or session['user']['role'] != 'AGENT':
            flash('Unauthorized', 'danger')
            return redirect(url_for('login_register'))

        person_id = session['user']['person_id']
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE PURCHASE
                SET payment_status = 'SHIPPED'
                WHERE purchase_id = :1
                  AND payment_status = 'CONFIRMED'
                  AND agent_code = (SELECT agent_code FROM FIELD_AGENT WHERE person_id = :2)
            """, (purchase_id, person_id))
            conn.commit()
            flash('Marked as on the way!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('agent_order_detail', purchase_id=purchase_id))


    @app.route('/agent/order/<purchase_id>/mark-delivered', methods=['POST'])
    def agent_mark_delivered(purchase_id):
        if 'user' not in session or session['user']['role'] != 'AGENT':
            flash('Unauthorized', 'danger')
            return redirect(url_for('login_register'))

        person_id = session['user']['person_id']
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE PURCHASE
                SET payment_status = 'DELIVERED'
                WHERE purchase_id = :1
                  AND payment_status IN ('CONFIRMED', 'SHIPPED')
                  AND agent_code = (SELECT agent_code FROM FIELD_AGENT WHERE person_id = :2)
            """, (purchase_id, person_id))
            conn.commit()
            flash('Order delivered successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('agent_purchases'))


    @app.route('/agent/inventory')
    def agent_inventory():
        if 'user' not in session or session['user']['role'] != 'AGENT':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))

        person_id = session['user']['person_id']
        conn = get_connection()
        inventory_list = []
        center_code = None

        if conn:
            cursor = conn.cursor()
            try:
                center_code = get_center_code(cursor, person_id)
                if center_code:
                    inventory_list = get_agent_inventory(cursor, center_code)
                cursor.close()
                conn.close()
            except Exception as e:
                cursor.close()
                conn.close()
                print(f"Inventory error: {e}")

        return render_template('agent/agent_inventory.html',
                               user=session['user'],
                               inventory=inventory_list,
                               center_code=center_code)


    @app.route('/agent/promote')
    def agent_promote():
        if 'user' not in session or session['user']['role'] != 'AGENT':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))

        person_id = session['user']['person_id']
        conn = get_connection()
        my_farmers = []
        outreach_list = []
        center_code = None

        if conn:
            cursor = conn.cursor()
            try:
                center_code = get_center_code(cursor, person_id)
                my_farmers = get_my_farmers(cursor, person_id)
                if center_code:
                    outreach_list = get_outreach_farmers(cursor, center_code)
                cursor.close()
                conn.close()
            except Exception as e:
                cursor.close()
                conn.close()
                print(f"Promote error: {e}")

        return render_template('agent/agent_promote.html',
                               user=session['user'],
                               my_farmers=my_farmers,
                               outreach=outreach_list,
                               center_code=center_code)


    @app.route('/agent/verify-kyc', methods=['POST'])
    def agent_verify_kyc():
        if 'user' not in session or session['user']['role'] != 'AGENT':
            flash('Unauthorized', 'danger')
            return redirect(url_for('login_register'))

        farmer_code = request.form.get('farmer_code')
        nid_front = request.files.get('nid_front')
        nid_back = request.files.get('nid_back')
        land_doc = request.files.get('land_doc')
        land_legal_status = request.form.get('land_legal_status')
        nominee_name = request.form.get('nominee_name')
        nominee_relation = request.form.get('nominee_relation')
        nominee_nid = request.form.get('nominee_nid')
        nominee_phone = request.form.get('nominee_phone')
        remarks = request.form.get('remarks', '')

        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT agent_code FROM FIELD_AGENT WHERE person_id = :1",
                           (session['user']['person_id'],))
            agent_row = cursor.fetchone()
            agent_code = agent_row[0] if agent_row else None

            if not agent_code:
                flash('Agent profile not found.', 'danger')
                return redirect(url_for('agent_kyc_requests'))

            cursor.execute("SELECT IS_FARMER_KYC_VERIFIED(:1) FROM DUAL", (farmer_code,))
            already = cursor.fetchone()[0]
            if already == 'YES':
                flash('This farmer is already KYC verified.', 'warning')
                return redirect(url_for('agent_kyc_requests'))

            nid_front_path = nid_front.filename if nid_front else None
            nid_back_path = nid_back.filename if nid_back else None
            land_doc_path = land_doc.filename if land_doc else None

            cursor.execute("""
                UPDATE KYC
                SET nid_front_ref = :1,
                    nid_back_ref = :2,
                    land_dolil_ref = :3,
                    land_legal_status = :4,
                    nominee_name = :5,
                    nominee_relation = :6,
                    nominee_nid = :7,
                    nominee_phone = :8
                WHERE farmer_code = :9
            """, (nid_front_path, nid_back_path, land_doc_path, land_legal_status,
                  nominee_name, nominee_relation, nominee_nid, nominee_phone, farmer_code))
            conn.commit()

            can_verify = cursor.var(str)
            message = cursor.var(str)
            cursor.callproc('VALIDATE_KYC_FOR_VERIFY', (farmer_code, can_verify, message))

            if can_verify.getvalue() != 'YES':
                flash(message.getvalue(), 'danger')
                return redirect(url_for('agent_kyc_requests'))

            cursor.callproc('PROCESS_KYC_VERIFICATION',
                            (farmer_code, agent_code, 'VERIFY', remarks))

            flash(f'KYC verified. {message.getvalue()}', 'success')

        except Exception as e:
            conn.rollback()
            flash(f'Error verifying KYC: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('agent_kyc_requests'))


    @app.route('/agent/reject-kyc', methods=['POST'])
    def agent_reject_kyc():
        if 'user' not in session or session['user']['role'] != 'AGENT':
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401

        farmer_code = request.form.get('farmer_code')

        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT agent_code FROM FIELD_AGENT WHERE person_id = :1",
                           (session['user']['person_id'],))
            agent_row = cursor.fetchone()
            agent_code = agent_row[0] if agent_row else None

            if not agent_code:
                return jsonify({'success': False, 'message': 'Agent profile not found'})

            cursor.callproc('PROCESS_KYC_VERIFICATION',
                            (farmer_code, agent_code, 'REJECT', 'Rejected by agent'))
            return jsonify({'success': True})

        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'message': str(e)})
        finally:
            cursor.close()
            conn.close()


    @app.route('/agent/request-extension', methods=['POST'])
    def agent_request_extension():
        if 'user' not in session or session['user']['role'] != 'AGENT':
            flash('Unauthorized', 'danger')
            return redirect(url_for('login_register'))

        loan_no = request.form.get('loan_no')
        extra_months = request.form.get('extra_months')
        reason = request.form.get('reason')

        if not loan_no or not extra_months or not reason:
            flash('All fields are required.', 'danger')
            return redirect(url_for('agent_loan_requests'))

        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT agent_code FROM FIELD_AGENT WHERE person_id = :1",
                           (session['user']['person_id'],))
            agent_row = cursor.fetchone()
            agent_code = agent_row[0] if agent_row else None

            if not agent_code:
                flash('Agent profile not found.', 'danger')
                return redirect(url_for('agent_loan_requests'))

            cursor.callproc('REQUEST_LOAN_EXTENSION',
                            (loan_no, agent_code, int(extra_months), reason))
            flash('Extension request submitted successfully!', 'success')

        except Exception as e:
            conn.rollback()
            flash(f'Error requesting extension: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('agent_loan_requests'))


    @app.route('/agent/farmer-profile')
    def agent_farmer_profile():
        farmer_code = request.args.get('farmer_code')

        if not farmer_code:
            return render_template('agent/agent_farmer_profile.html',
                                   user=session['user'],
                                   farmer=None,
                                   kyc_summary=None)

        conn = get_connection()
        if not conn:
            flash('Database connection failed.', 'danger')
            return render_template('agent/agent_farmer_profile.html',
                                   user=session['user'],
                                   farmer=None,
                                   kyc_summary=None)

        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT 
                    farmer_code,
                    farmer_name,
                    credit_score,
                    kyc_status,
                    active_loans,
                    total_assets,
                    eligibility_status,
                    max_loan_amount,
                    risk_category,
                    kyc_doc
                FROM FARMER_ELIGIBILITY_VIEW
                WHERE farmer_code = :1
            """, (farmer_code,))
            row = cursor.fetchone()

            kyc_summary = None
            if row:
                kyc_summary = get_farmer_kyc_summary(cursor, farmer_code)

            cursor.close()
            conn.close()

            if not row:
                flash('Farmer not found. Please check the code.', 'danger')
                return render_template('agent/agent_farmer_profile.html',
                                       user=session['user'],
                                       farmer=None,
                                       kyc_summary=None)

            return render_template('agent/agent_farmer_profile.html',
                                   user=session['user'],
                                   farmer=row,
                                   kyc_summary=kyc_summary)

        except Exception as e:
            cursor.close()
            conn.close()
            flash(f'Error: {str(e)}', 'danger')
            return render_template('agent/agent_farmer_profile.html',
                                   user=session['user'],
                                   farmer=None,
                                   kyc_summary=None)