import re

def sanitize_filename(text: str) -> str:
    # Removes special characters and replaces spaces with underscores
    # Professional comment: Ensures file system compatibility across OS.
    clean_text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    return re.sub(r'[-\s]+', '_', clean_text)