from pydantic import BaseModel

from config import root_config


class AgentConfig(BaseModel):
    LLM_MODEL_PROVIDER: str = root_config.agents.llm_model.provider
    LLM_MODEL_API_KEY: str = root_config.agents.llm_model.api_key
    LLM_MODEL_NAME: str = root_config.agents.llm_model.model_name
    LLM_MODEL_TEMPERATURE: float = root_config.agents.llm_model.temperature
    LLM_MODEL_MAX_TOKENS: int = root_config.agents.llm_model.max_tokens
