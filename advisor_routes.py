# ============================================================
# advisor_routes.py — Oracle-native, wired to real schema.
# Notifications fire via DB triggers automatically.
# ============================================================

from flask import render_template, request, redirect, url_for, session, flash, jsonify
from db_connect import get_connection
from datetime import datetime
from advisor_queries import (
    get_advisor_by_person, get_advisor_by_id, get_advisor_rates,
    get_advisor_availability, list_all_advisors, upsert_advisor_rate,
    replace_availability, get_bookings_for_advisor, get_bookings_for_farmer,
    get_advisor_reviews, get_user_notifications, count_unread_notifications,
    create_booking, update_booking_status, complete_booking,
    upsert_booking_rating, update_advisor_profile, toggle_advisor_availability,
    mark_notification_read, mark_all_notifications_read,
)


def get_lang():
    return session.get('language', 'bn')


def get_flash_message(bn_msg, en_msg):
    return bn_msg if get_lang() == 'bn' else en_msg


def register_advisor_routes(app):

    # ---------- NOTIFICATIONS API ----------

    @app.route('/api/notifications')
    def api_notifications():
        if 'user' not in session:
            return jsonify({'notifications': [], 'unread_count': 0})
        person_id = session['user'].get('person_id')
        conn = get_connection()
        if not conn:
            return jsonify({'error': 'DB error'}), 500
        cursor = conn.cursor()
        try:
            rows = get_user_notifications(cursor, person_id, limit=20)
            unread = count_unread_notifications(cursor, person_id)
            notifications = [{
                'id': r[0], 'title': r[1], 'message': r[2], 'link': r[3],
                'is_read': r[4] == 'YES', 'created_at': r[5], 'type': r[6],
            } for r in rows]
            return jsonify({'notifications': notifications, 'unread_count': unread})
        finally:
            cursor.close()
            conn.close()

    @app.route('/api/notifications/<notif_id>/read', methods=['POST'])
    def api_mark_read(notif_id):
        if 'user' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        person_id = session['user'].get('person_id')
        conn = get_connection()
        if not conn:
            return jsonify({'error': 'DB error'}), 500
        cursor = conn.cursor()
        try:
            mark_notification_read(cursor, notif_id, person_id)
            conn.commit()
            return jsonify({'success': True})
        except Exception as e:
            conn.rollback()
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()

    @app.route('/api/notifications/read-all', methods=['POST'])
    def api_mark_all_read():
        if 'user' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        person_id = session['user'].get('person_id')
        conn = get_connection()
        if not conn:
            return jsonify({'error': 'DB error'}), 500
        cursor = conn.cursor()
        try:
            mark_all_notifications_read(cursor, person_id)
            conn.commit()
            return jsonify({'success': True})
        except Exception as e:
            conn.rollback()
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()

    # ---------- ADVISOR DASHBOARD ----------

    @app.route('/advisor/dashboard')
    def advisor_dashboard():
        if 'user' not in session or session['user']['role'] not in ['ADVISOR', 'ADMIN']:
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))

        person_id = session['user']['person_id']
        conn = get_connection()
        if not conn:
            flash(get_flash_message('ডেটাবেস সংযোগ ব্যর্থ।', 'DB connection failed.'), 'danger')
            return redirect(url_for('login_register'))

        cursor = conn.cursor()
        try:
            row = get_advisor_by_person(cursor, person_id)
            if not row:
                flash(get_flash_message('উপদেষ্টা প্রোফাইল পাওয়া যায়নি।',
                                        'Advisor profile not found.'), 'warning')
                return redirect(url_for('dashboard'))

            advisor = {
                'advisor_id': row[0], 'person_id': row[1], 'first_name': row[2],
                'last_name': row[3], 'phone': row[4], 'specialization': row[5],
                'bio': row[6], 'experience_years': row[7], 'qualification': row[8],
                'rating': float(row[9] or 5.0), 'total_bookings': row[10],
                'is_available': row[11],
            }
            advisor_id = advisor['advisor_id']

            rates_rows = get_advisor_rates(cursor, advisor_id)
            rates = {r[0]: float(r[1]) for r in rates_rows}
            rates.setdefault('HOURLY', 500.0)
            rates.setdefault('DAILY', 3500.0)

            availability = get_advisor_availability(cursor, advisor_id)
            all_bookings = get_bookings_for_advisor(cursor, advisor_id)

            pending, upcoming, completed, cancelled = [], [], [], []
            total_earnings = 0.0
            for r in all_bookings:
                b = {
                    'booking_id': r[0], 'scheduled_date': r[1],
                    'start_time': r[2], 'end_time': r[3],
                    'duration_hours': r[4], 'rate_type': r[5],
                    'total_amount': float(r[6] or 0),
                    'payment_status': r[7], 'booking_status': r[8],
                    'consultation_topic': r[9], 'notes': r[10],
                    'farmer_name': r[11], 'farmer_phone': r[12],
                    'farmer_id': r[13], 'booking_date': r[14],
                    'rating': r[15], 'review': r[16],
                }
                if b['booking_status'] == 'PENDING':    pending.append(b)
                elif b['booking_status'] == 'CONFIRMED': upcoming.append(b)
                elif b['booking_status'] == 'COMPLETED':
                    completed.append(b)
                    total_earnings += b['total_amount']
                elif b['booking_status'] == 'CANCELLED': cancelled.append(b)

            reviews = get_advisor_reviews(cursor, advisor_id, limit=10)
            notifications = get_user_notifications(cursor, person_id, limit=10)

            stats = {
                'total_earnings': total_earnings,
                'total_completed': len(completed),
                'pending_requests': len(pending),
                'upcoming_sessions': len(upcoming),
                'total_bookings': len(all_bookings),
                'rating': advisor['rating'],
                'reviews_count': len(reviews),
            }

            return render_template('dashboard_advisor.html',
                                   advisor=advisor, stats=stats, rates=rates,
                                   availability=availability,
                                   pending_bookings=pending,
                                   upcoming_bookings=upcoming,
                                   completed_bookings=completed,
                                   cancelled_bookings=cancelled,
                                   all_bookings=all_bookings, reviews=reviews,
                                   notifications=notifications,
                                   user=session['user'])
        except Exception as e:
            print(f"Advisor dashboard error: {e}")
            import traceback; traceback.print_exc()
            flash(f'Error: {e}', 'danger')
            return redirect(url_for('dashboard'))
        finally:
            cursor.close()
            conn.close()

    # ---------- BOOKING ACTIONS ----------

    @app.route('/advisor/booking/<int:booking_id>/action', methods=['POST'])
    def advisor_booking_action(booking_id):
        if 'user' not in session or session['user']['role'] != 'ADVISOR':
            flash(get_flash_message('অনুমোদিত নয়।', 'Unauthorized.'), 'danger')
            return redirect(url_for('login_register'))

        action = request.form.get('action', '').upper()
        notes = request.form.get('notes', '').strip()

        conn = get_connection()
        cursor = conn.cursor()
        try:
            if action == 'ACCEPT':
                update_booking_status(cursor, booking_id, 'CONFIRMED', notes or None)
                flash(get_flash_message('বুকিং নিশ্চিত হয়েছে।', 'Booking confirmed.'), 'success')
            elif action == 'COMPLETE':
                complete_booking(cursor, booking_id)
                flash(get_flash_message('পরামর্শ সম্পন্ন।', 'Consultation completed.'), 'success')
            elif action in ('REJECT', 'CANCEL'):
                update_booking_status(cursor, booking_id, 'CANCELLED', notes or None)
                flash(get_flash_message('বুকিং বাতিল।', 'Booking cancelled.'), 'warning')
            conn.commit()
        except Exception as e:
            conn.rollback()
            flash(f'Error: {e}', 'danger')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('advisor_dashboard'))

    @app.route('/advisor/booking/<int:booking_id>/notes', methods=['POST'])
    def advisor_add_notes(booking_id):
        if 'user' not in session or session['user']['role'] != 'ADVISOR':
            return redirect(url_for('login_register'))
        notes = request.form.get('notes', '').strip()
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE ADVISOR_BOOKING SET NOTES = :1 WHERE BOOKING_ID = :2",
                           (notes, booking_id))
            conn.commit()
            flash(get_flash_message('নোট সংরক্ষিত।', 'Notes saved.'), 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error: {e}', 'danger')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('advisor_dashboard'))

    # ---------- PROFILE / RATES / AVAILABILITY ----------

    @app.route('/advisor/status/toggle', methods=['POST'])
    def advisor_toggle_status():
        if 'user' not in session or session['user']['role'] != 'ADVISOR':
            return jsonify({'error': 'Unauthorized'}), 401
        person_id = session['user']['person_id']
        conn = get_connection()
        if not conn:
            return jsonify({'error': 'DB error'}), 500
        cursor = conn.cursor()
        try:
            new_val = toggle_advisor_availability(cursor, person_id)
            conn.commit()
            session['user']['is_available'] = new_val
            session.modified = True
            return jsonify({'success': True, 'is_available': new_val})
        except Exception as e:
            conn.rollback()
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()

    @app.route('/advisor/profile/update', methods=['POST'])
    def advisor_update_profile():
        if 'user' not in session or session['user']['role'] != 'ADVISOR':
            return redirect(url_for('login_register'))
        person_id = session['user']['person_id']
        specialization = request.form.get('specialization', '').strip()
        bio = request.form.get('bio', '').strip()
        qualification = request.form.get('qualification', '').strip()
        try:
            exp = int(request.form.get('experience_years', '0') or 0)
        except ValueError:
            exp = 0
        phone = request.form.get('phone', '').strip() or None

        conn = get_connection()
        cursor = conn.cursor()
        try:
            update_advisor_profile(cursor, person_id, specialization, bio,
                                    qualification, exp, phone)
            conn.commit()
            flash(get_flash_message('প্রোফাইল আপডেট হয়েছে।', 'Profile updated.'), 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error: {e}', 'danger')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('advisor_dashboard'))

    @app.route('/advisor/rates/update', methods=['POST'])
    def advisor_update_rates():
        if 'user' not in session or session['user']['role'] != 'ADVISOR':
            return redirect(url_for('login_register'))
        person_id = session['user']['person_id']
        try:
            hourly = float(request.form.get('hourly_rate', 500))
            daily = float(request.form.get('daily_rate', 3500))
        except ValueError:
            flash(get_flash_message('অবৈধ ফি।', 'Invalid rate.'), 'danger')
            return redirect(url_for('advisor_dashboard'))

        conn = get_connection()
        cursor = conn.cursor()
        try:
            row = get_advisor_by_person(cursor, person_id)
            if not row:
                flash('Advisor not found.', 'danger')
                return redirect(url_for('advisor_dashboard'))
            upsert_advisor_rate(cursor, row[0], 'HOURLY', hourly)
            upsert_advisor_rate(cursor, row[0], 'DAILY', daily)
            conn.commit()
            flash(get_flash_message('ফি আপডেট হয়েছে।', 'Rates updated.'), 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error: {e}', 'danger')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('advisor_dashboard'))

    @app.route('/advisor/availability/update', methods=['POST'])
    def advisor_update_availability():
        if 'user' not in session or session['user']['role'] != 'ADVISOR':
            return redirect(url_for('login_register'))
        person_id = session['user']['person_id']
        days = request.form.getlist('days')
        start_time = request.form.get('start_time', '09:00')
        end_time = request.form.get('end_time', '17:00')

        conn = get_connection()
        cursor = conn.cursor()
        try:
            row = get_advisor_by_person(cursor, person_id)
            if not row:
                flash('Advisor not found.', 'danger')
                return redirect(url_for('advisor_dashboard'))
            replace_availability(cursor, row[0], days, start_time, end_time)
            conn.commit()
            flash(get_flash_message('সময়সূচী সংরক্ষিত।', 'Schedule saved.'), 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error: {e}', 'danger')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('advisor_dashboard'))

    # ---------- PUBLIC LISTING + PROFILE ----------

    @app.route('/advisors')
    @app.route('/advisor/listing')
    def advisor_listing():
        if 'user' not in session:
            return redirect(url_for('login_register'))
        search = request.args.get('q', '').strip()
        specialization = request.args.get('specialization', '').strip()
        only_available = request.args.get('availability') == 'YES'

        conn = get_connection()
        cursor = conn.cursor()
        try:
            rows = list_all_advisors(cursor, search, specialization, only_available)
            advisors = [{
                'advisor_id': r[0], 'first_name': r[1], 'last_name': r[2],
                'phone': r[3], 'specialization': r[4], 'bio': r[5],
                'experience_years': r[6], 'qualification': r[7],
                'rating': float(r[8] or 5.0), 'total_bookings': r[9],
                'is_available': r[10],
                'rates': get_advisor_rates(cursor, r[0]),
            } for r in rows]
            return render_template('advisor/advisor_listing.html',
                                   advisors=advisors,
                                   search_query=search,
                                   selected_specialization=specialization,
                                   availability='YES' if only_available else '',
                                   user=session['user'])
        finally:
            cursor.close()
            conn.close()

    @app.route('/advisor/<int:advisor_id>')
    @app.route('/advisor/<int:advisor_id>/profile')
    def advisor_profile(advisor_id):
        if 'user' not in session:
            return redirect(url_for('login_register'))
        conn = get_connection()
        cursor = conn.cursor()
        try:
            adv = get_advisor_by_id(cursor, advisor_id)
            if not adv:
                flash(get_flash_message('উপদেষ্টা পাওয়া যায়নি।', 'Advisor not found.'), 'warning')
                return redirect(url_for('advisor_listing'))
            rates = get_advisor_rates(cursor, advisor_id)
            availability = get_advisor_availability(cursor, advisor_id)
            ratings = get_advisor_reviews(cursor, advisor_id, limit=5)
            return render_template('advisor/advisor_profile.html',
                                   advisor=adv, rates=rates,
                                   availability=availability, ratings=ratings,
                                   user=session['user'])
        finally:
            cursor.close()
            conn.close()

    # ---------- BOOK ADVISOR ----------

    @app.route('/advisor/<int:advisor_id>/book', methods=['GET', 'POST'])
    def book_advisor(advisor_id):
        if 'user' not in session:
            return redirect(url_for('login_register'))
        if session['user']['role'] != 'FARMER':
            flash(get_flash_message('শুধুমাত্র কৃষকরা বুক করতে পারবেন।',
                                    'Only farmers can book.'), 'warning')
            return redirect(url_for('advisor_listing'))

        farmer_code = session['user'].get('farmer_code')
        if not farmer_code:
            flash(get_flash_message('কৃষক কোড পাওয়া যায়নি।',
                                    'Farmer code not found.'), 'danger')
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            try:
                scheduled = request.form.get('scheduled_date')
                start_time = request.form.get('start_time', '10:00')
                end_time = request.form.get('end_time', '11:00')
                rate_type = request.form.get('rate_type', 'HOURLY')
                topic = request.form.get('consultation_topic', 'সাধারণ কৃষি পরামর্শ')

                if rate_type == 'DAILY':
                    duration = 8.0
                    end_time = '17:00'
                else:
                    try:
                        s = datetime.strptime(start_time, '%H:%M')
                        e = datetime.strptime(end_time, '%H:%M')
                        duration = max(1.0, (e - s).total_seconds() / 3600)
                    except ValueError:
                        duration = 1.0

                conn = get_connection()
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT AMOUNT FROM ADVISOR_RATE
                    WHERE ADVISOR_ID = :1 AND RATE_TYPE = :2
                """, (advisor_id, rate_type))
                rate_row = cursor.fetchone()
                rate_amount = float(rate_row[0]) if rate_row else (500.0 if rate_type == 'HOURLY' else 3500.0)
                total = rate_amount * (1 if rate_type == 'DAILY' else duration)

                agent_code = session['user'].get('agent_code')

                booking_id = create_booking(
                    cursor, advisor_id, farmer_code, agent_code,
                    scheduled, start_time, end_time, duration,
                    rate_type, total, topic
                )
                conn.commit()
                flash(get_flash_message(f'বুকিং #{booking_id} পাঠানো হয়েছে।',
                                        f'Booking #{booking_id} sent.'), 'success')
                return redirect(url_for('my_bookings'))
            except Exception as e:
                try: conn.rollback()
                except: pass
                print(f"Book error: {e}")
                import traceback; traceback.print_exc()
                flash(f'Error: {e}', 'danger')
                return redirect(url_for('advisor_listing'))
            finally:
                try: cursor.close(); conn.close()
                except: pass

        # GET — show form
        conn = get_connection()
        cursor = conn.cursor()
        try:
            adv = get_advisor_by_id(cursor, advisor_id)
            if not adv:
                flash('Advisor not found.', 'danger')
                return redirect(url_for('advisor_listing'))
            rates = get_advisor_rates(cursor, advisor_id)
            availability = get_advisor_availability(cursor, advisor_id)
            return render_template('advisor/advisor_booking.html',
                                   advisor=adv, rates=rates,
                                   availability=availability,
                                   user=session['user'],
                                   today_date=datetime.now().strftime('%Y-%m-%d'))
        finally:
            cursor.close()
            conn.close()

    # ---------- MY BOOKINGS ----------

    @app.route('/my-bookings')
    def my_bookings():
        if 'user' not in session:
            return redirect(url_for('login_register'))
        role = session['user']['role']
        conn = get_connection()
        cursor = conn.cursor()
        try:
            bookings = []
            if role == 'FARMER':
                fc = session['user'].get('farmer_code')
                if fc:
                    bookings = get_bookings_for_farmer(cursor, fc)
            elif role == 'ADVISOR':
                row = get_advisor_by_person(cursor, session['user']['person_id'])
                if row:
                    bookings = get_bookings_for_advisor(cursor, row[0])
            elif role == 'ADMIN':
                cursor.execute("""
                    SELECT B.BOOKING_ID,
                           TO_CHAR(B.SCHEDULED_DATE, 'YYYY-MM-DD'),
                           B.START_TIME, B.END_TIME, B.RATE_TYPE,
                           B.TOTAL_AMOUNT, B.PAYMENT_STATUS, B.BOOKING_STATUS,
                           B.CONSULTATION_TOPIC,
                           P.FIRST_NAME || ' ' || P.LAST_NAME,
                           A.SPECIALIZATION, NVL(A.RATING, 5.0),
                           B.ADVISOR_ID, B.NOTES,
                           NVL(R.RATING, 0), R.REVIEW
                    FROM ADVISOR_BOOKING B
                    JOIN ADVISOR A ON B.ADVISOR_ID = A.ADVISOR_ID
                    JOIN PERSON P ON A.PERSON_ID = P.PERSON_ID
                    LEFT JOIN ADVISOR_RATING R ON B.BOOKING_ID = R.BOOKING_ID
                    ORDER BY B.BOOKING_DATE DESC
                """)
                bookings = cursor.fetchall()

            return render_template('advisor/my_bookings.html',
                                   bookings=bookings,
                                   user=session['user'],
                                   user_role=role)
        finally:
            cursor.close()
            conn.close()

    # ---------- RATE A BOOKING ----------

    @app.route('/advisor/<int:booking_id>/rate', methods=['POST'])
    def rate_booking(booking_id):
        if 'user' not in session or session['user']['role'] != 'FARMER':
            flash(get_flash_message('শুধুমাত্র কৃষকরা রেটিং দিতে পারবেন।',
                                    'Only farmers can rate.'), 'warning')
            return redirect(url_for('my_bookings'))

        farmer_code = session['user'].get('farmer_code')
        try:
            rating = int(request.form.get('rating', 5))
            review = request.form.get('review', '').strip()
            if not 1 <= rating <= 5:
                raise ValueError
        except (ValueError, TypeError):
            flash(get_flash_message('অবৈধ রেটিং।', 'Invalid rating.'), 'danger')
            return redirect(url_for('my_bookings'))

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT ADVISOR_ID FROM ADVISOR_BOOKING
                WHERE BOOKING_ID = :1 AND FARMER_ID = :2
            """, (booking_id, farmer_code))
            row = cursor.fetchone()
            if not row:
                flash(get_flash_message('বুকিং পাওয়া যায়নি।', 'Booking not found.'), 'warning')
                return redirect(url_for('my_bookings'))

            upsert_booking_rating(cursor, booking_id, row[0], farmer_code, rating, review)
            conn.commit()
            flash(get_flash_message('রেটিং জমা হয়েছে।', 'Rating submitted.'), 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error: {e}', 'danger')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('my_bookings'))
    