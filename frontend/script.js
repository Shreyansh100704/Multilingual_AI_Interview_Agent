// Configuration
const API_BASE_URL = 'http://localhost:5000/api';

// Global state
let config = {};
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let recognition = null;
// Track current question and recording context to avoid overwrites
let activeQuestionNumber = 0;
let recordingForQuestionNumber = 0;


// Initialization
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Script v3 loaded'); // Version check
    await fetchConfig();
    initializeEventListeners();
    initializeSpeechRecognition();
});

// Fetch Backend Configuration
async function fetchConfig() {
    try {
        const response = await fetch(`${API_BASE_URL}/config`);
        config = await response.json();

        // Show/hide API key section
        if (config.requireUserKeys) {
            document.getElementById('apiKeySection').style.display = 'block';
        }
    } catch (error) {
        console.error('Failed to fetch config:', error);
        showStatus('configStatus', 'Failed to connect to server. Please check if backend is running.', 'error');
    }
}

// Event Listeners
function initializeEventListeners() {
    // Resume upload
    document.getElementById('resumeUpload').addEventListener('change', handleFileSelect);
    document.getElementById('uploadBtn').addEventListener('click', uploadResume);

    // Interview configuration
    document.getElementById('startBtn').addEventListener('click', startInterview);

    // STT toggle
    document.getElementById('sttToggle').addEventListener('change', handleSTTToggle);
    document.getElementById('languageSelect').addEventListener('change', handleLanguageChange);

    // Interview controls
    document.getElementById('speakQuestionBtn').addEventListener('click', speakQuestion);
    document.getElementById('recordBtn').addEventListener('click', toggleRecording);
    document.getElementById('submitAnswerBtn').addEventListener('click', submitAnswer);
    document.getElementById('nextQuestionBtn').addEventListener('click', getNextQuestion);
    document.getElementById('finishBtn').addEventListener('click', generateReport);
    document.getElementById('endSessionBtn').addEventListener('click', endSession);
}

// Resume Upload
function handleFileSelect(event) {
    const file = event.target.files[0];
    const uploadBtn = document.getElementById('uploadBtn');

    if (file && file.type === 'application/pdf') {
        uploadBtn.disabled = false;
        document.querySelector('.upload-label span:nth-child(2)').textContent = `Selected: ${file.name}`;
    } else {
        uploadBtn.disabled = true;
        showStatus('uploadStatus', 'Please select a valid PDF file', 'error');
    }
}

async function uploadResume() {
    const fileInput = document.getElementById('resumeUpload');
    const file = fileInput.files[0];

    if (!file) {
        showStatus('uploadStatus', 'Please select a file', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('resume', file);

    // Add API keys if required
    if (config.requireUserKeys) {
        const openrouterKey = document.getElementById('openrouterKey').value;
        const geminiKey = document.getElementById('geminiKey').value;

        if (!openrouterKey || !geminiKey) {
            showStatus('uploadStatus', 'Please provide both API keys', 'error');
            return;
        }

        formData.append('openrouter_key', openrouterKey);
        formData.append('gemini_key', geminiKey);
    }

    showLoading('Extracting and analyzing your resume...');

    try {
        const response = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });

        const data = await response.json();

        hideLoading();

        if (response.ok) {
            showStatus('uploadStatus', 'Resume processed successfully!', 'success');

            // Show next section
            setTimeout(() => {
                document.getElementById('uploadSection').classList.remove('active');
                document.getElementById('configSection').classList.add('active');
            }, 1000);
        } else {
            showStatus('uploadStatus', data.error || 'Upload failed', 'error');
        }
    } catch (error) {
        hideLoading();
        showStatus('uploadStatus', 'Network error. Please try again.', 'error');
        console.error('Upload error:', error);
    }
}

