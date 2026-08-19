from agent.ollama_agent import extract_records


# ============================================================
# SAMPLE WEBPAGE TEXT
# ============================================================

sample_text = """
Pelling is a popular tourist destination in West Sikkim, Sikkim, India.

It is known for beautiful views of Mount Kanchenjunga and surrounding
mountains.

Tourists visit Pelling for sightseeing, nature, monasteries, trekking
and peaceful surroundings.

Important attractions around Pelling include Pemayangtse Monastery,
Rabdentse Ruins and Khecheopalri Lake.

Pelling is a popular base for exploring western Sikkim.
"""


# ============================================================
# MAIN TEST
# ============================================================

def main():

    print("\n==============================")
    print("SIKKIM TOURISM EXTRACTION TEST")
    print("==============================\n")

    print("[TEST] Sending sample webpage text to Qwen...")

    records = extract_records(
        text=sample_text,
        source_name="Sikkim Tourism Test",
        source_url="https://example.com",
        page_title="Pelling Tourism",
        page_url="https://example.com/pelling"
    )

    # --------------------------------------------------------
    # CHECK RESULT
    # --------------------------------------------------------

    print("\n==============================")
    print("EXTRACTED TOURISM RECORDS")
    print("==============================\n")

    print(f"Records extracted: {len(records)}")

    # --------------------------------------------------------
    # DISPLAY EACH RECORD
    # --------------------------------------------------------

    for index, record in enumerate(records, start=1):

        print("\n------------------------------")
        print(f"RECORD {index}")
        print("------------------------------")

        print(f"Name       : {record.name}")
        print(f"Category   : {record.category}")
        print(f"Description: {record.description}")
        print(f"Activities : {record.activities}")
        print(f"Nearby     : {record.nearby_places}")
        print(f"District   : {record.district}")
        print(f"Region     : {record.region}")
        print(f"Permit     : {record.permit_required}")
        print(f"Status     : {record.status}")

    # --------------------------------------------------------
    # BASIC VALIDATION
    # --------------------------------------------------------

    print("\n==============================")
    print("BASIC VALIDATION")
    print("==============================\n")

    if not records:
        print("[FAIL] No records were extracted.")
        return

    print("[PASS] At least one record was extracted.")

    # --------------------------------------------------------
    # CHECK THAT PELLING EXISTS
    # --------------------------------------------------------

    pelling_records = [
        record
        for record in records
        if record.name.lower() == "pelling"
    ]

    if pelling_records:
        print("[PASS] Pelling record found.")
    else:
        print("[WARNING] Pelling record was not found.")

    # --------------------------------------------------------
    # CHECK FOR UNWANTED INVENTED RECORDS
    # --------------------------------------------------------

    unwanted_names = {
        "trekking",
        "sightseeing",
        "nature",
        "monasteries",
        "western sikkim"
    }

    unwanted_records = [
        record.name
        for record in records
        if record.name.lower() in unwanted_names
    ]

    if unwanted_records:

        print(
            "[WARNING] Possible unwanted records detected:",
            unwanted_records
        )

        print(
            "[INFO] General activities such as trekking and "
            "sightseeing should normally be stored inside "
            "the activities field."
        )

    else:

        print(
            "[PASS] No obvious activity records were created."
        )

    # --------------------------------------------------------
    # DISPLAY FULL JSON ONLY IF NEEDED
    # --------------------------------------------------------

    print("\n==============================")
    print("FULL JSON")
    print("==============================\n")

    for record in records:

        if hasattr(record, "model_dump_json"):

            print(
                record.model_dump_json(
                    indent=2
                )
            )

        else:

            print(record)

    # --------------------------------------------------------
    # COMPLETE
    # --------------------------------------------------------

    print("\n==============================")
    print("TEST SUCCESSFUL")
    print("==============================")


# ============================================================
# RUN TEST
# ============================================================

if __name__ == "__main__":
    main()