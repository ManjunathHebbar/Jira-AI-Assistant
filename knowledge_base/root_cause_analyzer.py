import requests
from app.config import OLLAMA_MODEL, OLLAMA_URL
from knowledge_base.vector_store import search_knowledge_base

# ==========================================
# CONFIG
# ==========================================

KB_SIMILARITY_THRESHOLD = 3  # min chars to treat KB result as valid


def analyze_root_cause(title: str, description: str, translated_content: str = "") -> str:
    """
    1. Search the knowledge base for similar past tickets.
    2. If relevant results found → summarize root cause from KB context.
    3. If KB is empty or irrelevant → ask Ollama directly.
    """

    search_text = translated_content.strip() or f"{title} {description}".strip()

    query = search_text

    # ==========================================
    # KNOWLEDGE BASE LOOKUP
    # ==========================================

    kb_context = search_knowledge_base(query)

    # Prefer grounded root-cause analysis when similar resolved tickets exist.
    if kb_context and len(kb_context.strip()) > KB_SIMILARITY_THRESHOLD:

        print("\nROOT CAUSE: Found relevant KB entries — using KB context")

        prompt = f"""You are a Jira support engineer.
Based on the following knowledge base entries from similar past resolved tickets, identify the most likely root cause for the current issue.

=== KNOWLEDGE BASE (Past Resolved Tickets) ===
{kb_context}

=== CURRENT ISSUE ===
Title: {title}
Description: {description}
English Context: {translated_content or "Not available"}

Instructions:
- Identify the most likely root cause based on the KB entries above.
- Be concise and specific.
- If the KB entries are not relevant, say "No matching root cause found in knowledge base."
- Do NOT make up causes that aren't supported by the KB.

Root Cause:"""

        source_label = "📚 Source: Knowledge Base (Past Resolved Tickets)"

    else:

        print("\nROOT CAUSE: KB empty or no match — falling back to Ollama")

        # Fall back to model-only reasoning when KB has no usable match.
        prompt = f"""You are a Jira support engineer analyzing a bug report.

=== CURRENT ISSUE ===
Title: {title}
Description: {description}
English Context: {translated_content or "Not available"}

Based on your technical knowledge, what is the most likely root cause of this issue?
Be concise and specific. Provide 2-3 possible causes ranked by likelihood.

Root Cause:"""

        source_label = "🤖 Source: AI Analysis (No matching KB entry found)"

    # ==========================================
    # OLLAMA CALL
    # ==========================================

    root_cause_text = _call_ollama(prompt)

    return f"{root_cause_text}\n\n{source_label}"


def _call_ollama(prompt: str) -> str:

    try:

        # Use the same Ollama endpoint/model configured for the rest of the app.
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )

        response.raise_for_status()

        return response.json().get("response", "").strip()

    except requests.exceptions.ConnectionError:

        return "⚠️ Root cause analysis unavailable — Ollama service not reachable."

    except requests.exceptions.Timeout:

        return "⚠️ Root cause analysis timed out."

    except Exception as error:

        print(f"Ollama error: {error}")

        return f"⚠️ Root cause analysis failed: {str(error)}"
