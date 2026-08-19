from typing import Optional
from pydantic import BaseModel, ConfigDict

class Source(BaseModel):
    model_config=ConfigDict(extra="allow")
    source_name:str
    source_url:str
    page_title:str=""
    page_url:str
    source_type:str="website"
    trust_level:str="medium"
    collected_date:str
    last_verified:Optional[str]=None

class TourismRecord(BaseModel):
    model_config=ConfigDict(extra="allow")
    id:str
    name:str
    aliases:list[str]=[]
    category:str
    region:Optional[str]=None
    district:Optional[str]=None
    description:Optional[str]=None
    altitude:Optional[str]=None
    best_time:list[str]=[]
    activities:list[str]=[]
    nearby_places:list[str]=[]
    how_to_reach:Optional[str]=None
    permit_required:Optional[bool]=None
    safety_information:list[str]=[]
    travel_tips:list[str]=[]
    contact:Optional[str]=None
    website:Optional[str]=None
    price_range:Optional[str]=None
    duration:Optional[str]=None
    source:Optional[Source]=None
    confidence:str="medium"
    dynamic_information:bool=False
    status:str="pending_review"

class ExtractionEnvelope(BaseModel):
    records:list[TourismRecord]=[]
