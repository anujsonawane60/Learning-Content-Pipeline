"""OpenAI-powered JSON enrichment for Stage 2 (used with --ai flag)."""

import json
import os
import time

import click


def _get_client():
    """Lazy-init OpenAI client; fails fast if key is missing."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable is not set. "
            "Add it to .env or export it before using --ai."
        )
    from openai import OpenAI

    return OpenAI(api_key=api_key)


SYSTEM_PROMPT = """\
You are a course content structuring assistant. Given raw chapter text from a \
course document, restructure it into the fields below. ONLY use content from the \
provided text — do NOT invent or fabricate any new information.

Return valid JSON with these fields:
{
  "description": "A concise 1-2 sentence chapter description",
  "overview": ["paragraph1", "paragraph2"],
  "instructions": ["step1", "step2"],
  "prompt_text": ["any prompts or questions found in the text"],
  "key_learnings": ["key takeaway 1", "key takeaway 2"]
}

Rules:
- overview: main explanatory paragraphs (the bulk of the content)
- instructions: any step-by-step instructions, how-to items, or action items
- prompt_text: any questions, prompts, or exercises for the learner
- key_learnings: main takeaways; extract from content, do not invent
- description: summarize what this chapter covers in 1-2 sentences
- If a field has no matching content, return an empty array []
"""


def enrich_chapter(chapter_title: str, chapter_body: str, module_title: str) -> dict:
    """Send chapter text to OpenAI and return structured content fields."""
    client = _get_client()

    user_msg = (
        f"Module: {module_title}\n"
        f"Chapter: {chapter_title}\n\n"
        f"--- Chapter Content ---\n{chapter_body}"
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    return json.loads(raw)


def enrich_chapters(chapters: list[dict], module_title: str) -> list[dict]:
    """Enrich a list of chapter dicts in-place using OpenAI, return the list."""
    for ch in chapters:
        # Build chapter body from overview paragraphs
        overview = ch["content_data"]["languages"]["en"].get("overview", [])
        chapter_body = "\n\n".join(overview)

        if not chapter_body.strip():
            continue

        try:
            enriched = enrich_chapter(ch["title"], chapter_body, module_title)

            en = ch["content_data"]["languages"]["en"]
            if enriched.get("overview"):
                en["overview"] = enriched["overview"]
            if enriched.get("instructions"):
                en["instructions"] = enriched["instructions"]
            if enriched.get("prompt_text"):
                en["prompt_text"] = enriched["prompt_text"]
            if enriched.get("key_learnings"):
                en["key_learnings"] = enriched["key_learnings"]
            if enriched.get("description"):
                ch["description"] = enriched["description"]

            ch["content_data"]["metadata"]["ai_generated"] = True
            ch["content_data"]["metadata"]["last_ai_update"] = (
                time.strftime("%Y-%m-%dT%H:%M:%S")
            )

            click.echo(f"    AI enriched: {ch['title']}")
        except Exception as e:
            click.echo(f"    Warning: AI enrichment failed for '{ch['title']}': {e}")

        # Rate limit: small delay between calls
        time.sleep(0.5)

    return chapters
