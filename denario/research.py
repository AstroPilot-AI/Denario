from typing import List, Dict
from pydantic import BaseModel, Field

class Research(BaseModel):
    """Research class."""
    data_description: str = Field(default="", description="The data description of the project")
    """The data description of the project."""
    idea: str = Field(default="", description="The idea of the project")
    """The idea of the project."""
    methodology: str = Field(default="", description="The methodology of the project")
    """The methodology of the project."""
    results: str = Field(default="", description="The results of the project")
    """The results of the project."""
    authorship_confirmation: str = Field(
        default="",
        description="Human confirmation that the generated artifacts were reviewed before paper writing.",
    )
    """Human confirmation that generated artifacts were reviewed before paper writing."""
    plot_paths: List[str] = Field(default_factory=list, description="The plot paths of the project")
    """The plot paths of the project."""
    keywords: Dict[str, str] | list = Field(default_factory=dict, description="The keywords describing the project")
    """The keywords describing the project."""
