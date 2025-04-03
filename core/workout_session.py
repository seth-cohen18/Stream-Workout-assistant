# core/workout_session.py
import os
import cv2
import json
import time
import datetime
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO

class WorkoutSession:
    """
    Manages workout sessions, saving data, and generating progress reports.
    This class integrates with the AppManager to provide a complete workout tracking experience.
    """
    
    def __init__(self, user_id="default_user"):
        self.user_id = user_id
        self.current_exercise = None
        self.session_start_time = None
        self.session_end_time = None
        self.rep_data = []
        self.feedback_data = []
        self.video_path = None
        
        # Ensure session directory exists
        self.sessions_dir = os.path.join("data", "sessions")
        os.makedirs(self.sessions_dir, exist_ok=True)
        
        # Path to user profile
        self.profile_path = os.path.join("data", f"user_{user_id}_profile.json")
        self.load_user_profile()
    
    def load_user_profile(self):
        """Load user profile from file or create new one if it doesn't exist"""
        if os.path.exists(self.profile_path):
            with open(self.profile_path, 'r') as f:
                self.profile = json.load(f)
        else:
            # Default profile structure
            self.profile = {
                "user_id": self.user_id,
                "created_at": datetime.datetime.now().isoformat(),
                "exercises": {
                    "Squats": {"level": "beginner", "max_reps": 0, "sessions": []},
                    "Bicep Curls": {"level": "beginner", "max_reps": 0, "sessions": []},
                    "Push-Ups": {"level": "beginner", "max_reps": 0, "sessions": []},
                    "Shoulder Press": {"level": "beginner", "max_reps": 0, "sessions": []},
                    "Lunges": {"level": "beginner", "max_reps": 0, "sessions": []}
                },
                "settings": {
                    "auto_save_video": True,
                    "voice_feedback": True,
                    "difficulty": "standard"
                },
                "goals": {
                    "weekly_workouts": 3,
                    "target_exercises": ["Squats", "Push-Ups"]
                }
            }
            self.save_user_profile()
    
    def save_user_profile(self):
        """Save user profile to file"""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.profile_path), exist_ok=True)
        
        with open(self.profile_path, 'w') as f:
            json.dump(self.profile, f, indent=2)
        
        print(f"User profile saved to {self.profile_path}")
    
    def start_session(self, exercise_name):
        """Start a new workout session for the given exercise"""
        self.current_exercise = exercise_name
        self.session_start_time = datetime.datetime.now()
        self.rep_data = []
        self.feedback_data = []
        
        print(f"Started {exercise_name} session at {self.session_start_time}")
        return True
    
    def add_rep(self, rep_time, rep_form_quality=None):
        """Add a completed rep to the current session"""
        if not self.current_exercise:
            return False
            
        rep_info = {
            "time": rep_time,
            "timestamp": datetime.datetime.now().isoformat(),
            "form_quality": rep_form_quality
        }
        
        self.rep_data.append(rep_info)
        return True
    
    def add_feedback(self, feedback_text, severity="info"):
        """Add feedback to the current session"""
        if not self.current_exercise:
            return False
            
        feedback_info = {
            "text": feedback_text,
            "timestamp": datetime.datetime.now().isoformat(),
            "severity": severity  # info, warning, error
        }
        
        self.feedback_data.append(feedback_info)
        return True
    
    def end_session(self, video_path=None):
        """End the current workout session and save all data"""
        if not self.current_exercise:
            return False, "No active session"
            
        self.session_end_time = datetime.datetime.now()
        self.video_path = video_path
        
        # Create session summary
        session_summary = {
            "exercise": self.current_exercise,
            "start_time": self.session_start_time.isoformat(),
            "end_time": self.session_end_time.isoformat(),
            "duration": (self.session_end_time - self.session_start_time).total_seconds(),
            "reps": len(self.rep_data),
            "rep_data": self.rep_data,
            "feedback": self.feedback_data,
            "video_path": self.video_path
        }
        
        # Generate session ID
        session_id = f"{self.current_exercise.replace(' ', '_')}_{self.session_start_time.strftime('%Y%m%d_%H%M%S')}"
        
        # Save session to file
        session_file = os.path.join(self.sessions_dir, f"{session_id}.json")
        with open(session_file, 'w') as f:
            json.dump(session_summary, f, indent=2)
        
        # Update user profile
        if self.current_exercise in self.profile["exercises"]:
            current_max = self.profile["exercises"][self.current_exercise]["max_reps"]
            if len(self.rep_data) > current_max:
                self.profile["exercises"][self.current_exercise]["max_reps"] = len(self.rep_data)
            
            # Add session reference
            self.profile["exercises"][self.current_exercise]["sessions"].append({
                "id": session_id,
                "date": self.session_start_time.isoformat(),
                "reps": len(self.rep_data)
            })
            
            # Update difficulty level based on performance
            self.update_exercise_level()
            
            # Save updated profile
            self.save_user_profile()
        
        print(f"Session ended and saved: {session_id}")
        
        # Reset session data
        exercise_name = self.current_exercise
        self.current_exercise = None
        self.session_start_time = None
        self.session_end_time = None
        self.rep_data = []
        self.feedback_data = []
        
        return True, {
            "session_id": session_id,
            "exercise": exercise_name,
            "reps": session_summary["reps"],
            "duration": session_summary["duration"],
            "video_saved": video_path is not None
        }
    
    def update_exercise_level(self):
        """Update the exercise difficulty level based on performance"""
        if not self.current_exercise:
            return
            
        exercise = self.profile["exercises"][self.current_exercise]
        reps = len(self.rep_data)
        
        # Simple level progression rules
        if self.current_exercise == "Push-Ups":
            if reps >= 30:
                exercise["level"] = "advanced"
            elif reps >= 15:
                exercise["level"] = "intermediate"
            else:
                exercise["level"] = "beginner"
        elif self.current_exercise == "Squats":
            if reps >= 40:
                exercise["level"] = "advanced"
            elif reps >= 20:
                exercise["level"] = "intermediate"
            else:
                exercise["level"] = "beginner"
        elif self.current_exercise == "Bicep Curls":
            if reps >= 15:
                exercise["level"] = "advanced"
            elif reps >= 10:
                exercise["level"] = "intermediate"
            else:
                exercise["level"] = "beginner"
        elif self.current_exercise == "Shoulder Press":
            if reps >= 15:
                exercise["level"] = "advanced"
            elif reps >= 8:
                exercise["level"] = "intermediate"
            else:
                exercise["level"] = "beginner"
        elif self.current_exercise == "Lunges":
            if reps >= 30:
                exercise["level"] = "advanced"
            elif reps >= 15:
                exercise["level"] = "intermediate"
            else:
                exercise["level"] = "beginner"
    
    def generate_progress_report(self, exercise_name=None, last_n_sessions=5):
        """Generate a progress report for the given exercise or all exercises"""
        if exercise_name and exercise_name in self.profile["exercises"]:
            exercises = [exercise_name]
        else:
            exercises = list(self.profile["exercises"].keys())
            
        reports = {}
        
        for exercise in exercises:
            exercise_data = self.profile["exercises"][exercise]
            sessions = exercise_data["sessions"]
            
            if not sessions:
                reports[exercise] = {
                    "status": "No sessions recorded yet",
                    "level": exercise_data["level"],
                    "max_reps": 0,
                    "recent_progress": []
                }
                continue
                
            # Sort sessions by date
            sorted_sessions = sorted(sessions, key=lambda x: x["date"], reverse=True)
            recent_sessions = sorted_sessions[:last_n_sessions]
            
            # Calculate progress metrics
            if len(recent_sessions) > 1:
                first_session = recent_sessions[-1]
                last_session = recent_sessions[0]
                rep_change = last_session["reps"] - first_session["reps"]
                percent_change = (rep_change / first_session["reps"]) * 100 if first_session["reps"] > 0 else 0
                
                progress_status = "improving" if rep_change > 0 else "declining" if rep_change < 0 else "maintaining"
            else:
                progress_status = "baseline"
                percent_change = 0
                
            reports[exercise] = {
                "status": progress_status,
                "level": exercise_data["level"],
                "max_reps": exercise_data["max_reps"],
                "recent_progress": [{
                    "date": session["date"],
                    "reps": session["reps"]
                } for session in recent_sessions],
                "percent_change": percent_change
            }
            
        return reports
    
    def get_recommendations(self):
        """Generate workout recommendations based on user's progress"""
        progress = self.generate_progress_report()
        recommendations = []
        
        for exercise, data in progress.items():
            if data["status"] == "No sessions recorded yet":
                recommendations.append(f"Try your first {exercise} workout")
            elif data["status"] == "declining":
                recommendations.append(f"Focus more on {exercise} - your reps are decreasing")
            elif data["level"] == "beginner" and data["max_reps"] > 0:
                recommendations.append(f"Build up your {exercise} - aim for {data['max_reps'] + 3} reps next time")
            elif data["status"] == "improving" and data["percent_change"] > 20:
                recommendations.append(f"Great progress on {exercise}! You might be ready to increase difficulty")
        
        # General recommendations
        if len(self.profile["exercises"]) > len([ex for ex, data in progress.items() if data["max_reps"] > 0]):
            recommendations.append("Try exercises you haven't done yet for a balanced workout")
            
        # Limit to 3 recommendations
        return recommendations[:3]
    
    def generate_rep_distribution_chart(self, exercise_name, as_file=False):
        """Generate a bar chart of rep time distribution for the given exercise"""
        if exercise_name not in self.profile["exercises"]:
            return None
            
        # Collect rep times from all sessions
        sessions = self.profile["exercises"][exercise_name]["sessions"]
        session_ids = [s["id"] for s in sessions]
        
        all_rep_times = []
        for session_id in session_ids:
            session_file = os.path.join(self.sessions_dir, f"{session_id}.json")
            if os.path.exists(session_file):
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                    rep_times = [rep["time"] for rep in session_data.get("rep_data", [])]
                    all_rep_times.extend(rep_times)
        
        if not all_rep_times:
            return None
            
        # Round to nearest 0.5 second
        rounded_times = [round(t * 2) / 2 for t in all_rep_times]
        
        # Count occurrences
        time_counts = {}
        for t in rounded_times:
            time_counts[t] = time_counts.get(t, 0) + 1
            
        # Create chart with improved styling
        plt.figure(figsize=(10, 6))
        plt.style.use('ggplot')  # Use a nicer style
        
        times = sorted(time_counts.keys())
        counts = [time_counts[t] for t in times]
        
        # Create bars with custom styling
        bars = plt.bar(times, counts, color='#3498db', width=0.4, alpha=0.8)
        
        # Add value labels on top of bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{int(height)}', ha='center', va='bottom')
        
        # Style the chart
        plt.xlabel('Time (seconds)', fontsize=12)
        plt.ylabel('Number of Reps', fontsize=12)
        plt.title(f'Rep Time Distribution - {exercise_name}', fontsize=14, fontweight='bold')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        if as_file:
            # Save to file
            chart_dir = os.path.join("static", "charts")
            os.makedirs(chart_dir, exist_ok=True)
            
            filename = f"{exercise_name.replace(' ', '_')}_distribution.png"
            filepath = os.path.join(chart_dir, filename)
            plt.savefig(filepath, dpi=100)
            plt.close()
            
            return filepath
        else:
            # Save to memory
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=100)
            buffer.seek(0)
            plt.close()
            
            return buffer
    
    def generate_progress_chart(self, exercise_name, as_file=False):
        """Generate a line chart of exercise progress over time"""
        if exercise_name not in self.profile["exercises"]:
            return None
            
        # Get sessions data
        sessions = self.profile["exercises"][exercise_name]["sessions"]
        
        if not sessions:
            return None
            
        # Sort sessions by date
        sorted_sessions = sorted(sessions, key=lambda x: x["date"])
        
        # Extract dates and rep counts
        dates = [datetime.datetime.fromisoformat(s["date"]) for s in sorted_sessions]
        rep_counts = [s["reps"] for s in sorted_sessions]
        
        # Create chart with improved styling
        plt.figure(figsize=(10, 6))
        plt.style.use('ggplot')  # Use a nicer style
        
        # Plot line chart with markers
        plt.plot(dates, rep_counts, marker='o', markersize=8, 
                linestyle='-', linewidth=2, color='#3498db')
        
        # Add value labels above each point
        for i, (date, count) in enumerate(zip(dates, rep_counts)):
            plt.text(date, count + 0.5, str(count), ha='center', va='bottom')
        
        # Style the chart
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Reps Completed', fontsize=12)
        plt.title(f'Progress Over Time - {exercise_name}', fontsize=14, fontweight='bold')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        if as_file:
            # Save to file
            chart_dir = os.path.join("static", "charts")
            os.makedirs(chart_dir, exist_ok=True)
            
            filename = f"{exercise_name.replace(' ', '_')}_progress.png"
            filepath = os.path.join(chart_dir, filename)
            plt.savefig(filepath, dpi=100)
            plt.close()
            
            return filepath
        else:
            # Save to memory
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=100)
            buffer.seek(0)
            plt.close()
            
            return buffer