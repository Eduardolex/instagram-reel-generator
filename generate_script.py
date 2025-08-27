import os
from dotenv import load_dotenv

load_dotenv()

def generate_script(topic: str) -> str:
    """
    Generate a ~35-second Instagram Reel script using an LLM (OpenAI v1 client).
    Env:
      LLM_API_KEY  = your API key
      LLM_MODEL    = gpt-4o-mini (default) | gpt-4o | other compatible model
      LLM_API_BASE = (optional) override base URL, e.g. https://api.openai.com/v1
    """
    api_key = os.getenv("LLM_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing LLM_API_KEY in .env")

    model = os.getenv("LLM_MODEL", "gpt-4o-mini").strip()
    base_url = os.getenv("LLM_API_BASE", "").strip() or "https://api.openai.com/v1"

    # OpenAI Python SDK v1.x
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url)

    prompt = f"""Create a 35-second Instagram Reel script about: {topic}

Requirements:
- Conversational and engaging
- ~90–110 words (~35 seconds at normal pace)
- Start with a strong hook
- Include 2–3 practical, actionable tips
- End with a clear CTA: “Try the Neraptic demo—link in bio”
- Natural spoken style (contractions, short sentences)
- Return ONLY the spoken text (no labels or directions)
"""

    try:
        resp = client.chat.completions.create(
            model=model,                     # e.g., gpt-4o-mini
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=220,                  # enough for ~110 words
        )
        content = resp.choices[0].message.content
        if not content or not content.strip():
            raise RuntimeError("Empty response from model.")
        return content.strip()
    except Exception as e:
        # Bubble up a clear message (helps when model/URL/key is wrong)
        raise RuntimeError(f"Failed to generate script: {e}") from e

if __name__ == "__main__":
    print(generate_script("How to model the word 'Drink' during daily routines"))
