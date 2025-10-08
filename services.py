"""
Math Evaluation Services
"""
import os
import json
import logging
import time
import base64
from typing import Dict, Any
from dotenv import load_dotenv
from google import genai
from openai import OpenAI
from PIL import Image
from prompts import eval_prompt, ocr_prompt

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define constants for model names to avoid magic strings
GEMINI_FLASH_MODEL = "gemini-2.0-flash"
GPT_NANO_MODEL = "gpt-5-mini"

class MathEvaluationService:
    """Service class for handling math evaluation operations"""

    def __init__(self):
        """Initialize OpenAI client"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        logger.info("OpenAI API key found.")
        self.client = OpenAI(api_key=api_key)
        self.system_prompt = self._get_system_prompt()

    def _get_system_prompt(self) -> str:
        """Get the system prompt for evaluation"""
        return eval_prompt

    def extract_text_from_image(self, image_data: str) -> Dict[str, Any]:
        """
        Extract handwritten text from image using Google's Gemini API.

        Args:
            image_data: Path to the image file.

        Returns:
            A dictionary with success status, extracted text, and error info.
        """
        try:
            client1 = genai.Client()
            img = Image.open(image_data)

            response = client1.models.generate_content(
                model=GEMINI_FLASH_MODEL,
                contents=[img, ocr_prompt]
            )
            extracted_text = response.text

            logger.info("Successfully extracted text: %s...", extracted_text[:100])

            return {
                "success": True,
                "text": extracted_text,
                "error": None
            }

        except FileNotFoundError:
            logger.error("OCR Error: Image file not found at path: %s", image_data)
            return {
                "success": False,
                "text": None,
                "error": f"Image file not found: {image_data}"
            }
        except Exception as e:
            # Catching a broad exception for unexpected API or other errors.
            logger.error("An unexpected error occurred during OCR: %s", e, exc_info=True)
            return {
                "success": False,
                "text": None,
                "error": f"Failed to extract text: {str(e)}"
            }

    def evaluate_math_solution(
        self,
        question: str,
        correct_answer: str,
        student_work: str,
        step_count: int,
        prev_history: str
    ) -> Dict[str, Any]:
        """
        Evaluate student's math solution against correct answer.

        Args:
            question: The original math problem.
            correct_answer: The expected correct answer.
            student_work: Student's work/answer.
            step_count: Current step count for tracking.

        Returns:
            A dictionary containing evaluation results.
        """
        try:
            user_content = (
                f"Question: {question}\n"
                f"Correct Answer: {correct_answer}\n"
                f"Students previous steps (Ignore if this answers is wrong): {prev_history}\n, Dont judge this step. Check this only when necessary"
                f"Student's Current Answer: {student_work}\n, Evaluate this step only."
            )

            response = self.client.responses.create(
                model=GPT_NANO_MODEL,
                input=[
                    {
                        "role": "system",
                        "content": [{"type": "input_text", "text": self.system_prompt}]
                    },
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": user_content}]
                    }
                ],
                text={ "verbosity": "low" },
                reasoning={ "effort": "low" },
            )

            evaluation_text = response.output_text
            # Clean up any markdown formatting
            evaluation_text = evaluation_text.replace('```json', '').replace('```', '').strip()

            logger.info("Successfully evaluated solution for question: %s...", evaluation_text[:100])

            # Use a different name than the built-in 'eval'
            evaluation_data = json.loads(evaluation_text)
            ret = {
                "success": True,
                "nextStepCount": step_count + 1,
                "error": None
            }
            ret.update(evaluation_data)
            return ret

        except json.JSONDecodeError as e:
            logger.error("Evaluation failed: Could not decode JSON from API response. Error: %s", e)
            return {
                "success": False,
                "evaluation": None,
                "hint": None,
                "nextStepCount": step_count + 1,
                "error": f"Invalid JSON response from evaluation API: {e}"
            }
        except Exception as e:
            logger.error("An unexpected error occurred during evaluation: %s", e, exc_info=True)
            return {
                "success": False,
                "evaluation": None,
                "hint": None,
                "nextStepCount": step_count + 1,
                "error": f"An unexpected evaluation error occurred: {str(e)}"
            }

    def process_full_evaluation(
        self,
        image_data: str,
        question: str,
        correct_answer: str,
        step_count: int,
        prev_history: str
    ) -> Dict[str, Any]:
        """
        Perform OCR + Evaluation in one operation.

        Args:
            image_data: Path to the image file.
            question: Math question.
            correct_answer: Expected answer.
            step_count: Current step count.

        Returns:
            Combined OCR and evaluation results.
        """
        # Step 1: Extract text
        start_time = time.time()
        ocr_result = self.extract_text_from_image(image_data)
        ocr_duration = time.time() - start_time
        logger.info("OCR processing time: %.2f seconds", ocr_duration)

        if not ocr_result['success']:
            logger.info("OCR Failed")
            return {
                "success": False,
                "error": f"OCR failed: {ocr_result['error']}",
                "extracted_text": None,
                "evaluation": None
            }

        # Step 2: Evaluate the extracted text
        start_time = time.time()
        eval_result = self.evaluate_math_solution(
            question,
            correct_answer,
            ocr_result['text'],
            step_count, 
            prev_history
        )
        eval_duration = time.time() - start_time
        # print("---------------------------------\n", prev_history)
        cur_history = prev_history + "\n" + ocr_result['text']
        # print("---------------------------------\n", cur_history)
        # For debugging purposes, you might want to log the full extracted text and evaluation result
        # logger.info("Successfully extracted text: %s...", eval_result)
        print(eval_result)
        logger.info("Evaluation processing time: %.2f seconds", eval_duration)

        if not eval_result['success']:
            return {
                "success": False,
                "error": f"Evaluation failed: {eval_result['error']}",
                "extracted_text": ocr_result['text'],
                "evaluation": None,
                "nextStepCount": eval_result['nextStepCount'],
                "hint": None,
                "chat_history": cur_history
            }

        # Determine if the process is finished based on the hint content
        is_finished = 'correct' in eval_result.get('verdict', '').lower()
        if 'incorrect' in eval_result.get('verdict', '').lower():
            is_finished = False
        elif 'on track' in eval_result.get('verdict', '').lower():
            is_finished = False
        elif 'correct' in eval_result.get('verdict', '').lower():
            is_finished = True

        
        return {
            "success": True,
            "extracted_text": ocr_result['text'],
            "evaluation": eval_result.get('evaluation'),
            "nextStepCount": eval_result['nextStepCount'],
            "hint": eval_result.get('hint'),
            "error": None,
            "is_finished": is_finished,
            "chat_history": cur_history,
            "verdict": eval_result.get('verdict').lower()
        }


class ValidationService:
    """Service for input validation"""

    # Supported image MIME types for OpenAI Vision API
    SUPPORTED_IMAGE_TYPES = {
        'image/png',
        'image/jpeg',
        'image/jpg',
        'image/gif',
        'image/webp'
    }

    @staticmethod
    def validate_image_data(image_data: str) -> Dict[str, Any]:
        """Validate base64 image data"""
        if not image_data:
            return {"valid": False, "error": "Image data is required"}

        # Remove data URL prefix if present
        if image_data.startswith('data:image'):
            image_data = image_data.split(',', 1)[1]

        # Basic base64 validation
        try:
            base64.b64decode(image_data, validate=True)
            return {"valid": True, "cleaned_data": image_data, "error": None}
        except (ValueError, TypeError):
            return {"valid": False, "error": "Invalid base64 image data format"}

    @staticmethod
    def validate_mime_type(mime_type: str) -> Dict[str, Any]:
        """Validate image MIME type"""
        if not mime_type:
            return {"valid": False, "error": "MIME type is required"}

        if mime_type not in ValidationService.SUPPORTED_IMAGE_TYPES:
            supported_types_str = ', '.join(ValidationService.SUPPORTED_IMAGE_TYPES)
            return {
                "valid": False,
                "error": f"Unsupported MIME type: {mime_type}. Supported types: {supported_types_str}"
            }

        return {"valid": True, "error": None}

    @staticmethod
    def validate_evaluation_request(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate evaluation request data"""
        required_fields = ['question', 'correct_answer', 'student_answer']
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            return {
                "valid": False,
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }

        return {"valid": True, "error": None}

    @staticmethod
    def validate_full_evaluation_request(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate full evaluation request data"""
        required_fields = ['image', 'question', 'correct_answer']
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            return {
                "valid": False,
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }

        # Validate image
        image_validation = ValidationService.validate_image_data(data['image'])
        if not image_validation['valid']:
            return image_validation

        return {"valid": True, "error": None}


# Create service instances for use in other modules
math_service = MathEvaluationService()
validation_service = ValidationService()