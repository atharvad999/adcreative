import sys
import os

# Add the virtual environment site-packages to the path
venv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'venv', 'lib', 'python3.13', 'site-packages')
if venv_path not in sys.path:
    sys.path.insert(0, venv_path)

from openai import OpenAI
from app.config import OPENAI_API_KEY, OPENAI_ORG_ID
import base64
from PIL import Image
import io
import uuid
import os

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY, organization=OPENAI_ORG_ID)

async def generate_ad_image(prompt: str, size: str = "1024x1024", ad_text: str = None):
    """Generate an image using OpenAI's API."""
    # If ad_text is provided, incorporate it into the prompt
    enhanced_prompt = prompt
    if ad_text:
        enhanced_prompt = f"{prompt}. Include the following text in the ad: '{ad_text}'"
    
    # The OpenAI API call doesn't need await - it's not an async function
    response = client.images.generate(
        model="gpt-image-1",
        prompt=enhanced_prompt,
        n=1,
        size=size,
        quality="high"
    )
    
    image_b64 = response.data[0].b64_json
    image_bytes = base64.b64decode(image_b64)
    
    # Generate a unique filename
    filename = f"generated_ad_{uuid.uuid4()}.png"
    
    # Ensure directory exists
    os.makedirs("static/generated", exist_ok=True)
    
    # Save the image
    with open(f"static/generated/{filename}", "wb") as f:
        f.write(image_bytes)
    
    return {
        "filename": filename,
        "url": f"/static/generated/{filename}"
    }

async def analyze_image_content(image_data: bytes):
    """Analyze the content of an image using OpenAI's API."""
    # Convert image data to base64
    image_b64 = base64.b64encode(image_data).decode('utf-8')
    
    # Create a data URL for the image
    image_url = f"data:image/jpeg;base64,{image_b64}"
    
    # Call OpenAI API to analyze the image
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": "what's in this image?"},
                {
                    "type": "input_image",
                    "image_url": image_url,
                },
            ],
        }],
    )
    
    # Extract the analysis text
    analysis = response.output_text
    
    return analysis

async def modify_image(image_data: bytes, modification_prompt: str, size: str = "1024x1024", ad_text: str = None):
    """Modify an uploaded image using OpenAI's API with content analysis."""
    # First analyze the image content
    try:
        image_analysis = await analyze_image_content(image_data)
    except Exception as e:
        print(f"Error analyzing image: {str(e)}")
        image_analysis = "Unable to analyze image content"
    
    # Save the uploaded image temporarily
    temp_input_path = f"static/temp_input_{uuid.uuid4()}.png"
    os.makedirs("static/temp", exist_ok=True)
    
    try:
        # Save the input image
        with open(temp_input_path, "wb") as f:
            f.write(image_data)
        
        # Open and convert the image to ensure it's in a compatible format
        img = Image.open(temp_input_path)
        img_rgb = img.convert("RGB")
        
        # Save as PNG for processing
        img_buffer = io.BytesIO()
        img_rgb.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        
        # Convert to base64
        image_b64 = base64.b64encode(img_buffer.read()).decode('utf-8')
        
        # Enhance the modification prompt with image analysis
        enhanced_prompt = f"Image content: {image_analysis}. Modification request: {modification_prompt}"
        
        # If ad_text is provided, incorporate it into the prompt
        if ad_text:
            enhanced_prompt = f"{enhanced_prompt}. Include the following text in the ad: '{ad_text}'"
        
        # Instead of using edit, use the variation or generation API
        # For now, we'll use the generation API with the prompt
        response = client.images.generate(
            model="gpt-image-1",
            prompt=enhanced_prompt,
            n=1,
            size=size,
            quality="high"
        )
        
        result_image_b64 = response.data[0].b64_json
        result_image_bytes = base64.b64decode(result_image_b64)
        
        # Generate a unique filename
        filename = f"modified_ad_{uuid.uuid4()}.png"
        
        # Ensure directory exists
        os.makedirs("static/generated", exist_ok=True)
        
        # Save the image
        with open(f"static/generated/{filename}", "wb") as f:
            f.write(result_image_bytes)
        
        return {
            "filename": filename,
            "url": f"/static/generated/{filename}",
            "analysis": image_analysis
        }
    except Exception as e:
        raise Exception(f"Error modifying image: {str(e)}")
    finally:
        # Clean up temporary file
        if os.path.exists(temp_input_path):
            os.remove(temp_input_path)

