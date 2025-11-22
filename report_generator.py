"""
PDF Report Generator using tFPDF (Unicode-enabled FPDF)
Creates professional interview performance reports with Unicode support.
"""

from io import BytesIO
from datetime import datetime
from fpdf import FPDF
from fpdf.fonts import FontFace


class InterviewReportPDF(FPDF):
    """
    Custom PDF class for interview reports with header and footer.
    Uses Arial (built-in Unicode font).
    """
    
    def header(self):
        """Add header to each page"""
        self.set_font('Times', 'B', 16)
        self.set_text_color(41, 128, 185)  # Blue color
        self.cell(0, 10, 'AI Interview Performance Report', 0, 1, 'C')
        self.ln(5)
    
    def footer(self):
        """Add footer to each page"""
        self.set_y(-15)
        self.set_font('Times', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')


def generate_pdf_report(report_data):
    """
    Generate comprehensive interview report as PDF.
    
    Args:
        report_data: Dictionary containing:
            - role: Job role
            - difficulty: Difficulty level
            - model: LLM model used
            - language: Interview language
            - num_questions: Number of questions asked
            - history: List of Q&A with evaluations
            - overall_summary: Overall performance summary
            - avg_rating: Average rating
            
    Returns:
        BytesIO: PDF file buffer
    """
    # Initialize PDF with Unicode support
    pdf = InterviewReportPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Interview Metadata Section
    pdf.set_font('Times', 'B', 14)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, 'Interview Details', 0, 1, 'L')
    pdf.ln(2)
    
    pdf.set_font('Times', '', 11)
    pdf.cell(0, 8, f"Date: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", 0, 1)
    pdf.cell(0, 8, f"Role: {clean_text(report_data['role'])}", 0, 1)
    pdf.cell(0, 8, f"Difficulty Level: {clean_text(report_data['difficulty'])}", 0, 1)
    pdf.cell(0, 8, f"Model Used: {clean_text(report_data['model'])}", 0, 1)
    pdf.cell(0, 8, f"Language: {report_data['language']}", 0, 1)
    pdf.cell(0, 8, f"Total Questions: {report_data['num_questions']}", 0, 1)
    pdf.cell(0, 8, f"Average Rating: {report_data['avg_rating']:.2f}/10.00", 0, 1)
    pdf.ln(5)
    
    # Overall Performance Summary Section
    pdf.set_font('Times', 'B', 14)
    pdf.set_fill_color(230, 240, 255)
    pdf.cell(0, 10, 'Overall Performance Summary', 0, 1, 'L', True)
    pdf.ln(2)
    
    pdf.set_font('Times', '', 10)
    summary_text = clean_text(report_data['overall_summary'])
    pdf.multi_cell(0, 6, summary_text)
    pdf.ln(5)
    
    # Performance Rating Analysis
    avg_rating = report_data['avg_rating']
    pdf.set_font('Times', 'B', 12)
    pdf.cell(0, 8, 'Performance Assessment:', 0, 1)
    
    pdf.set_font('Times', '', 10)
    if avg_rating >= 8.0:
        assessment = "Excellent - Strong command of subject matter with clear articulation"
        color = (39, 174, 96)  # Green
    elif avg_rating >= 6.0:
        assessment = "Good - Solid understanding with minor areas for improvement"
        color = (241, 196, 15)  # Yellow
    elif avg_rating >= 4.0:
        assessment = "Fair - Basic knowledge demonstrated, needs focused development"
        color = (230, 126, 34)  # Orange
    else:
        assessment = "Needs Improvement - Significant knowledge gaps identified"
        color = (231, 76, 60)  # Red
    
    pdf.set_text_color(*color)
    pdf.multi_cell(0, 6, assessment)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)
    
    # Detailed Q&A Section
    pdf.set_font('Times', 'B', 14)
    pdf.cell(0, 10, 'Detailed Question-by-Question Analysis', 0, 1, 'L')
    pdf.ln(2)
    
    for i, entry in enumerate(report_data['history'], 1):
        # Check for page break
        if pdf.get_y() > 250:
            pdf.add_page()
        
        # Question
        pdf.set_font('Times', 'B', 11)
        pdf.set_text_color(52, 73, 94)
        question_text = clean_text(entry['question'])
        pdf.multi_cell(0, 6, f"Question {i}: {question_text}")
        pdf.ln(2)
        
        # Answer
        pdf.set_font('Times', '', 10)
        pdf.set_text_color(0, 0, 0)
        answer_text = clean_text(entry['answer'])
        pdf.multi_cell(0, 6, f"Your Answer: {answer_text}")
        pdf.ln(2)
        
        # Rating
        pdf.set_font('Times', 'B', 10)
        rating_color = _get_rating_color(entry['rating'])
        pdf.set_text_color(*rating_color)
        pdf.cell(0, 6, f"Rating: {entry['rating']:.2f}/10.00", 0, 1)
        pdf.ln(1)
        
        # Feedback sections
        pdf.set_text_color(0, 0, 0)
        
        # Strengths
        pdf.set_font('Times', 'B', 10)
        pdf.cell(0, 6, "Strengths:", 0, 1)
        pdf.set_font('Times', '', 9)
        strengths_text = clean_text(entry['strengths'])
        pdf.multi_cell(0, 5, f"  + {strengths_text}")
        pdf.ln(1)
        
        # Improvements
        pdf.set_font('Times', 'B', 10)
        pdf.cell(0, 6, "Areas for Improvement:", 0, 1)
        pdf.set_font('Times', '', 9)
        improvements_text = clean_text(entry['improvements'])
        pdf.multi_cell(0, 5, f"  - {improvements_text}")
        pdf.ln(1)
        
        # Missing Points
        if entry.get('missing_points') and entry['missing_points'] not in ['N/A', 'Unable to parse detailed feedback']:
            pdf.set_font('Times', 'B', 10)
            pdf.cell(0, 6, "Missing Key Points:", 0, 1)
            pdf.set_font('Times', '', 9)
            missing_text = clean_text(entry['missing_points'])
            pdf.multi_cell(0, 5, f"  ! {missing_text}")
            pdf.ln(1)
        
        # Separator line
        pdf.set_draw_color(200, 200, 200)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
    
    # Recommendations Section
    pdf.add_page()
    pdf.set_font('Times', 'B', 14)
    pdf.set_fill_color(255, 240, 230)
    pdf.cell(0, 10, 'Next Steps & Recommendations', 0, 1, 'L', True)
    pdf.ln(2)
    
    pdf.set_font('Times', '', 10)
    recommendations = _generate_recommendations(report_data['avg_rating'])
    recommendations_text = clean_text(recommendations)
    pdf.multi_cell(0, 6, recommendations_text)
    pdf.ln(5)
    
    # Footer note
    pdf.set_font('Times', 'I', 9)
    pdf.set_text_color(128, 128, 128)
    pdf.multi_cell(0, 5, "This report is generated by AI Interview Agent for self-assessment and improvement purposes. Use the feedback to guide your interview preparation and skill development.")
    
    # Generate PDF buffer
    pdf_buffer = BytesIO()
    pdf_output = pdf.output()
    pdf_buffer.write(pdf_output)
    pdf_buffer.seek(0)
    
    return pdf_buffer


