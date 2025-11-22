# AI Interview Agent

An intelligent, voice-enabled interview practice application that generates personalized questions based on your resume, evaluates your answers in real-time, and provides a comprehensive performance report.

## Features

*   **Resume Analysis**: Upload your PDF resume to get questions tailored to your experience and skills.
*   **Adaptive Difficulty**: Questions automatically adjust based on your performance (Easy → Medium → Hard).
*   **Voice Interaction**:
    *   **Text-to-Speech (TTS)**: The agent reads questions aloud.
    *   **Speech-to-Text (STT)**: Answer using your voice with browser-native speech recognition or Google Cloud Speech-to-Text.
*   **Multi-Language Support**: Practice in English or Hindi/Hinglish.
*   **Real-time Evaluation**: Get instant feedback on your answers with:
    *   Numerical ratings (1-10)
    *   Strengths analysis
    *   Areas for improvement
    *   Missing key points
*   **Comprehensive PDF Report**: Download a detailed performance report with overall assessment and recommendations.

## Tech Stack

*   **Frontend**: HTML5, CSS3, Vanilla JavaScript
*   **Backend**: Python, Flask, Flask-Session (Server-side sessions)
*   **AI/LLM**: Google Gemini (via LangChain) or OpenRouter models
*   **Speech Services**: Web Speech API (Browser) / Google Cloud Speech-to-Text
*   **PDF Processing**: PyPDF2 (Extraction), fpdf2 (Report Generation)
<!-- *   **Transliteration**: transliterate library (for Hindi text in PDF reports) -->

## Prerequisites

*   Python 3.8+
*   Google Gemini API key (or OpenRouter API key for free models)
*   (Optional) Google Cloud credentials for Google Speech-to-Text

## Installation

1.  **Clone the repository**
    ```bash
    git clone <repository-url>
    cd "AI Interviewing Agent"
    ```

2.  **Create a virtual environment**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Mac/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Environment Configuration**
    Create a `.env` file in the root directory with your API keys:
    ```env
    FLASK_SECRET_KEY=your_secret_key_here
    GEMINI_API_KEY=your_gemini_api_key
    # Optional: For OpenRouter models
    OPENROUTER_API_KEY=your_openrouter_key
    # Optional: Enable user API key input in UI
    ENABLE_USER_API_KEYS=False
    # Optional: Session timeout in minutes
    SESSION_TIMEOUT_MINUTES=10
    ```

## Usage

1.  **Start the Backend Server**
    ```bash
    python app.py
    ```
    The server will start at `http://localhost:5000`.

2.  **Start the Frontend in New Terminal**    
    Serve the `frontend` folder using any static file server. For example:
    ```bash
    cd frontend
    python -m http.server 8000
    ```

4.  **Access the Application**
    Open your browser and navigate to `http://localhost:8000`.

5.  **Start Interviewing**
    *   **Upload Resume**: Select a text-based PDF resume (scanned PDFs not supported)
    *   **Configure Interview**:
        - Enter target job role
        - Select difficulty level (Easy/Medium/Hard)
        - Choose AI model (Gemini recommended)
        - Select language (English or Hindi/Hinglish)
        - Choose STT mode (Browser or Google)
    *   **Answer Questions**: 
        - Use microphone button to record voice answers
        - Or type answers directly
        - Submit and get instant feedback
    *   **Generate Report**: Finish interview and download PDF report

## Language Support

### English Mode
- Questions in English
- Browser STT uses `en-US`
- Evaluation feedback in English

### Hindi/Hinglish Mode
- Questions in natural Hinglish
- Browser STT uses `hi-IN` (transcribes to Devanagari script)
- Evaluation feedback in Hinglish
<!-- - **Note**: PDF reports use transliteration to convert Devanagari to Roman script for compatibility -->

## Adaptive Difficulty

The system automatically adjusts question difficulty based on your performance:
- **Rating > 7.0**: Difficulty increases (Easy → Medium → Hard)
- **Rating between 4.0 to 7.0**: Difficulty stays the same
- **Rating < 4.0**: Difficulty decreases (Hard → Medium → Easy)

## Project Structure

*   `app.py`: Main Flask application server with API endpoints
*   `langchain_agent.py`: LLM orchestration and interview logic
*   `prompts.py`: Centralized system prompts (English and Hinglish)
*   `report_generator.py`: PDF report generation
*   `frontend/`: Static assets
    - `index.html`: Main UI
    - `script.js`: Frontend logic and STT handling
    - `styles.css`: Styling


## API Endpoints

- `POST /api/upload`: Upload and analyze resume
- `POST /api/start-interview`: Initialize interview session
- `POST /api/next-question`: Generate next question
- `POST /api/transcribe`: Google STT proxy (optional)
- `POST /api/evaluate`: Evaluate answer and update difficulty
- `GET /api/report`: Generate and download PDF report
- `POST /api/end-session`: Clear session data

## Known Limitations

- **PDF Reports**: Answers for questions in Hinglish are transcribed into Devanagari script (Hindi) so they are not getting printed in report as user's answer.
- **Resume Format**: Only text-based PDFs supported; scanned/OCR PDFs will not work
- **Browser STT**: Accuracy varies by browser; Chrome recommended
- **Session Management**: Sessions expire after inactivity (default: 10 minutes)

## Troubleshooting

**Issue**: Resume upload fails
- **Solution**: Ensure PDF is text-based, not scanned. Try extracting text manually to verify.

**Issue**: Microphone not working
- **Solution**: Grant browser microphone permissions. Check browser console for errors.

**Issue**: Questions not in Hinglish
- **Solution**: Verify "Hindi/Hinglish" is selected in language dropdown.

**Issue**: PDF generation fails
- **Solution**: Check backend logs. Ensure all dependencies installed correctly.

## Known Issues & Solutions

For detailed technical analysis of resolved issues, please refer to [problems.md](problems.md).

**Resolved Issues:**
1.  **Speech-to-Text Race Condition**: Fixed "stale read" bugs where new transcriptions overwrote previous text.
2.  **Missing Last Question in Report**: Fixed by switching from client-side cookies to server-side filesystem sessions (`Flask-Session`) to handle large interview data.

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
