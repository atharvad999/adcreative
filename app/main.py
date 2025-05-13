import os
import base64
from typing import Optional, List

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.image_gen import edit_image, generate_image
from app.shutterstock_api import search_images_by_category
from app.supabase_storage import upload_image
from app.supabase_db import get_all_images

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

@app.get("/library")
async def get_library(limit: int = 50, offset: int = 0, include_reference: bool = True):
    """Get all generated images from the library."""
    try:
        images = await get_all_images(limit, offset, include_reference)
        return {"images": images}
    except Exception as e:
        print(f"Error in get_library: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching library images: {str(e)}")
    
@app.post("/generate-image/")
async def create_image(
    prompt: str = Form(...),
    size: str = Form("1024x1024"),
    background: str = Form("auto"),
    quality: str = Form("auto"),
    output_format: str = Form("png"),
    output_compression: Optional[int] = Form(None),
    reference_images: list[UploadFile] = File(None),
    background_tasks: BackgroundTasks = None,
    category: str = Form(None),
    title: str = Form(None),
):
    """Generate an image using OpenAI's API with customizable parameters."""
    print(f"Received request with prompt: {prompt}")
    print(f"Reference images: {reference_images}")
    
    if size not in SUPPORTED_SIZES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid size. Allowed sizes: {', '.join(SUPPORTED_SIZES)}"
        )
    
    try:
        # Process reference images if provided
        reference_image_data = []
        if reference_images:
            print(f"Processing {len(reference_images)} reference images")
            for idx, image in enumerate(reference_images):
                print(f"Reading reference image {idx + 1}: {image.filename}")
                contents = await image.read()
                print(f"Reference image {idx + 1} size: {len(contents)} bytes")
                reference_image_data.append(contents)
        
        result = await generate_image(
            prompt=prompt,
            size=size,
            background=background,
            quality=quality,
            output_format=output_format,
            output_compression=output_compression,
            reference_images=reference_image_data if reference_image_data else None
        )
        print(f"Generation result: {result}")
        
        # Store the generated image in Supabase
        if result and result.data and len(result.data) > 0:
            # Get the base64 image data
            b64_image = result.data[0].b64_json
            # Convert base64 to bytes
            image_bytes = base64.b64decode(b64_image)
            
            # Upload to Supabase storage
            filename, public_url = await upload_image(
                image_bytes=image_bytes,
                folder="generated",
                prompt=prompt,
                category=category,
                size=size,
                title=title
            )
            
            # Add URL to the response
            result.public_url = public_url
            result.filename = filename
            
            print(f"Image stored in Supabase: {public_url}")
        
        return result
    except Exception as e:
        print(f"Error in create_image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating image: {str(e)}")

@app.post("/edit-image/")
async def edit_image_endpoint(
    prompt: str = Form(...),
    images: list[UploadFile] = File(...),
    mask: Optional[UploadFile] = File(None),
    size: str = Form("1024x1024"),
    background: str = Form("auto"),
    quality: str = Form("auto"),
    output_compression: Optional[int] = Form(None),
    background_tasks: BackgroundTasks = None,
    category: str = Form(None),
    title: str = Form(None),
):
    """Edit images using OpenAI's API with customizable parameters."""
    print(f"Received edit request with prompt: {prompt}")
    print(f"Number of images to edit: {len(images)}")
    
    if size not in SUPPORTED_SIZES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid size. Allowed sizes: {', '.join(SUPPORTED_SIZES)}"
        )
    
    if background not in {"transparent", "opaque", "auto"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid background. Allowed values: transparent, opaque, auto"
        )
    
    if quality not in {"standard", "low", "medium", "high", "auto"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid quality. Allowed values: standard, low, medium, high, auto"
        )
    
    try:
        # Instead of reading all contents at once, pass the UploadFile objects directly
        # This allows the edit_image function to handle the file objects properly
        
        # Process mask if provided
        mask_file = mask
        
        result = await edit_image(
            upload_files=images,  # Pass the UploadFile objects directly
            prompt=prompt,
            mask_file=mask_file,  # Pass the UploadFile object directly
            size=size,
            background=background,
            quality=quality,
            output_compression=output_compression,
        )
        print(f"Edit result: {result}")
        
        # Store the edited image in Supabase
        if result and result.data and len(result.data) > 0:
            # Get the base64 image data
            b64_image = result.data[0].b64_json
            # Convert base64 to bytes
            image_bytes = base64.b64decode(b64_image)
            
            # Upload to Supabase storage
            filename, public_url = await upload_image(
                image_bytes=image_bytes,
                folder="edited",
                prompt=prompt,
                category=category,
                size=size,
                title=title
            )
            
            # Add URL to the response
            result.public_url = public_url
            result.filename = filename
            
            print(f"Edited image stored in Supabase: {public_url}")
        
        return result
    except Exception as e:
        print(f"Error in edit_image_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error editing image: {str(e)}")