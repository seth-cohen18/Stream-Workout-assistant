// progress.js - Handles progress tracking functionality

document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const progressExerciseSelect = document.getElementById('progress-exercise-select');
    const bestSession = document.getElementById('best-session');
    const lastSession = document.getElementById('last-session');
    const currentLevel = document.getElementById('current-level');
    const recommendations = document.getElementById('recommendations');
    const distChart = document.getElementById('dist-chart');
    const historyChart = document.getElementById('history-chart');

    // Initialize
    function init() {
        // Set up event listeners
        progressExerciseSelect.addEventListener('change', updateProgressView);

        // Initial load
        updateProgressView();

        // Set up automatic chart refresh if page visibility changes 
        // (helps with chart rendering issues)
        document.addEventListener('visibilitychange', function() {
            if (document.visibilityState === 'visible') {
                // Small delay to ensure DOM is ready
                setTimeout(() => {
                    updateCharts(progressExerciseSelect.value);
                }, 500);
            }
        });

        // Add scroll handlers to refresh charts when they come into view
        window.addEventListener('scroll', debounce(checkChartsVisibility, 200));
    }

    // Update progress view for selected exercise
    async function updateProgressView() {
        const selectedExercise = progressExerciseSelect.value;
        if (!selectedExercise) return;

        try {
            // Fetch user profile data to update stats
            const response = await fetch('/', {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                }
            });

            // If the server returns JSON profile data, use it
            if (response.headers.get('Content-Type')?.includes('application/json')) {
                const data = await response.json();
                updateStats(selectedExercise, data.profile);
            } else {
                // Otherwise use the profile data from the loaded page
                // This is a fallback in case the server doesn't support the JSON endpoint
                updateStats(selectedExercise, window.appData?.profile || {});
            }

            // Update charts with added timeout to ensure charts render properly
            setTimeout(() => {
                updateCharts(selectedExercise);
            }, 300);
        } catch (error) {
            console.error('Error updating progress view:', error);
        }
    }

    // Update exercise statistics
    function updateStats(exercise, profile) {
        if (!profile || !profile[exercise]) {
            console.warn(`No profile data found for ${exercise}`);
            bestSession.textContent = 'No data';
            lastSession.textContent = 'No data';
            currentLevel.textContent = 'Beginner';
            return;
        }

        const exerciseData = profile[exercise];
        
        // Find best session
        let maxReps = 0;
        let bestDate = null;
        
        // Find most recent session
        let lastDate = null;
        let lastReps = 0;
        
        if (exerciseData.progress && exerciseData.progress.length > 0) {
            exerciseData.progress.forEach(session => {
                if (session.reps > maxReps) {
                    maxReps = session.reps;
                    bestDate = new Date(session.date);
                }
                
                const sessionDate = new Date(session.date);
                if (!lastDate || sessionDate > lastDate) {
                    lastDate = sessionDate;
                    lastReps = session.reps;
                }
            });
            
            if (bestDate) {
                bestSession.textContent = `${maxReps} reps on ${formatDate(bestDate)}`;
            } else {
                bestSession.textContent = 'No data';
            }
            
            if (lastDate) {
                lastSession.textContent = `${lastReps} reps on ${formatDate(lastDate)}`;
            } else {
                lastSession.textContent = 'No data';
            }
        } else {
            bestSession.textContent = 'No data';
            lastSession.textContent = 'No data';
        }
        
        // Set exercise level
        let level = 'Beginner';
        
        if (exercise === 'Push-Ups') {
            if (maxReps >= 30) level = 'Advanced';
            else if (maxReps >= 15) level = 'Intermediate';
        } else if (exercise === 'Squats') {
            if (maxReps >= 40) level = 'Advanced';
            else if (maxReps >= 20) level = 'Intermediate';
        } else if (exercise === 'Bicep Curls') {
            if (maxReps >= 15) level = 'Advanced';
            else if (maxReps >= 10) level = 'Intermediate';
        } else if (exercise === 'Shoulder Press') {
            if (maxReps >= 15) level = 'Advanced';
            else if (maxReps >= 8) level = 'Intermediate';
        } else if (exercise === 'Lunges') {
            if (maxReps >= 30) level = 'Advanced';
            else if (maxReps >= 15) level = 'Intermediate';
        }
        
        currentLevel.textContent = level;
        
        // Update recommendations
        updateRecommendations(exercise, maxReps, level, lastReps, profile);
    }

    // Update exercise-specific recommendations
    function updateRecommendations(exercise, maxReps, level, lastReps, profile) {
        const recs = [];
        
        // Exercise-specific recommendations
        if (maxReps === 0) {
            recs.push(`Try your first ${exercise} workout to establish a baseline.`);
        } else {
            // Progression recommendations
            if (level === 'Beginner') {
                recs.push(`Aim for ${maxReps + 2} reps in your next ${exercise} session.`);
            } else if (level === 'Intermediate') {
                recs.push(`You're doing great! Try to reach ${maxReps + 3} reps to advance to the advanced level.`);
            } else if (level === 'Advanced') {
                recs.push(`Excellent work! Consider increasing weight or trying a more challenging variation of ${exercise}.`);
            }
            
            // Form recommendations
            if (exercise === 'Squats') {
                recs.push('Focus on proper depth - hips should go below knee level for full benefit.');
            } else if (exercise === 'Push-Ups') {
                recs.push('Maintain a straight body line throughout the movement for maximum effectiveness.');
            } else if (exercise === 'Bicep Curls') {
                recs.push('Keep your elbows close to your body and fully extend at the bottom of each rep.');
            } else if (exercise === 'Shoulder Press') {
                recs.push('Keep your core engaged and avoid arching your back during the press.');
            } else if (exercise === 'Lunges') {
                recs.push('Step far enough forward so your knee forms a 90-degree angle at the bottom position.');
            }
        }
        
        // General recommendations
        const untriedExercises = Object.keys(profile).filter(ex => 
            !profile[ex].progress || profile[ex].progress.length === 0
        );
        
        if (untriedExercises.length > 0) {
            recs.push(`Try ${untriedExercises.join(', ')} to build a more balanced workout routine.`);
        }
        
        // Update recommendations list
        recommendations.innerHTML = '';
        recs.slice(0, 3).forEach(rec => {
            const li = document.createElement('li');
            li.className = 'list-group-item';
            li.textContent = rec;
            recommendations.appendChild(li);
        });
    }

    // Update charts for the selected exercise with theme support
    function updateCharts(exercise) {
        if (!exercise) return;
        
        // Get the current theme
        const currentTheme = localStorage.getItem('theme') || 'light';
        
        // Update rep distribution chart
        distChart.src = `/api/progress/rep_distribution/${exercise}?theme=${currentTheme}&t=${Date.now()}`;
        
        // Update progress history chart
        historyChart.src = `/api/progress/history/${exercise}?theme=${currentTheme}&t=${Date.now()}`;
        
        // Add error handlers for the images
        distChart.onerror = function() {
            console.error('Failed to load distribution chart');
            this.src = currentTheme === 'dark' ? 
                '/static/img/no-data-chart-dark.svg' : 
                '/static/img/no-data-chart.svg';
        };
        
        historyChart.onerror = function() {
            console.error('Failed to load history chart');
            this.src = currentTheme === 'dark' ? 
                '/static/img/no-data-chart-dark.svg' : 
                '/static/img/no-data-chart.svg';
        };
        
        // Force redraw of charts
        distChart.style.opacity = '0.99';
        historyChart.style.opacity = '0.99';
        
        setTimeout(() => {
            distChart.style.opacity = '1';
            historyChart.style.opacity = '1';
        }, 100);
    }
    
    // Check if charts are visible in viewport and refresh them if needed
    function checkChartsVisibility() {
        const progressSection = document.getElementById('progress-section');
        if (!progressSection) return;
        
        const rect = progressSection.getBoundingClientRect();
        const isVisible = (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
        
        if (isVisible) {
            // If the progress section is visible, refresh the charts
            updateCharts(progressExerciseSelect.value);
        }
    }
    
    // Debounce function to limit how often a function is called
    function debounce(func, wait) {
        let timeout;
        return function() {
            const context = this;
            const args = arguments;
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                func.apply(context, args);
            }, wait);
        };
    }

    // Helper function to format dates
    function formatDate(date) {
        if (!date) return 'Unknown';
        
        // Format as MM/DD/YYYY
        return `${date.getMonth() + 1}/${date.getDate()}/${date.getFullYear()}`;
    }

    // Expose updateCharts function globally so it can be called from other scripts
    window.updateCharts = updateCharts;

    // Initialize the module
    init();
});