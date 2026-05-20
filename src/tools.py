import json

def extract_chunk_number(frame):
    try:
        fragment = json.loads(frame["payload"].decode())
        return fragment.get("chunk_number")
    except Exception:
        pass