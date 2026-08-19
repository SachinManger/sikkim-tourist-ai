from agent.ollama_agent import validate_record_evidence


def test_evidence_accepts_basic_singular_plural_variant():
    record = {"name": "Taxi Route Rates"}
    source_text = "Sikkim Taxi Route Rate Chart"

    assert validate_record_evidence(record, source_text)


def test_evidence_accepts_one_intervening_title_word():
    record = {"name": "Taxi Rate Chart"}
    source_text = "Sikkim Taxi Route Rate Chart"

    assert validate_record_evidence(record, source_text)


def test_evidence_still_requires_a_contiguous_phrase():
    record = {"name": "Taxi Route Rates"}
    source_text = "Taxi services are listed here. Route details have separate rate tables."

    assert not validate_record_evidence(record, source_text)
