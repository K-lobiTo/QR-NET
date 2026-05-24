import json

def extract_chunk_number(frame):
    try:
        fragment = json.loads(frame["payload"].decode())
        return fragment.get("chunk_number")
    except Exception:
        pass

def sanitize_post_content(content):
    end_command_indx = content.find("[END]")
    if end_command_indx != -1:
        content = content[:end_command_indx+5]
    post_content = content.replace(f"\n", " ")
    return post_content