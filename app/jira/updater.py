import requests
from requests.auth import HTTPBasicAuth

from app.config import (
    API_TOKEN,
    CUSTOM_FIELD_ID,
    EMAIL,
    JIRA_DOMAIN,
    require_settings
)


def update_custom_field(issue_key, content):

    require_settings(
        "JIRA_DOMAIN",
        "EMAIL",
        "API_TOKEN",
        "CUSTOM_FIELD_ID"
    )

    url = f"{JIRA_DOMAIN}/rest/api/3/issue/{issue_key}"

    if isinstance(content, dict):

        field_content = content

    else:

        field_content = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": str(content)[:30000]
                        }
                    ]
                }
            ]
        }

    payload = {
        "fields": {
            CUSTOM_FIELD_ID: field_content
        }
    }

    response = requests.put(
        url,
        auth=HTTPBasicAuth(
            EMAIL,
            API_TOKEN
        ),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=30
    )

    print("UPDATE STATUS:", response.status_code)
    print("UPDATE RESPONSE:", response.text)

    try:

        response.raise_for_status()

    except requests.HTTPError as error:

        raise RuntimeError(
            f"Failed to update Jira AI field for {issue_key}: "
            f"{response.status_code} {response.text}"
        ) from error

    return response
