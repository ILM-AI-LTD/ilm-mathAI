from openai import OpenAI
from flask import Flask, request, jsonify, render_template
import base64
import os
from flask_cors import CORS
from prompts import prompt  # Make sure this file exists with your evaluation prompt

# Initialize OpenAI client
client = OpenAI()  # Reads OPENAI_API_KEY from environment

app = Flask(__name__)
CORS(app)

def evaluate_math_question(math_question, cr_answer, st_answer, previous_steps=None):
    """
    Evaluate a student's answer against the correct answer for a math question.
    Provides hints and guidance rather than full solutions.
    
    Args:
        math_question: The original math problem
        cr_answer: The correct/expected answer
        st_answer: The student's current answer/work
        previous_steps: Optional list of previous student steps for multi-step problems
    """
    try:
        # Construct the evaluation prompt
        user_content = f"Question: {math_question}\nCorrect Answer: {cr_answer}\nStudent's Current Work: {st_answer}"
        
        # Add previous steps context if provided
        if previous_steps:
            steps_text = "\n".join([f"Step {i+1}: {step}" for i, step in enumerate(previous_steps)])
            user_content += f"\n\nPrevious Steps:\n{steps_text}"
            user_content += "\n\nNote: Focus evaluation on the latest step only."
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=800,  # Reduced since we want concise hints, not full solutions
            temperature=0.2  # Lower temperature for more consistent educational feedback
        )
        
        evaluation = response.choices[0].message.content
        return {
            "success": True,
            "evaluation": evaluation,
            "error": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "evaluation": None,
            "error": str(e)
        }

def handwritten_ocr(image_data):
    """
    Extract handwritten text from image using GPT-4V
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Extract all handwritten text from this image. 
                            Focus on mathematical expressions, numbers, and equations. 
                            If there are mathematical symbols or formulas, transcribe them accurately.
                            Return only the extracted text without additional commentary."""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000
        )
        
        extracted_text = response.choices[0].message.content
        return {
            "success": True,
            "text": extracted_text,
            "error": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "text": None,
            "error": str(e)
        }

# Flask Routes

@app.route('/')
def home():
    """Main page with upload form"""
    return render_template('index.html')

@app.route('/api/evaluate', methods=['POST'])
def api_evaluate():
    """API endpoint for evaluating math questions with hint-based feedback"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['question', 'correct_answer', 'student_answer']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": f"Missing required field: {field}"
                }), 400
        
        # Get optional previous steps for multi-step problems
        previous_steps = data.get('previous_steps', None)
        
        # Evaluate the question
        result = evaluate_math_question(
            data['question'],
            data['correct_answer'],
            data['student_answer'],
            previous_steps
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/ocr', methods=['POST'])
def api_ocr():
    """API endpoint for OCR extraction"""
    try:
        data = request.json
        
        if 'image' not in data:
            return jsonify({
                "success": False,
                "error": "Missing image data"
            }), 400
        
        # Remove data URL prefix if present
        image_data = data['image']
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]
        
        # Extract text from image
        result = handwritten_ocr(image_data)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/full_evaluation', methods=['POST'])
def api_full_evaluation():
    """Combined OCR + Evaluation endpoint with hint-based feedback"""
    try:
        data = request.json
        
        # Validate required fields
        if 'image' not in data or 'question' not in data or 'correct_answer' not in data:
            return jsonify({
                "success": False,
                "error": "Missing required fields: image, question, correct_answer"
            }), 400
        
        # Extract image data
        image_data = data['image']
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]
        
        # Get optional previous steps
        previous_steps = data.get('previous_steps', None)
        
        # Step 1: OCR
        ocr_result = handwritten_ocr(image_data)
        if not ocr_result['success']:
            return jsonify({
                "success": False,
                "error": f"OCR failed: {ocr_result['error']}"
            }), 500
        
        # Step 2: Evaluation with hints
        eval_result = evaluate_math_question(
            data['question'],
            data['correct_answer'],
            ocr_result['text'],
            previous_steps
        )
        
        if not eval_result['success']:
            return jsonify({
                "success": False,
                "error": f"Evaluation failed: {eval_result['error']}"
            }), 500
        
        # Return combined results
        return jsonify({
            "success": True,
            "extracted_text": ocr_result['text'],
            "evaluation": eval_result['evaluation'],
            "error": None
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({
        "success": False,
        "error": "File too large. Please upload a smaller image."
    }), 413

if __name__ == '__main__':
    # Set maximum file size (16MB)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    
    # Run the app
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print("Math Evaluation System starting...")
    print(f"Running on port {port}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)