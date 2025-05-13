import base64
import io
from typing import Optional

from fastapi import UploadFile, HTTPException
from openai import OpenAI
from PIL import Image

from app.config import OPENAI_API_KEY

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

async def generate_image(
    prompt: str,
    size: str = "1024x1024",
    background: str = "auto",
    quality: str = "auto",
    output_format: str = "png",
    output_compression: int = None,
    reference_images: list[bytes] = None,
):
    """
    Generate an image using OpenAI's gpt-image-1 model.
    
    Args:
        prompt: The text prompt describing the image to generate
        size: The size of the output image
        background: Background style preference
        quality: Image quality setting
        output_format: Output image format
        output_compression: Compression level for output
        reference_images: Optional list of reference image data in bytes
    """
    try:
        enhanced_prompt = prompt
        print(f"Original prompt: {prompt}")
        print(f"Number of reference images: {len(reference_images) if reference_images else 0}")
        
        # Process reference images if provided
        if reference_images:
            style_descriptions = []
            for idx, img_data in enumerate(reference_images):
                print(f"Processing reference image {idx + 1}")
                try:
                    # Convert image to base64
                    img = Image.open(io.BytesIO(img_data))
                    img_rgb = img.convert("RGB")
                    img_buffer = io.BytesIO()
                    img_rgb.save(img_buffer, format="PNG")
                    img_buffer.seek(0)
                    image_b64 = base64.b64encode(img_buffer.getvalue()).decode("utf-8")
                    image_url = f"data:image/png;base64,{image_b64}"

                    # Extract style
                    print(f"Sending image {idx + 1} to GPT-4 Vision")
                    vision_response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Describe the visual style of this image in a prompt-friendly sentence. Be concise."},
                                {"type": "image_url", "image_url": {"url": image_url}}
                            ]
                        }]
                    )
                    style_description = vision_response.choices[0].message.content.strip()
                    print(f"Style description for image {idx + 1}: {style_description}")
                    style_descriptions.append(style_description)
                except Exception as e:
                    error_msg = f"Failed to process reference image {idx + 1}: {str(e)}"
                    print(error_msg)
                    raise Exception(error_msg)

            # Add style descriptions to the prompt
            if style_descriptions:
                style_hints = ". Style hints: " + "; ".join(style_descriptions)
                enhanced_prompt = f"{prompt}{style_hints}"
                print(f"Enhanced prompt with style hints: {enhanced_prompt}")
            else:
                raise Exception("No style descriptions were generated from reference images")
        
        # Prepare request parameters
        params = {
            "model": "gpt-image-1",
            "prompt": enhanced_prompt,
            "n": 1,
        }
        
        # Add optional parameters
        if size != "auto":
            params["size"] = size
        
        if background != "auto":
            params["background"] = background
            
        if quality != "auto":
            params["quality"] = quality
            
        params["output_format"] = output_format
        
        if output_compression is not None:
            params["output_compression"] = output_compression

        # Generate the image
        print(params)
        response = client.images.generate(**params)
        print(response)
                
        return response
    except Exception as e:
        raise Exception(f"Error generating image: {str(e)}")

async def edit_image(
    upload_files: list[UploadFile],  
    prompt: str,
    mask_file: Optional[UploadFile] = None,  
    size: str = "1024x1024",
    background: str = "auto",
    quality: str = "auto",
    output_compression: Optional[int] = None,
):
    """
    Edit images using OpenAI's image editing API.
    
    Args:
        upload_files: List of FastAPI UploadFile objects
        prompt: The text prompt describing the desired edit
        mask_file: Optional FastAPI UploadFile for the mask
        size: The size of the output image
        background: Background style preference (transparent/opaque/auto)
        quality: Image quality setting (standard/low/medium/high/auto)
        output_compression: Compression level for output
    """
    try:
        print(f"Received edit request with prompt: {prompt}")
        # Prepare request parameters
        params = {
            "model": "gpt-image-1",
            "prompt": prompt,
            "n": 1,
            "background": background,
            "quality": quality,
        }
        
        # Read all image files and convert to file-like objects
        image_files = []
        for idx, upload_file in enumerate(upload_files):
            content = await upload_file.read()
            file = io.BytesIO(content)
            file.name = upload_file.filename or f"image_{idx}.png"
            image_files.append(file)
            
            # Reset file position for future reads if needed
            await upload_file.seek(0)
        
        # Set the image parameter with the file-like objects
        params["image"] = image_files
        
        # Process mask if provided
        if mask_file:
            mask_content = await mask_file.read()
            mask_io = io.BytesIO(mask_content)
            mask_io.name = mask_file.filename or "mask.png"
            params["mask"] = mask_io
            
            # Reset file position for future reads if needed
            await mask_file.seek(0)
            
        if size != "auto":
            params["size"] = size
                    
        if output_compression is not None:
            params["output_compression"] = output_compression

        # Generate the edited image
        print(f"Editing images with prompt: {prompt}")
        print(f"Parameters: {params}")
        response = client.images.edit(**params)
        print(f"OpenAI API response: {response}")
                
        return response
    except Exception as e:
        error_message = str(e)
        print(f"Error in edit_image: {error_message}")
        
        # Check for quota exceeded error
        if "quota" in error_message.lower():
            raise HTTPException(
                status_code=429,
                detail="OpenAI API quota exceeded. Please try again later or check your API key."
            )
        
        # Handle other common OpenAI API errors
        if "rate limit" in error_message.lower():
            raise HTTPException(
                status_code=429,
                detail="OpenAI API rate limit reached. Please try again later."
            )
            
        # Generic error
        raise HTTPException(
            status_code=500,
            detail=f"Error editing image: {error_message}"
        )