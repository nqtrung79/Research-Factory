from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class ResearchLevel(str, Enum):
    UNDERGRADUATE = "Khóa luận tốt nghiệp (Sinh viên)"
    MASTER = "Luận văn (Thạc sĩ)"
    PHD = "Luận án (Tiến sĩ)"
    PROJECT = "Đề tài / Dự án (Nhà nghiên cứu)"

class ProjectBudget(str, Enum):
    LEVEL_1 = "< 500 triệu VNĐ"
    LEVEL_2 = "500 triệu - 2 tỷ VNĐ"
    LEVEL_3 = "2 tỷ - 5 tỷ VNĐ"
    LEVEL_4 = "> 5 tỷ VNĐ"

class ResearchContext(BaseModel):
    level: ResearchLevel
    # For students
    university: Optional[str] = None
    faculty: Optional[str] = None
    department: Optional[str] = None
    supervisor: Optional[str] = None
    
    # For professionals
    institution: Optional[str] = None
    specialty: Optional[str] = None # Lĩnh vực quan tâm
    
    research_site: Optional[str] = None # Địa điểm nghiên cứu
    duration_months: int = 6
    technologies: Optional[str] = None
    
    # PhD & Project specific
    budget_level: Optional[ProjectBudget] = None
    has_international_potential: bool = False
    social_impact_target: Optional[str] = None
    
    # User Input
    interests: str
    existing_title: Optional[str] = None
    research_gap_thoughts: Optional[str] = None
    abstracts_from_uploads: List[str] = Field(default_factory=list)

class LiteratureResult(BaseModel):
    title: str
    authors: List[str]
    year: str
    abstract: str
    source: str
    url: str

class TopicSuggestion(BaseModel):
    title_vi: str
    title_en: str
    reasoning: str
    feasibility: str
    novelty_score: float
    outline: Dict[str, List[str]]
