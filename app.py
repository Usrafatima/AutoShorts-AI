import os
import uuid
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'shorts_output'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'error': 'No video'}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No file'}), 400
    
    # Save file (Mock)
    filename = f"{uuid.uuid4().hex}_{file.filename}"
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    return jsonify({
        'job_id': uuid.uuid4().hex,
        'filename': filename
    })

@app.route('/status/<job_id>')
def get_status(job_id):
    # Dummy status for the frontend to poll
    return jsonify({'status': 'processing'})

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
