import logging
from groq import Groq
from config import GROQ_API_KEY, MODEL_NAME

groq_client = Groq(api_key=GROQ_API_KEY)

def translate_vi2en(text: str, model: str = MODEL_NAME) -> str:
    prompt = (
        "Bạn là một dịch giả chuyên nghiệp cho các giấy tờ của bộ phận 1 cửa tại trung tâm hành chỉnh công, dịch chính xác và tự nhiên..."
        f"\n\n{text.strip()}\n\nEnglish:"
    )
    try:
        resp = groq_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
    except Exception as e:
        logging.warning("%s failed (%s), fallback to 8B", model, e)
        resp = groq_client.chat.completions.create(
            model="openai/gpt-oss-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
    return resp.choices[0].message.content.strip()
