// nutrition.js - Handles recipe search functionality

document.addEventListener('DOMContentLoaded', function() {
    // DOM elements - Ingredient Search
    const ingredientsInput = document.getElementById('ingredients-input');
    const addIngredientBtn = document.getElementById('add-ingredient-btn');
    const ingredientsList = document.getElementById('ingredients-list');
    const searchAllRadio = document.getElementById('search-all');
    const searchAnyRadio = document.getElementById('search-any');
    const findRecipesBtn = document.getElementById('find-recipes-btn');
    
    // DOM elements - Meal Search
    const mealSearchInput = document.getElementById('meal-search-input');
    const searchMealBtn = document.getElementById('search-meal-btn');
    const categorySelect = document.getElementById('category-select');
    const searchCategoryBtn = document.getElementById('search-category-btn');
    
    // DOM elements - Dietary Preferences
    const allergiesInput = document.getElementById('allergies-input');
    const addAllergyBtn = document.getElementById('add-allergy-btn');
    const allergiesList = document.getElementById('allergies-list');
    const savePreferencesBtn = document.getElementById('save-preferences-btn');
    const dietRestrictions = document.querySelectorAll('.diet-restriction');
    
    // DOM elements - Results and Details
    const recipeResults = document.getElementById('recipe-results');
    const resultsMessage = document.getElementById('results-message');
    const recipeCards = document.getElementById('recipe-cards');
    const recipeDetail = document.getElementById('recipe-detail');
    const backToResultsBtn = document.getElementById('back-to-results');
    
    // Recipe detail elements
    const recipeImage = document.getElementById('recipe-image');
    const recipeTitle = document.getElementById('recipe-title');
    const recipeCategory = document.getElementById('recipe-category');
    const recipeArea = document.getElementById('recipe-area');
    const recipeTags = document.getElementById('recipe-tags');
    const recipeIngredients = document.getElementById('recipe-ingredients');
    const recipeInstructions = document.getElementById('recipe-instructions');
    const recipeSource = document.getElementById('recipe-source');
    const recipeYoutube = document.getElementById('recipe-youtube');

    // State variables
    let ingredients = [];
    let allergies = [];
    let foundRecipes = [];
    let filteredRecipes = [];

    // Initialize
    function init() {
        // Set up event listeners - Ingredient Search
        addIngredientBtn.addEventListener('click', addIngredient);
        ingredientsInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                addIngredient();
            }
        });
        findRecipesBtn.addEventListener('click', searchRecipesByIngredients);

        // Set up event listeners - Meal Search
        searchMealBtn.addEventListener('click', searchRecipesByName);
        mealSearchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                searchRecipesByName();
            }
        });
        searchCategoryBtn.addEventListener('click', searchRecipesByCategory);

        // Set up event listeners - Dietary Preferences
        addAllergyBtn.addEventListener('click', addAllergy);
        allergiesInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                addAllergy();
            }
        });
        savePreferencesBtn.addEventListener('click', savePreferences);

        // Navigation event listeners
        backToResultsBtn.addEventListener('click', showRecipeList);

        // Load saved preferences
        loadPreferences();
    }

    // Load saved preferences from localStorage
    function loadPreferences() {
        // Load allergies
        const savedAllergies = localStorage.getItem('foodAllergies');
        if (savedAllergies) {
            const parsedAllergies = JSON.parse(savedAllergies);
            allergies = parsedAllergies;
            
            // Create tags for each saved allergy
            allergies.forEach(allergy => {
                createAllergyTag(allergy);
            });
        }
        
        // Load dietary restrictions
        const savedRestrictions = localStorage.getItem('dietaryRestrictions');
        if (savedRestrictions) {
            const parsedRestrictions = JSON.parse(savedRestrictions);
            
            // Set checkboxes based on saved preferences
            dietRestrictions.forEach(checkbox => {
                const restrictionType = checkbox.id.replace('-check', '');
                if (parsedRestrictions.includes(restrictionType)) {
                    checkbox.checked = true;
                }
            });
        }
    }

    // Save preferences to localStorage
    function savePreferences() {
        // Save allergies
        localStorage.setItem('foodAllergies', JSON.stringify(allergies));
        
        // Save dietary restrictions
        const activeRestrictions = [];
        dietRestrictions.forEach(checkbox => {
            if (checkbox.checked) {
                const restrictionType = checkbox.id.replace('-check', '');
                activeRestrictions.push(restrictionType);
            }
        });
        
        localStorage.setItem('dietaryRestrictions', JSON.stringify(activeRestrictions));
        
        // Show confirmation
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-success mt-3';
        alertDiv.innerHTML = '<i class="fas fa-check-circle"></i> Dietary preferences saved successfully!';
        alertDiv.style.transition = 'opacity 0.5s';
        
        document.getElementById('preferences-panel').appendChild(alertDiv);
        
        // Fade out after 3 seconds
        setTimeout(() => {
            alertDiv.style.opacity = '0';
            setTimeout(() => alertDiv.remove(), 500);
        }, 3000);
    }

    // Add an ingredient to the list
    function addIngredient() {
        const inputValue = ingredientsInput.value.trim();
        
        if (!inputValue) return;
        
        // Check if multiple ingredients (comma separated)
        if (inputValue.includes(',')) {
            const items = inputValue.split(',');
            items.forEach(item => {
                const trimmed = item.trim();
                if (trimmed && !ingredients.includes(trimmed.toLowerCase())) {
                    createIngredientTag(trimmed);
                    ingredients.push(trimmed.toLowerCase());
                }
            });
        } else {
            // Single ingredient
            if (!ingredients.includes(inputValue.toLowerCase())) {
                createIngredientTag(inputValue);
                ingredients.push(inputValue.toLowerCase());
            }
        }
        
        // Reset input
        ingredientsInput.value = '';
        ingredientsInput.focus();
        
        // Enable search button if we have ingredients
        findRecipesBtn.disabled = ingredients.length === 0;
    }

    // Create and add an ingredient tag to the UI
    function createIngredientTag(ingredient) {
        const tag = document.createElement('div');
        tag.className = 'ingredient-tag';
        tag.textContent = ingredient;
        
        const removeBtn = document.createElement('button');
        removeBtn.className = 'remove-ingredient';
        removeBtn.innerHTML = '&times;';
        removeBtn.setAttribute('aria-label', `Remove ${ingredient}`);
        removeBtn.addEventListener('click', function() {
            removeIngredient(tag, ingredient.toLowerCase());
        });
        
        tag.appendChild(removeBtn);
        ingredientsList.appendChild(tag);
    }

    // Remove an ingredient from the list
    function removeIngredient(tagElement, ingredient) {
        // Remove from array
        const index = ingredients.indexOf(ingredient);
        if (index > -1) {
            ingredients.splice(index, 1);
        }
        
        // Remove from UI
        tagElement.remove();
        
        // Disable search button if no ingredients
        findRecipesBtn.disabled = ingredients.length === 0;
    }

    // Add an allergy to the list
    function addAllergy() {
        const inputValue = allergiesInput.value.trim();
        
        if (!inputValue) return;
        
        // Check if multiple allergies (comma separated)
        if (inputValue.includes(',')) {
            const items = inputValue.split(',');
            items.forEach(item => {
                const trimmed = item.trim();
                if (trimmed && !allergies.includes(trimmed.toLowerCase())) {
                    createAllergyTag(trimmed);
                    allergies.push(trimmed.toLowerCase());
                }
            });
        } else {
            // Single allergy
            if (!allergies.includes(inputValue.toLowerCase())) {
                createAllergyTag(inputValue);
                allergies.push(inputValue.toLowerCase());
            }
        }
        
        // Reset input
        allergiesInput.value = '';
        allergiesInput.focus();
    }

    // Create and add an allergy tag to the UI
    function createAllergyTag(allergy) {
        const tag = document.createElement('div');
        tag.className = 'allergy-tag';
        tag.textContent = allergy;
        
        const removeBtn = document.createElement('button');
        removeBtn.className = 'remove-allergy';
        removeBtn.innerHTML = '&times;';
        removeBtn.setAttribute('aria-label', `Remove ${allergy}`);
        removeBtn.addEventListener('click', function() {
            removeAllergy(tag, allergy.toLowerCase());
        });
        
        tag.appendChild(removeBtn);
        allergiesList.appendChild(tag);
    }

    // Remove an allergy from the list
    function removeAllergy(tagElement, allergy) {
        // Remove from array
        const index = allergies.indexOf(allergy);
        if (index > -1) {
            allergies.splice(index, 1);
        }
        
        // Remove from UI
        tagElement.remove();
    }

    // Search for recipes using selected ingredients
    async function searchRecipesByIngredients() {
        if (ingredients.length === 0) {
            alert('Please add at least one ingredient');
            return;
        }
        
        try {
            // Show loading message
            showLoadingMessage();
            
            // Build query parameters
            const searchAll = searchAllRadio.checked;
            const params = new URLSearchParams({
                ingredients: ingredients.join(','),
                searchAll: searchAll
            });
            
            // Make API request with retry logic
            let retryCount = 0;
            let response = null;
            let success = false;
            
            while (retryCount < 3 && !success) {
                try {
                    // Add a small delay on retries to avoid overwhelming the API
                    if (retryCount > 0) {
                        await new Promise(resolve => setTimeout(resolve, 1000));
                    }
                    
                    response = await fetch(`/api/recipes/search?${params.toString()}`, {
                        method: 'GET',
                        headers: {
                            'Accept': 'application/json'
                        }
                    });
                    
                    if (response.ok) {
                        success = true;
                    } else {
                        retryCount++;
                    }
                } catch (error) {
                    console.error(`API request attempt ${retryCount + 1} failed:`, error);
                    retryCount++;
                }
            }
            
            if (!success) {
                throw new Error('Failed to connect to recipe API after multiple attempts');
            }
            
            const data = await response.json();
            
            // Store all found recipes
            foundRecipes = data.meals || [];
            
            // Filter out recipes with allergic ingredients
            filteredRecipes = filterRecipesByAllergies(foundRecipes);
            
            // Display results
            displayRecipeResults(filteredRecipes, data.status);
            
        } catch (error) {
            console.error('Error searching recipes:', error);
            resultsMessage.textContent = `Error: ${error.message}. Please try again later.`;
            resultsMessage.className = 'alert alert-danger';
            resultsMessage.classList.remove('d-none');
        }
    }

    // Search for recipes by name
    async function searchRecipesByName() {
        const searchTerm = mealSearchInput.value.trim();
        
        if (!searchTerm) {
            alert('Please enter a meal or recipe name');
            return;
        }
        
        try {
            // Show loading message
            showLoadingMessage();
            
            // Make API request
            const response = await fetch(`/api/recipes/search-name?name=${encodeURIComponent(searchTerm)}`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`API returned error: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Store all found recipes
            foundRecipes = data.meals || [];
            
            // Filter out recipes with allergic ingredients
            filteredRecipes = filterRecipesByAllergies(foundRecipes);
            
            // Display results
            displayRecipeResults(filteredRecipes, data.status, searchTerm);
            
        } catch (error) {
            console.error('Error searching recipes by name:', error);
            resultsMessage.textContent = `Error: ${error.message}. Please try again later.`;
            resultsMessage.className = 'alert alert-danger';
            resultsMessage.classList.remove('d-none');
        }
    }

    // Search for recipes by category
    async function searchRecipesByCategory() {
        const category = categorySelect.value;
        
        try {
            // Show loading message
            showLoadingMessage();
            
            // Make API request
            const response = await fetch(`/api/recipes/category?c=${encodeURIComponent(category)}`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`API returned error: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Store all found recipes
            foundRecipes = data.meals || [];
            
            // Filter out recipes with allergic ingredients
            filteredRecipes = filterRecipesByAllergies(foundRecipes);
            
            // Display results
            const categoryName = category || 'All Categories';
            displayRecipeResults(filteredRecipes, data.status, categoryName);
            
        } catch (error) {
            console.error('Error searching recipes by category:', error);
            resultsMessage.textContent = `Error: ${error.message}. Please try again later.`;
            resultsMessage.className = 'alert alert-danger';
            resultsMessage.classList.remove('d-none');
        }
    }

    // Filter recipes to exclude those with allergic ingredients
    function filterRecipesByAllergies(recipes) {
        // If no allergies, return all recipes
        if (!allergies.length) return recipes;
        
        return recipes.filter(recipe => {
            // For each recipe, we need to check its ingredients
            // First, need to get the details for the recipe
            let hasAllergen = false;
            
            // Check if the recipe has the 'matchedIngredients' property
            const recipeIngredients = recipe.matchedIngredients || [];
            
            // In case of search by name or category, we might have pre-populated ingredients
            if (recipe.ingredients) {
                recipeIngredients.push(...recipe.ingredients);
            }
            
            // Check against allergies
            for (const allergen of allergies) {
                if (recipeIngredients.some(ingredient => 
                    ingredient.toLowerCase().includes(allergen))) {
                    hasAllergen = true;
                    break;
                }
            }
            
            // Only include recipe if it doesn't contain allergens
            return !hasAllergen;
        });
    }

    // Show loading message
    function showLoadingMessage() {
        recipeResults.classList.remove('d-none');
        recipeDetail.classList.add('d-none');
        resultsMessage.textContent = 'Searching for recipes...';
        resultsMessage.className = 'alert alert-info';
        resultsMessage.classList.remove('d-none');
        recipeCards.innerHTML = '';
    }

    // Display recipe search results
    function displayRecipeResults(recipes, status, searchTerm = '') {
        // Update results section visibility
        recipeResults.classList.remove('d-none');
        recipeDetail.classList.add('d-none');
        
        // Handle no results or filtered out all recipes
        if (!recipes || recipes.length === 0) {
            let message = 'No recipes found';
            
            if (searchTerm) {
                message += ` for "${searchTerm}"`;
            }
            
            if (foundRecipes.length > 0 && filteredRecipes.length === 0) {
                message += ". Note: All found recipes were filtered out due to your dietary preferences.";
            }
            
            resultsMessage.textContent = message;
            resultsMessage.className = 'alert alert-warning';
            resultsMessage.classList.remove('d-none');
            recipeCards.innerHTML = '';
            return;
        }
        
        // Show success message
        let successMessage = `Found ${recipes.length} recipe${recipes.length !== 1 ? 's' : ''}`;
        
        if (searchTerm) {
            successMessage += ` for "${searchTerm}"`;
        }
        
        // Note if recipes were filtered out
        if (foundRecipes.length > filteredRecipes.length) {
            const filteredCount = foundRecipes.length - filteredRecipes.length;
            successMessage += ` (${filteredCount} filtered out based on dietary preferences)`;
        }
        
        resultsMessage.textContent = successMessage;
        resultsMessage.className = 'alert alert-success';
        resultsMessage.classList.remove('d-none');
        
        // Create recipe cards
        recipeCards.innerHTML = '';
        
        recipes.forEach((recipe, index) => {
            const matchedText = recipe.matchedIngredients 
                ? `<span class="badge bg-info">Matched: ${recipe.matchedIngredients.join(', ')}</span>` 
                : '';
                
            const card = document.createElement('div');
            card.className = 'col-md-4 mb-4';
            card.innerHTML = `
                <div class="card h-100 shadow-sm recipe-card" data-recipe-id="${recipe.idMeal}">
                    <img src="${recipe.strMealThumb}" class="card-img-top" alt="${recipe.strMeal}" loading="lazy">
                    <div class="card-body">
                        <h5 class="card-title">${recipe.strMeal}</h5>
                        <div class="mt-2 mb-2">${matchedText}</div>
                        <p class="card-text text-muted small">${recipe.strCategory || ''} ${recipe.strArea ? '• ' + recipe.strArea : ''}</p>
                    </div>
                    <div class="card-footer bg-transparent">
                        <button class="btn btn-primary btn-sm view-recipe" data-recipe-index="${index}">
                            View Recipe
                        </button>
                    </div>
                </div>
            `;
            
            recipeCards.appendChild(card);
        });
        
        // Add event listeners to view recipe buttons
        document.querySelectorAll('.view-recipe').forEach(button => {
            button.addEventListener('click', function() {
                const recipeIndex = parseInt(this.dataset.recipeIndex);
                const recipe = recipes[recipeIndex];
                viewRecipeDetails(recipe.idMeal);
            });
        });
        
        // Make entire cards clickable
        document.querySelectorAll('.recipe-card').forEach(card => {
            card.addEventListener('click', function(e) {
                // Ignore if clicked on the button itself
                if (!e.target.closest('.view-recipe')) {
                    const recipeId = this.dataset.recipeId;
                    viewRecipeDetails(recipeId);
                }
            });
        });
    }

    // Fetch and display detailed recipe information
    async function viewRecipeDetails(recipeId) {
        try {
            // Show loading in the recipe section
            recipeResults.classList.add('d-none');
            recipeDetail.classList.remove('d-none');
            recipeTitle.textContent = 'Loading recipe...';
            recipeIngredients.innerHTML = '<li class="list-group-item">Loading ingredients...</li>';
            recipeInstructions.innerHTML = '<p>Loading instructions...</p>';
            
            // Fetch recipe details
            const response = await fetch(`/api/recipes/${recipeId}`);
            
            if (!response.ok) {
                throw new Error(`Failed to fetch recipe details (${response.status})`);
            }
            
            const data = await response.json();
            
            if (data.error || !data.meal) {
                throw new Error(data.error || 'Recipe not found');
            }
            
            const recipe = data.meal;
            
            // Update recipe details
            recipeImage.src = recipe.strMealThumb;
            recipeTitle.textContent = recipe.strMeal;
            recipeCategory.textContent = recipe.strCategory || 'Uncategorized';
            recipeArea.textContent = recipe.strArea || 'Unknown';
            
            // Set tags if available
            if (recipe.strTags) {
                const tags = recipe.strTags.split(',');
                recipeTags.innerHTML = tags.map(tag => 
                    `<span class="badge bg-secondary me-1">${tag.trim()}</span>`
                ).join('');
            } else {
                recipeTags.innerHTML = '';
            }
            
            // Format ingredients
            recipeIngredients.innerHTML = '';
            if (recipe.formattedIngredients && recipe.formattedIngredients.length > 0) {
                recipe.formattedIngredients.forEach(item => {
                    // Check if this ingredient is in the allergies list
                    const isAllergen = allergies.some(allergen => 
                        item.name.toLowerCase().includes(allergen));
                    
                    const li = document.createElement('li');
                    li.className = 'list-group-item d-flex justify-content-between' + 
                                   (isAllergen ? ' list-group-item-danger' : '');
                    li.innerHTML = `
                        <span>${item.name}${isAllergen ? ' <i class="fas fa-exclamation-circle text-danger" title="Allergen"></i>' : ''}</span>
                        <span class="text-muted">${item.measure}</span>
                    `;
                    recipeIngredients.appendChild(li);
                });
            } else {
                // Legacy fallback
                for (let i = 1; i <= 20; i++) {
                    const ingredient = recipe[`strIngredient${i}`];
                    const measure = recipe[`strMeasure${i}`];
                    
                    if (ingredient && ingredient.trim()) {
                        // Check if this ingredient is in the allergies list
                        const isAllergen = allergies.some(allergen => 
                            ingredient.toLowerCase().includes(allergen));
                        
                        const li = document.createElement('li');
                        li.className = 'list-group-item d-flex justify-content-between' + 
                                       (isAllergen ? ' list-group-item-danger' : '');
                        li.innerHTML = `
                            <span>${ingredient}${isAllergen ? ' <i class="fas fa-exclamation-circle text-danger" title="Allergen"></i>' : ''}</span>
                            <span class="text-muted">${measure || ''}</span>
                        `;
                        recipeIngredients.appendChild(li);
                    }
                }
            }
            
            // Format instructions
            recipeInstructions.textContent = recipe.strInstructions;
            
            // Set up links
            if (recipe.strSource) {
                recipeSource.href = recipe.strSource;
                recipeSource.classList.remove('d-none');
            } else {
                recipeSource.classList.add('d-none');
            }
            
            if (recipe.strYoutube) {
                recipeYoutube.href = recipe.strYoutube;
                recipeYoutube.classList.remove('d-none');
            } else {
                recipeYoutube.classList.add('d-none');
            }
            
        } catch (error) {
            console.error('Error fetching recipe details:', error);
            recipeTitle.textContent = 'Error Loading Recipe';
            recipeInstructions.innerHTML = `<p class="text-danger">Failed to load recipe details: ${error.message}</p>`;
        }
    }

    // Show recipe listing and hide detail view
    function showRecipeList() {
        recipeDetail.classList.add('d-none');
        recipeResults.classList.remove('d-none');
    }

    // Initialize the module
    init();
});