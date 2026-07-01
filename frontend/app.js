// Shared JavaScript utilities for the application

// Production backend (Google Cloud Run). The frontend (hosted on Vercel) calls this
// directly via CORS. We do NOT proxy through Vercel rewrites because some endpoints
// (e.g. /evaluate) run for ~2 minutes, which exceeds Vercel's gateway timeout.
const PROD_BACKEND_URL = 'https://feedback-chatbot-75563101301.northamerica-northeast1.run.app';

// Auto-detect API base URL based on environment
function detectApiBaseUrl() {
    const hostname = window.location.hostname;
    const port = window.location.port;

    // Local development: static frontend on :3000, backend on :8000.
    if ((hostname === 'localhost' || hostname === '127.0.0.1') && port === '3000') {
        return 'http://localhost:8000';
    }

    // Local: backend serving the frontend itself (same origin).
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return window.location.origin;
    }

    // Production (Vercel or any other host): talk to Cloud Run directly.
    return PROD_BACKEND_URL;
}

const API_BASE_URL = detectApiBaseUrl();
console.log('🌐 API base URL:', API_BASE_URL);

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
