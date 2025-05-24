import requests
import datetime
import os

# Secrets from GitHub Actions
TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_A_ID = os.environ["DATABASE_A_ID"]
DATABASE_B_ID = os.environ["DATABASE_B_ID"]

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

start_date = datetime.datetime(2025, 1, 1)
end_date = datetime.datetime(2025, 12, 31)

def query_database(database_id):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    results = []
    next_cursor = None

    while True:
        payload = {"start_cursor": next_cursor} if next_cursor else {}
        r = requests.post(url, headers=HEADERS, json=payload)
        r.raise_for_status()
        data = r.json()
        results.extend(data["results"])
        next_cursor = data.get("next_cursor")
        if not next_cursor:
            break
    return results

def get_existing_book_ids_in_B():
    entries = query_database(DATABASE_B_ID)
    existing_ids = set()
    for entry in entries:
        rels = entry["properties"].get("Book", {}).get("relation", [])
        for rel in rels:
            existing_ids.add(rel["id"])
    return existing_ids

def filter_books(entries, already_linked_ids):
    eligible = []
    for entry in entries:
        props = entry["properties"]
        status = props.get("Status", {}).get("select", {}).get("name", "")
        date_str = props.get("Date Read", {}).get("date", {}).get("start", None)
        book_id = entry["id"]

        if status == "Read" and date_str and book_id not in already_linked_ids:
            date_read = datetime.datetime.fromisoformat(date_str[:10])
            if start_date <= date_read <= end_date:
                eligible.append(entry)
    return eligible

def add_to_log(book_entry):
    title = book_entry["properties"]["Name"]["title"][0]["plain_text"]
    book_id = book_entry["id"]

    url = "https://api.notion.com/v1/pages"
    payload = {
        "parent": { "database_id": DATABASE_B_ID },
        "properties": {
            "Name": {
                "title": [{ "text": { "content": f"Log for: {title}" } }]
            },
            "Book": {
                "relation": [{ "id": book_id }]
            }
        }
    }

    r = requests.post(url, headers=HEADERS, json=payload)
    r.raise_for_status()
    print(f"Linked: {title}")

def main():
    print("Fetching books...")
    books = query_database(DATABASE_A_ID)
    existing_ids = get_existing_book_ids_in_B()
    to_link = filter_books(books, existing_ids)

    for book in to_link:
        add_to_log(book)

if __name__ == "__main__":
    main()
