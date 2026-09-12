from flask import render_template, request, redirect, url_for, session, flash, jsonify
from db_connect import get_connection
from advisor_routes import add_notification
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
    get_farmer_detail,
    get_farmer_loans,
    get_farmer_repayments,
    get_farmer_purchases,
    get_community_posts,
    get_agent_ranking
)


def get_lang():
    return session.get('language', 'bn')


def get_flash_message(bn_msg, en_msg):
    return bn_msg if get_lang() == 'bn' else en_msg


def register_agent_routes(app):

    @app.route('/agent/dashboard')
    def agent_dashboard():
        if 'user' not in session or session['user']['role'] != 'AGENT':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))

        person_id = session['user']['person_id']
        user = session['user']
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
            'pending_deliveries': 0
        }
        my_farmers = []
        posts = []
        ranking = []
        
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
                    if row[6]:
                        agent_data['join_date'] = str(row[6]).split()[0]
                    else:
                        agent_data['join_date'] = 'N/A'
                    agent_data['total_farmers'] = row[7] or 0
                    agent_data['kyc_done'] = row[8] or 0
                    agent_data['loans_approved'] = row[9] or 0
                    agent_data['pending_loans'] = row[10] or 0
                    agent_data['pending_deliveries'] = row[11] or 0
                
                if row and row[0]:
                    center_code = get_center_code(cursor, person_id)
                    agent_data['pending_kyc'] = get_pending_kyc_count(cursor, center_code, person_id) or 0
                    my_farmers = get_my_farmers(cursor, person_id)
                    posts = get_community_posts(cursor)
                    ranking = get_agent_ranking(cursor)
                
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
                              ranking=ranking)


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
                pending_kyc_list = get_pending_kyc(cursor, center_code, person_id)
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
        
        if conn:
            cursor = conn.cursor()
            try:
                center_code = get_center_code(cursor, person_id)
                pending_loans_list = get_pending_loans(cursor, center_code, person_id)
                cursor.close()
                conn.close()
            except Exception as e:
                cursor.close()
                conn.close()
                print(f"Loan requests error: {e}")
        
        return render_template('agent/agent_loan_requests.html', 
                              user=session['user'], 
                              pending_loans=pending_loans_list,
                              center_code=center_code)


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
        
        print(f"=== DEBUG: farmer_code = {farmer_code} ===")
        
        conn = get_connection()
        farmer = None
        loans = []
        repayments = []
        purchases = []
        
        if conn:
            cursor = conn.cursor()
            try:
                farmer = get_farmer_detail(cursor, farmer_code)
                print(f"=== DEBUG: farmer = {farmer} ===")
                
                if farmer:
                    loans = get_farmer_loans(cursor, farmer_code)
                    repayments = get_farmer_repayments(cursor, farmer_code)
                    purchases = get_farmer_purchases(cursor, farmer_code)
                    print(f"=== DEBUG: loans = {len(loans)}, repayments = {len(repayments)}, purchases = {len(purchases)} ===")
                else:
                    print(f"=== DEBUG: Farmer {farmer_code} not found in database ===")
                cursor.close()
                conn.close()
            except Exception as e:
                cursor.close()
                conn.close()
                print(f"Farmer detail error: {e}")
        else:
            print("=== DEBUG: Database connection failed ===")
        
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
        center_code = None
        
        if conn:
            cursor = conn.cursor()
            try:
                center_code = get_center_code(cursor, person_id)
                if center_code:
                    purchases_list = get_pending_purchases(cursor, center_code)
                cursor.close()
                conn.close()
            except Exception as e:
                cursor.close()
                conn.close()
                print(f"Purchases error: {e}")
        
        return render_template('agent/agent_purchases.html', 
                              user=session['user'], 
                              purchases=purchases_list,
                              center_code=center_code)


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


    @app.route('/agent/outreach')
    def agent_outreach():
        if 'user' not in session or session['user']['role'] != 'AGENT':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))
        
        person_id = session['user']['person_id']
        conn = get_connection()
        outreach_list = []
        center_code = None
        
        if conn:
            cursor = conn.cursor()
            try:
                center_code = get_center_code(cursor, person_id)
                if center_code:
                    outreach_list = get_outreach_farmers(cursor, center_code)
                cursor.close()
                conn.close()
            except Exception as e:
                cursor.close()
                conn.close()
                print(f"Outreach error: {e}")
        
        return render_template('agent/agent_outreach.html', 
                              user=session['user'], 
                              outreach=outreach_list,
                              center_code=center_code)


    @app.route('/agent/verify-kyc', methods=['POST'])
    def agent_verify_kyc():
        if 'user' not in session or session['user']['role'] != 'AGENT':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))

        farmer_code = request.form.get('farmer_code')
        nid_front = request.files.get('nid_front')
        nid_back = request.files.get('nid_back')
        land_doc = request.files.get('land_doc')
        land_legal_status = request.form.get('land_legal_status', 'VERIFIED')
        remarks = request.form.get('remarks', 'Field Officer Verified')

        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            nid_front_path = nid_front.filename if (nid_front and nid_front.filename) else 'nid_front_verified.jpg'
            nid_back_path = nid_back.filename if (nid_back and nid_back.filename) else 'nid_back_verified.jpg'
            land_doc_path = land_doc.filename if (land_doc and land_doc.filename) else 'land_doc_verified.pdf'

            cursor.execute("SELECT agent_code FROM FIELD_AGENT WHERE person_id = ?", (session['user']['person_id'],))
            agent_row = cursor.fetchone()
            agent_code = agent_row[0] if agent_row else 2001

            cursor.execute("SELECT kyc_id FROM KYC WHERE farmer_code = ?", (farmer_code,))
            kyc_row = cursor.fetchone()

            if kyc_row:
                cursor.execute("""
                    UPDATE KYC
                    SET identity_verified = 'VERIFIED',
                        agent_code = ?,
                        verification_date = datetime('now')
                    WHERE farmer_code = ?
                """, (
                    agent_code,
                    farmer_code
                ))
            else:
                cursor.execute("""
                    INSERT INTO KYC (farmer_code, agent_code, identity_verified, verification_date)
                    VALUES (?, ?, 'VERIFIED', datetime('now'))
                """, (
                    farmer_code,
                    agent_code
                ))

            # Send Notification to Farmer
            cursor.execute("SELECT person_id FROM FARMER WHERE farmer_code = ?", (farmer_code,))
            f_row = cursor.fetchone()
            if f_row and f_row[0]:
                add_notification(
                    cursor,
                    f_row[0],
                    "✅ কেওয়াইসি ভেরিফিকেশন সম্পন্ন! / KYC Verified!",
                    "আপনার জাতীয় পরিচয়পত্র ও আবাদি জমির দলিল মাঠ কর্মকর্তা দ্বারা সফলভাবে যাচাই করা হয়েছে। আপনি এখন কৃষি ঋণ ও অন্যান্য সকল সেবার জন্য অনুমোদিত।",
                    url_for('dashboard')
                )

            conn.commit()
            cursor.close()
            conn.close()
            flash(get_flash_message('কেওয়াইসি সফলভাবে যাচাই ও সম্পন্ন করা হয়েছে!', 'KYC verified and approved successfully!'), 'success')
        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            flash('Error verifying KYC: ' + str(e), 'danger')

        return redirect(url_for('agent_kyc_requests'))


    @app.route('/agent/reject-kyc', methods=['POST'])
    def agent_reject_kyc():
        if 'user' not in session or session['user']['role'] != 'AGENT':
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401

        farmer_code = request.form.get('farmer_code')
        
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT agent_code FROM FIELD_AGENT WHERE person_id = ?", (session['user']['person_id'],))
            agent_row = cursor.fetchone()
            agent_code = agent_row[0] if agent_row else 2001

            cursor.execute("""
                UPDATE KYC
                SET identity_verified = 'REJECTED',
                    agent_code = ?,
                    verification_date = datetime('now')
                WHERE farmer_code = ?
            """, (agent_code, farmer_code))

            # Send notification to farmer
            cursor.execute("SELECT person_id FROM FARMER WHERE farmer_code = ?", (farmer_code,))
            f_row = cursor.fetchone()
            if f_row and f_row[0]:
                add_notification(
                    cursor,
                    f_row[0],
                    "❌ কেওয়াইসি প্রত্যাখ্যাত হয়েছে / KYC Verification Rejected",
                    "আপনার কেওয়াইসি তথ্যে অসঙ্গতি থাকায় তা বাতিল করা হয়েছে। সঠিক কাগজপত্র সহ ফিল্ড অফিসারের সাথে যোগাযোগ করুন।",
                    url_for('dashboard')
                )

            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': str(e)})


    @app.route('/agent/approve-loan', methods=['POST'])
    def agent_approve_loan():
        if 'user' not in session or session['user']['role'] != 'AGENT':
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401

        loan_no = request.form.get('loan_no')
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE LOAN SET loan_state = 'ACTIVE', approval_date = date('now') WHERE loan_no = ?", (loan_no,))
            cursor.execute("SELECT L.amount, F.person_id FROM LOAN L JOIN FARMER F ON L.farmer_code = F.farmer_code WHERE L.loan_no = ?", (loan_no,))
            row = cursor.fetchone()
            if row:
                amount, f_person_id = row
                add_notification(
                    cursor,
                    f_person_id,
                    "🎉 কৃষি ঋণ অনুমোদিত হয়েছে! / Krishi Loan Approved!",
                    f"আপনার ৳{amount} টাকার কৃষি ঋণ আবেদন মাঠ কর্মকর্তা কর্তৃক অনুমোদিত হয়েছে।",
                    url_for('dashboard')
                )
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': str(e)})


    @app.route('/agent/reject-loan', methods=['POST'])
    def agent_reject_loan():
        if 'user' not in session or session['user']['role'] != 'AGENT':
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401

        loan_no = request.form.get('loan_no')
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE LOAN SET loan_state = 'CANCELLED' WHERE loan_no = ?", (loan_no,))
            cursor.execute("SELECT L.amount, F.person_id FROM LOAN L JOIN FARMER F ON L.farmer_code = F.farmer_code WHERE L.loan_no = ?", (loan_no,))
            row = cursor.fetchone()
            if row:
                amount, f_person_id = row
                add_notification(
                    cursor,
                    f_person_id,
                    "❌ কৃষি ঋণ বাতিল করা হয়েছে / Krishi Loan Cancelled",
                    f"আপনার ৳{amount} টাকার কৃষি ঋণ আবেদন বাতিল করা হয়েছে।",
                    url_for('dashboard')
                )
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': str(e)})