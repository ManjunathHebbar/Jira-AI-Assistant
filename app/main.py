from fastapi import FastAPI, Request
from starlette.concurrency import run_in_threadpool
import time

from app.jira.fetcher import fetch_issue_by_key
from app.jira.updater import update_custom_field

from app.ai.translator import translate_content
from app.ai.summarizer import generate_ai_summary
from app.ai.summarizer import summarize_comments
from app.ai.sentiment import analyze_sentiment
from app.ai.language_detector import detect_language

from app.utils.extractor import extract_text
from app.utils.hash_util import generate_content_hash
from app.utils.logger import logger

from app.cache.sqlite_cache import (
    claim_ticket_for_processing,
    clear_processing_ticket,
    initialize_database,
    save_processed_ticket
)

from app.jira.adf_builder import (
    build_ai_summary_adf,
    build_failed_adf,
    build_processing_adf
)

from app.config import CUSTOM_FIELD_ID

from knowledge_base.root_cause_analyzer import analyze_root_cause
from knowledge_base.kb_updater import is_ticket_resolved, save_ticket_to_knowledge_base

app = FastAPI()

initialize_database()

SUPPORTED_NATIVE_WEBHOOK_EVENTS = {
    "jira:issue_created",
    "jira:issue_updated",
    "issue_created",
    "issue_updated",
    "comment_created",
    "comment_updated"
}

DONE_STATUS_NAMES = {
    "done",
    "closed",
    "resolved",
    "complete",
    "completed"
}


@app.get("/")
def home():

    return {
        "status": "running"
    }


async def update_processing_state(
    issue_key,
    current_step,
    completed_steps=None
):

    await run_in_threadpool(
        update_custom_field,
        issue_key,
        build_processing_adf(
            current_step=current_step,
            completed_steps=completed_steps
        )
    )


def get_issue_key_from_webhook_payload(payload):
    """
    Supports both Jira native webhooks and Jira Automation custom payloads.
    Native webhooks include a full `issue` object; Automation may send only
    {"issue": {"key": "MS-13"}}.
    """

    if not isinstance(payload, dict):

        return None

    issue_data = payload.get("issue")

    if isinstance(issue_data, dict) and issue_data.get("key"):

        return issue_data.get("key")

    issue_key = payload.get("issueKey") or payload.get("issue_key")

    if issue_key:

        return issue_key

    return None


def should_handle_webhook_event(payload):
    """
    Jira native webhooks include `webhookEvent`. Automation payloads usually do
    not, so payloads without this field are treated as supported.
    """

    webhook_event = payload.get("webhookEvent")

    if not webhook_event:

        return True

    return webhook_event in SUPPORTED_NATIVE_WEBHOOK_EVENTS


def get_changed_fields(payload):
    """Returns changed Jira field names/ids from native webhook changelog."""

    changelog = payload.get("changelog", {})

    items = changelog.get("items", [])

    changed_fields = []

    for item in items:

        changed_fields.append(
            item.get("fieldId") or item.get("field") or "unknown"
        )

    return changed_fields


def is_ai_field_only_webhook(payload):
    """
    Native Jira webhooks include changelog items. When our app updates only the
    AI custom field, Jira sends another webhook; ignore that self-trigger early.
    """

    if not CUSTOM_FIELD_ID:

        return False

    changelog = payload.get("changelog", {})

    items = changelog.get("items", [])

    if not items:

        return False

    return all(
        item.get("fieldId") == CUSTOM_FIELD_ID
        for item in items
    )


def is_status_changed_to_done(payload):
    """
    Returns True only when Jira changelog shows the status field moved to a
    Done-like status. Custom payloads without changelog are allowed for manual
    testing or Jira Automation rules that already filter the transition.
    """

    changelog = payload.get("changelog", {})

    items = changelog.get("items", [])

    if not items:

        return True

    for item in items:

        field_name = str(item.get("field") or "").lower()
        field_id = str(item.get("fieldId") or "").lower()

        if field_name != "status" and field_id != "status":

            continue

        new_status = str(
            item.get("toString") or item.get("to") or ""
        ).lower().strip()

        if new_status in DONE_STATUS_NAMES:

            return True

    return False


