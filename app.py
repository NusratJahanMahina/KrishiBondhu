from flask import Flask, send_from_directory
from login_register import register_login_routes
from admin_routes import register_admin_routes
from agent_routes import register_agent_routes
import os

app = Flask(__name__)
app.secret_key = 'krishibondhu_secret_key_2025'
app.permanent_session_lifetime = 3600

@app.route('/images/<filename>')
def serve_image(filename):
    try:
        # Path to your Downloads folder
        downloads_path = r'C:\Users\Mahina\Downloads'
        return send_from_directory(downloads_path, filename)
    except Exception as e:
        print(f"Error serving image: {e}")
        return "Image not found", 404


register_login_routes(app)
register_admin_routes(app)
register_agent_routes(app)

if __name__ == '__main__':
    app.run(debug=True, port=5000)