from flask import render_template, redirect, url_for, session, flash
from db_connect import get_connection


def register_admin_alerts_routes(app):

    @app.route('/admin/alerts')
    def admin_alerts():
        if 'user' not in session or session['user'].get('role') != 'ADMIN':
            flash('Admin access required.', 'danger')
            return redirect(url_for('login_register'))

        restock, inv_audit, order_notifs, kyc_notifs = [], [], [], []
        counts = {'restock': 0, 'audit': 0, 'orders': 0, 'kyc': 0}

        conn = get_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    SELECT restock_id, NVL(inventory_id,'-'),
                           NVL(item_name,'-'), NVL(current_qty,0),
                           NVL(min_stock_level,0), NVL(shortfall,0),
                           NVL(center_code,'-'),
                           TO_CHAR(flagged_date,'DD-Mon-YYYY HH24:MI'),
                           NVL(restock_status,'-')
                    FROM RESTOCK
                    WHERE restock_status = 'PENDING'
                    ORDER BY flagged_date DESC
                """)
                restock = cursor.fetchall()
                counts['restock'] = len(restock)

                cursor.execute("""
                    SELECT * FROM (
                        SELECT audit_id, NVL(item_name,'-'),
                               NVL(old_quantity,0), NVL(new_quantity,0),
                               NVL(change_amount,0), NVL(action_type,'-'),
                               TO_CHAR(changed_at,'DD-Mon-YYYY HH24:MI')
                        FROM INVENTORY_AUDIT
                        ORDER BY audit_id DESC
                    ) WHERE ROWNUM <= 20
                """)
                inv_audit = cursor.fetchall()
                counts['audit'] = len(inv_audit)

                cursor.execute("""
                    SELECT notif_id, NVL(title,'-'), NVL(message,'-'),
                           NVL(is_read,'NO'),
                           TO_CHAR(created_at,'DD-Mon-YYYY HH24:MI')
                    FROM NOTIFICATION
                    WHERE notification_type = 'ORDER'
                    ORDER BY created_at DESC
                """)
                order_notifs = cursor.fetchall()
                counts['orders'] = len(order_notifs)

                cursor.execute("""
                    SELECT notif_id, NVL(title,'-'), NVL(message,'-'),
                           NVL(is_read,'NO'),
                           TO_CHAR(created_at,'DD-Mon-YYYY HH24:MI')
                    FROM NOTIFICATION
                    WHERE notification_type = 'KYC'
                    ORDER BY created_at DESC
                """)
                kyc_notifs = cursor.fetchall()
                counts['kyc'] = len(kyc_notifs)
            except Exception as e:
                flash(f'Alerts Error: {e}', 'danger')
                import traceback; traceback.print_exc()
            finally:
                cursor.close(); conn.close()

        return render_template('admin_alerts.html',
                               restock=restock, inv_audit=inv_audit,
                               order_notifs=order_notifs, kyc_notifs=kyc_notifs, counts=counts)
