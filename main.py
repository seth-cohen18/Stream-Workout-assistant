# main.py
from flask import Flask, render_template, request, jsonify, send_from_directory, make_response, send_file
import os
import json
import base64
import numpy as np
import cv2
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
from app.app_manager import AppManager

app = Flask(__name__)
app_manager = AppManager()

# Create necessary directories
os.makedirs('static/img', exist_ok=True)
os.makedirs('uploads', exist_ok=True)
os.makedirs('static/temp', exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html',
                           exercise_options=list(app_manager.profile.keys()),
                           profile=app_manager.get_profile())

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/uploads/<path:path>')
def send_upload(path):
    return send_from_directory('uploads', path)

@app.route('/start_session', methods=['POST'])
def start_session():
    chosen_exercise = request.json.get('exercise')
    if chosen_exercise:
        success = app_manager.start_session(chosen_exercise)
        if success:
            return jsonify({"status": "session started", "exercise": chosen_exercise})
        else:
            return jsonify({"status": "error", "message": f"Invalid exercise: {chosen_exercise}"}), 400
    else:
        return jsonify({"status": "error", "message": "No exercise selected"}), 400

@app.route('/process_frame', methods=['POST'])
def process_frame():
    try:
        data = request.json.get('image')
        if not data:
            return jsonify({"error": "No image data"}), 400
            
        # Decode the image data
        header, encoded = data.split(',', 1)
        frame_data = base64.b64decode(encoded)
        np_arr = np.frombuffer(frame_data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        # Mirror the frame for natural viewing
        frame = cv2.flip(frame, 1)
        
        # Process the frame with the app manager
        processed_frame, rep_count, session_data = app_manager.process_frame(frame)
        
        # Encode the processed frame back to base64
        ret, buffer = cv2.imencode('.jpg', processed_frame)
        response_image = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            "image": "data:image/jpeg;base64," + response_image,
            "rep_count": rep_count,
            "session_data": session_data
        })
    except Exception as e:
        print(f"Error processing frame: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/end_session', methods=['POST'])
def end_session():
    save_video = request.json.get('save_video', True)
    saved, summary = app_manager.end_session(save_video=save_video)
    return jsonify({
        "status": "session ended", 
        "saved": saved, 
        "summary": summary, 
        "profile": app_manager.get_profile()
    })

# TheMealDB API integration
@app.route('/api/recipes/search', methods=['GET'])
def search_recipes():
    """Search recipes with TheMealDB API"""
    ingredients = request.args.get('ingredients', '')
    
    if not ingredients:
        return jsonify({"error": "No ingredients provided"}), 400
    
    # Split and clean ingredients
    ingredient_list = [i.strip() for i in ingredients.split(',')]
    search_all = request.args.get('searchAll', 'true').lower() == 'true'
    
    try:
        # Results will store all found recipes
        all_recipes = []
        recipe_ids = set()  # To track unique recipes
        
        # Make API calls for each ingredient
        for ingredient in ingredient_list:
            if not ingredient:
                continue
                
            # Use TheMealDB API
            url = f"https://www.themealdb.com/api/json/v1/1/filter.php?i={ingredient}"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                return jsonify({
                    "error": f"API error: status {response.status_code}",
                    "message": "TheMealDB API is not responding correctly"
                }), 500
                
            data = response.json()
            
            # TheMealDB returns null instead of an empty array when no meals found
            if not data.get('meals'):
                continue
                
            # Add found recipes
            for meal in data['meals']:
                if meal['idMeal'] not in recipe_ids:
                    recipe_ids.add(meal['idMeal'])
                    # Add the source ingredient
                    meal['sourceIngredient'] = ingredient
                    meal['matchedIngredients'] = [ingredient]
                    all_recipes.append(meal)
                else:
                    # Update existing recipe with additional matched ingredient
                    for recipe in all_recipes:
                        if recipe['idMeal'] == meal['idMeal']:
                            if 'matchedIngredients' not in recipe:
                                recipe['matchedIngredients'] = [recipe['sourceIngredient']]
                            recipe['matchedIngredients'].append(ingredient)
        
        # Filter if searching for ALL ingredients
        if search_all:
            filtered_recipes = [r for r in all_recipes 
                              if len(r.get('matchedIngredients', [])) == len(ingredient_list)]
        else:
            filtered_recipes = all_recipes
            
        # Sort by number of matching ingredients (descending)
        for recipe in filtered_recipes:
            recipe['matchCount'] = len(recipe.get('matchedIngredients', []))
            
        filtered_recipes.sort(key=lambda x: x['matchCount'], reverse=True)
        
        # Limit to 10 recipes
        filtered_recipes = filtered_recipes[:10]
        
        return jsonify({"meals": filtered_recipes})
    
    except requests.RequestException as e:
        return jsonify({
            "error": "Connection error",
            "message": f"Could not connect to recipe API: {str(e)}"
        }), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/recipes/<recipe_id>', methods=['GET'])
def get_recipe_details(recipe_id):
    """Get detailed recipe information"""
    try:
        # TheMealDB API endpoint for recipe details
        url = f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={recipe_id}"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return jsonify({"error": f"API error: status {response.status_code}"}), 500
            
        data = response.json()
        
        if not data.get('meals'):
            return jsonify({"error": "Recipe not found"}), 404
            
        return jsonify(data)
        
    except requests.RequestException as e:
        return jsonify({
            "error": "Connection error",
            "message": f"Could not connect to recipe API: {str(e)}"
        }), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Progress visualization endpoints
@app.route('/api/progress/rep_distribution/<exercise>', methods=['GET'])
def get_rep_distribution(exercise):
    """Generate bar chart of rep times distribution"""
    if exercise not in app_manager.profile:
        return jsonify({"error": "Exercise not found"}), 404
        
    # Collect all rep times from all workouts
    rep_times = []
    for workout in app_manager.profile[exercise]["progress"]:
        rep_times.extend(workout.get("rep_times", []))
        
    if not rep_times:
        return jsonify({"error": "No data available"}), 404
        
    # Round to nearest 0.5 second
    rounded_times = [round(t * 2) / 2 for t in rep_times]
    
    # Count occurrences
    time_counts = {}
    for t in rounded_times:
        time_counts[t] = time_counts.get(t, 0) + 1
        
    # Create chart
    plt.figure(figsize=(10, 6))
    times = sorted(time_counts.keys())
    counts = [time_counts[t] for t in times]
    
    plt.bar(times, counts, color='#3498db', width=0.4)
    plt.xlabel('Time (seconds)')
    plt.ylabel('Number of Reps')
    plt.title(f'Rep Time Distribution - {exercise}')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Save to memory
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100)
    buffer.seek(0)
    plt.close()
    
    # Create response
    response = make_response(buffer.getvalue())
    response.mimetype = 'image/png'
    
    return response

