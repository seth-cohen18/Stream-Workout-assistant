// theme-switcher.js - Handles dark/light theme switching

document.addEventListener('DOMContentLoaded', function() {
    const toggleSwitch = document.querySelector('.theme-switch input[type="checkbox"]');
    const currentTheme = localStorage.getItem('theme');

    // Check for saved user preference and apply it
    if (currentTheme) {
        document.documentElement.setAttribute('data-theme', currentTheme);
        if (currentTheme === 'dark') {
            toggleSwitch.checked = true;
        }
    } else {
        // Check for system preference
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            document.documentElement.setAttribute('data-theme', 'dark');
            toggleSwitch.checked = true;
            localStorage.setItem('theme', 'dark');
        }
    }

    // Function to handle theme switch
    function switchTheme(e) {
        if (e.target.checked) {
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
            updateCharts('dark');
        } else {
            document.documentElement.setAttribute('data-theme', 'light');
            localStorage.setItem('theme', 'light');
            updateCharts('light');
        }    
    }

    // Add event listener for theme switch
    toggleSwitch.addEventListener('change', switchTheme, false);

    // Function to update charts with the new theme colors
    function updateCharts(theme) {
        // If there are dynamic charts in the page, refresh them with new theme colors
        if (typeof refreshCharts === 'function') {
            refreshCharts(theme);
        }
        
        // Reload static chart images with theme parameter
        const chartImages = document.querySelectorAll('.chart-container img');
        chartImages.forEach(img => {
            if (img.src.includes('/api/progress/')) {
                let newSrc = img.src.split('?')[0]; // Remove any existing query params
                newSrc += `?theme=${theme}&t=${Date.now()}`; // Add theme and cache buster
                img.src = newSrc;
            }
        });
    }
});