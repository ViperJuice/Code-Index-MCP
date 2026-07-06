from pathlib import Path


def test_semincr_docs_freeze_incremental_mutation_contract():
    doc = Path("docs/guides/semantic-onboarding.md").read_text(encoding="utf-8")

    assert "Incremental mutation follows the same ordered semantic contract as full sync" in doc
    assert "Changed chunks invalidate stale semantic evidence before re-embedding" in doc
    assert "Deletes remove both authoritative summaries and semantic vectors" in doc
    assert "Watcher-triggered repair uses the same summary-first mutation contract" in doc


def test_semincr_docs_stay_out_of_query_routing_and_dogfood_claims():
    doc = Path("docs/guides/semantic-onboarding.md").read_text(encoding="utf-8")
    section = doc.split("## Incremental Mutation Contract", 1)[1]

    assert "does not change semantic query routing" in section
    assert "does not claim\ndogfood rebuild evidence" in section
