"""
Flask Backend for AI Interview Agent
Handles resume upload, interview orchestration, STT proxy, and report generation.
"""

import os
import json
from datetime import timedelta
from io import BytesIO

from flask import Flask, request, session, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from werkzeug.utils import secure_filename

from langchain_agent import InterviewAgent
from report_generator import generate_pdf_report

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(
    minutes=int(os.getenv('SESSION_TIMEOUT_MINUTES', 10))
)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Enable CORS for decoupled frontend
CORS(app, supports_credentials=True)

# Feature flag for API key management
USE_USER_API_KEYS = os.getenv('ENABLE_USER_API_KEYS', 'False') == 'True'

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf'}


def allowed_file(filename):
    """Check if uploaded file is a PDF"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_pdf(pdf_file):
    """
    Extract raw text from PDF file using PyPDF2.
    
    Args:
        pdf_file: FileStorage object from Flask request
        
    Returns:
        str: Extracted text or None if extraction failed
    """
    try:
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text.strip()
    except Exception as e:
        print(f"PDF extraction error: {e}")
        return None


@app.route('/api/config', methods=['GET'])
def get_config():
    """
    Return frontend configuration (API key requirement, models, etc.)
    """
    config = {
        "requireUserKeys": USE_USER_API_KEYS,
        "sessionTimeout": int(os.getenv('SESSION_TIMEOUT_MINUTES', 10)),
        "availableModels": {
            "gemini": [
                {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash (Recommended)", "provider": "gemini"},
                {"id": "gemini-2.5-flash-lite", "name": "Gemini 2.5 Flash-Lite (Faster)", "provider": "gemini"},
                {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro (Best Quality)", "provider": "gemini"},
                {"id": "gemini-flash-latest", "name": "Gemini Flash Latest (Auto-update)", "provider": "gemini"}
            ],
            "openrouter": [
                {"id": "microsoft/phi-3-mini-128k-instruct:free", "name": "Phi-3 Mini (Free)", "provider": "openrouter"},
                {"id": "meta-llama/llama-3.2-3b-instruct:free", "name": "Llama 3.2 3B (Free)", "provider": "openrouter"}
            ]
        }
    }
    return jsonify(config)




@app.route('/api/upload', methods=['POST'])
def upload_resume():
    """
    Handle resume upload, text extraction, and LLM summarization.
    
    Expected: multipart/form-data with 'resume' file and optional API keys
    """
    # Check if file is present
    if 'resume' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['resume']
    
    # Check if file is selected
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    # Validate file type
    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF files are accepted. Scanned/OCR PDFs are not supported."}), 400
    
    # Extract text from PDF
    raw_text = extract_text_from_pdf(file)
    
    if not raw_text:
        return jsonify({"error": "Failed to extract text from PDF"}), 500
    
    # Validate text extraction (minimum 100 characters)
    if len(raw_text) < 100:
        return jsonify({
            "error": "Insufficient text extracted. This may be a scanned/image-based PDF. Please upload a text-based PDF."
        }), 400
    
    # Get API keys (if user-provided mode is enabled)
    api_keys = {}
    if USE_USER_API_KEYS:
        api_keys['openrouter'] = request.form.get('openrouter_key', '')
        api_keys['gemini'] = request.form.get('gemini_key', '')
    else:
        api_keys['openrouter'] = os.getenv('OPENROUTER_API_KEY')
        api_keys['gemini'] = os.getenv('GEMINI_API_KEY')
    
    # Initialize agent for summarization (use default model)
    try:
        agent = InterviewAgent(
            model_id="gemini-2.5-flash",
            api_keys=api_keys,
            language="en"
        )
        
        # Generate resume summary
        summary = agent.summarize_resume(raw_text)
        
        # Store in session
        session['resume_summary'] = summary
        session['api_keys'] = api_keys
        
        return jsonify({
            "message": "Resume uploaded successfully",
            "summary": summary
        }), 200
        
    except Exception as e:
        print(f"Summarization error: {e}")
        return jsonify({"error": f"Failed to process resume: {str(e)}"}), 500


@app.route('/api/start-interview', methods=['POST'])
def start_interview():
    """
    Initialize interview session with role, difficulty, model, and language preferences.
    """
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['role', 'difficulty', 'model_id', 'language']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    # Validate resume summary exists
    if 'resume_summary' not in session:
        return jsonify({"error": "Please upload a resume first"}), 400
    
    # Store interview configuration in session
    session['role'] = data['role']
    session['difficulty'] = data['difficulty']
    session['model_id'] = data['model_id']
    session['language'] = data['language']
    session['stt_mode'] = data.get('stt_mode', 'browser')
    session['hinglish_mode'] = data.get('hinglish_mode', False)
    
    # If hinglish mode is enabled, override language to 'hi' for prompts
    if session['hinglish_mode']:
        session['language'] = 'hi'
    
    # Initialize interview history
    session['interview_history'] = []
    session['question_count'] = 0
    
    # Mark session as permanent (for timeout handling)
    session.permanent = True
    
    return jsonify({
        "message": "Interview initialized successfully",
        "config": {
            "role": session['role'],
            "difficulty": session['difficulty'],
            "model": session['model_id'],
            "language": session['language']
        }
    }), 200



@app.route('/api/next-question', methods=['POST'])
def get_next_question():
    """
    Generate the next interview question using LLM.
    """
    # Validate session
    required_session_keys = ['resume_summary', 'role', 'difficulty', 'model_id', 'language', 'api_keys']
    for key in required_session_keys:
        if key not in session:
            return jsonify({"error": f"Session expired or incomplete. Missing: {key}"}), 400
    
    try:
        # Initialize agent with current configuration
        agent = InterviewAgent(
            model_id=session['model_id'],
            api_keys=session['api_keys'],
            language=session['language']
        )
        
        # Generate question
        question = agent.generate_question(
            resume_summary=session['resume_summary'],
            role=session['role'],
            difficulty=session['difficulty'],
            history=session.get('interview_history', [])
        )
        
        # Store current question in session (for evaluation context)
        session['current_question'] = question
        session['question_count'] = session.get('question_count', 0) + 1
        
        return jsonify({
            "question": question,
            "question_number": session['question_count'],
            "language": "hinglish" if session.get('hinglish_mode') else session['language']
        }), 200
        
    except Exception as e:
        print(f"Question generation error: {e}")
        return jsonify({"error": f"Failed to generate question: {str(e)}"}), 500


@app.route('/api/transcribe', methods=['POST'])
def transcribe_audio():
    """
    Proxy for Google Cloud Speech-to-Text API.
    Only used when user selects Google STT mode.
    """
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    
    audio_file = request.files['audio']
    
    try:
        from google.cloud import speech
        
        # Initialize Google Speech client
        client = speech.SpeechClient()
        
        # Read audio content
        content = audio_file.read()
        
        # Configure recognition
        audio = speech.RecognitionAudio(content=content)
        
        # Determine language code based on session language
        language_code = "hi-IN" if session.get('language') == 'hi' else "en-US"
        
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            sample_rate_hertz=48000,
            language_code=language_code,
            enable_automatic_punctuation=True,
            model="latest_long"
        )
        
        # Perform transcription
        response = client.recognize(config=config, audio=audio)
        
        # Extract transcript
        if response.results:
            transcript = response.results[0].alternatives[0].transcript
            confidence = response.results[0].alternatives[0].confidence
            
            return jsonify({
                "transcript": transcript,
                "confidence": confidence
            }), 200
        else:
            return jsonify({"error": "No speech detected"}), 400
            
    except Exception as e:
        print(f"Transcription error: {e}")
        return jsonify({"error": f"Transcription failed: {str(e)}"}), 500


@app.route('/api/evaluate', methods=['POST'])
def evaluate_answer():
    """
    Evaluate user's answer and update adaptive difficulty.
    """
    data = request.get_json()
    
    if 'answer' not in data:
        return jsonify({"error": "No answer provided"}), 400
    
    # Validate session
    if 'current_question' not in session:
        return jsonify({"error": "No active question to evaluate"}), 400
    
    try:
        # Initialize agent
        agent = InterviewAgent(
            model_id=session['model_id'],
            api_keys=session['api_keys'],
            language=session['language']
        )
        
        # Evaluate answer
        evaluation = agent.evaluate_answer(
            question=session['current_question'],
            answer=data['answer']
        )
        
        # Store in history
        history_entry = {
            "question": session['current_question'],
            "answer": data['answer'],
            "rating": evaluation['rating'],
            "strengths": evaluation['strengths'],
            "improvements": evaluation['improvements'],
            "missing_points": evaluation.get('missing_points', '')
        }
        
        if 'interview_history' not in session:
            session['interview_history'] = []
        
        session['interview_history'].append(history_entry)
        session.modified = True
        
        # Store last rating for reference
        session['last_rating'] = evaluation['rating']
        
        # Adaptive Difficulty Logic
        current_difficulty = session['difficulty']
        rating = evaluation['rating']
        new_difficulty = current_difficulty
        
        # Define difficulty progression
        difficulty_order = ['Easy', 'Medium', 'Hard']
        current_index = difficulty_order.index(current_difficulty)
        
        # Update difficulty based on rating
        if rating > 7.0:
            # Increase difficulty (if not already at max)
            if current_index < len(difficulty_order) - 1:
                new_difficulty = difficulty_order[current_index + 1]
        elif rating < 4.0:
            # Decrease difficulty (if not already at min)
            if current_index > 0:
                new_difficulty = difficulty_order[current_index - 1]
        # else: rating between 4-7, stay at current difficulty
        
        # Update session difficulty
        session['difficulty'] = new_difficulty
        session.modified = True
        
        return jsonify({
            "evaluation": evaluation,
            "updated_difficulty": new_difficulty,
            "previous_difficulty": current_difficulty,
            "total_questions": len(session['interview_history']),
            "language": "hinglish" if session.get('hinglish_mode') else session['language']
        }), 200
        
    except Exception as e:
        print(f"Evaluation error: {e}")
        return jsonify({"error": f"Evaluation failed: {str(e)}"}), 500






@app.route('/api/report', methods=['GET'])
def generate_report():
    """
    Generate PDF report and clear session.
    """
    # Validate session data
    if 'interview_history' not in session or not session['interview_history']:
        return jsonify({"error": "No interview data available"}), 400
    
    try:
        # Initialize agent for overall summary
        agent = InterviewAgent(
            model_id=session['model_id'],
            api_keys=session['api_keys'],
            language=session['language']
        )
        
        # Generate overall summary
        overall_summary = agent.generate_overall_summary(
            role=session['role'],
            history=session['interview_history']
        )
        
        # Prepare report data
        report_data = {
            "role": session['role'],
            "difficulty": session['difficulty'],
            "model": session['model_id'],
            "language": session['language'],
            "num_questions": len(session['interview_history']),
            "history": session['interview_history'],
            "overall_summary": overall_summary,
            "avg_rating": sum(q['rating'] for q in session['interview_history']) / len(session['interview_history'])
        }
        
        # Generate PDF
        pdf_buffer = generate_pdf_report(report_data)
        
        # Clear session
        session.clear()
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=f"interview_report_{report_data['role'].replace(' ', '_')}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"Report generation error: {e}")
        return jsonify({"error": f"Failed to generate report: {str(e)}"}), 500


@app.route('/api/end-session', methods=['POST'])
def end_session():
    """
    Manually terminate interview session and clear memory.
    """
    session.clear()
    return jsonify({"message": "Session ended successfully"}), 200


@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for deployment monitoring.
    """
    return jsonify({
        "status": "healthy",
        "session_active": bool(session.get('resume_summary')),
        "user_keys_required": USE_USER_API_KEYS
    }), 200


# Session timeout handler
@app.before_request
def before_request():
    """
    Refresh session expiry on each request (rolling timeout).
    """
    session.modified = True


if __name__ == '__main__':
    app.run(
        debug=os.getenv('FLASK_DEBUG', 'True') == 'True',
        host='0.0.0.0',
        port=5000
    )
