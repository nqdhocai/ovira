from langchain.chat_models import init_chat_model

from config.settings import agents_config

_llm_model = None


def get_llm_model():
    global _llm_model
    if _llm_model is None:
        _llm_model = init_chat_model(
            model_provider=agents_config.LLM_MODEL_PROVIDER,
            model=agents_config.LLM_MODEL_NAME,
            api_key=agents_config.LLM_MODEL_API_KEY,
            temperature=agents_config.LLM_MODEL_TEMPERATURE,
            max_tokens=agents_config.LLM_MODEL_MAX_TOKENS,
        )
    return _llm_model