@app.route('/api/progress/history/<exercise>', methods=['GET'])
def get_progress_history(exercise):
    """Generate line chart of exercise progress over time"""
    if exercise not in app_manager.profile:
        return jsonify({"error": "Exercise not found"}), 404
        
    progress = app_manager.profile[exercise]["progress"]
    
    if not progress:
        return jsonify({"error": "No data available"}), 404
        
    # Extract dates and rep counts
    dates = []
    rep_counts = []
    
    for workout in progress:
        # Convert ISO format to datetime
        date = datetime.fromisoformat(workout["date"])
        dates.append(date)
        rep_counts.append(workout["reps"])
        
    # Sort by date
    date_rep_pairs = sorted(zip(dates, rep_counts))
    dates, rep_counts = zip(*date_rep_pairs) if date_rep_pairs else ([], [])
    
    # Create chart
    plt.figure(figsize=(10, 6))
    plt.plot(dates, rep_counts, marker='o', linestyle='-', color='#3498db')
    plt.xlabel('Date')
    plt.ylabel('Reps Completed')
    plt.title(f'Progress Over Time - {exercise}')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Save to memory
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100)
    buffer.seek(0)
    plt.close()
    
    # Create response
    response = make_response(buffer.getvalue())
    response.mimetype = 'image/png'
    
    return response

# Save user uploaded video
@app.route('/upload_video', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({"error": "No video file uploaded"}), 400
        
    video_file = request.files['video']
    if video_file.filename == '':
        return jsonify({"error": "No video selected"}), 400
        
    # Ensure uploads directory exists
    os.makedirs('uploads', exist_ok=True)
    
    # Save video file
    filename = os.path.join('uploads', video_file.filename)
    video_file.save(filename)
    
    return jsonify({
        "status": "success",
        "filename": video_file.filename,
        "path": filename
    })

if __name__ == '__main__':
    # Create logo.svg
    logo_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect width="100" height="100" rx="20" fill="#003c74"/>
  <circle cx="50" cy="30" r="15" fill="#ecf0f1"/>
  <rect x="40" y="45" width="20" height="25" fill="#ecf0f1"/>
  <line x1="25" y1="50" x2="75" y2="50" stroke="#ecf0f1" stroke-width="5"/>
  <line x1="25" y1="40" x2="30" y2="40" stroke="#ecf0f1" stroke-width="5"/>
  <line x1="25" y1="50" x2="30" y2="50" stroke="#ecf0f1" stroke-width="5"/>
  <line x1="25" y1="60" x2="30" y2="60" stroke="#ecf0f1" stroke-width="5"/>
  <line x1="70" y1="40" x2="75" y2="40" stroke="#ecf0f1" stroke-width="5"/>
  <line x1="70" y1="50" x2="75" y2="50" stroke="#ecf0f1" stroke-width="5"/>
  <line x1="70" y1="60" x2="75" y2="60" stroke="#ecf0f1" stroke-width="5"/>
  <line x1="40" y1="70" x2="40" y2="85" stroke="#ecf0f1" stroke-width="5"/>
  <line x1="60" y1="70" x2="60" y2="85" stroke="#ecf0f1" stroke-width="5"/>
</svg>'''
    
    # Save the SVG file
    with open(os.path.join('static', 'img', 'logo.svg'), 'w') as f:
        f.write(logo_svg)
    
    print("Starting Stream AI Workout Assistant...")
    print("Available exercises:", list(app_manager.profile.keys()))
    app.run(debug=True, host='0.0.0.0', port=5000)