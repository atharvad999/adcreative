from pydantic import BaseModel
from typing import Optional, List

class AdPrompt(BaseModel):
    prompt: str
    size: str = "1024x1024"
    ad_text: Optional[str] = None

class ShutterstockImage(BaseModel):
    id: str
    description: str
    url: str
    preview_url: str
    categories: List[str] = []

class GeneratedAd(BaseModel):
    filename: str
    url: str
    prompt: str

class ReferenceImagePrompt(BaseModel):
    prompt: str
    size: str = "1024x1024"
    ad_text: Optional[str] = None