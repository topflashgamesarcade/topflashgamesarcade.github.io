# api/index.py - Vercel Serverless Function
from flask import Flask, request, jsonify
from datetime import datetime
import json

app = Flask(__name__)

@app.route('/api/test', methods=['GET'])
def test():
    return jsonify({
        'status': 'Server is running!',
        'time': datetime.now().isoformat()
    })

@app.route('/api/verify', methods=['POST'])
def verify_license():
    try:
        data = request.json
        return jsonify({'valid': True, 'message': 'License verified!'})
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)})

@app.route('/api/activate', methods=['POST'])
def activate_license():
    try:
        data = request.json
        return jsonify({'success': True, 'message': 'License activated!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Vercel handler
def handler(request, context):
    return app(request.environ, context)