async def generate_with_reference_image(reference_image_data: bytes, prompt: str, size: str = "1024x1024", ad_text: str = None):
    """Generate an image in the style of a reference image using GPT-4o to extract style hints."""
    import base64
    import os
    import uuid
    import io
    from PIL import Image
    from openai import OpenAI
    from app.config import OPENAI_API_KEY

    os.makedirs("static/generated", exist_ok=True)

    # Convert image to base64
    img = Image.open(io.BytesIO(reference_image_data))
    img_rgb = img.convert("RGB")
    img_buffer = io.BytesIO()
    img_rgb.save(img_buffer, format="PNG")
    img_buffer.seek(0)
    image_b64 = base64.b64encode(img_buffer.getvalue()).decode("utf-8")
    image_url = f"data:image/png;base64,{image_b64}"

    # Extract style prompt using GPT-4o vision
    client = OpenAI(api_key=OPENAI_API_KEY)
    try:
        vision_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe the visual style of this ad image in a prompt-friendly sentence. Be concise."},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }]
        )
        style_description = vision_response.choices[0].message.content.strip()
    except Exception as e:
        style_description = ""
        print(f"Vision analysis failed: {e}")

    # Construct enhanced prompt
    enhanced_prompt = f"{prompt}. Style hint: {style_description}"
    if ad_text:
        enhanced_prompt += f". Include the following text: '{ad_text}'"

    # Generate image using gpt-image-1
    response = client.images.generate(
        model="gpt-image-1",
        prompt=enhanced_prompt,
        n=1,
        size=size,
        quality="high"
    )

    result_image_b64 = response.data[0].b64_json
    result_image_bytes = base64.b64decode(result_image_b64)

    filename = f"reference_style_ad_{uuid.uuid4()}.png"
    output_path = f"static/generated/{filename}"
    with open(output_path, "wb") as f:
        f.write(result_image_bytes)

    return {
        "filename": filename,
        "url": f"/static/generated/{filename}",
        "prompt": enhanced_prompt
    }

async def generate_with_multiple_references(reference_images_data: list, prompt: str, size: str = "1024x1024", ad_text: str = None):
    """Generate an image based on multiple reference images and a text prompt using OpenAI's gpt-image-1 API.
    
    Args:
        reference_images_data: List of image data in bytes
        prompt: The prompt describing what to generate
        size: The size of the output image
        ad_text: Optional text to include in the ad
    
    Returns:
        A dictionary containing the filename, URL, and prompt of the generated image
    """
    # Create temporary files for each reference image
    temp_input_paths = []
    image_buffers = []
    
    try:
        # Process each reference image
        for i, img_data in enumerate(reference_images_data):
            # Create a temporary file for this image
            temp_path = f"static/temp_input_{uuid.uuid4()}.png"
            temp_input_paths.append(temp_path)
            os.makedirs("static/temp", exist_ok=True)
            
            # Save the image
            with open(temp_path, "wb") as f:
                f.write(img_data)
            
            # Open and convert the image to ensure it's in a compatible format
            img = Image.open(temp_path)
            img_rgb = img.convert("RGB")
            
            # Save as PNG for processing
            img_buffer = io.BytesIO()
            img_rgb.save(img_buffer, format="PNG")
            img_buffer.seek(0)
            
            # Store the buffer
            image_buffers.append(img_buffer.getvalue())
        
        # Enhance prompt if ad_text is provided
        enhanced_prompt = prompt
        if ad_text:
            enhanced_prompt = f"{prompt}. Include the following text in the ad: '{ad_text}'"
        
        # According to the documentation, for composite images, we can pass multiple images directly to the edit endpoint
        # The OpenAI API expects an array of image files for the 'image' parameter
        response = client.images.edit(
            model="gpt-image-1",
            image=image_buffers,  # Pass all image buffers as an array
            prompt=enhanced_prompt,
            n=1,
            size=size,
            quality="standard"
        )
        
        result_image_b64 = response.data[0].b64_json
        result_image_bytes = base64.b64decode(result_image_b64)
        
        # Generate a unique filename
        filename = f"composite_ad_{uuid.uuid4()}.png"
        
        # Ensure directory exists
        os.makedirs("static/generated", exist_ok=True)
        
        # Save the image
        with open(f"static/generated/{filename}", "wb") as f:
            f.write(result_image_bytes)
        
        return {
            "filename": filename,
            "url": f"/static/generated/{filename}",
            "prompt": enhanced_prompt
        }
    except Exception as e:
        raise Exception(f"Error generating image with multiple references: {str(e)}")
    finally:
        # Clean up temporary files
        for path in temp_input_paths:
            if os.path.exists(path):
                os.remove(path)

