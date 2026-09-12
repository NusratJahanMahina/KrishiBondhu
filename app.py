import os
from flask import Flask, session
from login_register import register_login_routes
from agent_routes import register_agent_routes
from advisor_routes import register_advisor_routes
from admin_routes import register_admin_routes

app = Flask(__name__)
app.secret_key = 'krishibondhu_secret_key_2025'
app.permanent_session_lifetime = 3600

@app.before_request
def set_default_language():
    if 'language' not in session:
        session['language'] = 'bn'

# Register all routes
register_login_routes(app)   
register_agent_routes(app)
register_advisor_routes(app)
register_admin_routes(app)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    app.run(debug=True, port=port)
