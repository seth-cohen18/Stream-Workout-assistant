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
from datetime import datetime
from app.app_manager import AppManager

app = Flask(__name__)
app_manager = AppManager()

# API keys for additional recipe sources
EDAMAM_APP_ID = os.environ.get('EDAMAM_APP_ID', '')  # Set as environment variable
EDAMAM_APP_KEY = os.environ.get('EDAMAM_APP_KEY', '')  # Set as environment variable

# Create necessary directories
os.makedirs('static/img', exist_ok=True)
os.makedirs('uploads', exist_ok=True)
os.makedirs('static/temp', exist_ok=True)
os.makedirs('static/charts', exist_ok=True)
os.makedirs('data/sessions', exist_ok=True)

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
    save_video = request.json.get('save_video', False)  # Don't save by default
    saved, summary = app_manager.end_session(save_video=save_video)
    return jsonify({
        "status": "session ended", 
        "saved": saved, 
        "summary": summary, 
        "profile": app_manager.get_profile()
    })

@app.route('/save_session', methods=['POST'])
def save_session():
    try:
        data = request.json
        exercise = data.get('exercise')
        rep_count = data.get('rep_count', 0)
        duration = data.get('duration', '00:00')
        video_path = data.get('video_path')
        session_data = data.get('session_data', {})
        
        if not exercise:
            return jsonify({"status": "error", "message": "No exercise specified"}), 400
            
        # Format duration from "MM:SS" to seconds
        try:
            duration_parts = duration.split(':')
            duration_seconds = int(duration_parts[0]) * 60 + int(duration_parts[1])
        except:
            duration_seconds = 0
        
        # Prepare session data to save
        workout_data = {
            "date": datetime.now().isoformat(),
            "reps": rep_count,
            "duration": duration_seconds,
            "rep_times": session_data.get('rep_times', []),
            "video_path": video_path if video_path else "",
            "avg_rep_time": sum(session_data.get('rep_times', [])) / len(session_data.get('rep_times', [1])) if session_data.get('rep_times') else 0
        }
        
        # Update profile
        if exercise in app_manager.profile:
            app_manager.profile[exercise]["latest_reps"] = rep_count
            app_manager.profile[exercise]["progress"].append(workout_data)
            
            with open(app_manager.profile_path, 'w') as f:
                json.dump(app_manager.profile, f, indent=2)
                
            return jsonify({
                "status": "success",
                "message": "Workout saved successfully",
                "profile": app_manager.get_profile()
            })
        else:
            return jsonify({"status": "error", "message": f"Invalid exercise: {exercise}"}), 400
            
    except Exception as e:
        print(f"Error saving session: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

# TheMealDB API integration
@app.route('/api/recipes/search', methods=['GET'])
def search_recipes():
    """Search recipes with TheMealDB API by ingredients"""
    ingredients = request.args.get('ingredients', '')
    
    if not ingredients:
        return jsonify({"error": "No ingredients provided"}), 400
    
    # Split and clean ingredients
    ingredient_list = [i.strip() for i in ingredients.split(',') if i.strip()]
    search_all = request.args.get('searchAll', 'true').lower() == 'true'
    
    if not ingredient_list:
        return jsonify({"error": "No valid ingredients provided"}), 400
    
    try:
        # Results will store all found recipes
        all_recipes = []
        recipe_ids = set()  # To track unique recipes
        
        # Make API calls for each ingredient to TheMealDB
        for ingredient in ingredient_list:
            url = f"https://www.themealdb.com/api/json/v1/1/filter.php?i={ingredient}"
            
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                # TheMealDB returns null instead of an empty array when no meals found
                if not data.get('meals'):
                    continue
                    
                # Add found recipes
                for meal in data['meals']:
                    if meal['idMeal'] not in recipe_ids:
                        recipe_ids.add(meal['idMeal'])
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
            
            except requests.RequestException as e:
                print(f"Error fetching recipes for {ingredient} from TheMealDB: {str(e)}")
                # Continue with other ingredients instead of failing completely
                continue
        
        # If TheMealDB returned no results, try Edamam API if credentials are available
        if not all_recipes and EDAMAM_APP_ID and EDAMAM_APP_KEY:
            try:
                # Join all ingredients for Edamam API
                joined_ingredients = ','.join(ingredient_list)
                edamam_url = f"https://api.edamam.com/search?q={joined_ingredients}&app_id={EDAMAM_APP_ID}&app_key={EDAMAM_APP_KEY}"
                
                edamam_response = requests.get(edamam_url, timeout=10)
                edamam_response.raise_for_status()
                
                edamam_data = edamam_response.json()
                
                if edamam_data.get('hits'):
                    for idx, hit in enumerate(edamam_data['hits']):
                        recipe = hit['recipe']
                        # Format Edamam recipe to match TheMealDB format
                        meal = {
                            'idMeal': f"edamam_{idx}_{hash(recipe['uri'])}",
                            'strMeal': recipe['label'],
                            'strMealThumb': recipe['image'],
                            'strCategory': recipe.get('dishType', ['Uncategorized'])[0] if recipe.get('dishType') else 'Uncategorized',
                            'strArea': recipe.get('cuisineType', ['International'])[0] if recipe.get('cuisineType') else 'International',
                            'matchedIngredients': ingredient_list,
                            'ingredients': [item['food'] for item in recipe.get('ingredients', [])],
                            'sourceAPI': 'edamam'
                        }
                        all_recipes.append(meal)
            except Exception as e:
                print(f"Error fetching recipes from Edamam API: {str(e)}")
                # Continue with whatever TheMealDB returned
        
        # If no recipes found for any ingredient
        if not all_recipes:
            return jsonify({
                "status": "no_results",
                "message": f"No recipes found matching: {', '.join(ingredient_list)}",
                "meals": []
            })
        
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
        
        # Limit to 20 recipes (increased from 10)
        filtered_recipes = filtered_recipes[:20]
        
        return jsonify({
            "status": "success", 
            "count": len(filtered_recipes),
            "meals": filtered_recipes
        })
    
    except requests.RequestException as e:
        return jsonify({
            "error": "Connection error",
            "message": f"Could not connect to recipe API: {str(e)}"
        }), 503
    except Exception as e:
        return jsonify({
            "error": "Processing error",
            "message": f"An unexpected error occurred: {str(e)}"
        }), 500

@app.route('/api/recipes/<recipe_id>', methods=['GET'])
def get_recipe_details(recipe_id):
    """Get detailed recipe information"""
    try:
        # Check if it's an Edamam recipe
        if recipe_id.startswith('edamam_'):
            # For Edamam recipes, we already have all the data
            # This would need to be modified to properly store and retrieve Edamam recipes
            return jsonify({
                "status": "error",
                "message": "Detailed view for Edamam recipes is not implemented yet"
            }), 501
        
        # TheMealDB API endpoint for recipe details
        url = f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={recipe_id}"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get('meals'):
                return jsonify({"error": "Recipe not found"}), 404
                
            # Process the recipe to format ingredients consistently
            recipe = data['meals'][0]
            
            # Extract ingredients and measures
            ingredients = []
            for i in range(1, 21):  # TheMealDB provides up to 20 ingredients
                ingredient_key = f'strIngredient{i}'
                measure_key = f'strMeasure{i}'
                
                if ingredient_key in recipe and measure_key in recipe:
                    ingredient = recipe[ingredient_key]
                    measure = recipe[measure_key]
                    
                    if ingredient and ingredient.strip() and measure and measure.strip():
                        ingredients.append({
                            'name': ingredient.strip(),
                            'measure': measure.strip()
                        })
            
            # Add the processed ingredients to the recipe
            recipe['formattedIngredients'] = ingredients
            
            return jsonify({
                "status": "success",
                "meal": recipe
            })
            
        except requests.RequestException as e:
            return jsonify({
                "error": "Connection error",
                "message": f"Could not connect to recipe API: {str(e)}"
            }), 503
            
    except Exception as e:
        return jsonify({
            "error": "Processing error",
            "message": f"An unexpected error occurred: {str(e)}"
        }), 500

@app.route('/api/recipes/search-name', methods=['GET'])
def search_recipes_by_name():
    """Search recipes by name using TheMealDB API"""
    name = request.args.get('name', '')
    
    if not name:
        return jsonify({"error": "No search term provided"}), 400
    
    try:
        # TheMealDB API endpoint for searching by name
        url = f"https://www.themealdb.com/api/json/v1/1/search.php?s={name}"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get('meals'):
            # If TheMealDB returns no results, try Edamam API
            if EDAMAM_APP_ID and EDAMAM_APP_KEY:
                try:
                    edamam_url = f"https://api.edamam.com/search?q={name}&app_id={EDAMAM_APP_ID}&app_key={EDAMAM_APP_KEY}"
                    
                    edamam_response = requests.get(edamam_url, timeout=10)
                    edamam_response.raise_for_status()
                    
                    edamam_data = edamam_response.json()
                    
                    meals = []
                    if edamam_data.get('hits'):
                        for idx, hit in enumerate(edamam_data['hits']):
                            recipe = hit['recipe']
                            # Format Edamam recipe to match TheMealDB format
                            meal = {
                                'idMeal': f"edamam_{idx}_{hash(recipe['uri'])}",
                                'strMeal': recipe['label'],
                                'strMealThumb': recipe['image'],
                                'strCategory': recipe.get('dishType', ['Uncategorized'])[0] if recipe.get('dishType') else 'Uncategorized',
                                'strArea': recipe.get('cuisineType', ['International'])[0] if recipe.get('cuisineType') else 'International',
                                'ingredients': [item['food'] for item in recipe.get('ingredients', [])],
                                'sourceAPI': 'edamam'
                            }
                            meals.append(meal)
                        
                        return jsonify({
                            "status": "success",
                            "meals": meals
                        })
                except Exception as e:
                    print(f"Error fetching recipes from Edamam API: {str(e)}")
            
            return jsonify({
                "status": "no_results",
                "message": f"No recipes found matching: {name}",
                "meals": []
            })
        
        return jsonify({
            "status": "success",
            "meals": data['meals']
        })
        
    except requests.RequestException as e:
        return jsonify({
            "error": "Connection error",
            "message": f"Could not connect to recipe API: {str(e)}"
        }), 503
    except Exception as e:
        return jsonify({
            "error": "Processing error",
            "message": f"An unexpected error occurred: {str(e)}"
        }), 500

@app.route('/api/recipes/category', methods=['GET'])
def search_recipes_by_category():
    """Search recipes by category using TheMealDB API"""
    category = request.args.get('c', '')
    
    try:
        # TheMealDB API endpoint for filtering by category
        url = f"https://www.themealdb.com/api/json/v1/1/filter.php?c={category}" if category else "https://www.themealdb.com/api/json/v1/1/categories.php"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if category and not data.get('meals'):
            return jsonify({
                "status": "no_results",
                "message": f"No recipes found in category: {category}",
                "meals": []
            })
        
        return jsonify({
            "status": "success",
            "meals": data.get('meals', [])
        })
        
    except requests.RequestException as e:
        return jsonify({
            "error": "Connection error",
            "message": f"Could not connect to recipe API: {str(e)}"
        }), 503
    except Exception as e:
        return jsonify({
            "error": "Processing error",
            "message": f"An unexpected error occurred: {str(e)}"
        }), 500

# Progress visualization endpoints
@app.route('/api/progress/rep_distribution/<exercise>', methods=['GET'])
def get_rep_distribution(exercise):
    """Generate bar chart of rep times distribution"""
    if exercise not in app_manager.profile:
        return jsonify({"error": "Exercise not found"}), 404
        
    # Check if dark theme is requested
    theme = request.args.get('theme', 'light')
    is_dark = theme == 'dark'
    
    # Collect all rep times from all workouts
    rep_times = []
    for workout in app_manager.profile[exercise]["progress"]:
        rep_times.extend(workout.get("rep_times", []))
        
    if not rep_times:
        # Return no-data chart placeholder
        no_data_image = "static/img/no-data-chart-dark.svg" if is_dark else "static/img/no-data-chart.svg"
        if os.path.exists(no_data_image):
            return send_file(no_data_image, mimetype='image/svg+xml')
        return jsonify({"error": "No data available"}), 404
        
    # Round to nearest 0.5 second
    rounded_times = [round(t * 2) / 2 for t in rep_times]
    
    # Count occurrences
    time_counts = {}
    for t in rounded_times:
        time_counts[t] = time_counts.get(t, 0) + 1
        
    # Create chart with improved styling
    plt.figure(figsize=(10, 6))
    
    # Set dark theme if requested
    if is_dark:
        plt.style.use('dark_background')
        bar_color = '#4fa8e0'  # Lighter blue for dark mode
        text_color = '#f8f9fa'
        grid_color = '#343a40'
    else:
        plt.style.use('ggplot')  # Use a nicer style for light mode
        bar_color = '#3498db'
        text_color = '#333333'
        grid_color = '#dddddd'
    
    times = sorted(time_counts.keys())
    counts = [time_counts[t] for t in times]
    
    # Create bars with custom styling
    bars = plt.bar(times, counts, color=bar_color, width=0.4, alpha=0.8)
    
    # Add value labels on top of bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{int(height)}', ha='center', va='bottom', color=text_color)
    
    # Style the chart
    plt.xlabel('Time (seconds)', fontsize=12, color=text_color)
    plt.ylabel('Number of Reps', fontsize=12, color=text_color)
    plt.title(f'Rep Time Distribution - {exercise}', fontsize=14, fontweight='bold', color=text_color)
    plt.grid(axis='y', linestyle='--', alpha=0.7, color=grid_color)
    plt.tight_layout()
    
    # Save to memory
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100, facecolor='#1e1e1e' if is_dark else '#ffffff')
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
    
    # Check if dark theme is requested
    theme = request.args.get('theme', 'light')
    is_dark = theme == 'dark'
    
    progress = app_manager.profile[exercise]["progress"]
    
    if not progress:
        # Return no-data chart placeholder
        no_data_image = "static/img/no-data-chart-dark.svg" if is_dark else "static/img/no-data-chart.svg"
        if os.path.exists(no_data_image):
            return send_file(no_data_image, mimetype='image/svg+xml')
        return jsonify({"error": "No data available"}), 404
        
    # Extract dates and rep counts
    dates = []
    rep_counts = []
    
    for workout in progress:
        # Convert ISO format to datetime
        try:
            date = datetime.fromisoformat(workout["date"])
            dates.append(date)
            rep_counts.append(workout["reps"])
        except (ValueError, KeyError) as e:
            print(f"Error processing workout data: {e}")
            continue
        
    # Sort by date
    date_rep_pairs = sorted(zip(dates, rep_counts))
    dates, rep_counts = zip(*date_rep_pairs) if date_rep_pairs else ([], [])
    
    if not dates:
        # Return no-data chart placeholder
        no_data_image = "static/img/no-data-chart-dark.svg" if is_dark else "static/img/no-data-chart.svg"
        if os.path.exists(no_data_image):
            return send_file(no_data_image, mimetype='image/svg+xml')
        return jsonify({"error": "No valid date data available"}), 404
    
    # Create chart with improved styling
    plt.figure(figsize=(10, 6))
    
    # Set dark theme if requested
    if is_dark:
        plt.style.use('dark_background')
        line_color = '#4fa8e0'  # Lighter blue for dark mode
        marker_color = '#2ecc71'  # Green markers
        text_color = '#f8f9fa'
        grid_color = '#343a40'
    else:
        plt.style.use('ggplot')  # Use a nicer style for light mode
        line_color = '#3498db'
        marker_color = '#27ae60'
        text_color = '#333333'
        grid_color = '#dddddd'
    
    # Plot line chart with markers
    plt.plot(dates, rep_counts, marker='o', markersize=8, 
             linestyle='-', linewidth=2, color=line_color, markerfacecolor=marker_color)
    
    # Add value labels above each point
    for i, (date, count) in enumerate(zip(dates, rep_counts)):
        plt.text(date, count + 0.5, str(count), ha='center', va='bottom', color=text_color)
    
    # Style the chart
    plt.xlabel('Date', fontsize=12, color=text_color)
    plt.ylabel('Reps Completed', fontsize=12, color=text_color)
    plt.title(f'Progress Over Time - {exercise}', fontsize=14, fontweight='bold', color=text_color)
    plt.grid(True, linestyle='--', alpha=0.7, color=grid_color)
    plt.xticks(rotation=45, color=text_color)
    plt.yticks(color=text_color)
    plt.tight_layout()
    
    # Save to memory
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100, facecolor='#1e1e1e' if is_dark else '#ffffff')
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
    
    # Add timestamp to filename to prevent overwriting
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{video_file.filename}"
    filepath = os.path.join('uploads', filename)
    
    # Save video file
    video_file.save(filepath)
    
    return jsonify({
        "status": "success",
        "filename": filename,
        "path": filepath
    })

