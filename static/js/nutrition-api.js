// static/js/nutrition-api.js
class NutritionAPI {
    constructor() {
        // Base URL for API requests
        this.baseUrl = '/api/recipes';
    }

    /**
     * Search for recipes by multiple ingredients
     * @param {Array} ingredients - Array of ingredients to search for
     * @param {boolean} searchAll - If true, only return recipes that use all ingredients
     * @returns {Promise} - Promise that resolves to recipe results
     */
    async searchRecipes(ingredients, searchAll = true) {
        try {
            if (!ingredients || ingredients.length === 0) {
                throw new Error('No ingredients provided');
            }
            
            // Join ingredients with commas
            const ingredientsParam = ingredients.join(',');
            
            // Make API request
            const response = await fetch(
                `${this.baseUrl}/search?ingredients=${encodeURIComponent(ingredientsParam)}&searchAll=${searchAll}`
            );
            
            // Check for errors
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || `Error: ${response.status}`);
            }
            
            // Return data
            return await response.json();
        } catch (error) {
            console.error('Error searching recipes:', error);
            throw error;
        }
    }

    /**
     * Get detailed information about a specific recipe
     * @param {string} recipeId - The ID of the recipe to get details for
     * @returns {Promise} - Promise that resolves to recipe details
     */
    async getRecipeDetails(recipeId) {
        try {
            if (!recipeId) {
                throw new Error('No recipe ID provided');
            }
            
            // Make API request
            const response = await fetch(`${this.baseUrl}/${recipeId}`);
            
            // Check for errors
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || `Error: ${response.status}`);
            }
            
            // Return data
            return await response.json();
        } catch (error) {
            console.error('Error getting recipe details:', error);
            throw error;
        }
    }
    
    /**
     * Formats ingredients from a meal object into a readable list
     * @param {Object} meal - TheMealDB meal object
     * @returns {Array} - Array of ingredient and measure pairs
     */
    formatIngredients(meal) {
        const ingredients = [];
        
        // TheMealDB stores ingredients as ingredient1, ingredient2, etc.
        for (let i = 1; i <= 20; i++) {
            const ingredient = meal[`strIngredient${i}`];
            const measure = meal[`strMeasure${i}`];
            
            if (ingredient && ingredient.trim() !== '') {
                ingredients.push({
                    ingredient: ingredient,
                    measure: measure || ''
                });
            }
        }
        
        return ingredients;
    }
}

// Create global instance
window.nutritionAPI = new NutritionAPI();