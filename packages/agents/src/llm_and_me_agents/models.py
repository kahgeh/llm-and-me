from typing import List, Optional

from pydantic import BaseModel


# --- Agent Specification ---
class AgentSpecification(BaseModel):
    name: str
    description: str
    llm_model_name: str
    base_url: Optional[str] = None
    data_classification: str # Added data_classification, now mandatory
    mcp_servers: List[str]
    instructions: Optional[str] = "You are a software engineering assistant, using en-AU locale. If the user asks for json, return plain json text, nothing more"
# --- End Agent Specification ---
