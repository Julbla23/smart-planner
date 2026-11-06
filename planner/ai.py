import json
import os
from groq import Groq

def rozbij_cel_na_kroki(cel: str) -> list[str]:
    if not os.getenv("GROQ_API_KEY"):
        return []
    client = Groq()
    prompt = (
        "Rozbij cel na 5-7 konkretnych małych zadań do wpisania do planera. "
        "Każde zadanie zaczyna się od czasownika i zajmuje maks. 2 godziny. "
        "Odpowiedź WYŁĄCZNIE obiektem JSON w formacie {'kroki': ['...', '...']}.\n\n"
        f"Cel: {cel}"
    )
    try:
        odp = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_completion_tokens=2000,
            reasoning_effort="low",
        )
        dane = json.loads(odp.choices[0].message.content)
        return [str(k) for k in dane.get("kroki", [])][:7]
    except Exception as e:
        print("Błąd AI:", e)
        return []