from flask import Flask, render_template
from db_connect import get_connection

app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>KrishiBondhu</h1><p>Welcome to the Farmer Management System!</p>"

if __name__ == '__main__':
    app.run(debug=True)

    