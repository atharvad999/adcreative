from supabase import create_client, Client
from app.config import SUPABASE_URL, SUPABASE_KEY
from typing import Optional, List, Dict, Any
import uuid

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Table name for image metadata
IMAGE_TABLE = "image_metadata"

async def insert_image_metadata(
    image_id: str,
    storage_path: str,
    public_url: str,
    prompt: str = None,
    ad_text: str = None,
    category: str = None,
    size: str = "1024x1024",
    is_reference: bool = False,
    title: str = None
) -> Dict[str, Any]:
    """
    Insert metadata for an image into the database.
    
    Args:
        image_id: The filename or ID of the image in storage
        storage_path: The full path in Supabase storage
        public_url: The public URL to access the image
        prompt: The prompt used to generate the image
        ad_text: Any text included in the ad
        category: Image category
        size: Image dimensions
        is_reference: Whether this is a reference image
        title: Custom title for the image
        
    Returns:
        The inserted record
    """
    try:
        data = {
            "image_id": image_id,
            "storage_path": storage_path,
            "public_url": public_url,
            "prompt": prompt,
            "ad_text": ad_text,
            "category": category,
            "size": size,
            "is_reference": is_reference,
            "title": title
        }
        
        response = supabase.table(IMAGE_TABLE).insert(data).execute()
        
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error inserting image metadata: {str(e)}")
        return None

async def get_images_by_category(category: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Retrieve images by category.
    
    Args:
        category: The category to filter by
        limit: Maximum number of results to return
        
    Returns:
        List of image metadata records
    """
    try:
        response = supabase.table(IMAGE_TABLE)\
            .select("*")\
            .eq("category", category)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
            
        return response.data
    except Exception as e:
        print(f"Error retrieving images by category: {str(e)}")
        return []

async def get_all_images(limit: int = 50, offset: int = 0, include_reference: bool = True) -> List[Dict[str, Any]]:
    """
    Retrieve all images with pagination.
    
    Args:
        limit: Maximum number of results to return
        offset: Number of records to skip
        include_reference: Whether to include reference images in the results
        
    Returns:
        List of image metadata records
    """
    try:
        query = supabase.table(IMAGE_TABLE)\
            .select("*")\
            .order("created_at", desc=True)
            
        # Filter out reference images if not included
        if not include_reference:
            query = query.eq("is_reference", False)
            
        response = query.range(offset, offset + limit - 1).execute()
            
        return response.data
    except Exception as e:
        print(f"Error retrieving all images: {str(e)}")
        return []

async def search_images(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Search for images by prompt or ad_text using text search.
    
    Args:
        query: The search term
        limit: Maximum number of results to return
        
    Returns:
        List of matching image metadata records
    """
    try:
        # Using ilike for basic text matching
        response = supabase.table(IMAGE_TABLE)\
            .select("*")\
            .or_(f"prompt.ilike.%{query}%,ad_text.ilike.%{query}%")\
            .limit(limit)\
            .execute()
            
        return response.data
    except Exception as e:
        print(f"Error searching images: {str(e)}")
        return []

async def delete_image_metadata(image_id: str) -> bool:
    """
    Delete image metadata for a specific image.
    
    Args:
        image_id: The image ID to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        response = supabase.table(IMAGE_TABLE)\
            .delete()\
            .eq("image_id", image_id)\
            .execute()
            
        return len(response.data) > 0
    except Exception as e:
        print(f"Error deleting image metadata: {str(e)}")
        return False
