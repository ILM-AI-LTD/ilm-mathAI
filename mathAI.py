"""
Math Evaluation Flask Application
Clean, production-ready Flask app with proper error handling and structure
"""

import os
import logging
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
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
    
    # Configuration
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    app.config['JSON_SORT_KEYS'] = False
    
    # Enable CORS
    CORS(app)
    
    return app

app = create_app()

# Routes
@app.route('/')
def home():
    """Serve the main application page"""
    return render_template('index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Math Evaluation API",
        "version": "1.0.0"
    })

@app.route('/api/ocr', methods=['POST'])
def extract_text():
    """Extract text from uploaded image"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
        
        # Validate image data
        image_validation = validation_service.validate_image_data(data.get('image', ''))
        if not image_validation['valid']:
            return jsonify({
                "success": False,
                "error": image_validation['error']
            }), 400
        
        # Extract text
        result = math_service.extract_text_from_image(image_validation['cleaned_data'])
        
        return jsonify(result), 200 if result['success'] else 500
        
    except Exception as e:
        logger.error(f"OCR endpoint error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500

@app.route('/api/evaluate', methods=['POST'])
def evaluate_solution():
    """Evaluate math solution manually (without OCR)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
        
        # Validate request data
        validation = validation_service.validate_evaluation_request(data)
        if not validation['valid']:
            return jsonify({
                "success": False,
                "error": validation['error']
            }), 400
        
        # Perform evaluation
        step_count = data.get('nextStepCount', 0)
        result = math_service.evaluate_math_solution(
            question=data['question'],
            correct_answer=data['correct_answer'],
            student_work=data['student_answer'],
            step_count=step_count
        )
        
        return jsonify(result), 200 if result['success'] else 500
        
    except Exception as e:
        logger.error(f"Evaluation endpoint error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500

@app.route('/api/full_evaluation', methods=['POST'])
def full_evaluation():
    """Perform OCR + Evaluation in one request"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
        
        # Validate request data
        validation = validation_service.validate_full_evaluation_request(data)
        if not validation['valid']:
            return jsonify({
                "success": False,
                "error": validation['error']
            }), 400
        
        # Clean image data
        image_data = data['image']
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]
        
        # Perform full evaluation
        step_count = data.get('currentStepCount', 0)
        result = math_service.process_full_evaluation(
            image_data=image_data,
            question=data['question'],
            correct_answer=data['correct_answer'],
            step_count=step_count
        )
        
        return jsonify(result), 200 if result['success'] else 500
        
    except Exception as e:
        logger.error(f"Full evaluation endpoint error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500

# Error handlers
@app.errorhandler(400)
def bad_request(error):
    """Handle bad request errors"""
    return jsonify({
        "success": False,
        "error": "Bad request - please check your input data"
    }), 400

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file size too large errors"""
    return jsonify({
        "success": False,
        "error": "File too large. Maximum size is 16MB."
    }), 413

@app.errorhandler(500)
def internal_server_error(error):
    """Handle internal server errors"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({
        "success": False,
        "error": "Internal server error. Please try again later."
    }), 500

@app.errorhandler(404)
def not_found(error):
    """Handle not found errors"""
    return jsonify({
        "success": False,
        "error": "Endpoint not found"
    }), 404

@app.before_request
def log_request():
    """Log incoming requests"""
    if request.endpoint != 'health_check':  # Skip health check logs
        logger.info(f"{request.method} {request.path} - {request.remote_addr}")

def main():
    """Main application entry point"""
    # Environment configuration
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    host = os.environ.get('HOST', '0.0.0.0')
    
    # Check for required environment variables
    if not os.environ.get('OPENAI_API_KEY'):
        logger.error("OPENAI_API_KEY environment variable is required")
        return
    
    logger.info(f"Starting Math Evaluation System on {host}:{port}")
    logger.info(f"Debug mode: {debug}")
    
    try:
        app.run(host=host, port=port, debug=debug)
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")

if __name__ == '__main__':
    main()