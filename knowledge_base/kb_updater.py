import re
import time
from pathlib import Path
from knowledge_base.vector_store import get_collection, get_model

# ==========================================
# CONFIG
# ==========================================

# Jira status names that mean "done" — adjust to match your workflow
RESOLVED_STATUSES = {"done", "closed", "resolved", "complete", "completed", "DONE"}

SNAPSHOT_PATH = Path(__file__).resolve().parent / "resolved_snapshots"
NEAR_DUPLICATE_DISTANCE_THRESHOLD = 0.15
MIN_DESCRIPTION_LENGTH = 20
MIN_ROOT_CAUSE_LENGTH = 20
MAX_COMMENTS_LENGTH = 3000


def is_ticket_resolved(fields: dict) -> bool:
    """Returns True if the ticket status means it's closed/done."""

    status_name = (
        fields
        .get("status", {})
        .get("name", "")
        .lower()
        .strip()
    )

    print(f"\nTICKET STATUS: '{status_name}'")

    return status_name in RESOLVED_STATUSES


def save_ticket_to_knowledge_base(
    issue_key: str,
    title: str,
    description: str,
    translated_content: str,
    comments_summary: str,
    comments: str,
    root_cause: str,
    sentiment: str
) -> bool:
    """
    Saves a resolved ticket as a KB entry in ChromaDB.
    Uses the issue_key as the document ID so re-saves are safe (upsert).
    Also writes a .txt snapshot to knowledge_base/resolved_snapshots/ for review.
    Returns True if saved, False if skipped.
    """

    doc_id = f"resolved/{issue_key}"

    # Normalize all incoming text before quality checks and KB formatting.
    title = _clean_text(title)
    description = _clean_text(description)
    translated_content = _clean_text(translated_content)
    comments_summary = _clean_text(comments_summary)
    comments = _clean_text(comments)
    root_cause = _clean_text(root_cause)
    sentiment = _clean_text(sentiment)

    if not _passes_quality_gate(
        issue_key,
        title,
        description,
        translated_content,
        root_cause
    ):

        return False

    # ==========================================
    # BUILD CLEAN KB DOCUMENT
    # ==========================================

    # Store the reusable learning, not a raw ticket dump.
    kb_entry = f"""========================================
TITLE: {_safe_for_kb(title)}
TICKET: {issue_key}
========================================

Problem Pattern:
{_safe_for_kb(translated_content or description)}

Root Cause:
{_safe_for_kb(root_cause)}

Customer Sentiment:
{_safe_for_kb(sentiment)}
"""

    if comments_summary.strip():
        kb_entry += f"""
Resolution Notes:
{_safe_for_kb(comments_summary)}
"""

    if comments.strip():
        # Raw comments are useful for context, but cap them to keep vectors focused.
        kb_entry += f"""
Relevant Comments:
{_safe_for_kb(_truncate_text(comments, MAX_COMMENTS_LENGTH))}
"""

    kb_entry += f"""
Keywords:
{_extract_keywords(title, translated_content or description)}
"""

    # ==========================================
    # SAVE TO CHROMADB
    # ==========================================

    try:

        collection = get_collection()

        model = get_model()

        embedding = model.encode(kb_entry).tolist()

        # Avoid filling the KB with many nearly identical resolved tickets.
        if _is_near_duplicate(
            collection,
            embedding,
            doc_id
        ):

            return False

        collection.upsert(
            documents=[kb_entry],
            embeddings=[embedding],
            ids=[doc_id],
            # Metadata lets future searches/debugging distinguish auto-learned KB.
            metadatas=[
                {
                    "issue_key": issue_key,
                    "source": "resolved_ticket",
                    "sentiment": sentiment[:100],
                    "created_at": int(time.time())
                }
            ]
        )

        print(f"\nKB SAVED: {issue_key} → ChromaDB ({doc_id})")

    except Exception as error:

        print(f"\nKB SAVE FAILED (ChromaDB): {error}")

        return False

    # ==========================================
    # WRITE SNAPSHOT .TXT (optional, for review)
    # ==========================================

    try:

        SNAPSHOT_PATH.mkdir(parents=True, exist_ok=True)

        snapshot_path = SNAPSHOT_PATH / f"{issue_key}.txt"

        with open(snapshot_path, "w", encoding="utf-8") as f:

            f.write(kb_entry)

        print(f"KB SNAPSHOT: Written to resolved_snapshots/{issue_key}.txt")

    except Exception as error:

        # Non-fatal — ChromaDB save already succeeded
        print(f"KB snapshot write failed (non-fatal): {error}")

    return True


