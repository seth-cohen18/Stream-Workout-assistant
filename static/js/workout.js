// workout.js - Handles workout tracking functionality

document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const cameraFeed = document.getElementById('camera-feed');
    const processedFeed = document.getElementById('processed-feed');
    const exerciseSelect = document.getElementById('exercise-select');
    const startBtn = document.getElementById('start-btn');
    const endBtn = document.getElementById('end-btn');
    const waitingMessage = document.getElementById('waiting-message');
    const loadingSpinner = document.getElementById('loading-spinner');
    const workoutControls = document.getElementById('workout-controls');
    const discardWorkoutBtn = document.getElementById('discard-workout-btn');
    const saveWorkoutBtn = document.getElementById('save-workout-btn');
    const sessionSummary = document.getElementById('session-summary');
    const currentExercise = document.getElementById('current-exercise');
    const repCounter = document.getElementById('rep-counter');
    const repProgress = document.getElementById('rep-progress');
    const sessionDuration = document.getElementById('session-duration');
    const lastFeedback = document.getElementById('last-feedback');
    const summaryReps = document.getElementById('summary-reps');
    const summaryAvgTime = document.getElementById('summary-avg-time');
    const summaryDuration = document.getElementById('summary-duration');
    const feedbackList = document.getElementById('feedback-list');

    // State variables
    let stream = null;
    let isExercising = false;
    let processingFrame = false;
    let startTime = null;
    let durationInterval = null;
    let lastRepCount = 0;
    let videoChunks = [];
    let mediaRecorder = null;
    let recordedBlob = null;
    let sessionData = null;

    // Initialize
    function init() {
        // Set up event listeners
        startBtn.addEventListener('click', startExercise);
        endBtn.addEventListener('click', endExercise);
        discardWorkoutBtn.addEventListener('click', discardWorkout);
        saveWorkoutBtn.addEventListener('click', saveWorkout);
        exerciseSelect.addEventListener('change', updateStartButtonState);

        // Check for camera permission
        if (!localStorage.getItem('cameraPermissionShown')) {
            const permissionModal = new bootstrap.Modal(document.getElementById('cameraPermissionModal'));
            permissionModal.show();
            localStorage.setItem('cameraPermissionShown', 'true');
        }

        updateStartButtonState();
    }

    // Update the state of the start button based on exercise selection
    function updateStartButtonState() {
        startBtn.disabled = !exerciseSelect.value;
    }

    // Start the exercise
    async function startExercise() {
        const selectedExercise = exerciseSelect.value;
        if (!selectedExercise) {
            alert('Please select an exercise first.');
            return;
        }

        try {
            // Show loading spinner
            waitingMessage.classList.add('d-none');
            loadingSpinner.classList.remove('d-none');

            // Request camera access
            stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: 'user'
                },
                audio: false
            });

            // Set up camera feed
            cameraFeed.srcObject = stream;
            await cameraFeed.play();

            // Start session on server
            const response = await fetch('/start_session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    exercise: selectedExercise
                })
            });

            const data = await response.json();
            if (data.status !== 'session started') {
                throw new Error(data.message || 'Failed to start session');
            }

            // Start video recording
            startRecording();

            // Update UI
            isExercising = true;
            startBtn.disabled = true;
            endBtn.disabled = false;
            exerciseSelect.disabled = true;
            loadingSpinner.classList.add('d-none');
            cameraFeed.classList.add('d-none');
            processedFeed.classList.remove('d-none');
            currentExercise.textContent = selectedExercise;

            // Start timer
            startTime = new Date();
            durationInterval = setInterval(updateDuration, 1000);

            // Start processing frames
            requestAnimationFrame(processFrame);

        } catch (error) {
            console.error('Error starting exercise:', error);
            alert(`Error starting exercise: ${error.message}`);
            loadingSpinner.classList.add('d-none');
            waitingMessage.classList.remove('d-none');
        }
    }

    // Process video frames
    async function processFrame() {
        if (!isExercising) return;

        // Skip if we're still processing the previous frame
        if (processingFrame) {
            requestAnimationFrame(processFrame);
            return;
        }

        processingFrame = true;

        try {
            // Take snapshot of video
            const canvas = document.createElement('canvas');
            canvas.width = cameraFeed.videoWidth;
            canvas.height = cameraFeed.videoHeight;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(cameraFeed, 0, 0);
            
            // Convert to base64
            const imageData = canvas.toDataURL('image/jpeg');
            
            // Send to server for processing
            const response = await fetch('/process_frame', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    image: imageData
                })
            });
            
            const data = await response.json();
            
            if (data.error) {
                console.error('Error processing frame:', data.error);
            } else {
                // Update the processed feed
                processedFeed.src = data.image;
                
                // Update rep counter
                repCounter.textContent = data.rep_count;
                
                // Update rep progress bar
                let progressPercentage = Math.min((data.rep_count / 15) * 100, 100);
                repProgress.style.width = `${progressPercentage}%`;
                
                // Update feedback if available
                if (data.session_data && data.session_data.feedback_history) {
                    const latestFeedback = data.session_data.feedback_history.slice(-1)[0];
                    if (latestFeedback) {
                        lastFeedback.textContent = latestFeedback;
                    }
                }
                
                // Store session data for later use
                sessionData = data.session_data;
                
                // Celebrate milestone reps
                if (data.rep_count > lastRepCount) {
                    if (data.rep_count % 5 === 0) {
                        celebrateReps(data.rep_count);
                    }
                    lastRepCount = data.rep_count;
                }
            }
        } catch (error) {
            console.error('Error processing frame:', error);
        } finally {
            processingFrame = false;
            
            // Continue processing if still exercising
            if (isExercising) {
                requestAnimationFrame(processFrame);
            }
        }
    }

    // Update duration display
    function updateDuration() {
        if (!startTime) return;
        
        const elapsed = Math.floor((new Date() - startTime) / 1000);
        const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
        const seconds = (elapsed % 60).toString().padStart(2, '0');
        sessionDuration.textContent = `${minutes}:${seconds}`;
    }

    // End the exercise session
    async function endExercise() {
        if (!isExercising) return;
        
        try {
            // Show loading spinner during processing
            loadingSpinner.classList.remove('d-none');
            
            // Stop frame processing
            isExercising = false;
            
            // Stop timer
            clearInterval(durationInterval);
            
            // Stop recording
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
            }
            
            // Call server to end session but don't save yet
            const response = await fetch('/end_session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    save_video: false  // Don't save automatically
                })
            });
            
            const data = await response.json();
            
            // Update summary
            if (data.summary) {
                summaryReps.textContent = data.summary.total_reps || 0;
                
                // Calculate average rep time
                if (data.summary.rep_times && data.summary.rep_times.length > 0) {
                    const avgTime = data.summary.rep_times.reduce((a, b) => a + b, 0) / data.summary.rep_times.length;
                    summaryAvgTime.textContent = `${avgTime.toFixed(1)}s`;
                } else {
                    summaryAvgTime.textContent = "N/A";
                }
                
                // Show feedback history
                if (data.summary.feedback && data.summary.feedback.length > 0) {
                    feedbackList.innerHTML = '';
                    data.summary.feedback.forEach(feedback => {
                        const li = document.createElement('li');
                        li.className = 'list-group-item';
                        li.textContent = feedback;
                        feedbackList.appendChild(li);
                    });
                } else {
                    feedbackList.innerHTML = '<li class="list-group-item text-muted">No feedback recorded</li>';
                }
            }
            
            // Show total duration
            summaryDuration.textContent = sessionDuration.textContent;
            
            // Show summary section
            sessionSummary.classList.remove('d-none');
            
            // Show workout controls
            workoutControls.classList.remove('d-none');
            
        } catch (error) {
            console.error('Error ending exercise:', error);
            alert(`Error ending exercise: ${error.message}`);
        } finally {
            // Update UI
            loadingSpinner.classList.add('d-none');
            endBtn.disabled = true;
            processedFeed.classList.add('d-none');
            waitingMessage.textContent = 'Session ended';
            waitingMessage.classList.remove('d-none');
        }
    }

    // Start recording video
    function startRecording() {
        try {
            if (!stream) return;
            
            videoChunks = [];
            const options = { mimeType: 'video/webm;codecs=vp9' };
            mediaRecorder = new MediaRecorder(stream, options);
            
            mediaRecorder.ondataavailable = function(e) {
                if (e.data.size > 0) {
                    videoChunks.push(e.data);
                }
            };
            
            mediaRecorder.onstop = function() {
                recordedBlob = new Blob(videoChunks, { type: 'video/webm' });
            };
            
            mediaRecorder.start(1000); // Collect 1 second chunks
        } catch (error) {
            console.error('Error starting video recording:', error);
        }
    }

    // Save workout to profile
    async function saveWorkout() {
        try {
            loadingSpinner.classList.remove('d-none');
            
            // First upload the video if available
            let videoPath = null;
            if (recordedBlob) {
                // Create form data with video blob
                const formData = new FormData();
                const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
                const filename = `workout_${currentExercise.textContent.replace(/\s+/g, '_')}_${timestamp}.webm`;
                formData.append('video', recordedBlob, filename);
                
                // Upload to server
                const uploadResponse = await fetch('/upload_video', {
                    method: 'POST',
                    body: formData
                });
                
                const uploadData = await uploadResponse.json();
                
                if (uploadData.status === 'success') {
                    videoPath = uploadData.path;
                }
            }
            
            // Now save the session with the video path
            const saveResponse = await fetch('/save_session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    exercise: currentExercise.textContent,
                    rep_count: parseInt(summaryReps.textContent),
                    duration: sessionDuration.textContent,
                    video_path: videoPath,
                    session_data: sessionData
                })
            });
            
            const saveData = await saveResponse.json();
            
            if (saveData.status === 'success') {
                // Show success message
                const successAlert = document.createElement('div');
                successAlert.className = 'alert alert-success mt-3';
                successAlert.innerHTML = '<i class="fas fa-check-circle me-2"></i> Workout saved successfully!';
                sessionSummary.prepend(successAlert);
                
                // Disable save button
                saveWorkoutBtn.disabled = true;
                saveWorkoutBtn.innerHTML = '<i class="fas fa-check"></i> Workout Saved';
                
                // Update charts after a short delay
                setTimeout(() => {
                    if (typeof updateCharts === 'function') {
                        updateCharts(currentExercise.textContent);
                    }
                }, 1000);
                
                // Auto-scroll to progress section after a short delay
                setTimeout(() => {
                    document.getElementById('progress-section').scrollIntoView({ behavior: 'smooth' });
                }, 2000);
            } else {
                throw new Error(saveData.message || 'Failed to save workout');
            }
            
        } catch (error) {
            console.error('Error saving workout:', error);
            alert(`Error saving workout: ${error.message}`);
        } finally {
            loadingSpinner.classList.add('d-none');
        }
    }

    // Discard workout without saving
    function discardWorkout() {
        // Ask for confirmation
        if (confirm('Are you sure you want to discard this workout? This action cannot be undone.')) {
            resetWorkout();
        }
    }

    // Reset for a new workout
    function resetWorkout() {
        // Reset UI elements
        exerciseSelect.disabled = false;
        startBtn.disabled = !exerciseSelect.value;
        endBtn.disabled = true;
        repCounter.textContent = '0';
        repProgress.style.width = '0%';
        sessionDuration.textContent = '00:00';
        currentExercise.textContent = '-';
        lastFeedback.textContent = 'No feedback yet';
        
        // Hide summary and controls
        sessionSummary.classList.add('d-none');
        workoutControls.classList.add('d-none');
        
        // Reset state
        lastRepCount = 0;
        recordedBlob = null;
        videoChunks = [];
        sessionData = null;
        
        // Stop camera if still active
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
        }
        
        // Update waiting message
        waitingMessage.textContent = 'Click "Start Exercise" to begin';
        
        // Remove any success alerts
        const alerts = sessionSummary.querySelectorAll('.alert');
        alerts.forEach(alert => alert.remove());
        
        // Re-enable save button
        saveWorkoutBtn.disabled = false;
        saveWorkoutBtn.innerHTML = '<i class="fas fa-save"></i> Save Workout';
    }

    // Visual celebration for milestone reps
    function celebrateReps(count) {
        // Create a temporary overlay for celebration
        const overlay = document.createElement('div');
        overlay.className = 'overlay-message';
        overlay.style.backgroundColor = 'rgba(39, 174, 96, 0.7)';
        overlay.style.zIndex = '1000';
        overlay.innerHTML = `<div><h2>${count} REPS!</h2><p>Great job! Keep going!</p></div>`;
        
        document.querySelector('.video-container').appendChild(overlay);
        
        // Remove after 2 seconds
        setTimeout(() => {
            overlay.remove();
        }, 2000);
    }

    // Initialize the module
    init();
});