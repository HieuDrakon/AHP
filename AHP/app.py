# app.py
from flask import Flask, render_template
from flask_cors import CORS
from config import Config
from ahp_api import ahp_bp

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Register Blueprints
app.register_blueprint(ahp_bp)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