async def edit_image_with_mask(image_data: bytes, mask_data: bytes = None, prompt: str = "", size: str = "1024x1024", ad_text: str = None):
    """Edit an image using a mask with OpenAI's gpt-image-1 API.
    
    The mask should be an image with an alpha channel. The transparent areas of the mask
    indicate which parts of the image should be edited, while the opaque areas will be preserved.
    
    Args:
        image_data: The image to edit
        mask_data: Optional mask to specify which areas to edit (transparent = edit, opaque = preserve)
        prompt: The prompt describing the desired changes
        size: The size of the output image
        ad_text: Optional text to include in the ad
    
    Returns:
        A dictionary containing the filename, URL, and prompt of the edited image
    """
    # Save the input image temporarily
    temp_input_path = f"static/temp_input_{uuid.uuid4()}.png"
    temp_mask_path = f"static/temp_mask_{uuid.uuid4()}.png" if mask_data else None
    os.makedirs("static/temp", exist_ok=True)
    
    try:
        # Save the input image
        with open(temp_input_path, "wb") as f:
            f.write(image_data)
        
        # Process the input image
        img = Image.open(temp_input_path)
        img_rgb = img.convert("RGB")
        img_buffer = io.BytesIO()
        img_rgb.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        
        # Process mask if provided
        mask_buffer = None
        if mask_data:
            # Save the mask
            with open(temp_mask_path, "wb") as f:
                f.write(mask_data)
            
            # Process the mask to ensure it has an alpha channel
            mask = Image.open(temp_mask_path)
            
            # If mask is not in RGBA mode, convert it
            if mask.mode != "RGBA":
                # If it's a grayscale image, use it to create an alpha channel
                if mask.mode == "L":
                    mask_rgba = mask.convert("RGBA")
                    # Use the grayscale values as the alpha channel
                    r, g, b, a = mask_rgba.split()
                    mask_rgba.putalpha(mask)
                else:
                    # For other modes, convert to RGBA
                    mask_rgba = mask.convert("RGBA")
            else:
                mask_rgba = mask
            
            # Save the processed mask
            mask_buffer = io.BytesIO()
            mask_rgba.save(mask_buffer, format="PNG")
            mask_buffer.seek(0)
        
        # Enhance prompt if ad_text is provided
        enhanced_prompt = prompt
        if ad_text:
            enhanced_prompt = f"{prompt}. Include the following text in the ad: '{ad_text}'"
        
        # Call OpenAI API to edit the image
        if mask_buffer:
            # According to the documentation, we pass the image and mask as binary data
            response = client.images.edit(
                model="gpt-image-1",
                image=img_buffer.getvalue(),
                mask=mask_buffer.getvalue(),
                prompt=enhanced_prompt,
                n=1,
                size=size,
                quality="standard"
            )
        else:
            # If no mask, just pass the image
            response = client.images.edit(
                model="gpt-image-1",
                image=img_buffer.getvalue(),
                prompt=enhanced_prompt,
                n=1,
                size=size,
                quality="standard"
            )
        
        result_image_b64 = response.data[0].b64_json
        result_image_bytes = base64.b64decode(result_image_b64)
        
        # Generate a unique filename
        filename = f"edited_ad_{uuid.uuid4()}.png"
        
        # Ensure directory exists
        os.makedirs("static/generated", exist_ok=True)
        
        # Save the image
        with open(f"static/generated/{filename}", "wb") as f:
            f.write(result_image_bytes)
        
        return {
            "filename": filename,
            "url": f"/static/generated/{filename}",
            "prompt": enhanced_prompt
        }
    except Exception as e:
        raise Exception(f"Error editing image: {str(e)}")
    finally:
        # Clean up temporary files
        if os.path.exists(temp_input_path):
            os.remove(temp_input_path)
        if temp_mask_path and os.path.exists(temp_mask_path):
            os.remove(temp_mask_path)