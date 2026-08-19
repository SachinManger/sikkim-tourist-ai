import re, hashlib
def clean_text(text):
    text=text.replace("\r\n","\n").replace("\r","\n")
    text=re.sub(r"[ \t]+"," ",text)
    text=re.sub(r"\n\s*\n+","\n\n",text)
    return "\n".join(x.strip() for x in text.split("\n") if x.strip()).strip()
def content_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()
