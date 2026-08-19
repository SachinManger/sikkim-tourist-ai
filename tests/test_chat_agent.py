from agent.chat_agent import answer_question


print("\n===================================")
print("SIKKIM TOURIST AI - CHAT TEST")
print("===================================\n")


questions = [
    "What is Sikkim?",
    "What can I do in Pelling?",
    "What activities are available in Sikkim?",
    "Tell me about monasteries in Sikkim."
]


for question in questions:

    print("\n-----------------------------------")
    print("USER:")
    print(question)

    print("\nAI:")

    try:

        result = answer_question(question)

        print(result["answer"])

        print("\nSOURCES:")

        if result["sources"]:

            for source in result["sources"]:
                print("-", source)

        else:
            print("No sources found.")

    except Exception as e:

        print("\n[ERROR]")
        print(e)


print("\n===================================")
print("CHAT TEST COMPLETE")
print("===================================")