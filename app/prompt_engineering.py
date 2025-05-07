import sys
import os

# Add the virtual environment site-packages to the path
venv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'venv', 'lib', 'python3.13', 'site-packages')
if venv_path not in sys.path:
    sys.path.insert(0, venv_path)

import openai
from app.config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

async def reverse_engineer_prompt(image_url: str, ad_text: str = None):
    """Generate a creative prompt based on an existing image."""
    messages = [
        {
            "role": "system",
            "content": "You are an expert ad creative director. Analyze this image and create a detailed prompt that would generate a similar image using an AI image generator."
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Create a detailed prompt for an AI image generator based on this ad image."},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        }
    ]
    
    if ad_text:
        messages[1]["content"].append({"type": "text", "text": f"The ad text is: {ad_text}"})
    
    # The OpenAI API call doesn't need await - it's not an async function
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )
    
    return response.choices[0].message.content