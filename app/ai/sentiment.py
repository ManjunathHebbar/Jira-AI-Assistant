from app.ai.ollama_client import ask_ollama


ALLOWED_SENTIMENTS = [
    "Calm",
    "Frustrated",
    "Escalating"
]


def analyze_sentiment(title, description, comments):

    with open("app/prompts/sentiment.txt") as file:
        prompt_template = file.read()

    prompt = prompt_template.format(
        title=title,
        description=description,
        comments=comments
    )

    sentiment = ask_ollama(prompt)

    return normalize_sentiment(sentiment)


def normalize_sentiment(value):
    """Keeps Jira output stable even if the LLM returns extra explanation."""

    normalized_value = str(value or "").lower()

    for sentiment in ALLOWED_SENTIMENTS:

        if sentiment.lower() in normalized_value:

            return sentiment

    return "Frustrated"
