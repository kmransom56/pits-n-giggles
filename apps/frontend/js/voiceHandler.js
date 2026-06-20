/**
 * Voice Communication Handler for Pits n' Giggles
 * Handles microphone capture, audio streaming, and voice feedback
 */

class VoiceHandler {
    constructor(socketIO, config = {}) {
        this.socket = socketIO;
        this.config = config;
        this.isRecording = false;
        this.mediaRecorder = null;
        this.audioContext = null;
        this.processor = null;
        this.stream = null;
        this.audioChunks = [];
        this.micButton = null;
        this.statusText = null;

        // Web Audio configuration
        this.sampleRate = 16000;
        this.chunkDurationMs = 100;
        this.chunkSize = (this.sampleRate * this.chunkDurationMs) / 1000; // 1600 samples at 16kHz for 100ms

        // Socket.IO event listeners for voice feedback
        this.setupSocketListeners();
    }

    setupSocketListeners() {
        /**
         * Listen for transcript results from the backend
         */
        this.socket.on('voice-transcript', (data) => {
            const transcript = data.text;
            console.log('Transcript:', transcript);
            this.displayTranscript(transcript);
            this.setStatus('Received transcript...', 'processing');
        });

        /**
         * Listen for audio response from backend (LLM + TTS)
         */
        this.socket.on('voice-audio-response', (data) => {
            const audioB64 = data.audio;
            const responseText = data.text;
            console.log('Audio Response:', responseText);
            this.setStatus('Playing response...', 'success');
            this.playAudioResponse(audioB64);
        });

        /**
         * Listen for voice errors
         */
        this.socket.on('voice-error', (data) => {
            console.error('Voice error:', data.error);
            this.setStatus(`Error: ${data.error}`, 'error');
        });
    }

