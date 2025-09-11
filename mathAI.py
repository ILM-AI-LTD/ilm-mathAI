"""
Math Evaluation Flask Application
"""

import os
import base64
import logging
import io
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from services import math_service, validation_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Configuration from environment variables for better security and flexibility
    cors_origins = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000,null').split(',')
    
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    app.config['JSON_SORT_KEYS'] = False
    app.config['UPLOAD_FOLDER'] = 'uploads'

    # Create upload folder if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Enable CORS with configured origins
    CORS(   
        app,
        origins=cors_origins,
        methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
        supports_credentials=True
    )
    
    return app

app = create_app()

# --- API Routes ---

@app.route('/')
def home():
    """Serve a simple welcome message."""
    return "Math Evaluation API is running."

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify service status."""
    return jsonify({
        "status": "healthy",
        "service": "Math Evaluation API",
        "version": "1.0.0"
    })

@app.route('/api/ocr', methods=['POST'])
def extract_text():
    """Extract text from a base64 encoded image string."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400
        
        # Validate and clean base64 image data
        image_validation = validation_service.validate_image_data(data.get('image'))
        if not image_validation['valid']:
            return jsonify({"success": False, "error": image_validation['error']}), 400
        
        # The service expects a file-like object, so we decode the base64 string
        image_bytes = base64.b64decode(image_validation['cleaned_data'])
        image_file = io.BytesIO(image_bytes)

        result = math_service.extract_text_from_image(image_file)
        
        return jsonify(result), 200 if result.get('success') else 500
        
    except (ValueError, TypeError) as e:
        logger.warning("OCR endpoint validation error: %s", e, exc_info=True)
        return jsonify({"success": False, "error": f"Invalid data provided: {e}"}), 400
    except Exception as e:
        logger.error("OCR endpoint error: %s", e, exc_info=True)
        return jsonify({"success": False, "error": "An internal server error occurred during OCR."}), 500

@app.route('/api/evaluate', methods=['POST'])
def evaluate_solution():
    """Evaluate a math solution provided as text."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400
        
        # Validate required text fields
        validation = validation_service.validate_evaluation_request(data)
        if not validation['valid']:
            return jsonify({"success": False, "error": validation['error']}), 400
        histo = data.get('chat_history', '')
        step_count = data.get('nextStepCount', 0)
        result = math_service.evaluate_math_solution(
            question=data['question'],
            correct_answer=data['correct_answer'],
            student_work=data['student_answer'],
            step_count=step_count,
            prev_history=histo
        )
        
        return jsonify(result), 200 if result.get('success') else 500
        
    except Exception as e:
        logger.error("Evaluation endpoint error: %s", e, exc_info=True)
        return jsonify({"success": False, "error": "An internal server error occurred during evaluation."}), 500

@app.route('/api/full_evaluation', methods=['POST'])
def full_evaluation():
    """Perform OCR and evaluation from an uploaded image file."""
    try:
        # 1. Validate request parts
        if 'image' not in request.files:
            return jsonify({"success": False, "error": "No image file provided in the 'image' field."}), 400

        image_file = request.files['image']
        if image_file.filename == '':
            return jsonify({"success": False, "error": "No image file selected."}), 400

        question = request.form.get('question')
        correct_answer = request.form.get('correct_answer')
        step_count = int(request.form.get('currentStepCount', 0))

        if not all([question, correct_answer]):
            return jsonify({"success": False, "error": "Missing required form fields: question, correct_answer."}), 400

        # 2. Securely save the file to a temporary location
        filename = secure_filename(image_file.filename)
        temp_image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(temp_image_path)
        histo = request.form.get('chat_history', '[]')
        # 3. Process the file using the service
        result = math_service.process_full_evaluation(
            image_data=temp_image_path,
            question=question,
            correct_answer=correct_answer,
            step_count=step_count,
            prev_history = histo 
        )
        
        # 4. Clean up the temporary file
        os.remove(temp_image_path)
        print(result)

        return jsonify(result), 200 if result.get('success') else 500

    except Exception as e:
        logger.error("Full evaluation endpoint error: %s", e, exc_info=True)
        return jsonify({"success": False, "error": "An internal server error occurred."}), 500

# --- Error Handlers ---

@app.errorhandler(400)
def bad_request(error):
    """Handle bad request errors."""
    return jsonify({"success": False, "error": "Bad request. Please check your input data and format."}), 400

@app.errorhandler(404)
def not_found(error):
    """Handle not found errors for undefined routes."""
    return jsonify({"success": False, "error": "This endpoint does not exist."}), 404

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file size too large errors."""
    return jsonify({"success": False, "error": f"File too large. Maximum size is {app.config['MAX_CONTENT_LENGTH'] // 1024 // 1024}MB."}), 413

@app.errorhandler(500)
def internal_server_error(error):
    """Handle unexpected internal server errors."""
    logger.error("Internal server error: %s", error, exc_info=True)
    return jsonify({"success": False, "error": "An internal server error occurred. Please try again later."}), 500

# --- Request Logging ---

@app.before_request
def log_request():
    """Log incoming requests, skipping health checks for cleaner logs."""
    if request.endpoint != 'health_check':
        logger.info("Request: %s %s from %s", request.method, request.path, request.remote_addr)

# --- Main Application Runner ---

def main():
    """Main application entry point."""
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    host = os.environ.get('HOST', '0.0.0.0')
    
    # Pre-flight check for required environment variables
    if not os.environ.get('OPENAI_API_KEY'):
        logger.critical("FATAL: OPENAI_API_KEY environment variable is not set. Application will not start.")
        return
    
    logger.info("Starting Math Evaluation System on http://%s:%s", host, port)
    logger.info("Debug mode: %s", 'On' if debug else 'Off')
    
    try:
        # Use app.run() for development. For production, use a WSGI server like Gunicorn or Waitress.
        app.run(host=host, port=port, debug=debug)
    except Exception as e:
        logger.critical("Failed to start application: %s", e, exc_info=True)

if __name__ == '__main__':
    main()