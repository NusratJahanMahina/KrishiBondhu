"""
Advisor-related routes for the KrishiBondhu application
"""
from flask import render_template, session, redirect, url_for, request, jsonify, flash
from db_connect import get_connection
from datetime import datetime, timedelta

def ensure_notification_table(cursor):
    """Ensure the NOTIFICATION table exists in the database"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS NOTIFICATION (
            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            link TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(person_id) REFERENCES PERSON(person_id) ON DELETE CASCADE
        )
    """)

def add_notification(cursor, person_id, title, message, link=None):
    """Helper function to insert an in-app notification"""
    try:
        ensure_notification_table(cursor)
        cursor.execute("""
            INSERT INTO NOTIFICATION (person_id, title, message, link, is_read)
            VALUES (?, ?, ?, ?, 0)
        """, (person_id, title, message, link))
    except Exception as e:
        print(f"Error adding notification: {e}")

def register_advisor_routes(app):
    """Register all advisor routes to the Flask app"""

    # ============================================
    # NOTIFICATION API ENDPOINTS
    # ============================================

    @app.route('/api/notifications', methods=['GET'])
    def get_notifications_api():
        """Fetch latest notifications and unread count for current user"""
        if 'user' not in session:
            return jsonify({'notifications': [], 'unread_count': 0})
        
        person_id = session['user'].get('person_id')
        try:
            conn = get_connection()
            cursor = conn.cursor()
            ensure_notification_table(cursor)
            
            cursor.execute("""
                SELECT notification_id, title, message, link, is_read, created_at
                FROM NOTIFICATION
                WHERE person_id = ?
                ORDER BY created_at DESC
                LIMIT 20
            """, (person_id,))
            rows = cursor.fetchall()
            
            cursor.execute("""
                SELECT COUNT(*) FROM NOTIFICATION
                WHERE person_id = ? AND is_read = 0
            """, (person_id,))
            unread_count = cursor.fetchone()[0]
            
            conn.close()
            
            notifications = []
            for r in rows:
                notifications.append({
                    'id': r[0],
                    'title': r[1],
                    'message': r[2],
                    'link': r[3],
                    'is_read': bool(r[4]),
                    'created_at': str(r[5])
                })
            
            return jsonify({'notifications': notifications, 'unread_count': unread_count})
        except Exception as e:
            print(f"Error fetching notifications: {e}")
            return jsonify({'error': str(e), 'notifications': [], 'unread_count': 0}), 500

    @app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
    def mark_notification_read(notification_id):
        """Mark single notification as read"""
        if 'user' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        person_id = session['user'].get('person_id')
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE NOTIFICATION SET is_read = 1
                WHERE notification_id = ? AND person_id = ?
            """, (notification_id, person_id))
            conn.commit()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/notifications/read-all', methods=['POST'])
    def mark_all_notifications_read():
        """Mark all notifications as read for current user"""
        if 'user' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        person_id = session['user'].get('person_id')
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE NOTIFICATION SET is_read = 1
                WHERE person_id = ?
            """, (person_id,))
            conn.commit()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500


    # ============================================
    # ADVISOR DASHBOARD
    # ============================================

    @app.route('/advisor/dashboard', methods=['GET'])
    def advisor_dashboard():
        """Comprehensive dashboard for advisors with hire notifications, bookings, stats, and profile controls"""
        if 'user' not in session:
            return redirect(url_for('login_register'))
        
        user = session.get('user')
        user_role = user.get('role')
        
        if user_role not in ['ADVISOR', 'ADMIN']:
            return redirect(url_for('login_register'))
        
        person_id = user.get('person_id')
        try:
            conn = get_connection()
            cursor = conn.cursor()
            ensure_notification_table(cursor)
            
            # Fetch advisor profile
            cursor.execute("""
                SELECT 
                    A.advisor_id,
                    P.first_name,
                    P.last_name,
                    P.login_phone,
                    A.specialization,
                    A.bio,
                    A.experience_years,
                    A.qualification,
                    COALESCE(A.rating, 5.0) as rating,
                    A.total_bookings,
                    COALESCE(A.is_available, 'YES'),
                    P.person_id
                FROM ADVISOR A
                JOIN PERSON P ON A.person_id = P.person_id
                WHERE A.person_id = ?
            """, (person_id,))
            advisor_row = cursor.fetchone()
            
            if not advisor_row:
                # Auto-initialize advisor row if missing
                cursor.execute("""
                    INSERT INTO ADVISOR (person_id, specialization, bio, experience_years, qualification, is_available)
                    VALUES (?, 'মৃত্তিকা ও সার ব্যবস্থাপনা', 'মাটির পুষ্টিমান বিশ্লেষণ এবং আধুনিক কৃষি বিশেষজ্ঞ', 5, 'এম.এস.সি. কৃষি বিজ্ঞান', 'YES')
                """, (person_id,))
                conn.commit()
                cursor.execute("""
                    SELECT 
                        A.advisor_id,
                        P.first_name,
                        P.last_name,
                        P.login_phone,
                        A.specialization,
                        A.bio,
                        A.experience_years,
                        A.qualification,
                        COALESCE(A.rating, 5.0) as rating,
                        A.total_bookings,
                        COALESCE(A.is_available, 'YES'),
                        P.person_id
                    FROM ADVISOR A
                    JOIN PERSON P ON A.person_id = P.person_id
                    WHERE A.person_id = ?
                """, (person_id,))
                advisor_row = cursor.fetchone()
            
            advisor_id = advisor_row[0]
            session['user']['advisor_id'] = advisor_id
            session['user']['is_available'] = advisor_row[10]
            session.modified = True
            
            advisor = {
                'advisor_id': advisor_row[0],
                'first_name': advisor_row[1],
                'last_name': advisor_row[2],
                'phone': advisor_row[3],
                'specialization': advisor_row[4],
                'bio': advisor_row[5],
                'experience_years': advisor_row[6],
                'qualification': advisor_row[7],
                'rating': round(advisor_row[8], 1),
                'total_bookings': advisor_row[9],
                'is_available': advisor_row[10],
                'person_id': advisor_row[11]
            }
            
            # Fetch rates
            cursor.execute("""
                SELECT rate_type, amount, currency
                FROM ADVISOR_RATE
                WHERE advisor_id = ?
                ORDER BY rate_type
            """, (advisor_id,))
            rates_data = cursor.fetchall()
            rates = {r[0]: r[1] for r in rates_data}
            if 'HOURLY' not in rates:
                rates['HOURLY'] = 500.0
            if 'DAILY' not in rates:
                rates['DAILY'] = 3500.0
                
            # Fetch availability schedule
            cursor.execute("""
                SELECT day_of_week, start_time, end_time, is_available
                FROM ADVISOR_AVAILABILITY
                WHERE advisor_id = ?
                ORDER BY day_of_week
            """, (advisor_id,))
            availability = cursor.fetchall()
            
            # Fetch all bookings with farmer details
            cursor.execute("""
                SELECT 
                    AB.booking_id,
                    AB.scheduled_date,
                    AB.start_time,
                    AB.end_time,
                    AB.duration_hours,
                    AB.rate_type,
                    AB.total_amount,
                    AB.payment_status,
                    AB.booking_status,
                    AB.consultation_topic,
                    AB.notes,
                    P.first_name,
                    P.last_name,
                    P.login_phone,
                    AB.farmer_id,
                    AB.booking_date,
                    AR.rating,
                    AR.review
                FROM ADVISOR_BOOKING AB
                JOIN FARMER F ON AB.farmer_id = F.farmer_code
                JOIN PERSON P ON F.person_id = P.person_id
                LEFT JOIN ADVISOR_RATING AR ON AB.booking_id = AR.booking_id
                WHERE AB.advisor_id = ?
                ORDER BY AB.booking_date DESC, AB.scheduled_date DESC
            """, (advisor_id,))
            all_bookings_rows = cursor.fetchall()
            
            bookings = []
            pending_bookings = []
            upcoming_bookings = []
            completed_bookings = []
            cancelled_bookings = []
            total_earnings = 0.0
            
            for r in all_bookings_rows:
                b_item = {
                    'booking_id': r[0],
                    'scheduled_date': r[1],
                    'start_time': r[2],
                    'end_time': r[3],
                    'duration_hours': r[4],
                    'rate_type': r[5],
                    'total_amount': r[6],
                    'payment_status': r[7],
                    'booking_status': r[8],
                    'consultation_topic': r[9],
                    'notes': r[10],
                    'farmer_name': f"{r[11]} {r[12]}",
                    'farmer_phone': r[13],
                    'farmer_id': r[14],
                    'booking_date': r[15],
                    'rating': r[16],
                    'review': r[17]
                }
                bookings.append(b_item)
                if b_item['booking_status'] == 'PENDING':
                    pending_bookings.append(b_item)
                elif b_item['booking_status'] == 'CONFIRMED':
                    upcoming_bookings.append(b_item)
                elif b_item['booking_status'] == 'COMPLETED':
                    completed_bookings.append(b_item)
                    total_earnings += float(b_item['total_amount'] or 0)
                elif b_item['booking_status'] == 'CANCELLED':
                    cancelled_bookings.append(b_item)
            
            # Fetch reviews
            cursor.execute("""
                SELECT 
                    AR.rating,
                    AR.review,
                    AR.created_at,
                    P.first_name,
                    P.last_name,
                    AB.consultation_topic
                FROM ADVISOR_RATING AR
                JOIN FARMER F ON AR.farmer_id = F.farmer_code
                JOIN PERSON P ON F.person_id = P.person_id
                JOIN ADVISOR_BOOKING AB ON AR.booking_id = AB.booking_id
                WHERE AR.advisor_id = ?
                ORDER BY AR.created_at DESC
                LIMIT 10
            """, (advisor_id,))
            reviews = cursor.fetchall()
            
            # Fetch notifications
            cursor.execute("""
                SELECT notification_id, title, message, link, is_read, created_at
                FROM NOTIFICATION
                WHERE person_id = ?
                ORDER BY created_at DESC
                LIMIT 10
            """, (person_id,))
            notifications = cursor.fetchall()
            
            stats = {
                'total_earnings': total_earnings,
                'total_completed': len(completed_bookings),
                'pending_requests': len(pending_bookings),
                'upcoming_sessions': len(upcoming_bookings),
                'total_bookings': len(bookings),
                'rating': advisor['rating'],
                'reviews_count': len(reviews)
            }
            
            conn.close()
            
            return render_template('dashboard_advisor.html',
                                 advisor=advisor,
                                 stats=stats,
                                 rates=rates,
                                 availability=availability,
                                 pending_bookings=pending_bookings,
                                 upcoming_bookings=upcoming_bookings,
                                 completed_bookings=completed_bookings,
                                 cancelled_bookings=cancelled_bookings,
                                 all_bookings=bookings,
                                 reviews=reviews,
                                 notifications=notifications,
                                 user=user)
        except Exception as e:
            print(f"Error loading advisor dashboard: {str(e)}")
            import traceback
            traceback.print_exc()
            return render_template('error.html', message=f"Error loading advisor dashboard: {str(e)}")


    # ============================================
    # ADVISOR BOOKING ACTIONS & STATUS UPDATES
    # ============================================

    @app.route('/advisor/booking/<int:booking_id>/action', methods=['POST'])
    def update_booking_action(booking_id):
        """Advisor accepts, completes, or cancels a booking"""
        if 'user' not in session:
            return redirect(url_for('login_register'))
        
        user = session.get('user')
        if user.get('role') not in ['ADVISOR', 'ADMIN']:
            flash('অননুমোদিত অ্যাক্সেস / Unauthorized access', 'danger')
            return redirect(url_for('login_register'))
        
        action = request.form.get('action', '').upper()  # ACCEPT, COMPLETE, REJECT, CANCEL
        advisor_notes = request.form.get('notes', '').strip()
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Fetch booking info & farmer's person_id (robust join)
            cursor.execute("""
                SELECT 
                    AB.advisor_id, 
                    AB.farmer_id, 
                    COALESCE(F.person_id, P.person_id, AB.farmer_id) as farmer_person_id, 
                    COALESCE(P.first_name, 'কৃষক'), 
                    COALESCE(P.last_name, ''), 
                    AB.consultation_topic, 
                    AB.scheduled_date
                FROM ADVISOR_BOOKING AB
                LEFT JOIN FARMER F ON (AB.farmer_id = F.farmer_code OR AB.farmer_id = F.person_id)
                LEFT JOIN PERSON P ON (F.person_id = P.person_id OR AB.farmer_id = P.person_id)
                WHERE AB.booking_id = ?
            """, (booking_id,))
            booking_row = cursor.fetchone()
            
            if not booking_row:
                conn.close()
                flash('বুকিং খুঁজে পাওয়া যায়নি / Booking not found', 'danger')
                return redirect(url_for('advisor_dashboard'))
            
            advisor_id, farmer_code, farmer_person_id, f_first, f_last, topic, sched_date = booking_row
            
            if action == 'ACCEPT':
                cursor.execute("""
                    UPDATE ADVISOR_BOOKING
                    SET booking_status = 'CONFIRMED'
                    WHERE booking_id = ?
                """, (booking_id,))
                
                # Send notification to farmer
                add_notification(
                    cursor,
                    farmer_person_id,
                    "✅ বুকিং নিশ্চিত হয়েছে / Booking Confirmed",
                    f"আপনার বুকিং #{booking_id} ('{topic}') উপদেষ্টা দ্বারা গৃহীত হয়েছে। নির্ধারিত তারিখ: {sched_date}",
                    url_for('my_bookings')
                )
                flash(f'বুকিং #{booking_id} সফলভাবে নিশ্চিত করা হয়েছে! / Booking #{booking_id} confirmed successfully!', 'success')
                
            elif action == 'COMPLETE':
                cursor.execute("""
                    UPDATE ADVISOR_BOOKING
                    SET booking_status = 'COMPLETED', payment_status = 'PAID'
                    WHERE booking_id = ?
                """, (booking_id,))
                
                # Update advisor total bookings count
                cursor.execute("""
                    UPDATE ADVISOR
                    SET total_bookings = total_bookings + 1
                    WHERE advisor_id = ?
                """, (advisor_id,))
                
                # Send notification to farmer
                add_notification(
                    cursor,
                    farmer_person_id,
                    "🎉 পরামর্শ সম্পন্ন হয়েছে / Consultation Completed",
                    f"বুকিং #{booking_id} ('{topic}') সম্পন্ন হয়েছে। আপনার মূল্যবান রেটিং ও মতামত দিন!",
                    url_for('my_bookings')
                )
                flash(f'পরামর্শ #{booking_id} সম্পন্ন হিসেবে চিহ্নিত করা হয়েছে! / Consultation #{booking_id} marked as completed!', 'success')
                
            elif action in ['REJECT', 'CANCEL']:
                cursor.execute("""
                    UPDATE ADVISOR_BOOKING
                    SET booking_status = 'CANCELLED'
                    WHERE booking_id = ?
                """, (booking_id,))
                
                # Send notification to farmer
                add_notification(
                    cursor,
                    farmer_person_id,
                    "❌ বুকিং বাতিল করা হয়েছে / Booking Cancelled",
                    f"বুকিং #{booking_id} ('{topic}') বাতিল করা হয়েছে।",
                    url_for('my_bookings')
                )
                flash(f'বুকিং #{booking_id} বাতিল করা হয়েছে। / Booking #{booking_id} has been cancelled.', 'warning')
            
            if advisor_notes:
                cursor.execute("UPDATE ADVISOR_BOOKING SET notes = ? WHERE booking_id = ?", (advisor_notes, booking_id))
            
            conn.commit()
            conn.close()
            return redirect(url_for('advisor_dashboard'))
        except Exception as e:
            print(f"Error updating booking status: {e}")
            flash(f"Error: {str(e)}", 'danger')
            return redirect(url_for('advisor_dashboard'))

    @app.route('/advisor/booking/<int:booking_id>/complete', methods=['POST'])
    def complete_booking_direct(booking_id):
        """Direct helper route for completing a booking"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE ADVISOR_BOOKING SET booking_status = 'COMPLETED', payment_status = 'PAID' WHERE booking_id = ?", (booking_id,))
            cursor.execute("""
                SELECT AB.advisor_id, AB.farmer_id, F.person_id, AB.consultation_topic 
                FROM ADVISOR_BOOKING AB
                LEFT JOIN FARMER F ON (AB.farmer_id = F.farmer_code OR AB.farmer_id = F.person_id)
                WHERE AB.booking_id = ?
            """, (booking_id,))
            row = cursor.fetchone()
            if row:
                adv_id, f_code, f_pid, topic = row
                cursor.execute("UPDATE ADVISOR SET total_bookings = total_bookings + 1 WHERE advisor_id = ?", (adv_id,))
                if f_pid:
                    add_notification(
                        cursor,
                        f_pid,
                        "🎉 পরামর্শ সম্পন্ন হয়েছে / Consultation Completed",
                        f"বুকিং #{booking_id} ('{topic}') সম্পন্ন হয়েছে। আপনার মূল্যবান রেটিং ও মতামত দিন!",
                        url_for('my_bookings')
                    )
            conn.commit()
            conn.close()
            flash(f'পরামর্শ #{booking_id} সম্পন্ন হিসেবে চিহ্নিত করা হয়েছে!', 'success')
            return redirect(url_for('advisor_dashboard'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('advisor_dashboard'))

    @app.route('/advisor/booking/<int:booking_id>/notes', methods=['POST'])
    def add_consultation_notes(booking_id):
        """Add advice, prescriptions, or notes to a booking"""
        if 'user' not in session:
            return redirect(url_for('login_register'))
        
        user = session.get('user')
        if user.get('role') not in ['ADVISOR', 'ADMIN']:
            flash('Unauthorized', 'danger')
            return redirect(url_for('login_register'))
        
        notes = request.form.get('notes', '').strip()
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("UPDATE ADVISOR_BOOKING SET notes = ? WHERE booking_id = ?", (notes, booking_id))
            
            # Notify farmer
            cursor.execute("""
                SELECT F.person_id, AB.consultation_topic
                FROM ADVISOR_BOOKING AB
                JOIN FARMER F ON AB.farmer_id = F.farmer_code
                WHERE AB.booking_id = ?
            """, (booking_id,))
            row = cursor.fetchone()
            if row:
                farmer_person_id, topic = row
                add_notification(
                    cursor,
                    farmer_person_id,
                    "📝 নতুন পরামর্শ নোট / New Advisory Notes Added",
                    f"বুকিং #{booking_id} ('{topic}')-এর জন্য উপদেষ্টা পরামর্শ নোট যুক্ত করেছেন।",
                    url_for('my_bookings')
                )
            
            conn.commit()
            conn.close()
            flash('পরামর্শ নোট সফলভাবে সংরক্ষণ করা হয়েছে! / Advisory notes saved successfully!', 'success')
            return redirect(url_for('advisor_dashboard'))
        except Exception as e:
            print(f"Error adding notes: {e}")
            flash(f"Error: {str(e)}", 'danger')
            return redirect(url_for('advisor_dashboard'))


    # ============================================
    # ADVISOR AVAILABILITY & PROFILE MANAGEMENT
    # ============================================

    @app.route('/advisor/status/toggle', methods=['POST'])
    def toggle_advisor_status():
        """Toggle active availability status for advisor"""
        if 'user' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        user = session.get('user')
        person_id = user.get('person_id')
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT is_available, advisor_id FROM ADVISOR WHERE person_id = ?", (person_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return jsonify({'error': 'Advisor record not found'}), 404
            
            current_status = row[0]
            new_status = 'NO' if current_status == 'YES' else 'YES'
            
            cursor.execute("UPDATE ADVISOR SET is_available = ? WHERE person_id = ?", (new_status, person_id))
            conn.commit()
            conn.close()
            
            session['user']['is_available'] = new_status
            session.modified = True
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({'success': True, 'is_available': new_status})
            
            flash(f'উপলব্ধতার স্থিতি পরিবর্তন করা হয়েছে: {new_status} / Availability updated to {new_status}', 'success')
            return redirect(url_for('advisor_dashboard'))
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/advisor/profile/update', methods=['POST'])
    def update_advisor_profile():
        """Update advisor bio, specialization, qualification, and experience"""
        if 'user' not in session:
            return redirect(url_for('login_register'))
        
        user = session.get('user')
        person_id = user.get('person_id')
        
        specialization = request.form.get('specialization', '').strip()
        bio = request.form.get('bio', '').strip()
        qualification = request.form.get('qualification', '').strip()
        try:
            experience_years = int(request.form.get('experience_years', '0'))
        except ValueError:
            experience_years = 0
            
        phone = request.form.get('phone', '').strip()
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE ADVISOR 
                SET specialization = ?, bio = ?, qualification = ?, experience_years = ?
                WHERE person_id = ?
            """, (specialization, bio, qualification, experience_years, person_id))
            
            if phone:
                cursor.execute("UPDATE PERSON SET login_phone = ? WHERE person_id = ?", (phone, person_id))
                cursor.execute("UPDATE PHONE SET phone_number = ? WHERE person_id = ? AND is_primary = 'YES'", (phone, person_id))
            
            conn.commit()
            conn.close()
            flash('প্রোফাইল সফলভাবে আপডেট করা হয়েছে! / Profile updated successfully!', 'success')
            return redirect(url_for('advisor_dashboard'))
        except Exception as e:
            flash(f'Error updating profile: {str(e)}', 'danger')
            return redirect(url_for('advisor_dashboard'))

    @app.route('/advisor/rates/update', methods=['POST'])
    def update_advisor_rates():
        """Update advisor hourly and daily rates"""
        if 'user' not in session:
            return redirect(url_for('login_register'))
        
        user = session.get('user')
        person_id = user.get('person_id')
        
        try:
            hourly_rate = float(request.form.get('hourly_rate', 500))
            daily_rate = float(request.form.get('daily_rate', 3500))
            
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT advisor_id FROM ADVISOR WHERE person_id = ?", (person_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                flash('Advisor not found', 'danger')
                return redirect(url_for('advisor_dashboard'))
            
            advisor_id = row[0]
            
            # Upsert hourly
            cursor.execute("DELETE FROM ADVISOR_RATE WHERE advisor_id = ?", (advisor_id,))
            cursor.execute("""
                INSERT INTO ADVISOR_RATE (advisor_id, rate_type, amount, currency)
                VALUES (?, 'HOURLY', ?, 'BDT')
            """, (advisor_id, hourly_rate))
            cursor.execute("""
                INSERT INTO ADVISOR_RATE (advisor_id, rate_type, amount, currency)
                VALUES (?, 'DAILY', ?, 'BDT')
            """, (advisor_id, daily_rate))
            
            conn.commit()
            conn.close()
            flash('পরামর্শ ফি সফলভাবে আপডেট করা হয়েছে! / Rates updated successfully!', 'success')
            return redirect(url_for('advisor_dashboard'))
        except Exception as e:
            flash(f'Error updating rates: {str(e)}', 'danger')
            return redirect(url_for('advisor_dashboard'))

    @app.route('/advisor/availability/update', methods=['POST'])
    def update_advisor_availability():
        """Update weekly schedule slots"""
        if 'user' not in session:
            return redirect(url_for('login_register'))
        
        user = session.get('user')
        person_id = user.get('person_id')
        
        days = request.form.getlist('days')
        start_time = request.form.get('start_time', '09:00')
        end_time = request.form.get('end_time', '17:00')
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT advisor_id FROM ADVISOR WHERE person_id = ?", (person_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                flash('Advisor not found', 'danger')
                return redirect(url_for('advisor_dashboard'))
            
            advisor_id = row[0]
            cursor.execute("DELETE FROM ADVISOR_AVAILABILITY WHERE advisor_id = ?", (advisor_id,))
            
            for day in days:
                cursor.execute("""
                    INSERT INTO ADVISOR_AVAILABILITY (advisor_id, day_of_week, start_time, end_time, is_available)
                    VALUES (?, ?, ?, ?, 'YES')
                """, (advisor_id, day, start_time, end_time))
            
            conn.commit()
            conn.close()
            flash('সাপ্তাহিক সময়সূচী সফলভাবে সংরক্ষিত হয়েছে! / Schedule updated successfully!', 'success')
            return redirect(url_for('advisor_dashboard'))
        except Exception as e:
            flash(f'Error updating schedule: {str(e)}', 'danger')
            return redirect(url_for('advisor_dashboard'))


    # ============================================
    # PUBLIC ADVISOR LISTING & PROFILE
    # ============================================

    @app.route('/advisors', methods=['GET'])
    @app.route('/advisor/listing', methods=['GET'])
    def advisor_listing():
        """Display list of available advisors with their rates and ratings"""
        if 'user' not in session:
            return redirect(url_for('login_register'))
        
        user = session.get('user')
        user_role = user.get('role')
        
        if user_role not in ['FARMER', 'AGENT', 'ADMIN']:
            return redirect(url_for('login_register'))
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            search_query = request.args.get('q', '').strip() or request.args.get('search', '').strip()
            specialization_filter = request.args.get('specialization', '').strip()
            availability_filter = request.args.get('availability', '').strip()
            try:
                min_rating = float(request.args.get('min_rating', '0'))
            except (TypeError, ValueError):
                min_rating = 0.0
            
            query = """
                SELECT 
                    A.advisor_id,
                    P.first_name,
                    P.last_name,
                    P.login_phone,
                    A.specialization,
                    A.bio,
                    A.experience_years,
                    A.qualification,
                    COALESCE(A.rating, 5.0) as rating,
                    A.total_bookings,
                    COALESCE(A.is_available, 'YES') as is_available
                FROM ADVISOR A
                JOIN PERSON P ON A.person_id = P.person_id
                WHERE 1=1
            """
            
            params = []
            
            if search_query:
                query += """ AND (
                    P.first_name LIKE ? OR 
                    P.last_name LIKE ? OR 
                    A.specialization LIKE ? OR 
                    A.bio LIKE ? OR 
                    A.qualification LIKE ?
                )"""
                pattern = f"%{search_query}%"
                params.extend([pattern, pattern, pattern, pattern, pattern])

            if specialization_filter:
                query += " AND A.specialization LIKE ?"
                params.append(f"%{specialization_filter}%")
            
            if min_rating > 0:
                query += " AND COALESCE(A.rating, 5.0) >= ?"
                params.append(min_rating)

            if availability_filter == 'YES':
                query += " AND COALESCE(A.is_available, 'YES') = 'YES'"
            elif availability_filter == 'NO':
                query += " AND COALESCE(A.is_available, 'YES') = 'NO'"
            
            query += " ORDER BY CASE WHEN COALESCE(A.is_available, 'YES') = 'YES' THEN 0 ELSE 1 END, COALESCE(A.rating, 5.0) DESC, A.total_bookings DESC"
            
            cursor.execute(query, params)
            advisors_data = cursor.fetchall()
            
            advisors = []
            for advisor in advisors_data:
                advisor_id = advisor[0]
                cursor.execute("""
                    SELECT rate_type, amount, currency
                    FROM ADVISOR_RATE
                    WHERE advisor_id = ?
                    ORDER BY rate_type
                """, (advisor_id,))
                rates = cursor.fetchall()
                if not rates:
                    rates = [('HOURLY', 500.0, 'BDT'), ('DAILY', 3500.0, 'BDT')]
                
                advisors.append({
                    'advisor_id': advisor[0],
                    'first_name': advisor[1] or '',
                    'last_name': advisor[2] or '',
                    'phone': advisor[3] or '',
                    'specialization': advisor[4] or 'কৃষি বিশেষজ্ঞ',
                    'bio': advisor[5] or 'অভিজ্ঞ কৃষি বিজ্ঞানী ও পরামর্শক। মাঠ পর্যায়ের ফসলের যে কোনো রোগ ও আধুনিক চাষাবাদ সম্পর্কে সেবা দিয়ে থাকেন।',
                    'experience_years': advisor[6] or 5,
                    'qualification': advisor[7] or 'বিএসসি ইন এগ্রিকালচার',
                    'rating': round(advisor[8] or 5.0, 1),
                    'total_bookings': advisor[9] or 0,
                    'is_available': advisor[10] or 'YES',
                    'rates': rates
                })
            
            cursor.execute("SELECT DISTINCT specialization FROM ADVISOR ORDER BY specialization")
            specializations = [row[0] for row in cursor.fetchall() if row[0]]
            
            conn.close()
            
            return render_template('advisor/advisor_listing.html', 
                                 advisors=advisors,
                                 specializations=specializations,
                                 selected_specialization=specialization_filter,
                                 search_query=search_query,
                                 min_rating=min_rating,
                                 availability=availability_filter,
                                 user=user)
        except Exception as e:
            print(f"Error fetching advisors: {str(e)}")
            return render_template('error.html', message=f"Error loading advisors: {str(e)}")

    @app.route('/advisor/<int:advisor_id>', methods=['GET'])
    @app.route('/advisor/<int:advisor_id>/profile', methods=['GET'])
    def advisor_profile(advisor_id):
        """Display detailed advisor profile with availability and booking option"""
        if 'user' not in session:
            return redirect(url_for('login_register'))
        
        user = session.get('user')
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    A.advisor_id,
                    P.first_name,
                    P.last_name,
                    P.login_phone,
                    A.specialization,
                    A.bio,
                    A.experience_years,
                    A.qualification,
                    COALESCE(A.rating, 5.0) as rating,
                    A.total_bookings,
                    A.is_available
                FROM ADVISOR A
                JOIN PERSON P ON A.person_id = P.person_id
                WHERE A.advisor_id = ?
            """, (advisor_id,))
            
            advisor_info = cursor.fetchone()
            if not advisor_info:
                conn.close()
                return render_template('error.html', message="Advisor not found")
            
            cursor.execute("""
                SELECT rate_type, amount, currency
                FROM ADVISOR_RATE
                WHERE advisor_id = ?
                ORDER BY rate_type
            """, (advisor_id,))
            rates = cursor.fetchall()
            
            cursor.execute("""
                SELECT day_of_week, start_time, end_time, is_available
                FROM ADVISOR_AVAILABILITY
                WHERE advisor_id = ?
                ORDER BY day_of_week
            """, (advisor_id,))
            availability = cursor.fetchall()
            
            cursor.execute("""
                SELECT 
                    AR.rating,
                    AR.review,
                    AB.scheduled_date,
                    P2.first_name,
                    P2.last_name
                FROM ADVISOR_RATING AR
                JOIN ADVISOR_BOOKING AB ON AR.booking_id = AB.booking_id
                JOIN FARMER F ON AR.farmer_id = F.farmer_code
                JOIN PERSON P2 ON F.person_id = P2.person_id
                WHERE AR.advisor_id = ?
                ORDER BY AB.scheduled_date DESC
                LIMIT 5
            """, (advisor_id,))
            ratings = cursor.fetchall()
            
            conn.close()
            
            return render_template('advisor/advisor_profile.html',
                                 advisor=advisor_info,
                                 rates=rates,
                                 availability=availability,
                                 ratings=ratings,
                                 user=user)
        except Exception as e:
            print(f"Error fetching advisor profile: {str(e)}")
            return render_template('error.html', message=f"Error loading advisor profile: {str(e)}")


    # ============================================
    # BOOK / HIRE ADVISOR (WITH NOTIFICATION TRIGGER)
    # ============================================

    @app.route('/advisor/<int:advisor_id>/book', methods=['GET', 'POST'])
    def book_advisor(advisor_id):
        """Book an advisor consultation and send instant hire notification to the advisor"""
        if 'user' not in session:
            return redirect(url_for('login_register'))
        
        user = session.get('user')
        user_role = user.get('role')
        
        if user_role != 'FARMER':
            flash('শুধুমাত্র কৃষকরা পরামর্শদাতা নিয়োগ করতে পারেন। / Only farmers can hire advisors.', 'warning')
            return redirect(url_for('advisor_listing'))
        
        person_id = user.get('person_id')
        
        if request.method == 'POST':
            try:
                conn = get_connection()
                cursor = conn.cursor()
                ensure_notification_table(cursor)
                
                # Fetch farmer_id (farmer_code) and agent_id
                farmer_id = user.get('farmer_id') or user.get('farmer_code')
                agent_id = user.get('agent_code') or user.get('agent_id')
                
                if not farmer_id:
                    cursor.execute("SELECT farmer_code, agent_code FROM FARMER WHERE person_id = ?", (person_id,))
                    f_row = cursor.fetchone()
                    if f_row:
                        farmer_id, agent_id = f_row[0], f_row[1]
                    else:
                        cursor.execute("INSERT INTO FARMER (farmer_code, person_id, land_acres) VALUES (?, ?, 1.0)", (person_id, person_id))
                        conn.commit()
                        farmer_id = person_id
                
                scheduled_date = request.form.get('scheduled_date')
                start_time = request.form.get('start_time', '10:00')
                rate_type = request.form.get('rate_type', 'HOURLY')
                consultation_topic = request.form.get('consultation_topic', 'সাধারণ কৃষি পরামর্শ')
                
                if rate_type == 'DAILY':
                    duration_hours = 8.0
                    end_time = '17:00'
                else:
                    end_time = request.form.get('end_time', '11:00')
                    try:
                        start_dt = datetime.strptime(start_time, '%H:%M')
                        end_dt = datetime.strptime(end_time, '%H:%M')
                        duration_hours = max(1.0, (end_dt - start_dt).total_seconds() / 3600)
                    except Exception:
                        duration_hours = 1.0
                
                cursor.execute("""
                    SELECT amount FROM ADVISOR_RATE
                    WHERE advisor_id = ? AND rate_type = ?
                """, (advisor_id, rate_type))
                rate_row = cursor.fetchone()
                rate_amount = rate_row[0] if rate_row else (500.0 if rate_type == 'HOURLY' else 3500.0)
                total_amount = rate_amount * (1 if rate_type == 'DAILY' else duration_hours)
                
                # Insert booking with status PENDING
                cursor.execute("""
                    INSERT INTO ADVISOR_BOOKING 
                    (advisor_id, farmer_id, agent_id, scheduled_date, start_time, end_time, 
                     duration_hours, rate_type, total_amount, payment_status, booking_status, 
                     consultation_topic)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', 'PENDING', ?)
                """, (advisor_id, farmer_id, agent_id, scheduled_date, start_time, end_time,
                      duration_hours, rate_type, total_amount, consultation_topic))
                
                booking_id = cursor.lastrowid
                
                # Fetch advisor person_id & name to send notification
                cursor.execute("""
                    SELECT A.person_id, P.first_name, P.last_name
                    FROM ADVISOR A
                    JOIN PERSON P ON A.person_id = P.person_id
                    WHERE A.advisor_id = ?
                """, (advisor_id,))
                adv_person = cursor.fetchone()
                
                farmer_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                
                if adv_person:
                    adv_person_id, adv_first, adv_last = adv_person
                    # Send NOTIFICATION to ADVISOR that someone hired them!
                    add_notification(
                        cursor,
                        adv_person_id,
                        "🔔 নতুন নিয়োগ অনুরোধ! / New Hire Request!",
                        f"কৃষক {farmer_name} আপনাকে পরামর্শের জন্য নিয়োগ করেছেন। বিষয়: '{consultation_topic}', তারিখ: {scheduled_date} ({start_time} - {end_time})।",
                        url_for('advisor_dashboard')
                    )
                
                # Send NOTIFICATION to FARMER confirming submission
                add_notification(
                    cursor,
                    person_id,
                    "📋 বুকিং অনুরোধ পাঠানো হয়েছে / Booking Request Sent",
                    f"উপদেষ্টা {adv_first if adv_person else 'Advisor'} {adv_last if adv_person else ''}-এর কাছে বুকিং #{booking_id} অনুরোধ পাঠানো হয়েছে। নিশ্চিতকরণের অপেক্ষায় রয়েছে।",
                    url_for('my_bookings')
                )
                
                conn.commit()
                conn.close()
                
                flash(f'বুকিং অনুরোধ সফলভাবে পাঠানো হয়েছে! উপদেষ্টা শীঘ্রই এটি পর্যালোচনা করবেন। / Booking request sent successfully! The advisor will review it shortly.', 'success')
                return redirect(url_for('my_bookings'))
            
            except Exception as e:
                print(f"Error booking advisor: {str(e)}")
                import traceback
                traceback.print_exc()
                return render_template('error.html', message=f"Error booking advisor: {str(e)}")
        
        # GET request - show booking form
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT A.advisor_id, P.first_name, P.last_name, A.specialization
                FROM ADVISOR A
                JOIN PERSON P ON A.person_id = P.person_id
                WHERE A.advisor_id = ?
            """, (advisor_id,))
            advisor_info = cursor.fetchone()
            
            cursor.execute("""
                SELECT rate_type, amount, currency
                FROM ADVISOR_RATE
                WHERE advisor_id = ?
            """, (advisor_id,))
            rates = cursor.fetchall()
            
            cursor.execute("""
                SELECT day_of_week, start_time, end_time
                FROM ADVISOR_AVAILABILITY
                WHERE advisor_id = ? AND is_available = 'YES'
                ORDER BY day_of_week
            """, (advisor_id,))
            availability = cursor.fetchall()
            
            conn.close()
            
            return render_template('advisor/advisor_booking.html',
                                 advisor=advisor_info,
                                 rates=rates,
                                 availability=availability,
                                 user=user,
                                 today_date=datetime.now().strftime('%Y-%m-%d'))
        except Exception as e:
            print(f"Error loading booking form: {str(e)}")
            return render_template('error.html', message=f"Error loading booking form: {str(e)}")


    # ============================================
    # MY BOOKINGS (FARMER & ALL ROLES)
    # ============================================

    @app.route('/my-bookings', methods=['GET'])
    def my_bookings():
        """Display user's advisor bookings"""
        if 'user' not in session:
            return redirect(url_for('login_register'))
        
        user = session.get('user')
        user_role = user.get('role')
        person_id = user.get('person_id')
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            ensure_notification_table(cursor)
            
            bookings = []
            
            if user_role == 'FARMER':
                farmer_id = user.get('farmer_id') or user.get('farmer_code')
                if not farmer_id:
                    cursor.execute("SELECT farmer_code FROM FARMER WHERE person_id = ?", (person_id,))
                    f_row = cursor.fetchone()
                    farmer_id = f_row[0] if f_row else person_id
                
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
                        AB.advisor_id,
                        AB.notes,
                        AR.rating as given_rating,
                        AR.review as given_review
                    FROM ADVISOR_BOOKING AB
                    JOIN ADVISOR A ON AB.advisor_id = A.advisor_id
                    JOIN PERSON P ON A.person_id = P.person_id
                    LEFT JOIN ADVISOR_RATING AR ON AB.booking_id = AR.booking_id
                    WHERE AB.farmer_id = ?
                    ORDER BY AB.booking_date DESC, AB.scheduled_date DESC
                """, (farmer_id,))
                bookings = cursor.fetchall()
            
            elif user_role == 'ADVISOR':
                cursor.execute("SELECT advisor_id FROM ADVISOR WHERE person_id = ?", (person_id,))
                adv_row = cursor.fetchone()
                advisor_id = adv_row[0] if adv_row else user.get('advisor_id')
                
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
                        COALESCE(A.rating, 5.0) as rating,
                        AB.farmer_id,
                        AB.notes,
                        AR.rating as given_rating,
                        AR.review as given_review
                    FROM ADVISOR_BOOKING AB
                    JOIN FARMER F ON AB.farmer_id = F.farmer_code
                    JOIN PERSON P ON F.person_id = P.person_id
                    JOIN ADVISOR A ON AB.advisor_id = A.advisor_id
                    LEFT JOIN ADVISOR_RATING AR ON AB.booking_id = AR.booking_id
                    WHERE AB.advisor_id = ?
                    ORDER BY AB.booking_date DESC, AB.scheduled_date DESC
                """, (advisor_id,))
                bookings = cursor.fetchall()
            
            elif user_role == 'ADMIN':
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
                        COALESCE(A.rating, 5.0) as rating,
                        AB.advisor_id,
                        AB.notes,
                        AR.rating as given_rating,
                        AR.review as given_review
                    FROM ADVISOR_BOOKING AB
                    JOIN ADVISOR A ON AB.advisor_id = A.advisor_id
                    JOIN PERSON P ON A.person_id = P.person_id
                    LEFT JOIN ADVISOR_RATING AR ON AB.booking_id = AR.booking_id
                    ORDER BY AB.booking_date DESC, AB.scheduled_date DESC
                """)
                bookings = cursor.fetchall()
            
            conn.close()
            
            return render_template('advisor/my_bookings.html',
                                 bookings=bookings,
                                 user=user,
                                 user_role=user_role)
        
        except Exception as e:
            print(f"Error fetching bookings: {str(e)}")
            import traceback
            traceback.print_exc()
            return render_template('error.html', message=f"Error loading bookings: {str(e)}")


    # ============================================
    # RATE A COMPLETED CONSULTATION
    # ============================================

    @app.route('/advisor/<int:booking_id>/rate', methods=['POST'])
    def rate_booking(booking_id):
        """Submit rating for a completed booking and notify the advisor"""
        if 'user' not in session:
            return redirect(url_for('login_register'))
        
        user = session.get('user')
        person_id = user.get('person_id')
        
        if user.get('role') != 'FARMER':
            return jsonify({'error': 'Only farmers can rate bookings'}), 403
        
        try:
            rating = int(request.form.get('rating', 5))
            review = request.form.get('review', '').strip()
            
            if rating < 1 or rating > 5:
                return jsonify({'error': 'Rating must be between 1 and 5'}), 400
            
            conn = get_connection()
            cursor = conn.cursor()
            ensure_notification_table(cursor)
            
            cursor.execute("""
                SELECT AB.advisor_id, AB.farmer_id, A.person_id, P.first_name, P.last_name
                FROM ADVISOR_BOOKING AB
                JOIN ADVISOR A ON AB.advisor_id = A.advisor_id
                JOIN PERSON P ON A.person_id = P.person_id
                WHERE AB.booking_id = ?
            """, (booking_id,))
            booking = cursor.fetchone()
            
            if not booking:
                conn.close()
                return jsonify({'error': 'Booking not found'}), 404
            
            advisor_id, farmer_id, adv_person_id, adv_first, adv_last = booking
            
            # Check if already rated
            cursor.execute("SELECT COUNT(*) FROM ADVISOR_RATING WHERE booking_id = ?", (booking_id,))
            if cursor.fetchone()[0] > 0:
                cursor.execute("UPDATE ADVISOR_RATING SET rating = ?, review = ? WHERE booking_id = ?", (rating, review, booking_id))
            else:
                cursor.execute("""
                    INSERT INTO ADVISOR_RATING (booking_id, advisor_id, farmer_id, rating, review)
                    VALUES (?, ?, ?, ?, ?)
                """, (booking_id, advisor_id, farmer_id, rating, review))
            
            # Recalculate advisor average rating
            cursor.execute("""
                SELECT AVG(rating) as avg_rating, COUNT(*) as total_ratings
                FROM ADVISOR_RATING
                WHERE advisor_id = ?
            """, (advisor_id,))
            result = cursor.fetchone()
            avg_rating = round(result[0], 2) if result[0] else 5.0
            
            cursor.execute("""
                UPDATE ADVISOR
                SET rating = ?
                WHERE advisor_id = ?
            """, (avg_rating, advisor_id))
            
            # Send NOTIFICATION to ADVISOR
            farmer_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            add_notification(
                cursor,
                adv_person_id,
                f"⭐ নতুন রেটিং পেয়েছেন ({rating}/5)! / New Review Received!",
                f"কৃষক {farmer_name} বুকিং #{booking_id}-এর জন্য {rating} তারকা রেটিং দিয়েছেন: \"{review[:80]}\"",
                url_for('advisor_dashboard')
            )
            
            conn.commit()
            conn.close()
            
            flash('রেটিং এবং পর্যালোচনা সফলভাবে জমা দেওয়া হয়েছে! / Rating submitted successfully!', 'success')
            return redirect(url_for('my_bookings'))
        
        except Exception as e:
            print(f"Error rating booking: {str(e)}")
            flash(f"Error: {str(e)}", 'danger')
            return redirect(url_for('my_bookings'))
