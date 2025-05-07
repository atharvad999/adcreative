import httpx
from app.config import SHUTTERSTOCK_API_KEY
from typing import List, Dict, Any

BASE_URL = "https://api.shutterstock.com/v2"

async def search_images_by_category(category: str, per_page: int = 20):
    """Search for images in a specific category."""
    headers = {
        "Authorization": f"Bearer {SHUTTERSTOCK_API_KEY}"
    }
    params = {
        "query": category,
        "per_page": per_page,
        "sort": "popular",
        "view": "full"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/images/search", headers=headers, params=params)
        data = response.json()
        
        # Extract relevant image information
        processed_images = []
        if "data" in data:
            for image in data["data"]:
                image_info = {
                    "id": image["id"],
                    "description": image.get("description", ""),
                    "preview_url": image.get("assets", {}).get("preview", {}).get("url", ""),
                    "thumbnail_url": image.get("assets", {}).get("large_thumb", {}).get("url", ""),
                    "categories": [cat.get("name") for cat in image.get("categories", [])]
                }
                processed_images.append(image_info)
        
        return processed_images

async def get_similar_images(image_url: str):
    """Find similar images using computer vision API."""
    # This would require uploading the image first, then using the asset_id
    # to search for similar images. For simplicity, we'll implement this later.
    pass

async def get_collections(per_page: int = 20):
    """Get a list of featured collections from Shutterstock."""
    if not SHUTTERSTOCK_API_KEY:
        print("Warning: SHUTTERSTOCK_API_KEY is not set")
        # Return mock data for development if API key is missing
        return {
            "data": [
                {
                    "id": "mock-collection-1",
                    "name": "Travel Photography",
                    "description": "Beautiful travel destinations",
                    "total_item_count": 25
                },
                {
                    "id": "mock-collection-2",
                    "name": "Business \u0026 Finance",
                    "description": "Professional business imagery",
                    "total_item_count": 18
                },
                {
                    "id": "mock-collection-3",
                    "name": "Food \u0026 Cuisine",
                    "description": "Delicious food photography",
                    "total_item_count": 30
                }
            ]
        }
    
    # Check if API key starts with 'v2/' and format headers accordingly
    if SHUTTERSTOCK_API_KEY.startswith('v2/'):
        # For v2 format API keys, use the key directly without 'Bearer'
        headers = {
            "Authorization": SHUTTERSTOCK_API_KEY
        }
    else:
        # For standard API keys, use Bearer format
        headers = {
            "Authorization": f"Bearer {SHUTTERSTOCK_API_KEY}"
        }
    
    params = {
        "per_page": per_page
    }
    
    try:
        # Try the featured collections endpoint first
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{BASE_URL}/images/collections/featured", headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                print(f"Shutterstock collections API response: {data}")
                return data
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    # If featured endpoint fails, try the standard collections endpoint
                    print("Featured collections endpoint not found, trying standard collections endpoint")
                    response = await client.get(f"{BASE_URL}/images/collections", headers=headers, params=params)
                    response.raise_for_status()
                    data = response.json()
                    print(f"Shutterstock standard collections API response: {data}")
                    return data
                else:
                    raise e
    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
        # Return mock data on error
        return {
            "data": [
                {
                    "id": "error-collection-1",
                    "name": "API Error - Using Mock Data",
                    "description": f"Error: Client error '404 Not Found' for url '{e.request.url}'. For more information check: https://developers.shutterstock.com/api/v2",
                    "total_item_count": 5
                }
            ]
        }
    except Exception as e:
        print(f"Error fetching collections: {str(e)}")
        # Return mock data on error
        return {
            "data": [
                {
                    "id": "error-collection-1",
                    "name": "Error - Using Mock Data",
                    "description": f"Error: {str(e)}",
                    "total_item_count": 5
                }
            ]
        }

async def get_collection_items(collection_id: str, per_page: int = 20):
    """Get images from a specific collection."""
    headers = {
        "Authorization": f"Bearer {SHUTTERSTOCK_API_KEY}"
    }
    params = {
        "per_page": per_page
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/images/collections/featured/{collection_id}/items", headers=headers, params=params)
        data = response.json()
        
        # Extract relevant image information
        processed_images = []
        if "data" in data:
            for image in data["data"]:
                image_info = {
                    "id": image["id"],
                    "description": image.get("description", ""),
                    "preview_url": image.get("assets", {}).get("preview", {}).get("url", ""),
                    "thumbnail_url": image.get("assets", {}).get("large_thumb", {}).get("url", ""),
                    "categories": [cat.get("name") for cat in image.get("categories", [])]
                }
                processed_images.append(image_info)
        
        return processed_images