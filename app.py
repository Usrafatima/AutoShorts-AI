import os
import uuid
import threading
from flask import Flask, render_template, request, jsonify, send_from_directory
from run_pipeline import run_pipeline

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'shorts_output'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Global dictionary to track job status
jobs = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    """
    Receives video file and starts the processing pipeline in a background thread.
    """
    if 'video' not in request.files:
        return jsonify({'error': 'No video part'}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # Get parameters from request (if provided by frontend)
    num_shorts = int(request.form.get('num_shorts', 3))
    model_size = request.form.get('model_size', 'base')
    
    # Save the uploaded file with a unique name to avoid collisions
    job_id = uuid.uuid4().hex
    filename = f"{job_id}_{file.filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    # Initialize job status
    jobs[job_id] = {
        'status': 'processing',
        'filename': filename,
        'shorts': []
    }
    
    # Start the pipeline in the background so the response is immediate
    thread = threading.Thread(target=process_video_task, args=(job_id, filepath, num_shorts, model_size))
    thread.start()
    
    return jsonify({
        'job_id': job_id,
        'message': 'Processing started'
    })

def process_video_task(job_id, video_path, num_shorts, model_size):
    """
    Worker function to run the pipeline in a background thread.
    """
    try:
        # Run the integrated pipeline
        run_pipeline(video_path, output_dir=app.config['OUTPUT_FOLDER'], num_shorts=num_shorts, model_size=model_size)
        
        # After pipeline finishes, list the generated shorts
        # Note: run_pipeline saves files as short_1.mp4, short_2.mp4, etc.
        # For a real multi-user app, we'd use job-specific subfolders.
        generated_files = [f for f in os.listdir(app.config['OUTPUT_FOLDER']) if f.endswith('.mp4')]
        
        jobs[job_id]['status'] = 'completed'
        jobs[job_id]['shorts'] = generated_files
    except Exception as e:
        print(f"Pipeline Error for job {job_id}: {str(e)}")
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['error'] = str(e)

@app.route('/status/<job_id>')
def get_status(job_id):
    """
    Returns the current status of a specific processing job.
    """
    job_info = jobs.get(job_id)
    if not job_info:
        return jsonify({'status': 'not_found'}), 404
    return jsonify(job_info)

@app.route('/download/<filename>')
def download_file(filename):
    """
    Serves the processed shorts for download.
    """
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

if __name__ == '__main__':
    # Using threaded=True to ensure multiple requests (like polling) can be handled while processing
    app.run(debug=True, port=5000, threaded=True)
