// navigation.js - Handles section navigation and UI state

document.addEventListener('DOMContentLoaded', function() {
    // Navigation links
    const homeNav = document.getElementById('home-nav');
    const workoutNav = document.getElementById('workout-nav');
    const progressNav = document.getElementById('progress-nav');
    const nutritionNav = document.getElementById('nutrition-nav');
    
    // Section content elements
    const homeSection = document.getElementById('home-section');
    const instructionsSection = document.getElementById('instructions-section');
    const workoutSection = document.getElementById('workout-section');
    const progressSection = document.getElementById('progress-section');
    const nutritionSection = document.getElementById('nutrition-section');
    
    // Buttons that navigate between sections
    const startTrainingBtn = document.getElementById('start-training-btn');
    const continueToWorkoutBtn = document.getElementById('continue-to-workout');
    
    // Exercise instruction elements
    const exerciseInstructions = document.querySelectorAll('.exercise-instruction');
    const exerciseSelect = document.getElementById('exercise-select');
    const instructionTitle = document.getElementById('instruction-title');
    
    // Initialize 
    function init() {
        // Set up navigation event listeners
        homeNav.addEventListener('click', showHomeSection);
        workoutNav.addEventListener('click', function() {
            // First show instructions then workout
            showInstructionsSection();
        });
        progressNav.addEventListener('click', showProgressSection);
        nutritionNav.addEventListener('click', showNutritionSection);
        
        // Special navigation buttons
        startTrainingBtn.addEventListener('click', showInstructionsSection);
        continueToWorkoutBtn.addEventListener('click', showWorkoutSection);
        
        // Handle exercise selection for instructions
        if (exerciseSelect) {
            exerciseSelect.addEventListener('change', updateInstructions);
        }
        
        // Activate home section by default
        showHomeSection();
        
        // Handle hash-based navigation on page load
        handleHashNavigation();
        
        // Listen for hash changes
        window.addEventListener('hashchange', handleHashNavigation);
    }
    
    // Handle navigation based on URL hash
    function handleHashNavigation() {
        const hash = window.location.hash;
        
        switch(hash) {
            case '#home-section':
                showHomeSection();
                break;
            case '#instructions-section':
                showInstructionsSection();
                break;
            case '#workout-section':
                showWorkoutSection();
                break;
            case '#progress-section':
                showProgressSection();
                break;
            case '#nutrition-section':
                showNutritionSection();
                break;
            default:
                // Default to home if no hash or unrecognized hash
                if (hash === '') {
                    showHomeSection();
                }
        }
    }
    
    // Show Home Section
    function showHomeSection(e) {
        if (e) e.preventDefault();
        
        // Hide all sections
        hideAllSections();
        
        // Show home section
        homeSection.classList.remove('d-none');
        
        // Update active nav item
        updateActiveNavItem(homeNav);
        
        // Update URL hash
        window.location.hash = 'home-section';
    }
    
    // Show Instructions Section
    function showInstructionsSection(e) {
        if (e) e.preventDefault();
        
        // Hide all sections
        hideAllSections();
        
        // Show instructions section
        instructionsSection.classList.remove('d-none');
        
        // Update active nav item
        updateActiveNavItem(workoutNav);
        
        // Update URL hash
        window.location.hash = 'instructions-section';
        
        // Update instructions for currently selected exercise
        updateInstructions();
    }
    
    // Show Workout Section
    function showWorkoutSection(e) {
        if (e) e.preventDefault();
        
        // Hide all sections
        hideAllSections();
        
        // Show workout section
        workoutSection.classList.remove('d-none');
        
        // Update active nav item
        updateActiveNavItem(workoutNav);
        
        // Update URL hash
        window.location.hash = 'workout-section';
    }
    
    // Show Progress Section
    function showProgressSection(e) {
        if (e) e.preventDefault();
        
        // Hide all sections
        hideAllSections();
        
        // Show progress section
        progressSection.classList.remove('d-none');
        
        // Update active nav item
        updateActiveNavItem(progressNav);
        
        // Update URL hash
        window.location.hash = 'progress-section';
        
        // Refresh charts if needed
        if (typeof updateCharts === 'function') {
            const progressExerciseSelect = document.getElementById('progress-exercise-select');
            if (progressExerciseSelect) {
                updateCharts(progressExerciseSelect.value);
            }
        }
    }
    
    // Show Nutrition Section
    function showNutritionSection(e) {
        if (e) e.preventDefault();
        
        // Hide all sections
        hideAllSections();
        
        // Show nutrition section
        nutritionSection.classList.remove('d-none');
        
        // Update active nav item
        updateActiveNavItem(nutritionNav);
        
        // Update URL hash
        window.location.hash = 'nutrition-section';
    }
    
    // Hide all sections
    function hideAllSections() {
        const sections = document.querySelectorAll('.section-content');
        sections.forEach(section => {
            section.classList.add('d-none');
        });
    }
    
    // Update active navigation item
    function updateActiveNavItem(activeItem) {
        // Remove active class from all nav items
        const navItems = document.querySelectorAll('.navbar-nav .nav-link');
        navItems.forEach(item => {
            item.classList.remove('active');
        });
        
        // Add active class to the clicked item
        if (activeItem) {
            activeItem.classList.add('active');
        }
    }
    
    // Update exercise instructions based on selected exercise
    function updateInstructions() {
        const selectedExercise = exerciseSelect ? exerciseSelect.value : '';
        
        // Hide all exercise instructions
        exerciseInstructions.forEach(instruction => {
            instruction.style.display = 'none';
        });
        
        // If no exercise selected, show general instructions
        if (!selectedExercise) {
            instructionTitle.textContent = 'General Instructions';
            return;
        }
        
        // Show instructions for selected exercise
        const selectedInstruction = document.querySelector(`.exercise-instruction[data-exercise="${selectedExercise}"]`);
        if (selectedInstruction) {
            selectedInstruction.style.display = 'block';
            instructionTitle.textContent = `${selectedExercise} Instructions`;
        } else {
            instructionTitle.textContent = 'Exercise Instructions';
        }
    }
    
    // Initialize navigation
    init();
});