// Interview Configuration
async function startInterview() {
    const role = document.getElementById('roleInput').value.trim();
    const difficulty = document.getElementById('difficultySelect').value;
    const modelId = document.getElementById('modelSelect').value;
    const language = document.getElementById('languageSelect').value;
    const sttMode = document.getElementById('sttToggle').checked ? 'google' : 'browser';
    const hinglishMode = (language === 'hi'); // Automatically enable Hinglish when Hindi is selected

    if (!role) {
        showStatus('configStatus', 'Please enter a job role', 'error');
        return;
    }

    showLoading('Initializing your interview...');

    try {
        const response = await fetch(`${API_BASE_URL}/start-interview`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ role, difficulty, model_id: modelId, language, stt_mode: sttMode, hinglish_mode: hinglishMode })
        });

        const data = await response.json();

        hideLoading();

        if (response.ok) {
            // Transition to interview section
            document.getElementById('configSection').classList.remove('active');
            document.getElementById('interviewSection').classList.add('active');

            // Update difficulty badge immediately
            if (data.config && data.config.difficulty) {
                updateDifficultyBadge(data.config.difficulty);
            }

            // Load first question
            await getNextQuestion();
        } else {
            showStatus('configStatus', data.error || 'Failed to start interview', 'error');
        }
    } catch (error) {
        hideLoading();
        showStatus('configStatus', 'Network error. Please try again.', 'error');
        console.error('Start interview error:', error);
    }
}

// STT Toggle Handling
function handleSTTToggle(event) {
    // No special handling needed
}

function handleLanguageChange(event) {
    // No special handling needed - language selection is straightforward
}

// Question Generation
async function getNextQuestion() {
    // Hide evaluation box
    document.getElementById('evaluationBox').style.display = 'none';

    // Clear answer textarea
    document.getElementById('answerText').value = '';

    showLoading('Generating next question...');

    try {
        const response = await fetch(`${API_BASE_URL}/next-question`, {
            method: 'POST',
            credentials: 'include'
        });

        const data = await response.json();

        hideLoading();

        if (response.ok) {
            document.getElementById('questionText').textContent = data.question;
            document.getElementById('questionNumber').textContent = data.question_number;

            // Track active question so STT results are tied to the right context
            activeQuestionNumber = data.question_number || (activeQuestionNumber + 1);
            // Reset recording context when question changes
            recordingForQuestionNumber = 0;

            // Auto-speak question
            speakQuestion();
        } else {
            alert(data.error || 'Failed to generate question');
        }
    } catch (error) {
        hideLoading();
        alert('Network error. Please try again.');
        console.error('Question generation error:', error);
    }
}

// Text-to-Speech
function speakQuestion() {
    const questionText = document.getElementById('questionText').textContent;

    if ('speechSynthesis' in window) {
        // Cancel any ongoing speech
        window.speechSynthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(questionText);
        utterance.lang = document.getElementById('languageSelect').value === 'hi' ? 'hi-IN' : 'en-US';
        utterance.rate = 0.9;
        utterance.pitch = 1;

        window.speechSynthesis.speak(utterance);
    } else {
        alert('Text-to-speech not supported in your browser');
    }
}

// Punctuation Helper
function addBasicPunctuation(text) {
    if (!text || text.trim().length === 0) return text;

    // Trim whitespace
    text = text.trim();

    // Capitalize first letter
    text = text.charAt(0).toUpperCase() + text.slice(1);

    // Add period at end if missing punctuation
    if (!text.match(/[.!?]$/)) {
        text += '.';
    }

    // Capitalize after sentence enders
    text = text.replace(/([.!?])\s+(\w)/g, (match, punctuation, letter) => {
        return punctuation + ' ' + letter.toUpperCase();
    });

    // Add commas after common conjunctions (basic heuristic)
    text = text.replace(/\b(however|therefore|moreover|furthermore|additionally)\s+/gi, (match) => {
        return match.trim() + ', ';
    });

    return text;
}

