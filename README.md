# Math Evaluation System

An AI-powered educational tool that evaluates handwritten math solutions using OCR and provides intelligent hints to guide student learning. Built with OpenAI's GPT-4V for image recognition and GPT-4 for mathematical evaluation.

## Installation

```bash
pip install openai flask flask-cors
export OPENAI_API_KEY="your-openai-api-key"
python app.py
```

## Input Format

### Full Evaluation Endpoint
**POST** `/api/full_evaluation`

```json
{
  "question": "Solve x^2 + 2x + 1 = 0",
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAA...",
  "correct_answer": "x = -1 (double root)",
}
```

### Text-Only Evaluation Endpoint  
**POST** `/api/evaluate`

```json
{
  "question": "Solve x^2 + 2x + 1 = 0", 
  "correct_answer": "x = -1 (double root)",
  "student_answer": "x^2 + 2x + 1 = (x+1)^2",
}
```

### OCR Only Endpoint
**POST** `/api/ocr`

```json
{
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAA..."
}
```

## Output Format

### Full Evaluation Response
```json
{
  "extracted_text": "x^2 + 2x + 1 = (x+1)^2 = 0",
  "evaluation": "{\n\"evaluation\": \"Good work! You correctly factored the quadratic expression as (x+1)^2.\",\n\"hint\": \"Now that you have (x+1)^2 = 0, what value of x would make this equation true?\"\n}",
  "error": null
}
```

### Text-Only Evaluation Response
```json
{
  "evaluation": "{\n\"evaluation\": \"Excellent factoring! You correctly identified this as a perfect square trinomial.\",\n\"hint\": \"Now solve (x+1)^2 = 0. What happens when a squared term equals zero?\"\n}",
  "error": null
}
```

### OCR Only Response
```json
{
  "text": "x^2 + 2x + 1 = (x+1)^2",
  "error": null
}
```

### Error Response
```json
{
  "success": false,
  "error": "Missing required field: question",
  "evaluation": null
}
```
