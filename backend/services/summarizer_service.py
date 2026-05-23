def summarize_text(text):

    if not text:
        return "No content available"

    sentences = text.split(".")

    short_summary = ".".join(sentences[:2])

    return short_summary