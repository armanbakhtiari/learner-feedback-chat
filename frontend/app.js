// Shared JavaScript utilities for the application

// Auto-detect API base URL based on environment
const API_BASE_URL = (() => {
    const hostname = window.location.hostname;
    const port = window.location.port;
    
    // Check if running on Replit (any Replit domain)
    if (hostname.includes('replit.app') || 
        hostname.includes('repl.co') || 
        hostname.includes('replit.dev')) {
        
        console.log('🔧 Detected Replit environment');
        console.log('   Frontend:', window.location.href);
        
        // Check if we're on port 3000 (preview mode) or deployed (no port/80/443)
        if (port === '3000') {
            // Preview mode: separate frontend/backend ports
            const protocol = window.location.protocol;
            const backendUrl = `${protocol}//${hostname.replace(':3000', '')}:8000`;
            console.log('   Mode: Preview (port 3000)');
            console.log('   Backend:', backendUrl);
            return backendUrl;
        } else {
            // Deployed mode: same port for frontend and backend
            const backendUrl = window.location.origin; // Same as frontend
            console.log('   Mode: Deployed (single port)');
            console.log('   Backend:', backendUrl);
            return backendUrl;
        }
    }
    
    // Local development
    console.log('🏠 Local development mode');
    return 'http://localhost:8000';
})();

// API Helper Functions
async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.statusText}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

// Utility Functions
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${type === 'success' ? '#4caf50' : type === 'error' ? '#f44336' : '#2196f3'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { apiCall, showNotification };
}
