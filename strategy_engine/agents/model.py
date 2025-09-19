from config.settings import agents_config
from langchain.chat_models import init_chat_model

_llm_model = None


def get_llm_model():
    global _llm_model
    if _llm_model is None:
        _llm_model = init_chat_model(
            model=agents_config.LLM_MODEL_NAME,
            model_provider=agents_config.LLM_MODEL_PROVIDER,
            api_key=agents_config.LLM_MODEL_API_KEY,
            temperature=agents_config.LLM_MODEL_TEMPERATURE,
            max_tokens=agents_config.LLM_MODEL_MAX_TOKENS,
            api_version=agents_config.LLM_MODEL_API_VERSION,
            base_url=agents_config.LLM_MODEL_BASE_URL,
        )
    return _llm_model