if __name__ == '__main__':
    # Create logo.svg - Using the provided logo
    logo_path = os.path.join('static', 'img', 'logo.svg')
    if not os.path.exists(logo_path):
        # If logo doesn't exist, use the original code to create it
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
        with open(logo_path, 'w') as f:
            f.write(logo_svg)
    
    # Create a hero image if it doesn't exist
    hero_path = os.path.join('static', 'img', 'hero-image.svg')
    if not os.path.exists(hero_path):
        hero_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">
  <style>
    .st0{fill:#003c74;}
    .st1{fill:#3498db;}
    .st2{fill:#27ae60;}
    .st3{fill:#ecf0f1;}
    .st4{fill:#2c3e50;}
  </style>
  <rect width="800" height="600" fill="#f8f9fa"/>
  
  <!-- Person exercising -->
  <circle cx="300" cy="180" r="40" class="st3"/>
  <rect x="280" y="220" width="40" height="100" class="st3"/>
  <line x1="280" y1="260" x2="220" y2="220" stroke="#ecf0f1" stroke-width="25" stroke-linecap="round"/>
  <line x1="320" y1="260" x2="380" y2="220" stroke="#ecf0f1" stroke-width="25" stroke-linecap="round"/>
  <line x1="280" y1="320" x2="250" y2="400" stroke="#ecf0f1" stroke-width="25" stroke-linecap="round"/>
  <line x1="320" y1="320" x2="350" y2="400" stroke="#ecf0f1" stroke-width="25" stroke-linecap="round"/>
  
  <!-- Weights and equipment -->
  <circle cx="440" cy="400" r="50" class="st0"/>
  <circle cx="440" cy="400" r="40" class="st3"/>
  <circle cx="440" cy="400" r="5" class="st0"/>
  <rect x="160" y="400" width="100" height="20" rx="5" class="st1"/>
  <rect x="140" y="390" width="20" height="40" rx="5" class="st1"/>
  <rect x="260" y="390" width="20" height="40" rx="5" class="st1"/>
  
  <!-- Visualization elements -->
  <path d="M600,150 C650,100 700,200 600,250 C500,300 550,400 600,450" stroke="#27ae60" stroke-width="10" fill="none"/>
  <circle cx="600" cy="150" r="10" class="st1"/>
  <circle cx="600" cy="250" r="10" class="st1"/>
  <circle cx="600" cy="350" r="10" class="st1"/>
  <circle cx="600" cy="450" r="10" class="st1"/>
  
  <!-- Data points -->
  <rect x="500" y="200" width="20" height="60" class="st2"/>
  <rect x="530" y="180" width="20" height="80" class="st2"/>
  <rect x="560" y="150" width="20" height="110" class="st2"/>
  <rect x="590" y="180" width="20" height="80" class="st2"/>
  <rect x="620" y="160" width="20" height="100" class="st2"/>
  <rect x="650" y="120" width="20" height="140" class="st2"/>
</svg>'''
        
        # Save the SVG file
        with open(hero_path, 'w') as f:
            f.write(hero_svg)
    
    print("Starting Stream AI Workout Assistant...")
    print("Available exercises:", list(app_manager.profile.keys()))
    app.run(debug=True, host='0.0.0.0', port=5000)