def clean_text(text):
    """
    Clean text for PDF rendering and transliterate Devanagari to Roman script.
    
    Args:
        text: Input text string
        
    Returns:
        str: Cleaned text safe for PDF with Devanagari transliterated to Roman
    """
    if not text:
        return ''
    
    # Convert to string
    text = str(text)
    
    # Transliterate Devanagari to Roman script for PDF compatibility
    # Check if text contains Devanagari characters (U+0900 to U+097F)
    has_devanagari = any('\u0900' <= char <= '\u097F' for char in text)
    
    if has_devanagari:
        try:
            from transliterate import translit
            # Transliterate Hindi/Devanagari to Roman (Latin) script
            # reversed=True means from Devanagari to Latin
            text = translit(text, 'hi', reversed=True)
        except ImportError:
            # If transliterate library not available, remove Devanagari characters
            print("Warning: transliterate library not installed. Removing Devanagari characters.")
            text = ''.join(char if not ('\u0900' <= char <= '\u097F') else '' for char in text)
        except Exception as e:
            # If transliteration fails for any reason, remove Devanagari characters
            print(f"Warning: Transliteration failed ({e}). Removing Devanagari characters.")
            text = ''.join(char if not ('\u0900' <= char <= '\u097F') else '' for char in text)
    
    # Replace only problematic special characters that might cause PDF rendering issues
    replacements = {
        '\u2022': '*',      # Bullet point
        '\u2013': '-',      # En dash
        '\u2014': '--',     # Em dash
        '\u2019': "'",      # Right single quote
        '\u2018': "'",      # Left single quote
        '\u201c': '"',      # Left double quote
        '\u201d': '"',      # Right double quote
        '\u2026': '...',    # Ellipsis
        '\u2122': '(TM)',   # Trademark symbol
        '\u00ae': '(R)',    # Registered trademark
        '\u00a9': '(c)',    # Copyright
    }
    
    for unicode_char, ascii_char in replacements.items():
        text = text.replace(unicode_char, ascii_char)
    
    return text


