"""
Math Evaluation Services
Core business logic for OCR and math evaluation functionality
"""
from google import genai
from PIL import Image
import os
import base64
import json
import logging
from typing import Dict, Any, Optional
from openai import OpenAI
from prompts import eval_prompt, ocr_prompt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MathEvaluationService:
    """Service class for handling math evaluation operations"""
    
    def __init__(self):
        """Initialize OpenAI client"""
        self.client = OpenAI()
        self.system_prompt = self._get_system_prompt()
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for evaluation"""
        return eval_prompt
    
    # def extract_text_from_image(self, image_data: str, mime_type: str) -> Dict[str, Any]:
    #     """
    #     Extract handwritten text from image using OpenAI Vision API
        
    #     Args:
    #         image_data: Base64 encoded image string
            
    #     Returns:
    #         Dict containing extracted text and status
    #     """
    #     try:
    #         logger.info(type(image_data))
    #         response = self.client.chat.completions.create(
    #             model="gpt-5",
    #             messages=[
    #                 {
    #                     "role": "user",
    #                     "content": [
    #                         {
    #                             "type": "text",
    #                             "text": ocr_prompt
    #                         },
    #                         {
    #                             "type": "image_url",
    #                             "image_url": {
    #                                 "url": f"data:{mime_type};base64,{image_data}"
    #                             }
    #                         }
    #                     ]
    #                 }
    #             ],
    #             # max_tokens=1000
    #         )
            
    #         extracted_text = response.choices[0].message.content.strip()
    #         logger.info(f"Successfully extracted text: {extracted_text[:50]}...")
            
    #         return {
    #             "success": True,
    #             "text": extracted_text,
    #             "error": None
    #         }
            
    #     except Exception as e:
    #         logger.error(f"OCR extraction failed: {str(e)}")
    #         return {
    #             "success": False,
    #             "text": None,
    #             "error": f"Failed to extract text: {str(e)}"
    #         }

    def extract_text_from_image(self, image_data: str) -> Dict[str, Any]:
        """
        Extract handwritten text from image using OpenAI Vision API
        
        Args:
            image_data: Base64 encoded image string
            mime_type: MIME type of the image (e.g., 'image/png')
            
        Returns:
            Dict containing extracted text and status
        """
        try:
            # Debug logging
            # logger.info(f"Processing image with MIME type: {mime_type}")
            # logger.info(f"Image data length: {len(image_data)} characters")
            
            # Ensure MIME type is valid
            # if not mime_type.startswith('image/'):
            #     raise ValueError(f"Invalid MIME type: {mime_type}")
            # api_key = os.getenv("GOOGLE_API_KEY")
            client1 = genai.Client()
            img = Image.open(image_data)
            
            response = client1.models.generate_content(
                model="gemini-2.0-flash",
                contents=[img, ocr_prompt]
            )
            extracted_text = response.text
            
            # extracted_text = response.choices[0].message.content.strip()
            logger.info(f"Successfully extracted text: {extracted_text[:50]}...")
            
            return {
                "success": True,
                "text": extracted_text,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}")
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
        step_count: int = 0
    ) -> Dict[str, Any]:
        """
        Evaluate student's math solution against correct answer
        
        Args:
            question: The original math problem
            correct_answer: The expected correct answer
            student_work: Student's work/answer
            step_count: Current step count for tracking
            
        Returns:
            Dict containing evaluation results
        """
        try:
            user_content = (
                f"Question: {question}\n"
                f"Correct Answer: {correct_answer}\n"
                f"Student's Answer: {student_work}\n"
                # f"Current Step: {step_count}"
            )
            
            response = self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_content}
                ],
                # max_tokens=100,
                # temperature=0.3
            )
            
            evaluation_text = response.choices[0].message.content
            # Clean up any markdown formatting
            evaluation_text = evaluation_text.replace('```json', '').replace('```', '').strip()
            
            logger.info(f"Successfully evaluated solution for question: {question[:50]}...\n{evaluation_text[:50]}...")
            
            ret = {
                "success": True,
                "nextStepCount": step_count+1,
                "error": None
            }
            eval = json.loads(evaluation_text)
            ret.update(eval)
            return ret
            
        except Exception as e:
            logger.error(f"Evaluation failed: {str(e)}")
            return {
                "success": False,
                "evaluation": None,
                "hint":None,
                "nextStepCount": step_count + 1,
                "error": f"Evaluation failed: {str(e)}"
            }
    
    def process_full_evaluation(
        self,
        image_data: str,
        question: str,
        correct_answer: str,
        step_count: int,
        # mime_type: str,  
    ) -> Dict[str, Any]:
        """
        Perform OCR + Evaluation in one operation
        
        Args:
            image_data: Base64 encoded image
            question: Math question
            correct_answer: Expected answer
            step_count: Current step count
            
        Returns:
            Combined OCR and evaluation results
        """
        # Step 1: Extract text
        ocr_result = self.extract_text_from_image(image_data)
        
        if not ocr_result['success']:
            return {
                "success": False,
                "error": f"OCR failed: {ocr_result['error']}",
                "extracted_text": None,
                "evaluation": None
            }
        
        # Step 2: Evaluate the extracted text
        eval_result = self.evaluate_math_solution(
            question, 
            correct_answer, 
            ocr_result['text'], 
            step_count
        )
        
        if not eval_result['success']:
            return {
                "success": False,
                "error": f"Evaluation failed: {eval_result['error']}",
                "extracted_text": ocr_result['text'],
                "evaluation": None,
                "nextStepCount": eval_result['nextStepCount'],
                "hint":None
            }
        if "correct" not in eval_result['hint']:
            flag = False
        else:
            flag = True
        return {
            "success": True,
            "extracted_text": ocr_result['text'],
            "evaluation": eval_result['evaluation'],
            "nextStepCount": eval_result['nextStepCount'],
            "hint": eval_result['hint'],
            "error": None,
            "is_finished": flag
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
            image_data = image_data.split(',')[1]
        
        # Basic base64 validation
        try:
            import base64
            base64.b64decode(image_data)
            return {"valid": True, "cleaned_data": image_data, "error": None}
        except Exception:
            return {"valid": False, "error": "Invalid image data format"}
    
    @staticmethod
    def validate_mime_type(mime_type: str) -> Dict[str, Any]:
        """Validate image MIME type"""
        if not mime_type:
            return {"valid": False, "error": "MIME type is required"}
        
        if mime_type not in ValidationService.SUPPORTED_IMAGE_TYPES:
            return {
                "valid": False, 
                "error": f"Unsupported MIME type: {mime_type}. Supported types: {', '.join(ValidationService.SUPPORTED_IMAGE_TYPES)}"
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


# Create service instances
math_service = MathEvaluationService()
validation_service = ValidationService()