    /**
     * Initialize voice input with microphone access
     */
    async initialize() {
        try {
            // Request microphone permission
            this.stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: this.sampleRate,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                }
            });

            // Create Web Audio API components
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: this.sampleRate
            });

            const source = this.audioContext.createMediaStreamSource(this.stream);

            // Create ScriptProcessor for real-time audio processing
            // Buffer size must be power-of-2: 256, 512, 1024, 2048, 4096, 8192, 16384
            this.processor = this.audioContext.createScriptProcessor(
                4096,  // Valid buffer size (power of 2)
                1,     // input channels
                1      // output channels
            );

            // Connect nodes
            source.connect(this.processor);
            this.processor.connect(this.audioContext.destination);

            // Process audio in chunks
            this.processor.onaudioprocess = (event) => {
                if (this.isRecording) {
                    const audioData = event.inputBuffer.getChannelData(0);
                    this.sendAudioChunk(audioData);
                }
            };

            this.setStatus('Microphone ready', 'success');
            return true;
        } catch (error) {
            console.error('Microphone initialization error:', error);
            this.setStatus(`Microphone error: ${error.message}`, 'error');
            return false;
        }
    }

    /**
     * Start recording voice input
     */
    startRecording() {
        if (!this.audioContext || !this.processor) {
            this.setStatus('Microphone not initialized', 'error');
            return false;
        }

        this.isRecording = true;
        this.audioChunks = [];
        this.socket.emit('voice-start');
        this.setStatus('Recording...', 'recording');
        return true;
    }

    /**
     * Stop recording and send final chunk
     */
    stopRecording() {
        if (!this.isRecording) return false;

        this.isRecording = false;

        // Send final chunk if we have buffered audio
        if (this.audioChunks.length > 0) {
            this.sendFinalChunk();
        }

        this.socket.emit('voice-stop');
        this.setStatus('Processing...', 'processing');
        return true;
    }

    /**
     * Convert Float32Array audio to PCM bytes and send to backend
     * @param {Float32Array} audioData - Raw audio data from Web Audio API
     */
    sendAudioChunk(audioData) {
        try {
            // Convert float32 to int16 PCM
            const pcmData = this.float32ToPCM16(audioData);

            // Accumulate chunks
            this.audioChunks.push(pcmData);

            // Send accumulated chunks if we have enough data (e.g., every 5 chunks)
            if (this.audioChunks.length >= 5) {
                this.flushAudioChunks(false);
            }
        } catch (error) {
            console.error('Error processing audio chunk:', error);
        }
    }

    /**
     * Send accumulated audio chunks to backend
     * @param {boolean} isFinal - Whether this is the final chunk
     */
    flushAudioChunks(isFinal = false) {
        if (this.audioChunks.length === 0) return;

        try {
            // Concatenate all accumulated chunks
            const totalLength = this.audioChunks.reduce((sum, chunk) => sum + chunk.length, 0);
            const audioBuffer = new Uint8Array(totalLength);
            let offset = 0;

            for (const chunk of this.audioChunks) {
                audioBuffer.set(chunk, offset);
                offset += chunk.length;
            }

            // Send to backend via Socket.IO
            this.socket.emit('voice-audio-chunk', {
                audio: audioBuffer.buffer, // Send as ArrayBuffer for binary support
                is_final: isFinal
            });

            this.audioChunks = [];
        } catch (error) {
            console.error('Error flushing audio chunks:', error);
        }
    }

    /**
     * Send final audio chunk
     */
    sendFinalChunk() {
        this.flushAudioChunks(true);
    }

    /**
     * Convert Float32Array to Int16 PCM bytes
     * @param {Float32Array} float32Array - Audio data in float32 format
     * @returns {Uint8Array} PCM int16 data
     */
    float32ToPCM16(float32Array) {
        const length = float32Array.length;
        const int16Array = new Int16Array(length);

        for (let i = 0; i < length; i++) {
            // Clamp to [-1, 1]
            let sample = Math.max(-1, Math.min(1, float32Array[i]));

            // Convert to int16
            sample = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
            int16Array[i] = Math.round(sample);
        }

        // Convert to byte array
        return new Uint8Array(int16Array.buffer);
    }

    /**
     * Display transcript in UI
     * @param {string} text - Transcribed text
     */
    displayTranscript(text) {
        if (this.statusText) {
            this.statusText.textContent = `Transcript: ${text}`;
        }
        console.log('Displayed transcript:', text);
    }

    /**
     * Play audio response from backend
     * @param {string} audioBase64 - Base64-encoded audio data
     */
    playAudioResponse(audioBase64) {
        try {
            // Decode base64 to bytes
            const binaryString = atob(audioBase64);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }

            // Create blob and play
            const audioBlob = new Blob([bytes], { type: 'audio/wav' });
            const audioUrl = URL.createObjectURL(audioBlob);
            const audioElement = new Audio(audioUrl);
            audioElement.play();

            audioElement.onended = () => {
                URL.revokeObjectURL(audioUrl);
                this.setStatus('Ready', 'success');
                this.micButton.classList.remove('recording');
                this.micButton.textContent = '🎤 Voice';
            };
        } catch (error) {
            console.error('Error playing audio response:', error);
            this.setStatus('Error playing audio', 'error');
        }
    }

    /**
     * Speak the transcript using Web Speech API
     * @param {string} text - Text to speak
     */
    speakTranscript(text) {
        // Use existing textToSpeech if available
        if (typeof window.textToSpeech === 'function') {
            window.textToSpeech(text);
        } else {
            // Fallback to Web Speech API directly
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 1.2;
            speechSynthesis.speak(utterance);
        }
    }

    /**
     * Set status message in UI
     * @param {string} message - Status message
     * @param {string} status - Status type: 'recording', 'processing', 'success', 'error'
     */
    setStatus(message, status = 'info') {
        console.log(`[${status}] ${message}`);
        if (this.statusText) {
            this.statusText.textContent = message;
            this.statusText.className = `voice-status voice-status-${status}`;
        }
    }

    /**
     * Attach to UI button for record/stop toggle
     * @param {string} buttonId - HTML element ID of the record button
     */
    attachToButton(buttonId) {
        this.micButton = document.getElementById(buttonId);
        if (!this.micButton) {
            console.error(`Button ${buttonId} not found`);
            return;
        }

        this.micButton.addEventListener('click', async () => {
            if (!this.isRecording) {
                // Start recording
                if (this.audioContext && this.audioContext.state === 'suspended') {
                    await this.audioContext.resume();
                }
                this.startRecording();
                this.micButton.classList.add('recording');
                this.micButton.textContent = 'Stop Recording';
            } else {
                // Stop recording
                this.stopRecording();
                this.micButton.classList.remove('recording');
                this.micButton.textContent = 'Start Recording';
            }
        });
    }

    /**
     * Attach to status text element
     * @param {string} elementId - HTML element ID for status display
     */
    attachToStatus(elementId) {
        this.statusText = document.getElementById(elementId);
    }

    /**
     * Clean up resources
     */
    async destroy() {
        this.stopRecording();

        if (this.processor) {
            this.processor.disconnect();
            this.processor.onaudioprocess = null;
        }

        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
        }

        if (this.audioContext) {
            await this.audioContext.close();
        }
    }
}

// Export for use in HTML
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceHandler;
}