@app.post("/jira-webhook")
async def jira_webhook(request: Request):

    start_time = time.time()

    issue_key = None

    input_hash = None

    try:

        raw_body = await request.body()

        print("\n" + "=" * 100)
        print("WEBHOOK RECEIVED")

        if not raw_body:

            print("Empty webhook body received")

            return {
                "status": "ignored",
                "reason": "empty body"
            }

        try:

            payload = await request.json()

        except Exception:

            print("Invalid JSON payload")
            print(raw_body.decode("utf-8"))

            return {
                "status": "ignored",
                "reason": "invalid json"
            }

        print("WEBHOOK EVENT:", payload.get("webhookEvent", "automation/custom"))
        print("ISSUE KEY:", get_issue_key_from_webhook_payload(payload))
        print("CHANGED FIELDS:", get_changed_fields(payload) or "not provided")

        if is_ai_field_only_webhook(payload):

            print("\nSKIPPING - AI FIELD SELF-UPDATE")

            return {
                "status": "ignored",
                "reason": "ai field self-update"
            }

        if not should_handle_webhook_event(payload):

            return {
                "status": "ignored",
                "reason": "unsupported webhook event",
                "event": payload.get("webhookEvent")
            }

        issue_key = get_issue_key_from_webhook_payload(payload)

        if not issue_key:

            return {
                "status": "ignored",
                "error": "No issue key found in payload"
            }

        print(f"\nPROCESSING ISSUE: {issue_key}")

        logger.info(
            f"Webhook received for {issue_key}"
        )

        issue = await run_in_threadpool(
            fetch_issue_by_key,
            issue_key
        )

        fields = issue.get("fields", {})

        title = fields.get("summary", "")

        description = extract_text(
            fields.get("description", {})
        )

        comments = (
            fields
            .get("comment", {})
            .get("comments", [])
        )

        all_comments = []

        for comment in comments:

            comment_text = extract_text(
                comment.get("body", {})
            )

            if comment_text.strip():

                all_comments.append(comment_text)

        combined_comments = "\n".join(all_comments)

        issue_status = (
            fields
            .get("status", {})
            .get("name", "")
        )

        input_content = f"""
{title}
{description}
{combined_comments}
{issue_status}
"""

        input_hash = generate_content_hash(
            input_content
        )

        print("\nINPUT HASH:", input_hash)

        should_process = await run_in_threadpool(
            claim_ticket_for_processing,
            issue_key,
            input_hash
        )

        if not should_process:

            print("\nSKIPPING - INPUT UNCHANGED")

            return {
                "status": "skipped",
                "issue": issue_key
            }

        await update_processing_state(
            issue_key,
            "Detecting language and preparing translation",
            [
                "Webhook received",
                "Fetched Jira issue details",
                "Checked duplicate processing cache"
            ]
        )

        detected_language = detect_language(
            f"{title} {description}"
        )

        translated_content = await run_in_threadpool(
            translate_content,
            title,
            description
        )

        await update_processing_state(
            issue_key,
            "Generating AI summary with knowledge base context",
            [
                "Webhook received",
                "Fetched Jira issue details",
                "Checked duplicate processing cache",
                "Detected language and translated content"
            ]
        )

        comments_summary = ""

        if combined_comments.strip():

            comments_summary = await run_in_threadpool(
                summarize_comments,
                combined_comments
            )

        ai_summary = await run_in_threadpool(
            generate_ai_summary,
            title,
            description,
            combined_comments
        )

        sentiment = await run_in_threadpool(
            analyze_sentiment,
            title,
            description,
            combined_comments
        )

        await update_processing_state(
            issue_key,
            "Analyzing root cause",
            [
                "Webhook received",
                "Fetched Jira issue details",
                "Checked duplicate processing cache",
                "Detected language and translated content",
                "Generated AI summary and sentiment"
            ]
        )

        root_cause = await run_in_threadpool(
            analyze_root_cause,
            title,
            description,
            translated_content
        )

        final_adf = build_ai_summary_adf(
            ai_summary=ai_summary,
            root_cause=root_cause,
            translated_content=translated_content,
            sentiment=sentiment,
            comments_summary=comments_summary,
            detected_language=detected_language
        )

        print("\nUPDATING JIRA AI FIELD...")

        await run_in_threadpool(
            update_custom_field,
            issue_key,
            final_adf
        )

        ticket_resolved = is_ticket_resolved(fields)

        kb_saved = False

        status_changed_to_done = is_status_changed_to_done(payload)

        if ticket_resolved and status_changed_to_done:

            print(f"\nTICKET IS RESOLVED - saving to knowledge base...")

            # Resolved tickets become future KB examples after cleanup/quality checks.
            kb_saved = await run_in_threadpool(
                save_ticket_to_knowledge_base,
                issue_key,
                title,
                description,
                translated_content,
                comments_summary,
                combined_comments,
                root_cause,
                sentiment
            )

        elif ticket_resolved:

            print(
                "\nTICKET RESOLVED BUT STATUS DID NOT JUST CHANGE TO DONE - skipping KB save"
            )

        else:

            print(
                "\nTICKET NOT RESOLVED - skipping KB save"
            )

        if ticket_resolved and status_changed_to_done and not kb_saved:

            await run_in_threadpool(
                clear_processing_ticket,
                issue_key,
                input_hash
            )

            return {
                "status": "failed",
                "issue": issue_key,
                "error": "Ticket resolved but knowledge base save failed"
            }

        await run_in_threadpool(
            save_processed_ticket,
            issue_key,
            input_hash
        )

        total_time = round(
            time.time() - start_time,
            2
        )

        print(f"\nPROCESSING TIME: {total_time} sec")

        logger.info(
            f"Successfully processed {issue_key}"
        )

        return {
            "status": "success",
            "issue": issue_key,
            "processing_time": total_time,
            "kb_saved": kb_saved
        }

    except Exception as error:

        if issue_key:

            try:

                await run_in_threadpool(
                    update_custom_field,
                    issue_key,
                    build_failed_adf(error)
                )

            except Exception as update_error:

                logger.error(str(update_error))

        if issue_key and input_hash:

            await run_in_threadpool(
                clear_processing_ticket,
                issue_key,
                input_hash
            )

        logger.error(str(error))

        print("\nERROR:")
        print(str(error))

        return {
            "status": "failed",
            "error": str(error)
        }
