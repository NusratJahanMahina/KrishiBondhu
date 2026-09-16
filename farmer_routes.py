from flask import render_template, request, redirect, url_for, session, flash, jsonify
from db_connect import get_connection
from farmer_queries import *
import random
import time
from datetime import datetime
import json

import uuid

def generate_id():
    """Generate a unique ID using UUID (avoids duplicate IDs)"""
    return str(uuid.uuid4().int)[:12]

def get_lang():
    return session.get('language', 'bn')

def get_flash_message(bn_msg, en_msg):
    return bn_msg if get_lang() == 'bn' else en_msg

def register_farmer_routes(app):

    @app.route('/farmer/dashboard')
    def farmer_dashboard():
        if 'user' not in session or session['user']['role'] != 'FARMER':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))

        person_id = session['user']['person_id']
        user = session['user']
        conn = get_connection()
        
        stats = (0, 0, 0, 'PENDING')
        activities = []
        farmer_code = None

        if conn:
            cursor = conn.cursor()
            try:
                farmer_code = get_farmer_code(cursor, person_id)
                if farmer_code:
                    stats = get_farmer_dashboard_stats(cursor, farmer_code)
                    activities = get_recent_activity(cursor, farmer_code)
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"Farmer dashboard error: {e}")
                if conn:
                    conn.close()

        return render_template('farmer/dashboard.html', 
                               user=user, 
                               stats=stats, 
                               activities=activities,
                               farmer_code=farmer_code,
                               active_tab='overview')

    @app.route('/farmer/loans')
    def farmer_loans():
        if 'user' not in session or session['user']['role'] != 'FARMER':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))
        
        person_id = session['user']['person_id']
        conn = get_connection()
        loans = []
        farmer_code = None
        loan_repayments = {}

        if conn:
            cursor = conn.cursor()
            try:
                farmer_code = get_farmer_code(cursor, person_id)
                if farmer_code:
                    loans = get_farmer_loans(cursor, farmer_code)
                    for loan in loans:
                        loan_no = loan[0]
                        repayments = get_loan_repayments(cursor, loan_no)
                        loan_repayments[loan_no] = repayments
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"Loans error: {e}")
                if conn:
                    conn.close()

        return render_template('farmer/loans.html', 
                              user=session['user'], 
                              loans=loans, 
                              farmer_code=farmer_code, 
                              active_tab='loans',
                              loan_repayments=loan_repayments)

    @app.route('/farmer/apply_loan', methods=['POST'])
    def apply_loan():
        if 'user' not in session or session['user']['role'] != 'FARMER':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))
        
        amount = request.form.get('amount')
        purpose = request.form.get('purpose')
        tenure = request.form.get('tenure_months')
        
        if not amount or not purpose or not tenure:
            flash(get_flash_message('সব ফিল্ড পূরণ করুন।', 'Please fill all fields.'), 'danger')
            return redirect(url_for('farmer_loans'))
        
        try:
            amount = float(amount)
            tenure = int(tenure)
            if amount < 500 or amount > 200000:
                flash(get_flash_message('ঋণের পরিমাণ ৫০০ থেকে ২,০০,০০০ টাকার মধ্যে হতে হবে।', 
                      'Loan amount must be between 500 and 200,000 BDT.'), 'danger')
                return redirect(url_for('farmer_loans'))
            if tenure < 1 or tenure > 24:
                flash(get_flash_message('মেয়াদ ১ থেকে ২৪ মাসের মধ্যে হতে হবে।', 
                      'Tenure must be between 1 and 24 months.'), 'danger')
                return redirect(url_for('farmer_loans'))
        except ValueError:
            flash(get_flash_message('অবৈধ পরিমাণ বা মেয়াদ।', 'Invalid amount or tenure.'), 'danger')
            return redirect(url_for('farmer_loans'))
        
        conn = get_connection()
        if conn:
            cursor = conn.cursor()
            try:
                farmer_code = get_farmer_code(cursor, session['user']['person_id'])
                if not farmer_code:
                    flash(get_flash_message('কৃষক কোড পাওয়া যায়নি।', 'Farmer code not found.'), 'danger')
                    return redirect(url_for('farmer_loans'))
                
                cursor.execute("SELECT center_code, agent_code FROM FARMER WHERE farmer_code = :1", (farmer_code,))
                farmer_data = cursor.fetchone()
                
                if not farmer_data or not farmer_data[0]:
                    flash(get_flash_message('সেন্টার তথ্য পাওয়া যায়নি।', 'Center info not found.'), 'danger')
                    return redirect(url_for('farmer_loans'))
                
                cursor.execute("SELECT bank_code FROM BANK WHERE bank_state='ACTIVE' AND ROWNUM=1")
                bank_data = cursor.fetchone()
                if not bank_data:
                    flash(get_flash_message('কোন সক্রিয় ব্যাংক পাওয়া যায়নি।', 'No active bank found.'), 'danger')
                    return redirect(url_for('farmer_loans'))
                
                loan_no = 'LN-' + str(generate_id())[:8]
                cursor.execute("""
                    INSERT INTO LOAN (loan_no, farmer_code, center_code, bank_code, amount, tenure_months, purpose, loan_state, application_date)
                    VALUES (:1, :2, :3, :4, :5, :6, :7, 'PENDING', SYSDATE)
                """, (loan_no, farmer_code, farmer_data[0], bank_data[0], amount, tenure, purpose))
                conn.commit()
                
                activity_id = 'ACT-' + str(generate_id())[:8]
                cursor.execute("""
                    INSERT INTO ACTIVITY_RECORD (activity_id, farmer_code, activity_type, description, activity_date, reference_id)
                    VALUES (:1, :2, 'LOAN_APPLICATION', :3, SYSDATE, :4)
                """, (activity_id, farmer_code, f'Applied for loan of {amount} BDT for {purpose}', loan_no))
                conn.commit()
                
                flash(get_flash_message('ঋণ আবেদন সফল হয়েছে!', 'Loan application submitted successfully!'), 'success')
            except Exception as e:
                conn.rollback()
                flash(get_flash_message('ত্রুটি: ' + str(e), 'Error: ' + str(e)), 'danger')
                print(f"Apply loan error: {e}")
            finally:
                cursor.close()
                conn.close()
        return redirect(url_for('farmer_loans'))

    @app.route('/farmer/loans/<loan_no>/repayments')
    def farmer_loan_repayments(loan_no):
        if 'user' not in session or session['user']['role'] != 'FARMER':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))
        
        conn = get_connection()
        repayments = []
        if conn:
            cursor = conn.cursor()
            try:
                repayments = get_loan_repayments(cursor, loan_no)
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"Repayments error: {e}")
                if conn:
                    conn.close()
        
        return render_template('farmer_loan_detail.html', 
                              repayments=repayments, 
                              loan_no=loan_no,
                              user=session['user'])

    @app.route('/farmer/assets')
    def farmer_assets():
        if 'user' not in session or session['user']['role'] != 'FARMER':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))
        
        person_id = session['user']['person_id']
        conn = get_connection()
        assets = []
        farmer_code = None

        if conn:
            cursor = conn.cursor()
            try:
                farmer_code = get_farmer_code(cursor, person_id)
                if farmer_code:
                    assets = get_farmer_assets(cursor, farmer_code)
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"Assets error: {e}")
                if conn:
                    conn.close()

        return render_template('farmer/assets.html', 
                              user=session['user'], 
                              assets=assets,
                              farmer_code=farmer_code,
                              active_tab='assets')

    @app.route('/farmer/add_asset', methods=['POST'])
    def add_asset():
        if 'user' not in session or session['user']['role'] != 'FARMER':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))
        
        asset_type = request.form.get('asset_type')
        asset_name = request.form.get('asset_name')
        quantity = request.form.get('quantity', 1)
        unit = request.form.get('unit', '')
        acquisition_date = request.form.get('acquisition_date')
        expected_completion_date = request.form.get('expected_completion_date')
        revenue_generated = request.form.get('revenue_generated', 0)
        total_expense = request.form.get('total_expense', 0)
        
        if not asset_type or not asset_name:
            flash(get_flash_message('সম্পদের ধরন এবং নাম প্রয়োজন।', 'Asset type and name are required.'), 'danger')
            return redirect(url_for('farmer_assets'))
        
        valid_types = ['LAND', 'LIVESTOCK', 'EQUIPMENT', 'POULTRY', 'AQUACULTURE', 'VEHICLE', 'OTHER']
        if asset_type not in valid_types:
            flash(get_flash_message('অবৈধ সম্পদের ধরন।', 'Invalid asset type.'), 'danger')
            return redirect(url_for('farmer_assets'))
        
        try:
            quantity = int(quantity) if quantity else 1
            revenue_generated = float(revenue_generated) if revenue_generated else 0
            total_expense = float(total_expense) if total_expense else 0
        except ValueError:
            flash(get_flash_message('অবৈধ সংখ্যাসূচক মান।', 'Invalid numeric values.'), 'danger')
            return redirect(url_for('farmer_assets'))
        
        conn = get_connection()
        if conn:
            cursor = conn.cursor()
            try:
                farmer_code = get_farmer_code(cursor, session['user']['person_id'])
                if not farmer_code:
                    flash(get_flash_message('কৃষক কোড পাওয়া যায়নি।', 'Farmer code not found.'), 'danger')
                    return redirect(url_for('farmer_assets'))
                
                asset_id = 'AST-' + str(generate_id())[:8]
                cursor.execute("""
                    INSERT INTO ASSET (asset_id, farmer_code, asset_type, asset_name, quantity, unit, 
                                       acquisition_date, expected_completion_date, revenue_generated, total_expense, asset_status)
                    VALUES (:1, :2, :3, :4, :5, :6, TO_DATE(:7, 'YYYY-MM-DD'), 
                            TO_DATE(:8, 'YYYY-MM-DD'), :9, :10, 'ACTIVE')
                """, (asset_id, farmer_code, asset_type, asset_name, quantity, unit, 
                      acquisition_date or datetime.now().strftime('%Y-%m-%d'), 
                      expected_completion_date, revenue_generated, total_expense))
                conn.commit()
                flash(get_flash_message('সম্পদ সফলভাবে যোগ করা হয়েছে!', 'Asset added successfully!'), 'success')
            except Exception as e:
                conn.rollback()
                flash(get_flash_message('ত্রুটি: ' + str(e), 'Error: ' + str(e)), 'danger')
                print(f"Add asset error: {e}")
            finally:
                cursor.close()
                conn.close()
        return redirect(url_for('farmer_assets'))

    @app.route('/farmer/repayments')
    def farmer_repayments():
        if 'user' not in session or session['user']['role'] != 'FARMER':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))
        
        person_id = session['user']['person_id']
        conn = get_connection()
        repayments = []
        farmer_code = None
        loans = []

        if conn:
            cursor = conn.cursor()
            try:
                farmer_code = get_farmer_code(cursor, person_id)
                if farmer_code:
                    repayments = get_all_farmer_repayments(cursor, farmer_code)
                    loans = get_farmer_loans(cursor, farmer_code)
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"Repayments error: {e}")
                if conn:
                    conn.close()

        return render_template('farmer/repayments.html', 
                              user=session['user'], 
                              repayments=repayments,
                              loans=loans,
                              farmer_code=farmer_code,
                              active_tab='repayments')

    @app.route('/farmer/make_payment', methods=['POST'])
    def make_payment():
        if 'user' not in session or session['user']['role'] != 'FARMER':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))
        
        loan_no = request.form.get('loan_no')
        amount = request.form.get('amount')
        payment_method = request.form.get('payment_method', 'CASH')
        
        if not loan_no or not amount:
            flash(get_flash_message('ঋণ এবং পরিমাণ প্রয়োজন।', 'Loan and amount are required.'), 'danger')
            return redirect(url_for('farmer_repayments'))
        
        try:
            amount = float(amount)
            if amount <= 0:
                flash(get_flash_message('পরিমাণ অবশ্যই ০ এর বেশি হতে হবে।', 'Amount must be greater than 0.'), 'danger')
                return redirect(url_for('farmer_repayments'))
        except ValueError:
            flash(get_flash_message('অবৈধ পরিমাণ।', 'Invalid amount.'), 'danger')
            return redirect(url_for('farmer_repayments'))
        
        conn = get_connection()
        if conn:
            cursor = conn.cursor()
            try:
                farmer_code = get_farmer_code(cursor, session['user']['person_id'])
                if not farmer_code:
                    flash(get_flash_message('কৃষক কোড পাওয়া যায়নি।', 'Farmer code not found.'), 'danger')
                    return redirect(url_for('farmer_repayments'))
                
                cursor.execute("SELECT COUNT(*) FROM LOAN WHERE loan_no = :1 AND farmer_code = :2", 
                              (loan_no, farmer_code))
                if cursor.fetchone()[0] == 0:
                    flash(get_flash_message('এই ঋণটি আপনার নয়।', 'This loan does not belong to you.'), 'danger')
                    return redirect(url_for('farmer_repayments'))
                
                cursor.execute("SELECT NVL(MAX(installment_no), 0) + 1 FROM REPAYMENT WHERE loan_no = :1", (loan_no,))
                installment_no = cursor.fetchone()[0]
                
                cursor.execute("""
                    INSERT INTO REPAYMENT (loan_no, installment_no, amount_paid, payment_date, payment_method, payment_state)
                    VALUES (:1, :2, :3, SYSDATE, :4, 'PAID')
                """, (loan_no, installment_no, amount, payment_method))
                conn.commit()
                
                activity_id = 'ACT-' + str(generate_id())[:8]
                cursor.execute("""
                    INSERT INTO ACTIVITY_RECORD (activity_id, farmer_code, activity_type, description, activity_date, reference_id)
                    VALUES (:1, :2, 'REPAYMENT', :3, SYSDATE, :4)
                """, (activity_id, farmer_code, f'Paid installment {installment_no} of {amount} BDT for loan {loan_no}', loan_no))
                conn.commit()
                
                flash(get_flash_message('পেমেন্ট সফল হয়েছে!', 'Payment successful!'), 'success')
            except Exception as e:
                conn.rollback()
                flash(get_flash_message('ত্রুটি: ' + str(e), 'Error: ' + str(e)), 'danger')
                print(f"Make payment error: {e}")
            finally:
                cursor.close()
                conn.close()
        return redirect(url_for('farmer_repayments'))

    @app.route('/farmer/consultations')
    def farmer_consultations():
        if 'user' not in session or session['user']['role'] != 'FARMER':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))
        
        person_id = session['user']['person_id']
        conn = get_connection()
        consultations = []
        farmer_code = None

        if conn:
            cursor = conn.cursor()
            try:
                farmer_code = get_farmer_code(cursor, person_id)
                if farmer_code:
                    consultations = get_farmer_consultations(cursor, farmer_code)
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"Consultations error: {e}")
                if conn:
                    conn.close()

        return render_template('farmer/consultations.html', 
                              user=session['user'], 
                              consultations=consultations,
                              farmer_code=farmer_code,
                              active_tab='consultations')

    @app.route('/farmer/request_consultation', methods=['POST'])
    def request_consultation():
        if 'user' not in session or session['user']['role'] != 'FARMER':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))
        
        topic = request.form.get('topic')
        scheduled_date = request.form.get('scheduled_date')
        notes = request.form.get('notes', '')
        
        if not topic or not scheduled_date:
            flash(get_flash_message('বিষয় এবং তারিখ প্রয়োজন।', 'Topic and date are required.'), 'danger')
            return redirect(url_for('farmer_consultations'))
        
        conn = get_connection()
        if conn:
            cursor = conn.cursor()
            try:
                farmer_code = get_farmer_code(cursor, session['user']['person_id'])
                if not farmer_code:
                    flash(get_flash_message('কৃষক কোড পাওয়া যায়নি।', 'Farmer code not found.'), 'danger')
                    return redirect(url_for('farmer_consultations'))
                
                session_id = 'CON-' + str(generate_id())[:8]
                cursor.execute("INSERT INTO CONSULTATION (session_id, topic) VALUES (:1, :2)", (session_id, topic))
                conn.commit()
                
                advisor_id = 1004
                cursor.execute("""
                    INSERT INTO ATTENDS (advisor_id, farmer_code, session_id, scheduled_date, notes, resolution_status)
                    VALUES (:1, :2, :3, TO_DATE(:4, 'YYYY-MM-DD'), :5, 'PENDING')
                """, (advisor_id, farmer_code, session_id, scheduled_date, notes))
                conn.commit()
                
                activity_id = 'ACT-' + str(generate_id())[:8]
                cursor.execute("""
                    INSERT INTO ACTIVITY_RECORD (activity_id, farmer_code, activity_type, description, activity_date, reference_id)
                    VALUES (:1, :2, 'CONSULTATION', :3, SYSDATE, :4)
                """, (activity_id, farmer_code, f'Requested consultation on: {topic}', session_id))
                conn.commit()
                
                flash(get_flash_message('পরামর্শের অনুরোধ সফল হয়েছে!', 'Consultation request submitted successfully!'), 'success')
            except Exception as e:
                conn.rollback()
                flash(get_flash_message('ত্রুটি: ' + str(e), 'Error: ' + str(e)), 'danger')
                print(f"Request consultation error: {e}")
            finally:
                cursor.close()
                conn.close()
        return redirect(url_for('farmer_consultations'))

    @app.route('/farmer/community')
    def farmer_community():
        if 'user' not in session or session['user']['role'] != 'FARMER':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))
        
        conn = get_connection()
        posts = []
        farmer_code = None
        if conn:
            cursor = conn.cursor()
            try:
                farmer_code = get_farmer_code(cursor, session['user']['person_id'])
                if farmer_code:
                    posts = get_community_posts(cursor, farmer_code)
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"Community error: {e}")
                if conn:
                    conn.close()
        
        return render_template('farmer/community.html', 
                              user=session['user'], 
                              posts=posts, 
                              farmer_code=farmer_code, 
                              active_tab='community')

    @app.route('/farmer/toggle_like/<post_id>')
    def toggle_like(post_id):
        if 'user' not in session or session['user']['role'] != 'FARMER':
            return redirect(url_for('login_register'))
        
        conn = get_connection()
        if conn:
            cursor = conn.cursor()
            try:
                farmer_code = get_farmer_code(cursor, session['user']['person_id'])
                if not farmer_code:
                    return redirect(url_for('farmer_community'))
                    
                cursor.execute("SELECT COUNT(*) FROM POST_LIKE WHERE post_id = :1 AND farmer_code = :2", (post_id, farmer_code))
                exists = cursor.fetchone()[0]
                
                if exists > 0:
                    cursor.execute("DELETE FROM POST_LIKE WHERE post_id = :1 AND farmer_code = :2", (post_id, farmer_code))
                    cursor.execute("DELETE FROM ACTIVITY_RECORD WHERE farmer_code = :1 AND reference_id = :2 AND activity_type = 'LIKE'", 
                                  (farmer_code, post_id))
                else:
                    cursor.execute("INSERT INTO POST_LIKE (post_id, farmer_code, liked_date) VALUES (:1, :2, SYSDATE)", (post_id, farmer_code))
                    activity_id = 'ACT-' + str(generate_id())[:8]
                    cursor.execute("""
                        INSERT INTO ACTIVITY_RECORD (activity_id, farmer_code, activity_type, description, activity_date, reference_id)
                        VALUES (:1, :2, 'LIKE', :3, SYSDATE, :4)
                    """, (activity_id, farmer_code, f'Liked post {post_id}', post_id))
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as e:
                conn.rollback()
                print(f"Toggle like error: {e}")
                if conn:
                    conn.close()
        return redirect(url_for('farmer_community'))

    @app.route('/farmer/refer', methods=['GET', 'POST'])
    def farmer_refer():
        if 'user' not in session or session['user']['role'] != 'FARMER':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))
        
        conn = get_connection()
        my_referrals = []
        farmer_code = None
        search_results = None
        search_term = ''
        
        if conn:
            cursor = conn.cursor()
            try:
                farmer_code = get_farmer_code(cursor, session['user']['person_id'])
                
                if request.method == 'POST':
                    action = request.form.get('action')
                    
                    if action == 'search':
                        search_term = request.form.get('search_name', '').strip()
                        if search_term:
                            search_results = search_farmer_by_name(cursor, search_term)
                    
                    elif action == 'confirm':
                        referee_code = request.form.get('referee_code')
                        if referee_code and farmer_code:
                            if referee_code == farmer_code:
                                flash(get_flash_message(
                                    'আপনি নিজেকে রেফার করতে পারবেন না।',
                                    'You cannot refer yourself.'), 'warning')
                            else:
                                create_farmer_referral(cursor, farmer_code, referee_code)
                                conn.commit()
                                
                                activity_id = 'ACT-' + str(generate_id())[:8]
                                cursor.execute("""
                                    INSERT INTO ACTIVITY_RECORD (activity_id, farmer_code, activity_type, description, activity_date, reference_id)
                                    VALUES (:1, :2, 'REFERRAL', :3, SYSDATE, :4)
                                """, (activity_id, farmer_code, f'Referred a new farmer', referee_code))
                                conn.commit()
                                
                                flash(get_flash_message(
                                    'রেফারেল সফলভাবে যোগ করা হয়েছে!',
                                    'Referral submitted successfully!'), 'success')
                
                if farmer_code:
                    my_referrals = get_my_referrals(cursor, farmer_code)
                    
                cursor.close()
                conn.close()
            except Exception as e:
                if conn:
                    conn.rollback()
                    conn.close()
                flash(get_flash_message('ত্রুটি: ' + str(e), 'Error: ' + str(e)), 'danger')
                print(f"Refer error: {e}")
        
        return render_template('farmer/refer.html',
                              user=session['user'],
                              farmer_code=farmer_code,
                              my_referrals=my_referrals,
                              search_results=search_results,
                              search_term=search_term,
                              active_tab='refer')

    @app.route('/farmer/credit_score')
    def farmer_credit_score():
        if 'user' not in session or session['user']['role'] != 'FARMER':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))
        
        person_id = session['user']['person_id']
        conn = get_connection()
        credit_score = None
        farmer_code = None
        credit_breakdown = []

        if conn:
            cursor = conn.cursor()
            try:
                farmer_code = get_farmer_code(cursor, person_id)
                if farmer_code:
                    credit_score = get_farmer_credit_score(cursor, farmer_code)
                    credit_breakdown = get_credit_breakdown(cursor, farmer_code)
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"Credit score error: {e}")
                if conn:
                    conn.close()

        return render_template('farmer/credit_score.html', 
                              user=session['user'], 
                              credit_score=credit_score,
                              credit_breakdown=credit_breakdown,
                              farmer_code=farmer_code,
                              active_tab='credit')

    @app.route('/farmer/notifications')
    def get_notifications_api():
        if 'user' not in session or session['user']['role'] != 'FARMER':
            return jsonify({"error": "Unauthorized"}), 401
        
        conn = get_connection()
        notifs = []
        if conn:
            cursor = conn.cursor()
            try:
                farmer_code = get_farmer_code(cursor, session['user']['person_id'])
                if farmer_code:
                    notifs = get_notifications(cursor, farmer_code)
                    mark_notifications_read(cursor, farmer_code)
                    conn.commit()
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"Notifications error: {e}")
                if conn:
                    conn.close()
        return jsonify({"notifications": notifs})

    @app.route('/farmer/inventory', methods=['GET'])
    def farmer_inventory():
        if 'user' not in session or session['user']['role'] != 'FARMER':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))
        
        # Get search term from URL query string (e.g., /farmer/inventory?search=urea)
        search_term = request.args.get('search', '').strip()
        
        conn = get_connection()
        inventory = []
        farmer_code = None
        
        if conn:
            cursor = conn.cursor()
            try:
                farmer_code = get_farmer_code(cursor, session['user']['person_id'])
                if farmer_code:
                    center_code = get_center_code_for_farmer(cursor, farmer_code)
                    if center_code:
                        if search_term:
                            # User searched → use search query
                            inventory = search_inventory_items(cursor, center_code, search_term)
                        else:
                            # No search → show all items
                            inventory = get_inventory_items(cursor, center_code)
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"Inventory error: {e}")
                if conn: 
                    conn.close()
                
        return render_template('farmer/inventory.html', 
                              user=session['user'], 
                              inventory=inventory,
                              farmer_code=farmer_code,
                              search_term=search_term,
                              active_tab='inventory')

    @app.route('/farmer/orders')
    def farmer_orders():
        if 'user' not in session or session['user']['role'] != 'FARMER':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))
        
        conn = get_connection()
        order_history = []
        farmer_code = None
        
        if conn:
            cursor = conn.cursor()
            try:
                farmer_code = get_farmer_code(cursor, session['user']['person_id'])
                if farmer_code:
                    order_history = get_farmer_order_history(cursor, farmer_code)
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"Order history error: {e}")
                if conn: 
                    conn.close()
                
        return render_template('farmer/orders.html', 
                              user=session['user'], 
                              order_history=order_history,
                              farmer_code=farmer_code,
                              active_tab='orders')

    @app.route('/farmer/place_order', methods=['POST'])
    def place_order():
        if 'user' not in session or session['user']['role'] != 'FARMER':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))

        cart_data = request.form.get('cart_data')
        payment_method = request.form.get('payment_method', 'CASH')
        
        if not cart_data:
            flash(get_flash_message('আপনার কার্ট খালি!', 'Your cart is empty!'), 'danger')
            return redirect(url_for('farmer_inventory'))
        
        try:
            cart = json.loads(cart_data)
        except:
            flash(get_flash_message('কার্ট ডেটা অবৈধ।', 'Invalid cart data.'), 'danger')
            return redirect(url_for('farmer_inventory'))
        
        conn = get_connection()
        if conn:
            cursor = conn.cursor()
            try:
                farmer_code = get_farmer_code(cursor, session['user']['person_id'])
                if not farmer_code:
                    flash(get_flash_message('কৃষক কোড পাওয়া যায়নি।', 'Farmer code not found.'), 'danger')
                    return redirect(url_for('farmer_inventory'))
                
                agent_code = get_farmer_agent_code(cursor, farmer_code)
                purchase_id = create_new_purchase(cursor, farmer_code, agent_code, payment_method, generate_id)
                
                for item in cart:
                    inventory_id = item.get('id')
                    quantity = item.get('qty')
                    
                    cursor.execute("SELECT price_per_unit FROM INVENTORY WHERE inventory_id = :1", (inventory_id,))
                    price_row = cursor.fetchone()
                    
                    if not price_row:
                        continue
                    
                    unit_price = price_row[0]
                    add_item_to_purchase(cursor, purchase_id, inventory_id, quantity, unit_price, generate_id)
                
                conn.commit()
                flash(get_flash_message('অর্ডার সফলভাবে সম্পন্ন হয়েছে!', 'Order placed successfully!'), 'success')
                
            except Exception as e:
                conn.rollback()
                flash(get_flash_message('ত্রুটি: ' + str(e), 'Error: ' + str(e)), 'danger')
                print(f"Order error: {e}")
            finally:
                cursor.close()
                conn.close()
                
        return redirect(url_for('farmer_orders'))

    @app.route('/farmer/logout')
    def farmer_logout():
        session.clear()
        flash(get_flash_message('আপনি লগআউট হয়েছেন।', 'You have been logged out.'), 'info')
        return redirect(url_for('index'))