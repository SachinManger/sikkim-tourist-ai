from agent.ollama_agent import extract_records


# ============================================================
# REAL WEBPAGE EXTRACTION TEST
# ============================================================

def main():

    print("=" * 60)
    print("SIKKIM TOURISM REAL EXTRACTION TEST")
    print("=" * 60)

    # --------------------------------------------------------
    # For now, use realistic webpage text.
    # Later we will connect this directly to your collector.
    # --------------------------------------------------------

    webpage_text = """
    Pelling is a popular tourist destination in West Sikkim,
    known for beautiful views of Mount Kanchenjunga and the
    surrounding mountains.

    Tourists visit Pelling for sightseeing, nature activities,
    monasteries and trekking.

    Important attractions around Pelling include
    Pemayangtse Monastery, Rabdentse Ruins and
    Khecheopalri Lake.

    Pelling is a popular base for exploring western Sikkim.
    """

    print("\n[TEST] Sending webpage text to Qwen...")

    try:

        records = extract_records(
            text=webpage_text,
            source_name="Sikkim Tourism Test",
            source_url="https://www.sikkimtourism.gov.in/",
            page_title="Pelling Tourism",
            page_url="https://www.sikkimtourism.gov.in/pelling"
        )

    except Exception as e:

        print("\n[ERROR] Extraction failed")
        print(e)

        return

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    print("\nRecords extracted:", len(records))

    if not records:
        print("\n[FAIL] No records were extracted.")
        return

    # --------------------------------------------------------
    # DISPLAY RECORDS
    # --------------------------------------------------------

    for i, record in enumerate(records, start=1):

        print("\n" + "-" * 60)
        print(f"RECORD {i}")
        print("-" * 60)

        print("Name       :", record.name)
        print("Category   :", record.category)
        print("Description:", record.description)
        print("Activities :", record.activities)
        print("Nearby     :", record.nearby_places)
        print("District   :", record.district)
        print("Region     :", record.region)
        print("Permit     :", record.permit_required)
        print("Status     :", record.status)

    # --------------------------------------------------------
    # BASIC TESTS
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("VALIDATION")
    print("=" * 60)

    # Check that Pelling exists

    pelling_records = [
        r for r in records
        if r.name.lower() == "pelling"
    ]

    if pelling_records:
        print("[PASS] Pelling record found.")
    else:
        print("[FAIL] Pelling record not found.")

    # Check that activities were not incorrectly converted
    # into separate records.

    activity_names = {
        "trekking",
        "sightseeing",
        "nature",
        "monasteries"
    }

    bad_activity_records = [
        r for r in records
        if r.name.lower() in activity_names
    ]

    if bad_activity_records:
        print(
            "[FAIL] Activity records were incorrectly created:"
        )

        for r in bad_activity_records:
            print("       -", r.name)

    else:
        print("[PASS] No obvious activity records were created.")

    # --------------------------------------------------------
    # PRINT COMPLETE JSON
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("COMPLETE EXTRACTED JSON")
    print("=" * 60)

    for record in records:
        print(record.model_dump_json(indent=2))

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()