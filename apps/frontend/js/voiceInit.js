/**
 * Voice Handler Initialization
 * Sets up voice recording controls and event listeners
 */

let voiceHandler = null;

/**
 * Initialize voice handler after Socket.IO connection is established
 */
async function initializeVoiceHandler() {
    // Wait for Socket.IO to be available
    if (typeof window.socketIO === 'undefined' || !window.socketIO) {
        console.warn('Socket.IO not yet available, retrying voice handler initialization...');
        setTimeout(initializeVoiceHandler, 1000);
        return;
    }

    try {
        // Create voice handler instance
        voiceHandler = new VoiceHandler(window.socketIO);

        // Initialize microphone access
        const initialized = await voiceHandler.initialize();
        if (!initialized) {
            console.warn('Voice handler failed to initialize microphone');
            return;
        }

        // Attach to UI elements
        voiceHandler.attachToButton('voice-btn');
        voiceHandler.attachToStatus('voice-status');

        // Add CSS for voice status
        addVoiceStatusStyles();

        console.log('✓ Voice handler initialized successfully');
    } catch (error) {
        console.error('Error initializing voice handler:', error);
    }
}

/**
 * Add CSS styles for voice status display
 */
function addVoiceStatusStyles() {
    if (document.getElementById('voice-status-styles')) {
        return; // Already added
    }

    const style = document.createElement('style');
    style.id = 'voice-status-styles';
    style.textContent = `
        .voice-status {
            position: fixed;
            bottom: 20px;
            left: 20px;
            padding: 12px 16px;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 600;
            z-index: 9999;
            max-width: 300px;
            display: none;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
            font-family: 'Titillium Web', sans-serif;
        }

        .voice-status.voice-status-success,
        .voice-status.voice-status-recording,
        .voice-status.voice-status-processing,
        .voice-status.voice-status-error,
        .voice-status.voice-status-info {
            display: block;
        }

        .voice-status-recording {
            background-color: #dc3545;
            color: white;
            animation: pulse-red 1s infinite;
        }

        .voice-status-processing {
            background-color: #ffc107;
            color: #000;
            animation: pulse-yellow 1s infinite;
        }

        .voice-status-success {
            background-color: #198754;
            color: white;
            animation: fadeOutAfter3s;
        }

        .voice-status-error {
            background-color: #dc3545;
            color: white;
        }

        .voice-status-info {
            background-color: #0d6efd;
            color: white;
        }

        #voice-btn.recording {
            background-color: #dc3545 !important;
            color: white !important;
        }

        #voice-btn.recording i {
            animation: mic-pulse 0.5s infinite alternate;
        }

        @keyframes pulse-red {
            0%, 100% {
                opacity: 1;
            }
            50% {
                opacity: 0.7;
            }
        }

        @keyframes pulse-yellow {
            0%, 100% {
                opacity: 1;
            }
            50% {
                opacity: 0.7;
            }
        }

        @keyframes mic-pulse {
            0% {
                transform: scale(1);
            }
            100% {
                transform: scale(1.1);
            }
        }

        @keyframes fadeOutAfter3s {
            0% {
                opacity: 1;
            }
            80% {
                opacity: 1;
            }
            100% {
                opacity: 0;
                display: none;
            }
        }
    `;
    document.head.appendChild(style);
}

/**
 * Add hidden status element to page
 */
function createVoiceStatusElement() {
    if (document.getElementById('voice-status')) {
        return; // Already exists
    }

    const statusDiv = document.createElement('div');
    statusDiv.id = 'voice-status';
    statusDiv.className = 'voice-status';
    document.body.appendChild(statusDiv);
}

// Initialize voice handler when document is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        createVoiceStatusElement();
        setTimeout(initializeVoiceHandler, 500);
    });
} else {
    // Document already loaded
    createVoiceStatusElement();
    setTimeout(initializeVoiceHandler, 500);
}
