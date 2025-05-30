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

def find_year_page(year_str):
    entries = query_database(DATABASE_B_ID)
    for entry in entries:
        title_parts = entry["properties"].get("Name", {}).get("title", [])
        title = title_parts[0]["plain_text"] if title_parts else ""
        if title == year_str:
            return entry
    return None

def get_existing_book_ids(entry):
    rel = entry["properties"].get("Books Read", {}).get("relation", [])
    return set(r["id"] for r in rel)

def filter_books_by_year(books, year: int, already_linked_ids):
    start_date = datetime.datetime(year, 1, 1)
    end_date = datetime.datetime(year, 12, 31)
    to_add = []

    for entry in books:
        props = entry["properties"]

        status_obj = props.get("Status", {})
        status = ""
        if "status" in status_obj:
            status = status_obj["status"].get("name", "")
        elif "select" in status_obj:
            status = status_obj["select"].get("name", "")

        fim = None
        fim_prop = props.get("Fim")
        if fim_prop and isinstance(fim_prop.get("date"), dict):
            fim = fim_prop["date"].get("start")

        book_id = entry["id"]

        if status == "Lido" and fim:
            date = datetime.datetime.fromisoformat(fim[:10])
            if start_date <= date <= end_date and book_id not in already_linked_ids:
                title = props.get("Name", {}).get("title", [{}])[0].get("plain_text", "Untitled")
                to_add.append((book_id, title))

    return to_add

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

def update_least_recent_tags(books, n=2):
    not_started_books = []

    print("📋 Listing all book statuses:")
    for b in books:
        props = b["properties"]
        title = props.get("Name", {}).get("title", [{}])[0].get("plain_text", "Untitled")

        status_obj = props.get("Status", {})
        status = ""
        if "status" in status_obj:
            status = status_obj["status"].get("name", "")
        elif "select" in status_obj:
            status = status_obj["select"].get("name", "")

        print(f"📚 {title} — Status: '{status}'")

        if status == "Não iniciado":
            not_started_books.append(b)

    print(f"🔍 Found {len(not_started_books)} book(s) with Status == 'Não iniciado'.")

    books_sorted = sorted(not_started_books, key=lambda e: e["created_time"])
    least_recent_ids = set(entry["id"] for entry in books_sorted[:n])

    print(f"🏷 Will mark {len(least_recent_ids)} book(s) as Least Recent (oldest).")

    for entry in books:
        props = entry["properties"]
        book_id = entry["id"]
        title = props.get("Name", {}).get("title", [{}])[0].get("plain_text", "Untitled")
        current_flag = props.get("Least Recent", {}).get("checkbox", False)
        should_flag = book_id in least_recent_ids

        if current_flag != should_flag:
            print(f"🔧 Updating '{title}' → Least Recent = {should_flag}")
            url = f"https://api.notion.com/v1/pages/{book_id}"
            payload = {
                "properties": {
                    "Least Recent": {
                        "checkbox": should_flag
                    }
                }
            }
            r = requests.patch(url, headers=HEADERS, json=payload)
            r.raise_for_status()
        else:
            print(f"➖ No change for '{title}' (already set to {current_flag})")

def main():
    year_str = str(datetime.datetime.now().year)
    print(f"📆 Target year: {year_str}")

    books = query_database(DATABASE_A_ID)

    # Safely update Status to 'Lido' if Fim is filled
    for entry in books:
        props = entry["properties"]
        book_id = entry["id"]
        title = props.get("Name", {}).get("title", [{}])[0].get("plain_text", "Untitled")

        status_obj = props.get("Status", {})
        current_status = ""
        if "status" in status_obj:
            current_status = status_obj["status"].get("name", "")
        elif "select" in status_obj:
            current_status = status_obj["select"].get("name", "")

        fim = None
        fim_prop = props.get("Fim")
        if fim_prop and isinstance(fim_prop.get("date"), dict):
            fim = fim_prop["date"].get("start")

        if fim and current_status != "Lido":
            print(f"🔁 Updating '{title}' → Status = 'Lido' (Fim is set)")
            url = f"https://api.notion.com/v1/pages/{book_id}"
            payload = {
                "properties": {
                    "Status": {
                        "status": {
                            "name": "Lido"
                        }
                    }
                }
            }
            r = requests.patch(url, headers=HEADERS, json=payload)
            r.raise_for_status()

    # Refresh books list to reflect updates
    books = query_database(DATABASE_A_ID)

    update_least_recent_tags(books, n=2)

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
