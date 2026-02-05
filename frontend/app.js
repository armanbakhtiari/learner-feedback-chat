// Shared JavaScript utilities for the application

// Auto-detect API base URL based on environment
function detectApiBaseUrl() {
    const hostname = window.location.hostname;
    const port = window.location.port;
    const protocol = window.location.protocol;
    
    console.log('🔍 API URL Detection:');
    console.log('   Hostname:', hostname);
    console.log('   Port:', port);
    console.log('   Protocol:', protocol);
    console.log('   Full URL:', window.location.href);
    
    // If we're on localhost with port 3000, backend is on 8000
    if (hostname === 'localhost' && port === '3000') {
        const backendUrl = 'http://localhost:8000';
        console.log('🏠 Local development mode (separate ports)');
        console.log('   Backend URL:', backendUrl);
        return backendUrl;
    }
    
    // Check if running on Replit (any Replit domain)
    const isReplit = hostname.includes('replit.app') || 
                     hostname.includes('repl.co') || 
                     hostname.includes('replit.dev') ||
                     hostname.includes('riker.replit');
    
    if (isReplit) {
        console.log('🔧 Detected Replit environment');
        
        // Always use port 8000 for Replit - FastAPI serves everything
        // This works for both preview and deployment
        if (port && port !== '8000' && port !== '80' && port !== '443' && port !== '') {
            // We're on a different port, redirect API calls to 8000
            const backendUrl = `${protocol}//${hostname}:8000`;
            console.log('   Mode: Preview - redirecting to backend port');
            console.log('   Backend URL:', backendUrl);
            return backendUrl;
        } else {
            // Same origin (deployed or already on correct port)
            const backendUrl = window.location.origin;
            console.log('   Mode: Same origin');
            console.log('   Backend URL:', backendUrl);
            return backendUrl;
        }
    }
    
    // Fallback: use same origin (works for most deployment scenarios)
    const backendUrl = window.location.origin;
    console.log('🌐 Using same origin for API');
    console.log('   Backend URL:', backendUrl);
    return backendUrl;
}

const API_BASE_URL = detectApiBaseUrl();

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

// Make API_BASE_URL globally available
window.API_BASE_URL = API_BASE_URL;

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { apiCall, showNotification, API_BASE_URL };
}
