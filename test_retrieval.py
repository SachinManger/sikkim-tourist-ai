from retrieval.search import search_approved_records


print("\n===================================")
print("SIKKIM TOURIST AI - RETRIEVAL TEST")
print("===================================\n")


queries = [
    "Sikkim",
    "Pelling",
    "trekking",
    "monastery"
]


for query in queries:

    print("\n-----------------------------------")
    print("QUERY:", query)
    print("-----------------------------------")

    results = search_approved_records(
        query,
        limit=5
    )

    print("Results found:", len(results))

    for result in results:

        record = result["record"]

        print("\nRecord ID:", result["record_id"])
        print("Score:", result["score"])
        print("Name:", record.get("name"))
        print("Category:", record.get("category"))
        print("Description:", record.get("description"))
        print("Source:", result["source_url"])


print("\n===================================")
print("RETRIEVAL TEST COMPLETE")
print("===================================")