// Speech-to-Text
function initializeSpeechRecognition() {
    if ('webkitSpeechRecognition' in window) {
        recognition = new webkitSpeechRecognition();
        // Keep recognition continuous so pauses don't stop the stream
        recognition.continuous = true;
        // Allow interim results but only act on final results to avoid partial inserts
        recognition.interimResults = true;

        recognition.onresult = (event) => {
            // Only accept results that came from a recording started for the current question
            if (recordingForQuestionNumber !== activeQuestionNumber) {
                // Ignore stale transcription that belongs to a previous recording/question
                console.debug('Ignoring transcription for stale question context');
                return;
            }

            // Collect all final transcripts from this event
            // IMPORTANT: Start from event.resultIndex to avoid processing already processed results
            let finalTranscript = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const res = event.results[i];
                if (res.isFinal) {
                    finalTranscript += (res[0].transcript || '') + ' ';
                }
            }

            if (!finalTranscript.trim()) {
                // No final text to commit yet (maybe interim result)
                return;
            }

            const answerBox = document.getElementById('answerText');
            const punctuatedText = addBasicPunctuation(finalTranscript.trim());

            // Always append to existing content for the same question
            const currentText = answerBox.value;
            if (currentText.trim()) {
                answerBox.value = currentText.trim() + ' ' + punctuatedText;
            } else {
                answerBox.value = punctuatedText;
            }
            console.log('Appended text. New value:', answerBox.value);

            showStatus('recordingStatus', 'Transcription complete', 'success');
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            showStatus('recordingStatus', `Error: ${event.error}`, 'error');
        };
    }
}


async function toggleRecording() {
    const recordBtn = document.getElementById('recordBtn');
    const sttMode = document.getElementById('sttToggle').checked ? 'google' : 'browser';

    if (!isRecording) {
        // Start recording
        isRecording = true;
        recordBtn.classList.add('recording');
        recordBtn.querySelector('.record-text').textContent = 'Recording...';
        showStatus('recordingStatus', 'Recording... Speak now', 'info');
        // Record which question this recording is for so late transcriptions
        // don't get merged into a different question
        recordingForQuestionNumber = activeQuestionNumber;

        if (sttMode === 'browser') {
            // Use browser speech recognition
            const language = document.getElementById('languageSelect').value;
            // For Hindi/Hinglish, use hi-IN language code
            recognition.lang = language === 'hi' ? 'hi-IN' : 'en-US';
            recognition.start();
        } else {
            // Use Google STT (record audio and send to backend)
            await startGoogleSTTRecording();
        }
    } else {
        // Stop recording
        isRecording = false;
        recordBtn.classList.remove('recording');
        recordBtn.querySelector('.record-text').textContent = 'Start Recording';

        if (sttMode === 'browser') {
            recognition.stop();
        } else {
            await stopGoogleSTTRecording();
        }
    }
}

async function startGoogleSTTRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            await transcribeWithGoogle(audioBlob);

            // Stop all tracks
            stream.getTracks().forEach(track => track.stop());
        };

        mediaRecorder.start();
    } catch (error) {
        console.error('Microphone access error:', error);
        showStatus('recordingStatus', 'Microphone access denied', 'error');
        isRecording = false;
        document.getElementById('recordBtn').classList.remove('recording');
    }
}

async function stopGoogleSTTRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        showStatus('recordingStatus', 'Processing audio...', 'info');
        mediaRecorder.stop();
    }
}

async function transcribeWithGoogle(audioBlob) {
    const formData = new FormData();
    formData.append('audio', audioBlob);

    showLoading('Transcribing your answer...');

    try {
        const response = await fetch(`${API_BASE_URL}/transcribe`, {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });

        const data = await response.json();

        hideLoading();

        if (response.ok) {
            const answerBox = document.getElementById('answerText');

            // Only merge this transcription if it belongs to the same question
            if (recordingForQuestionNumber !== activeQuestionNumber) {
                console.debug('Received transcription for a different question context; ignoring.');
                hideLoading();
                return;
            }

            // Add basic punctuation
            const punctuatedText = addBasicPunctuation(data.transcript);

            // Always append to existing content
            const currentText = answerBox.value;
            if (currentText.trim()) {
                answerBox.value = currentText.trim() + ' ' + punctuatedText;
            } else {
                answerBox.value = punctuatedText;
            }
            console.log('Appended text (Google). New value:', answerBox.value);

            showStatus('recordingStatus', `Transcription complete (Confidence: ${(data.confidence * 100).toFixed(1)}%)`, 'success');
        } else {
            showStatus('recordingStatus', data.error || 'Transcription failed', 'error');
        }
    } catch (error) {
        hideLoading();
        showStatus('recordingStatus', 'Transcription error. Please try again.', 'error');
        console.error('Transcription error:', error);
    }
}