def _get_rating_color(rating):
    """
    Return RGB color based on rating score.
    
    Args:
        rating: Float rating value
        
    Returns:
        tuple: RGB color values
    """
    if rating >= 8.0:
        return (39, 174, 96)  # Green
    elif rating >= 6.0:
        return (241, 196, 15)  # Yellow/Orange
    elif rating >= 4.0:
        return (230, 126, 34)  # Orange
    else:
        return (231, 76, 60)  # Red


def _generate_recommendations(avg_rating):
    """
    Generate personalized recommendations based on average rating.
    
    Args:
        avg_rating: Average rating score
        
    Returns:
        str: Recommendation text
    """
    if avg_rating >= 8.0:
        return """Outstanding Performance!

You demonstrated excellent knowledge and communication skills throughout the interview.

Recommendations:
* Continue practicing with real-world scenarios and advanced technical questions
* Focus on system design and architectural thinking for senior-level positions  
* Prepare behavioral interview questions to complement your technical strength
* Consider conducting mock interviews with industry professionals
* Stay updated with latest industry trends and best practices

You are well-prepared for interviews in this domain. Keep refining your skills!"""
    
    elif avg_rating >= 6.0:
        return """Good Performance with Room for Growth

You showed solid understanding of core concepts with some areas needing improvement.

Recommendations:
* Review the specific topics where you received lower ratings
* Practice explaining technical concepts more clearly and concisely
* Work on providing complete answers that address all parts of questions
* Use the STAR method (Situation, Task, Action, Result) for better structure
* Practice with coding problems or case studies relevant to your target role
* Schedule follow-up mock interviews in 2-3 weeks to track improvement

Focus on the improvement areas highlighted in this report for best results."""
    
    elif avg_rating >= 4.0:
        return """Fair Performance - Focused Preparation Needed

Your interview revealed gaps in knowledge and explanation skills that need attention.

Recommendations:
* Strengthen fundamentals in your target domain through structured learning
* Use online courses, textbooks, or tutorials to fill knowledge gaps
* Practice explaining concepts out loud to improve articulation
* Work through beginner to intermediate level practice problems daily
* Join study groups or find a mentor for guidance and feedback
* Create a study plan focusing on topics where you struggled
* Schedule another mock interview after 3-4 weeks of focused preparation

Consistent effort will lead to significant improvement. Don't get discouraged!"""
    
    else:
        return """Needs Significant Improvement

This interview identified substantial gaps that require dedicated preparation.

Recommendations:
* Start with foundational concepts and build understanding from the ground up
* Invest time in comprehensive learning resources (courses, books, boot camps)
* Break down complex topics into smaller, manageable study sessions
* Practice basic problems before moving to intermediate difficulty
* Seek mentorship or tutoring for personalized guidance
* Join online communities or forums for learning support
* Set realistic goals and track your progress weekly
* Don't attempt real interviews until you've built a solid foundation
* Schedule a follow-up mock interview after 4-6 weeks of intensive study

Remember: Everyone starts somewhere. With dedication and the right approach, you can make significant progress. Focus on consistent daily practice rather than cramming."""
