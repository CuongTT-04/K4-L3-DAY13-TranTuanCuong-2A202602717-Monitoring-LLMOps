from dotenv import load_dotenv
from langfuse import get_client

load_dotenv()


def main():
    client = get_client()

    p1_text = "Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}"
    print("Creating day13-chat version 1...")
    p1 = client.create_prompt(
        name="day13-chat",
        prompt=p1_text,
        type="text",
        labels=["baseline", "production"],
        commit_message="Initial prompt template",
    )
    print(f"Created version {p1.version} with labels: {p1.labels}")

    p2_text = "Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}\nTrả lời ngắn gọn và súc tích."
    print("Creating day13-chat version 2...")
    p2 = client.create_prompt(
        name="day13-chat",
        prompt=p2_text,
        type="text",
        labels=["candidate"],
        commit_message="Candidate prompt with concise constraint",
    )
    print(f"Created version {p2.version} with labels: {p2.labels}")


if __name__ == "__main__":
    main()
