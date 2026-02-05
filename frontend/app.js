// Shared JavaScript utilities for the application

// Auto-detect API base URL based on environment
const API_BASE_URL = (() => {
    const hostname = window.location.hostname;
    const port = window.location.port;
    
    // If we're on localhost with port 3000, backend is on 8000
    if (hostname === 'localhost' && port === '3000') {
        console.log('🏠 Local development mode (separate ports)');
        return 'http://localhost:8000';
    }
    
    // Check if running on Replit (any Replit domain)
    if (hostname.includes('replit.app') || 
        hostname.includes('repl.co') || 
        hostname.includes('replit.dev')) {
        
        console.log('🔧 Detected Replit environment');
        console.log('   Frontend URL:', window.location.href);
        console.log('   Hostname:', hostname);
        console.log('   Port:', port);
        
        // Check if we're on port 3000 (preview mode) or deployed
        if (port === '3000') {
            // Preview mode: backend on port 8000
            const protocol = window.location.protocol;
            // Replit URLs format: https://hostname:port
            // We need to change :3000 to :8000
            const baseHost = hostname; // hostname doesn't include port
            const backendUrl = `${protocol}//${baseHost}:8000`;
            console.log('   Mode: Preview (two ports)');
            console.log('   Backend URL:', backendUrl);
            return backendUrl;
        } else {
            // Deployed mode: same origin (backend serves frontend)
            const backendUrl = window.location.origin;
            console.log('   Mode: Deployed (single port)');
            console.log('   Backend URL:', backendUrl);
            return backendUrl;
        }
    }
    
    // Fallback: use same origin (works for most deployment scenarios)
    console.log('🌐 Using same origin for API');
    return window.location.origin;
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
