"""LLM prompt templates for the summarization pipeline."""

SECTION_PROMPT = (
    "You are analyzing a section from a textbook. "
    "Given the section content below, return a JSON object with exactly these keys:\n\n"
    '1. "summary": A 3-5 sentence summary of this section\'s content and significance.\n'
    '2. "key_points": An array of 3-7 bullet-point takeaways (strings, each under 20 words).\n'
    '3. "entities": An array of objects, each with:\n'
    '   - "name": the term, case name, person, or statute\n'
    '   - "kind": one of "term", "case", "person", "statute", "concept"\n'
    '   - "definition": a one-line description (under 25 words)\n'
    '4. "relationships": An array of objects, each with:\n'
    '   - "source": entity name\n'
    '   - "relation": one of "PART-OF", "DEFINES", "CITED-IN", "APPLIES-IN", '
    '"OVERRULES", "ESTABLISHES", "PREREQUISITE-FOR", "RELATED-TO"\n'
    '   - "target": entity name\n'
    '5. "prerequisites": An array of concept/term names the reader should already know.\n'
    '6. "leads_to": An array of concept/term names this section prepares the reader for.\n\n'
    "Return ONLY valid JSON. No markdown fencing, no commentary."
)

CHAPTER_ROLLUP_PROMPT = (
    "You are summarizing a textbook chapter. "
    "Below are summaries of each section in this chapter. "
    "Return a JSON object with exactly one key:\n\n"
    '1. "summary": A 2-4 sentence summary of the entire chapter\'s scope and significance.\n\n'
    "Return ONLY valid JSON. No markdown fencing, no commentary."
)

BOOK_ROLLUP_PROMPT = (
    "You are summarizing an entire textbook. "
    "Below are summaries of each chapter. "
    "Return a JSON object with exactly one key:\n\n"
    '1. "overview": A 3-5 sentence overview of the book\'s scope, structure, '
    "and pedagogical approach.\n\n"
    "Return ONLY valid JSON. No markdown fencing, no commentary."
)
