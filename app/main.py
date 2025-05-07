from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.shutterstock_api import search_images_by_category
from app.openai_api import generate_ad_image, generate_with_reference_image
from app.models import AdPrompt
from typing import Optional
import os
from PIL import Image, UnidentifiedImageError
import io
import traceback
SUPPORTED_SIZES = {"1024x1024", "1024x1536", "1536x1024", "auto"}

# Create directories if they don't exist
os.makedirs("static/generated", exist_ok=True)

app = FastAPI(title="Ad Creative Generator API")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return {"message": "Ad Creative Generator API is running"}

@app.get("/categories")
async def get_categories():
    """Return a list of available ad categories."""
    return {
        "categories": [
            "travel", "technology", "beauty", "fitness", 
            "finance", "food", "fashion", "real estate"
        ]
    }

@app.get("/inspiration/{category}")
async def get_inspiration(category: str, limit: int = 20):
    """Get inspirational ads for a specific category."""
    try:
        images = await search_images_by_category(category, limit)
        return {"images": images}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching images: {str(e)}")

@app.post("/generate-ad/")
async def create_ad_image(ad_prompt: AdPrompt):
    """Generate a new ad image using the provided prompt."""
    try:
        result = await generate_ad_image(ad_prompt.prompt, ad_prompt.size, ad_prompt.ad_text)
        return {**result, "prompt": ad_prompt.prompt, "adText": ad_prompt.ad_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating image: {str(e)}")

@app.post("/reference-style-transfer/")
async def reference_style_transfer(
    reference_image: UploadFile = File(...),
    prompt: str = Form(...),
    size: str = Form("1024x1024"),
    ad_text: Optional[str] = Form(None)
):
    print(f"[DEBUG] Received size from frontend: '{size}'") 
    if size not in SUPPORTED_SIZES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid size. Allowed sizes: {', '.join(SUPPORTED_SIZES)}"
        )
    
    try:
        reference_image_data = await reference_image.read()

        # Check image validity before sending to OpenAI
        try:
            img = Image.open(io.BytesIO(reference_image_data))
            img.verify()
        except UnidentifiedImageError:
            raise HTTPException(status_code=400, detail="Unsupported or corrupt image file. Please upload PNG or JPG.")
        
        # Call OpenAI image generation with vision-based style extraction
        result = await generate_with_reference_image(reference_image_data, prompt, size, ad_text)
        
        return {
            **result,
            "adText": ad_text
        }

    except Exception as e:
        print("[ERROR] Reference Style Transfer Failed:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating image with reference style: {str(e)}")