// Answer Submission
async function submitAnswer() {
    const answer = document.getElementById('answerText').value.trim();

    if (!answer) {
        showStatus('recordingStatus', 'Please provide an answer', 'error');
        return;
    }

    showLoading('Evaluating your answer...');

    try {
        const response = await fetch(`${API_BASE_URL}/evaluate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ answer })
        });

        const data = await response.json();

        hideLoading();

        if (response.ok) {
            displayEvaluation(data.evaluation);

            // Update difficulty badge and show notification if changed
            if (data.updated_difficulty !== data.previous_difficulty) {
                updateDifficultyBadge(data.updated_difficulty);
                const direction = data.updated_difficulty > data.previous_difficulty ? 'increased' : 'decreased';
                showStatus('recordingStatus', `Difficulty ${direction} to ${data.updated_difficulty}!`, 'info');
            } else {
                updateDifficultyBadge(data.updated_difficulty);
            }
        } else {
            alert(data.error || 'Evaluation failed');
        }
    } catch (error) {
        hideLoading();
        alert('Network error. Please try again.');
        console.error('Evaluation error:', error);
    }
}

function displayEvaluation(evaluation) {
    const evaluationBox = document.getElementById('evaluationBox');
    const ratingScore = document.getElementById('ratingScore');

    // Show evaluation box
    evaluationBox.style.display = 'block';

    // Set rating with color coding
    const rating = parseFloat(evaluation.rating);
    ratingScore.textContent = rating.toFixed(2);
    ratingScore.className = 'rating-score';

    if (rating >= 8.0) {
        ratingScore.classList.add('high');
    } else if (rating >= 5.0) {
        ratingScore.classList.add('medium');
    } else {
        ratingScore.classList.add('low');
    }

    // Set feedback with fallbacks
    document.getElementById('strengthsText').textContent = evaluation.strengths || 'No specific strengths identified';
    document.getElementById('improvementsText').textContent = evaluation.improvements || 'No specific improvements identified';

    // Handle missing_points
    const missingPoints = evaluation.missing_points || '';
    if (missingPoints && missingPoints !== 'N/A' && !missingPoints.includes('Unable to parse')) {
        document.getElementById('missingPointsSection').style.display = 'block';
        document.getElementById('missingPointsText').textContent = missingPoints;
    } else {
        document.getElementById('missingPointsSection').style.display = 'none';
    }

    // Scroll to evaluation
    evaluationBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}


function updateDifficultyBadge(difficulty) {
    const badge = document.getElementById('currentDifficulty');
    badge.textContent = difficulty;
    badge.className = 'difficulty-badge ' + difficulty.toLowerCase();
}

// Report Generation
async function generateReport() {
    if (!confirm('Are you sure you want to finish the interview and generate your report?')) {
        return;
    }

    showLoading('Generating your performance report...');

    try {
        const response = await fetch(`${API_BASE_URL}/report`, {
            method: 'GET',
            credentials: 'include'
        });

        hideLoading();

        if (response.ok) {
            // Download PDF
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'interview_report.pdf';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            alert('Report downloaded successfully!\n\nThank you for using AI Interview Agent. Good luck with your interviews!');

            // Reset to initial state
            location.reload();
        } else {
            const data = await response.json();
            alert(data.error || 'Failed to generate report');
        }
    } catch (error) {
        hideLoading();
        alert('Network error. Please try again.');
        console.error('Report generation error:', error);
    }
}

// Session Management
async function endSession() {
    if (!confirm('Are you sure you want to end the interview? All progress will be lost.')) {
        return;
    }

    try {
        await fetch(`${API_BASE_URL}/end-session`, {
            method: 'POST',
            credentials: 'include'
        });

        alert('Session ended. Thank you!');
        location.reload();
    } catch (error) {
        console.error('End session error:', error);
        location.reload();
    }
}

// Utility Functions
function showLoading(message) {
    document.getElementById('loadingOverlay').style.display = 'flex';
    document.getElementById('loadingText').textContent = message;
}

function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

function showStatus(elementId, message, type) {
    const statusElement = document.getElementById(elementId);
    statusElement.textContent = message;
    statusElement.className = `status-message ${type}`;

    // Auto-hide after 5 seconds for success/info messages
    if (type !== 'error') {
        setTimeout(() => {
            statusElement.style.display = 'none';
        }, 5000);
    }
}
