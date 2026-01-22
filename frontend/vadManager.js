class VadManager {
    constructor() {
        this.vad = null;
        this.isListening = false;
        this.submitTimer = null;
        this.countdownInterval = null;
        this.isUserSpeaking = false;
        this.countdownSeconds = 4;

        // DOM Elements
        this.statusElement = document.getElementById('vadStatus');
        this.forceSubmitBtn = document.getElementById('forceSubmitBtn');
        this.timerDisplay = document.getElementById('vadTimer');
    }

    async initialize() {
        try {
            console.log("VAD Manager: Initializing...");
            this.vad = await vad.MicVAD.new({
                positiveSpeechThreshold: 0.8,
                minSpeechFrames: 5,
                preSpeechPadFrames: 5,
                onSpeechStart: () => {
                    console.log("VAD Manager: Speech Start Detected");
                    this.handleSpeechStart();
                },
                onSpeechEnd: (audio) => {
                    console.log("VAD Manager: Speech End Detected");
                    this.handleSpeechEnd(audio);
                },
                onVADMisfire: () => {
                    console.log("VAD Manager: Misfire (Noise)");
                }
            });
            console.log("VAD Manager: Initialized successfully");
            return true;
        } catch (e) {
            console.error("VAD Manager: Failed to initialize:", e);
            return false;
        }
    }

    start() {
        if (this.vad) {
            this.vad.start();
            this.isListening = true;
            this.updateStatus("Listening for speech...", "listening");
        }
    }

    stop() {
        if (this.vad) {
            this.vad.pause();
            this.isListening = false;
            this.clearTimers();
            this.updateStatus("VAD Paused", "paused");
            this.hideForceSubmit();
        }
    }

    handleSpeechStart() {
        console.log("Speech started");
        this.isUserSpeaking = true;
        this.clearTimers();
        this.updateStatus("User speaking...", "speaking");
        this.hideForceSubmit();

        // If using browser STT, ensure it's running
        // If using Google STT, ensure recording is active
        // This coordination should be handled by the main script, 
        // but we can trigger events or callbacks if needed.
    }

    handleSpeechEnd(audio) {
        console.log("Speech ended");
        this.isUserSpeaking = false;
        this.startCountdown();
    }

    startCountdown() {
        this.clearTimers();
        let remaining = this.countdownSeconds;

        this.showForceSubmit();
        this.updateStatus(`Processing in ${remaining}s...`, "waiting");

        this.countdownInterval = setInterval(() => {
            remaining--;
            if (remaining > 0) {
                this.updateStatus(`Processing in ${remaining}s...`, "waiting");
            } else {
                clearInterval(this.countdownInterval);
                this.submitFinalAnswer();
            }
        }, 1000);

        // Safety timeout
        this.submitTimer = setTimeout(() => {
            // This matches the interval completion
        }, this.countdownSeconds * 1000);
    }

    clearTimers() {
        if (this.submitTimer) clearTimeout(this.submitTimer);
        if (this.countdownInterval) clearInterval(this.countdownInterval);
        this.submitTimer = null;
        this.countdownInterval = null;
    }

    forceSubmit() {
        console.log("Force submit triggered");
        this.clearTimers();
        this.submitFinalAnswer();
    }

    submitFinalAnswer() {
        this.hideForceSubmit();
        this.updateStatus("Submitting answer...", "submitting");

        // Call the global handler in script.js which manages STT state
        if (typeof window.handleVadSubmit === 'function') {
            window.handleVadSubmit();
        } else if (typeof submitAnswer === 'function') {
            // Fallback
            submitAnswer();
        } else {
            console.error("submitAnswer function not found");
        }
    }

    updateStatus(text, className) {
        if (this.statusElement) {
            // Clear previous classes but keep base class
            this.statusElement.className = 'vad-status';
            this.statusElement.classList.add(className);

            // Update text
            // We need to preserve the ::before element which is CSS generated
            // so just changing textContent is fine
            this.statusElement.textContent = text;
        }
    }

    showForceSubmit() {
        if (this.forceSubmitBtn) {
            this.forceSubmitBtn.style.display = 'inline-block';
        }
    }

    hideForceSubmit() {
        if (this.forceSubmitBtn) {
            this.forceSubmitBtn.style.display = 'none';
        }
    }
}

// Export instance
window.vadManager = new VadManager();
