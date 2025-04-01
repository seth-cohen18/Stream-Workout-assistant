# main.py
from flask import Flask, render_template, request, jsonify
from app.app_manager import AppManager

app = Flask(__name__)
app_manager = AppManager()

@app.route('/')
def index():
    return render_template('index.html',
                           exercise_options=["Squats", "Bicep Curls", "Push-Ups"],
                           profile=app_manager.get_profile())

@app.route('/start_session', methods=['POST'])
def start_session():
    chosen_exercise = request.json.get('exercise')
    if chosen_exercise:
        app_manager.start_session(chosen_exercise)
        return jsonify({"status": "session started", "exercise": chosen_exercise})
    else:
        return jsonify({"status": "error", "message": "No exercise selected"}), 400

@app.route('/process_frame', methods=['POST'])
def process_frame():
    data = request.json.get('image')
    header, encoded = data.split(',', 1)
    import base64, numpy as np, cv2
    frame_data = base64.b64decode(encoded)
    np_arr = np.frombuffer(frame_data, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    frame = cv2.flip(frame, 1)  # Mirror the frame.
    
    processed_frame, rep_count, session_data = app_manager.process_frame(frame)
    
    ret, buffer = cv2.imencode('.jpg', processed_frame)
    response_image = base64.b64encode(buffer).decode('utf-8')
    return jsonify({
        "image": "data:image/jpeg;base64," + response_image,
        "rep_count": rep_count,
        "session_data": session_data
    })

@app.route('/end_session', methods=['POST'])
def end_session():
    saved, summary = app_manager.end_session()
    return jsonify({"status": "session ended", "saved": saved, "summary": summary, "profile": app_manager.get_profile()})

if __name__ == '__main__':
    app.run(debug=True)
