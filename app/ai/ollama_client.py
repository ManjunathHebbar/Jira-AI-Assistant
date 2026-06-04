import ollama

from app.config import OLLAMA_MODEL


def ask_ollama(prompt):

    try:

        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            options={
                "num_predict": 1024,  # max tokens to generate
            }
        )

        if hasattr(response, "message"):

            return response.message.content

        return response["message"]["content"]

    except ollama.ResponseError as e:

        print(f"Ollama response error: {e.status_code} — {e.error}")

        return "AI generation failed"

    except Exception as e:

        print("Ollama error:", e)

        return "AI generation failed"
