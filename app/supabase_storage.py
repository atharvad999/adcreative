import os
import io
import uuid
import base64
from supabase import create_client, Client
from app.config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_BUCKET_NAME
import traceback

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Check if a folder exists and create it if it doesn't
async def ensure_folder_exists(folder):
    """
    Check if a folder exists in the bucket and create it if it doesn't.
    
    Args:
        folder (str): The folder name to check/create
        
    Returns:
        bool: True if the folder exists or was created successfully
    """
    try:
        # Try to list the contents of the folder to see if it exists
        try:
            supabase.storage.from_(SUPABASE_BUCKET_NAME).list(folder)
            print(f"Folder '{folder}' exists in bucket '{SUPABASE_BUCKET_NAME}'")
            return True
        except Exception as e:
            # If we get an error, the folder might not exist
            print(f"Folder '{folder}' might not exist: {str(e)}")
            
            # Create an empty file in the folder to create it
            # This is a common way to create "folders" in object storage
            empty_file = io.BytesIO(b"")
            placeholder_path = f"{folder}/.placeholder"
            
            try:
                supabase.storage.from_(SUPABASE_BUCKET_NAME).upload(
                    placeholder_path,
                    empty_file,
                    file_options={"content-type": "text/plain"}
                )
                print(f"Created folder '{folder}' in bucket '{SUPABASE_BUCKET_NAME}'")
                return True
            except Exception as create_error:
                print(f"Failed to create folder '{folder}': {str(create_error)}")
                return False
    except Exception as e:
        print(f"Error checking/creating folder: {str(e)}")
        traceback.print_exc()
        return False

# Upload an image from bytes
async def upload_image(image_bytes, folder="generated", filename=None, prompt=None, ad_text=None, category=None, size="1024x1024", is_reference=False, title=None):
    """
    Upload an image to Supabase storage and store its metadata in the database.
    
    Args:
        image_bytes (bytes): The image data to upload
        folder (str): The folder within the bucket to store the image
        filename (str, optional): Custom filename. If None, a UUID will be generated
        prompt (str, optional): The prompt used to generate the image
        ad_text (str, optional): Any text included in the ad
        category (str, optional): Image category
        size (str): Image dimensions
        is_reference (bool): Whether this is a reference image
        title (str, optional): Custom title for the image
        
    Returns:
        tuple: (filename, public_url)
    """
    # Generate a unique filename if not provided
    if not filename:
        ext = ".png"  # Default extension
        filename = f"{folder}_{uuid.uuid4()}{ext}"
        
    # Path within the bucket
    storage_path = f"{folder}/{filename}"
    
    try:
        # Print debug info
        print(f"Uploading to Supabase bucket: {SUPABASE_BUCKET_NAME}")
        print(f"Storage path: {storage_path}")
        
        # Ensure the folder exists
        folder_exists = await ensure_folder_exists(folder)
        if not folder_exists:
            print(f"Warning: Could not confirm folder '{folder}' exists")
        
        # Upload the file directly without checking if bucket exists
        # The bucket should already exist in your Supabase project
        response = supabase.storage.from_(SUPABASE_BUCKET_NAME).upload(
            storage_path,
            image_bytes,
            file_options={"content-type": "image/png"}
        )
        
        print(f"Upload response: {response}")
        
        # Get the public URL
        public_url = supabase.storage.from_(SUPABASE_BUCKET_NAME).get_public_url(storage_path)
        
        print(f"Public URL: {public_url}")
        
        # Store metadata in database if we have the DB module imported
        try:
            from app.supabase_db import insert_image_metadata
            
            if public_url:
                await insert_image_metadata(
                    image_id=filename,
                    storage_path=storage_path,
                    public_url=public_url,
                    prompt=prompt,
                    ad_text=ad_text,
                    category=category,
                    size=size,
                    is_reference=is_reference,
                    title=title
                )
                print(f"Stored metadata for {filename} in database")
        except ImportError:
            print("Database module not available, skipping metadata storage")
        except Exception as db_error:
            print(f"Error storing metadata: {str(db_error)}")
            traceback.print_exc()
        
        return filename, public_url
    except Exception as e:
        print(f"Error uploading to Supabase: {str(e)}")
        traceback.print_exc()
        
        # Fall back to local storage for now to ensure functionality
        print("Falling back to local storage")
        return upload_local(image_bytes, folder, filename)

# Upload an image to local storage (fallback)
def upload_local(image_bytes, folder="generated", filename=None):
    """Fallback function to save image locally if Supabase upload fails."""
    try:
        # Generate a unique filename if not provided
        if not filename:
            ext = ".png"  # Default extension
            filename = f"{folder}_{uuid.uuid4()}{ext}"
        
        # Ensure directory exists
        os.makedirs(f"static/{folder}", exist_ok=True)
        
        # Save the image
        with open(f"static/{folder}/{filename}", "wb") as f:
            f.write(image_bytes)
        
        print(f"Saved image locally to static/{folder}/{filename}")
        return filename, f"/static/{folder}/{filename}"
    except Exception as e:
        print(f"Error in local fallback upload: {str(e)}")
        traceback.print_exc()
        raise

# Get list of images from a folder
async def list_images(folder="generated", limit=50):
    """
    List images from a folder in Supabase storage.
    
    Args:
        folder (str): The folder to list images from
        limit (int): Maximum number of images to return
        
    Returns:
        list: List of image objects with filename and url
    """
    try:
        # List files in the folder
        response = supabase.storage.from_(SUPABASE_BUCKET_NAME).list(folder)
        
        print(f"List response for folder '{folder}': {response}")
        
        # Limit the number of results
        files = response[:limit] if len(response) > limit else response
        
        # Get the public URL for each file
        images = []
        for file in files:
            storage_path = f"{folder}/{file['name']}"
            public_url = supabase.storage.from_(SUPABASE_BUCKET_NAME).get_public_url(storage_path)
            
            images.append({
                "filename": file['name'],
                "url": public_url,
                "created_at": file.get('created_at', None)
            })
        
        return images
    except Exception as e:
        print(f"Error listing images from Supabase: {str(e)}")
        traceback.print_exc()
        # Return empty list on error
        return []

# Delete an image
async def delete_image(filename, folder="generated"):
    """
    Delete an image from Supabase storage.
    
    Args:
        filename (str): The filename to delete
        folder (str): The folder containing the image
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Path within the bucket
        storage_path = f"{folder}/{filename}"
        
        # Delete the file
        supabase.storage.from_(SUPABASE_BUCKET_NAME).remove([storage_path])
        
        # Also delete metadata if possible
        try:
            from app.supabase_db import delete_image_metadata
            await delete_image_metadata(filename)
        except ImportError:
            pass  # Ignore if DB module is not available
        except Exception as db_error:
            print(f"Error deleting metadata: {str(db_error)}")
        
        return True
    except Exception as e:
        print(f"Error deleting image from Supabase: {str(e)}")
        traceback.print_exc()
        return False
