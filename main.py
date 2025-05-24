import requests
import datetime
import os

# === Environment variables ===
TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_A_ID = os.environ["DATABASE_A_ID"]  # Books
DATABASE_B_ID = os.environ["DATABASE_B_ID"]  # Years

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# === Get all entries from a Notion database ===
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

# === Find year page by name ===
def find_year_page(year: str):
    entries = query_database(DATABASE_B_ID)
    for entry in entries:
        title_parts = entry["properties"].get("Name", {}).get("title", [])
        title = title_parts[0]["plain_text"] if title_parts else ""
        if title == year:
            return entry
    return None

# === Get already-linked book IDs ===
def get_existing_book_ids(entry):
    rel = entry["properties"].get("Books Read", {}).get("relation", [])
    return set(r["id"] for r in rel)

# === Filter books that match the year and aren't already linked ===
def filter_books_by_year(books, year: int, already_linked_ids):
    start_date = datetime.datetime(year, 1, 1)
    end_date = datetime.datetime(year, 12, 31)
    to_add = []

    for entry in books:
        props = entry["properties"]
        status = props.get("Status", {}).get("select", {}).get("name", "")
        date_str = props.get("Fim", {}).get("date", {}).get("start", None)
        book_id = entry["id"]

        if status == "Lido" and date_str:
            date = datetime.datetime.fromisoformat(date_str[:10])
            if start_date <= date <= end_date and book_id not in already_linked_ids:
                to_add.append((book_id, props["Name"]["title"][0]["plain_text"]))

    return to_add

# === Update the 'Books Read' field with new links ===
def update_relation(year_page_id, all_book_ids):
    url = f"https://api.notion.com/v1/pages/{year_page_id}"
    payload = {
        "properties": {
            "Books Read": {
                "relation": [{"id": bid} for bid in all_book_ids]
            }
        }
    }
    r = requests.patch(url, headers=HEADERS, json=payload)
    r.raise_for_status()

# === MAIN ===
def main():
    target_year = str(datetime.datetime.now().year)  # Use current year dynamically
    print(f"📆 Target year: {target_year}")

    year_entry = find_year_page(target_year)
    if not year_entry:
        print(f"❌ Year entry '{target_year}' not found in Dataset B.")
        return

    year_page_id = year_entry["id"]
    existing_ids = get_existing_book_ids(year_entry)

    print("🔎 Fetching all books...")
    books = query_database(DATABASE_A_ID)
    new_books = filter_books_by_year(books, int(target_year), existing_ids)

    if not new_books:
        print("📚 No new books to add.")
        return

    all_ids = existing_ids.union([book_id for book_id, _ in new_books])
    update_relation(year_page_id, all_ids)

    print(f"✅ Added {len(new_books)} new book(s):")
    for _, title in new_books:
        print(f" • {title}")

if __name__ == "__main__":
    main()
