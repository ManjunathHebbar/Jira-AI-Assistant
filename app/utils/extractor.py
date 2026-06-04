def extract_text(node):

    if isinstance(node, str):

        return node.strip()

    text = ""

    if isinstance(node, dict):

        if node.get("type") == "text":
            text += node.get("text", "") + " "

        for child in node.get("content", []):
            text += extract_text(child)

    elif isinstance(node, list):

        for item in node:
            text += extract_text(item)

    return text.strip()
