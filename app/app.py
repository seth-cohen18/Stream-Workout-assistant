from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
import json

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Create uploads folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Store user progress in a simple file-based system
USER_DATA_FILE = 'user_data.json'

def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r') as f:
            return json.load(f)
    return {
        "exercises": {
            "Squats": {"total_reps": 0, "history": []},
            "Bicep Curls": {"total_reps": 0, "history": []},
            "Push-Ups": {"total_reps": 0, "history": []},
            "Shoulder Press": {"total_reps": 0, "history": []},
            "Lunges": {"total_reps": 0, "history": []}
        },
        "level": 1,
        "level_progress": 35
    }

def save_user_data(data):
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(data, f)

@app.route('/')
def index():
    user_data = load_user_data()
    return render_template('index.html', user_data=user_data)

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/api/save_workout', methods=['POST'])
def save_workout():
    data = request.json
    user_data = load_user_data()
    
    exercise = data.get('exercise')
    reps = data.get('reps', 0)
    duration = data.get('duration', 0)
    calories = data.get('calories', 0)
    
    if exercise in user_data["exercises"]:
        user_data["exercises"][exercise]["total_reps"] += reps
        user_data["exercises"][exercise]["history"].append({
            "date": data.get('date'),
            "reps": reps,
            "duration": duration,
            "calories": calories
        })
        
        # Update level progress
        user_data["level_progress"] += reps / 5
        if user_data["level_progress"] >= 100:
            user_data["level"] += 1
            user_data["level_progress"] = user_data["level_progress"] - 100
    
    save_user_data(user_data)
    return jsonify({"success": True, "user_data": user_data})

@app.route('/api/upload_video', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({"error": "No video file provided"}), 400
        
    file = request.files['video']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
        
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        return jsonify({"success": True, "filename": filename, "path": file_path})
    
    return jsonify({"error": "Upload failed"}), 500

if __name__ == '__main__':
    app.run(debug=True)