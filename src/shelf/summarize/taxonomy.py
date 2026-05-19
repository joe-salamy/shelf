"""Shared taxonomy for generated textbook entity graphs."""

from __future__ import annotations

ENTITY_KIND_LABELS: dict[str, str] = {
    "concept": "Concepts",
    "term": "Terms",
    "equation": "Equations",
    "formula": "Formulas",
    "distribution": "Distributions",
    "law": "Laws",
    "theorem": "Theorems",
    "principle": "Principles",
    "method": "Methods",
    "model": "Models",
    "process": "Processes",
    "system": "Systems",
    "structure": "Structures",
    "material": "Materials",
    "organism": "Organisms",
    "anatomy": "Anatomy",
    "condition": "Conditions",
    "treatment": "Treatments",
    "drug": "Drugs",
    "symptom": "Symptoms",
    "molecule": "Molecules",
    "protein": "Proteins",
    "gene": "Genes",
    "constant": "Constants",
    "variable": "Variables",
    "unit": "Units",
    "data_set": "Data Sets",
    "particle": "Particles",
    "field": "Fields",
    "case": "Cases",
    "person": "People",
    "place": "Places",
    "event": "Events",
    "statute": "Statutes",
    "work": "Works",
}

VALID_KINDS = frozenset(ENTITY_KIND_LABELS)

VALID_RELATIONS = frozenset(
    {
        "PART-OF",
        "HAS",
        "CONTAINS",
        "DEFINES",
        "DESCRIBES",
        "REPRESENTS",
        "EQUALS",
        "APPROXIMATES",
        "GENERALIZES",
        "SPECIAL-CASE-OF",
        "CAUSES",
        "ENABLES",
        "INHIBITS",
        "PRODUCES",
        "REQUIRES",
        "DEPENDS-ON",
        "DERIVES",
        "DERIVED-FROM",
        "CALCULATES",
        "CALCULATED-FROM",
        "MEASURES",
        "PREDICTS",
        "EXPLAINS",
        "USES",
        "APPLIES-IN",
        "EXAMPLE-OF",
        "PREREQUISITE-FOR",
        "LEADS-TO",
        "RELATED-TO",
        "CITED-IN",
        "ESTABLISHES",
        "OVERRULES",
        "CONTRASTS-WITH",
        "LIMITED-BY",
        "APPLIES-TO",
        "AVERAGES",
        "CALCULATED-IN",
        "CALCULATED-TO",
        "CALCULATED-UNDER",
        "CAUSED-BY",
        "CHANGES",
        "CONSTANT-UNDER",
        "CONSTRAINT-ON",
        "DECAYS",
        "DECOMPOSES",
        "DEFINE-PATH-TO",
        "DERIVES-APPLYING",
        "DIAGONALIZES",
        "DISTRIBUTED-TO",
        "DIVIDES-IN",
        "DRIVES",
        "EXEMPLIFIES",
        "EXPLORES",
        "FUNCTION-OF",
        "HAS-DEGREES-OF-FREEDOM",
        "HAS-VIBRATIONAL-DOF",
        "INCLUDES",
        "INCREASES-UNDER",
        "INTEGRATED-OVER",
        "INTEGRATES-TO",
        "IS-AN-AUTOMORPHISM-OF",
        "IS-EIGENSTATE-OF",
        "LEADS-TO",
        "MANAGES",
        "MULTIPLICATIVE-FOR",
        "OBSOLETE",
        "OVERLAPS",
        "PARAMETER-FOR",
        "PRECEDES",
        "PREPARES",
        "PRODUCED-THROUGH",
        "RELEVANT-FOR",
        "RESTRICTED-BY",
        "RESULTS-FROM",
        "SOLVES",
        "SUBSET-OF",
        "USED-IN",
        "USES-IN",
    }
)

RELATION_ALIASES = {
    "CITES": "CITED-IN",
    "CITES-IN": "CITED-IN",
    "CALCULATED-BY": "CALCULATES",
    "DERIVED-FROM": "DERIVED-FROM",
    "RELATES-TO": "RELATED-TO",
    "EXPLAIN": "EXPLAINS",
    "OVERRULED-FROM": "OVERRULES",
}


def format_taxonomy(values: frozenset[str]) -> str:
    """Format taxonomy values for inclusion in LLM prompts."""
    return ", ".join(f'"{value}"' for value in sorted(values))


def normalize_entity_kind(kind: object) -> str:
    """Normalize LLM-provided entity kind labels."""
    if not isinstance(kind, str) or not kind.strip():
        return "concept"
    return kind.strip().lower().replace(" ", "_").replace("-", "_")


def normalize_relation(relation: object) -> str:
    """Normalize LLM-provided relationship labels."""
    if not isinstance(relation, str):
        return ""
    normalized = relation.strip().upper().replace("_", "-").replace(" ", "-")
    return RELATION_ALIASES.get(normalized, normalized)