def _extract_keywords(title: str, description: str) -> str:
    """
    Simple keyword extraction — pulls meaningful words from title + description.
    For production, replace with a proper NLP approach if needed.
    """

    stop_words = {
        "the", "a", "an", "is", "in", "on", "at", "to", "for",
        "of", "and", "or", "but", "not", "with", "this", "that",
        "it", "was", "are", "be", "by", "from", "as", "has", "have",
        "had", "i", "we", "you", "they", "he", "she", "its"
    }

    words = (title + " " + description).lower().split()

    keywords = list(dict.fromkeys(
        w.strip(".,!?;:()[]") for w in words
        if len(w) > 3 and w not in stop_words
    ))

    return ", ".join(keywords[:15])


def _passes_quality_gate(
    issue_key: str,
    title: str,
    description: str,
    translated_content: str,
    root_cause: str
) -> bool:

    # Skip low-signal tickets before they can pollute future RAG results.
    combined_problem_text = f"{title} {description} {translated_content}".strip()

    if len(combined_problem_text) < MIN_DESCRIPTION_LENGTH:

        print(f"\nKB SKIPPED: {issue_key} has too little problem detail")

        return False

    if len(root_cause.strip()) < MIN_ROOT_CAUSE_LENGTH:

        print(f"\nKB SKIPPED: {issue_key} has too little root-cause detail")

        return False

    lower_text = f"{combined_problem_text} {root_cause}".lower()

    blocked_terms = [
        "ai generation failed",
        "root cause analysis unavailable",
        "root cause analysis timed out",
        "root cause analysis failed",
        "test ticket",
        "dummy ticket"
    ]

    for term in blocked_terms:

        if term in lower_text:

            print(f"\nKB SKIPPED: {issue_key} failed quality gate: {term}")

            return False

    return True


def _is_near_duplicate(collection, embedding, doc_id: str) -> bool:

    try:

        # Compare only against previously learned resolved-ticket entries.
        results = collection.query(
            query_embeddings=[embedding],
            n_results=1,
            where={
                "source": "resolved_ticket"
            }
        )

        ids = results.get("ids", [[]])[0]
        distances = results.get("distances", [[]])[0]

        if not ids or not distances:

            return False

        nearest_id = ids[0]
        nearest_distance = distances[0]

        if nearest_id == doc_id:

            return False

        if nearest_distance <= NEAR_DUPLICATE_DISTANCE_THRESHOLD:

            print(
                "\nKB SKIPPED: near-duplicate resolved ticket found "
                f"({nearest_id}, distance={nearest_distance})"
            )

            return True

    except Exception as error:

        print(f"\nKB duplicate check skipped: {error}")

    return False


def _clean_text(value: str) -> str:

    return str(value or "").strip()


def _truncate_text(value: str, max_length: int) -> str:

    text = _clean_text(value)

    # Long Jira discussions can dominate the embedding and reduce retrieval quality.
    if len(text) <= max_length:

        return text

    return text[:max_length].rstrip() + "\n[truncated]"


def _safe_for_kb(value: str) -> str:

    text = _clean_text(value)

    # Remove common sensitive values before persisting ticket text to the KB.
    text = re.sub(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        "[redacted-email]",
        text
    )

    text = re.sub(
        r"(?i)(api[_-]?token|password|secret|bearer)\s*[:=]\s*\S+",
        r"\1: [redacted]",
        text
    )

    return text
