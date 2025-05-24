import requests
import datetime
import os

# === Environment variables ===
TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_A_ID = os.environ["DATABASE_A_ID"]  # Books
DATABASE_B_ID = os.environ["DATABASE_B_ID"]  # Years

HEADERS = {
    "Authorization": f"Bearer " + TOKEN,
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# === Fetch all entries from a database ===
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

# === Find the page in Dataset B with Name == current year ===
def find_year_page(year_str):
    entries = query_database(DATABASE_B_ID)
    for entry in entries:
        title_parts = entry["properties"].get("Name", {}).get("title", [])
        title = title_parts[0]["plain_text"] if title_parts else ""
        if title == year_str:
            return entry
    return None

# === Get already-linked book IDs in 'Books Read' ===
def get_existing_book_ids(entry):
    rel = entry["properties"].get("Books Read", {}).get("relation", [])
    return set(r["id"] for r in rel)

# === Filter books marked as 'Lido' with Fim in the given year ===
def filter_books_by_year(books, year: int, already_linked_ids):
    start_date = datetime.datetime(year, 1, 1)
    end_date = datetime.datetime(year, 12, 31)
    to_add = []

    for entry in books:
        props = entry["properties"]
        status = props.get("Status", {}).get("select", {}).get("name", "")

        fim_prop = props.get("Fim")
        date_str = None
        if fim_prop and fim_prop.get("date"):
            date_str = fim_prop["date"].get("start")

        book_id = entry["id"]

        if status == "Lido" and date_str:
            date = datetime.datetime.fromisoformat(date_str[:10])
            if start_date <= date <= end_date and book_id not in already_linked_ids:
                title = props.get("Name", {}).get("title", [{}])[0].get("plain_text", "Untitled")
                to_add.append((book_id, title))

    return to_add

# === Update 'Books Read' property in Year page ===
def update_books_read(year_page_id, all_book_ids):
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

# === DEBUG VERSION: mark the N most recent books with Status == "Não iniciado" ===
def update_most_recent_tags(books, n=2):
    not_started_books = [
        b for b in books
        if b["properties"].get("Status", {}).get("select", {}).get("name", "") == "Não iniciado"
    ]

    print(f"🔍 Found {len(not_started_books)} book(s) with Status == 'Não iniciado'.")

    books_sorted = sorted(not_started_books, key=lambda e: e["created_time"], reverse=True)
    most_recent_ids = set(entry["id"] for entry in books_sorted[:n])

    print(f"🏷 Will mark {len(most_recent_ids)} book(s) as Most Recent.")

    for entry in books:
        book_id = entry["id"]
        title = entry["properties"].get("Name", {}).get("title", [{}])[0].get("plain_text", "Untitled")
        current_flag = entry["properties"].get("Most Recent", {}).get("checkbox", False)
        should_flag = book_id in most_recent_ids

        if current_flag != should_flag:
            print(f"🔧 Updating '{title}' → Most Recent = {should_flag}")
            url = f"https://api.notion.com/v1/pages/{book_id}"
            payload = {
                "properties": {
                    "Most Recent": {
                        "checkbox": should_flag
                    }
                }
            }
            r = requests.patch(url, headers=HEADERS, json=payload)
            r.raise_for_status()
        else:
            print(f"➖ No change for '{title}' (already set to {current_flag})")

# === MAIN ===
def main():
    year_str = str(datetime.datetime.now().year)
    print(f"📆 Target year: {year_str}")

    books = query_database(DATABASE_A_ID)
    update_most_recent_tags(books, n=2)

    year_entry = find_year_page(year_str)
    if not year_entry:
        print(f"❌ Year page '{year_str}' not found.")
        return

    existing_ids = get_existing_book_ids(year_entry)
    new_books = filter_books_by_year(books, int(year_str), existing_ids)

    if not new_books:
        print("📚 No new books to add.")
        return

    all_ids = existing_ids.union([book_id for book_id, _ in new_books])
    update_books_read(year_entry["id"], all_ids)

    print(f"✅ Added {len(new_books)} new book(s) to 'Books Read':")
    for _, title in new_books:
        print(f" • {title}")

if __name__ == "__main__":
    main()
