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
                    agent_data['phone'] = row[5] or 'N/A'
                    agent_data['join_date'] = row[6].strftime('%d %b %Y') if row[6] else 'N/A'
                    agent_data['total_farmers'] = row[7] or 0
                    agent_data['kyc_done'] = row[8] or 0
                    agent_data['loans_approved'] = row[9] or 0
                    agent_data['pending_loans'] = row[10] or 0
                    agent_data['pending_deliveries'] = row[11] or 0
                
                if row and row[0]:
                    center_code = get_center_code(cursor, person_id)
                    if center_code:
                        agent_data['pending_kyc'] = get_pending_kyc_count(cursor, center_code) or 0
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
        
        if conn:
            cursor = conn.cursor()
            try:
                center_code = get_center_code(cursor, person_id)
                if center_code:
                    pending_loans_list = get_pending_loans(cursor, center_code)
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
            flash('Unauthorized', 'danger')
            return redirect(url_for('login_register'))

        farmer_code = request.form.get('farmer_code')
        nid_front = request.files.get('nid_front')
        nid_back = request.files.get('nid_back')
        land_doc = request.files.get('land_doc')
        land_legal_status = request.form.get('land_legal_status')
        remarks = request.form.get('remarks')

        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            nid_front_path = nid_front.filename if nid_front else None
            nid_back_path = nid_back.filename if nid_back else None
            land_doc_path = land_doc.filename if land_doc else None

            cursor.execute("""
                UPDATE KYC
                SET identity_verified = 'VERIFIED',
                    verified_by = (SELECT agent_code FROM FIELD_AGENT WHERE person_id = :1),
                    verified_date = SYSDATE,
                    remarks = :2,
                    nid_front_ref = :3,
                    nid_back_ref = :4,
                    land_dolil_ref = :5,
                    land_legal_status = :6
                WHERE farmer_code = :7
            """, (
                session['user']['person_id'],
                remarks,
                nid_front_path,
                nid_back_path,
                land_doc_path,
                land_legal_status,
                farmer_code
            ))
            conn.commit()
            cursor.close()
            conn.close()
            flash('KYC verified successfully!', 'success')
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
            cursor.execute("""
                UPDATE KYC
                SET identity_verified = 'REJECTED',
                    verified_by = (SELECT agent_code FROM FIELD_AGENT WHERE person_id = :1),
                    verified_date = SYSDATE
                WHERE farmer_code = :2
            """, (session['user']['person_id'], farmer_code))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': str(e)})