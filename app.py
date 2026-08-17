from flask import Flask
from login_register import register_login_routes
from agent_routes import register_agent_routes   # 👈 ADD THIS

app = Flask(__name__)
app.secret_key = 'krishibondhu_secret_key_2025'
app.permanent_session_lifetime = 3600

# Register all routes
register_login_routes(app)
register_agent_routes(app)   # 👈 ADD THIS

if __name__ == '__main__':
    app.run(debug=True, port=5000)