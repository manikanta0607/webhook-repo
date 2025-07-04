// Global variables
let pollingInterval;
let lastEventCount = 0;
let isPolling = false;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Set webhook URL
    const webhookUrl = window.location.origin + '/webhook';
    document.getElementById('webhook-url').value = webhookUrl;
    
    // Start polling for events
    startPolling();
    
    // Load initial events
    loadEvents();
}

function startPolling() {
    if (isPolling) return;
    
    isPolling = true;
    updateStatusIndicator('connected');
    
    // Poll every 15 seconds as specified in requirements
    pollingInterval = setInterval(loadEvents, 15000);
    
    console.log('Started polling for events every 15 seconds');
}

function stopPolling() {
    if (!isPolling) return;
    
    isPolling = false;
    clearInterval(pollingInterval);
    updateStatusIndicator('disconnected');
    
    console.log('Stopped polling for events');
}

function updateStatusIndicator(status) {
    const indicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');
    
    if (status === 'connected') {
        indicator.className = 'fas fa-circle text-success me-1';
        statusText.textContent = 'Connected';
    } else if (status === 'disconnected') {
        indicator.className = 'fas fa-circle text-danger me-1';
        statusText.textContent = 'Disconnected';
    } else if (status === 'loading') {
        indicator.className = 'fas fa-spinner fa-spin text-warning me-1';
        statusText.textContent = 'Loading...';
    }
}

async function loadEvents() {
    try {
        updateStatusIndicator('loading');
        
        const response = await fetch('/api/events');
        const data = await response.json();
        
        if (response.ok) {
            renderEvents(data.events);
            updateStatusIndicator('connected');
            
            // Check for new events
            if (data.count > lastEventCount) {
                console.log(`New events detected: ${data.count - lastEventCount}`);
                lastEventCount = data.count;
            }
        } else {
            throw new Error(data.error || 'Failed to load events');
        }
    } catch (error) {
        console.error('Error loading events:', error);
        updateStatusIndicator('disconnected');
        showError('Failed to load events. Please check your connection.');
    }
}

function renderEvents(events) {
    const container = document.getElementById('events-container');
    
    if (!events || events.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fab fa-github text-muted"></i>
                <h5>No Events Yet</h5>
                <p class="text-muted">
                    Webhook events will appear here when they are received.<br>
                    You can test the system using the buttons below.
                </p>
            </div>
        `;
        return;
    }
    
    const eventsHtml = events.map(event => {
        const iconClass = getEventIcon(event.type);
        const eventClass = `event-${event.type}`;
        
        return `
            <div class="event-item d-flex align-items-start">
                <div class="event-icon ${eventClass}">
                    <i class="${iconClass}"></i>
                </div>
                <div class="event-content">
                    <p class="event-message">${escapeHtml(event.message)}</p>
                    <div class="event-meta">
                        <span class="badge bg-secondary me-2">${event.type.toUpperCase()}</span>
                        <span class="me-2">
                            <i class="fas fa-repository me-1"></i>
                            ${escapeHtml(event.repository)}
                        </span>
                        <span>
                            <i class="fas fa-clock me-1"></i>
                            ${escapeHtml(event.timestamp)}
                        </span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = eventsHtml;
}

function getEventIcon(eventType) {
    const icons = {
        'push': 'fas fa-upload',
        'pull_request': 'fas fa-code-branch',
        'merge': 'fas fa-code-merge'
    };
    
    return icons[eventType] || 'fas fa-question';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function sendTestEvent(eventType) {
    try {
        updateStatusIndicator('loading');
        
        const response = await fetch('/test-webhook', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ type: eventType })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showSuccess(`Test ${eventType} event created successfully!`);
            // Immediately load events to show the new one
            setTimeout(loadEvents, 500);
        } else {
            throw new Error(data.error || 'Failed to create test event');
        }
    } catch (error) {
        console.error('Error sending test event:', error);
        showError(`Failed to create test ${eventType} event: ${error.message}`);
    }
}

function refreshEvents() {
    loadEvents();
    showSuccess('Events refreshed successfully!');
}

function clearEvents() {
    if (confirm('Are you sure you want to clear all events? This action cannot be undone.')) {
        // Since we're using in-memory storage, we'll just refresh the page
        // In a real application, you would call an API to clear the events
        showInfo('Clear functionality would be implemented with proper backend storage.');
    }
}

function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    element.select();
    element.setSelectionRange(0, 99999);
    
    try {
        document.execCommand('copy');
        showSuccess('Webhook URL copied to clipboard!');
    } catch (error) {
        console.error('Error copying to clipboard:', error);
        showError('Failed to copy URL to clipboard');
    }
}

// Notification functions
function showSuccess(message) {
    showNotification(message, 'success');
}

function showError(message) {
    showNotification(message, 'error');
}

function showInfo(message) {
    showNotification(message, 'info');
}

function showNotification(message, type) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.style.minWidth = '300px';
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Add to body
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

// Handle visibility change to pause/resume polling
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        console.log('Page hidden, continuing polling in background');
    } else {
        console.log('Page visible, ensuring polling is active');
        if (!isPolling) {
            startPolling();
        }
        // Immediately load events when page becomes visible
        loadEvents();
    }
});

// Handle page unload
window.addEventListener('beforeunload', function() {
    stopPolling();
});