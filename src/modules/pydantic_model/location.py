from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Dict, Any

class LocationCreate(BaseModel):
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    google_map_link: Optional[str] = None
    phone: Optional[str] = None

class LocationUpdate(BaseModel):
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    google_map_link: Optional[str] = None
    phone: Optional[str] = None

class LocationResponse(LocationCreate):
    id: int
    clinic_id: int
    # created_at: datetime