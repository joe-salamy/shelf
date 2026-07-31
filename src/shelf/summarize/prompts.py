"""LLM prompt templates for the summarization pipeline."""

from shelf.summarize.taxonomy import VALID_KINDS, VALID_RELATIONS, format_taxonomy

SECTION_PROMPT = (
    "You are analyzing a section from a textbook. "
    "Given the section content below, return a JSON object with exactly these keys:\n\n"
    '1. "summary": A 3-5 sentence summary of this section\'s content and '
    "significance.\n"
    '2. "key_points": An array of 3-7 bullet-point takeaways (strings, each '
    "under 20 words).\n"
    '3. "entities": An array of objects, each with:\n'
    '   - "name": the named concept, term, equation, method, person, work, '
    "or other important textbook entity\n"
    f'   - "kind": one of {format_taxonomy(VALID_KINDS)}\n'
    '   - "definition": a one-line description (under 25 words)\n'
    '4. "relationships": An array of objects, each with:\n'
    '   - "source": entity name\n'
    f'   - "relation": one of {format_taxonomy(VALID_RELATIONS)}\n'
    '   - "target": entity name\n'
    '5. "prerequisites": An array of concept/term names the reader should '
    "already know.\n"
    '6. "leads_to": An array of concept/term names this section prepares the '
    "reader for.\n\n"
    "Use ONLY the listed entity kinds and relationship labels. "
    "Do not invent narrower labels such as WRITES, AUTHORED, EMPLOYED-BY, "
    "CREATES, or ARGUES-IN. When unsure, use broad labels such as "
    "RELATED-TO, USES, DESCRIBES, CITED-IN, or APPLIES-TO. "
    "If a field has no useful items, return an empty array for that key; "
    "do not omit any of the six keys.\n\n"
    "Return ONLY valid JSON. No markdown fencing, no commentary."
)

CHAPTER_ROLLUP_PROMPT = (
    "You are summarizing a textbook chapter. "
    "Below are summaries of each section in this chapter. "
    "Return a JSON object with exactly one key:\n\n"
    '1. "summary": A 2-4 sentence summary of the entire chapter\'s scope and '
    "significance.\n\n"
    "Return ONLY valid JSON. No markdown fencing, no commentary."
)

BOOK_ROLLUP_PROMPT = (
    "You are summarizing an entire textbook. "
    "Below are summaries of each chapter. "
    "Return a JSON object with exactly one key:\n\n"
    '1. "overview": A single sentence explaining the book\'s subject, scope, '
    "and when an agent should consult it.\n\n"
    "Return ONLY valid JSON. No markdown fencing, no commentary."
)
