def parse_watchlists(db, path, parsed_url, payload, timestamp):
    """Memproses katalog watchlist pengguna."""
    inner_data = payload.get("data", [])
    if isinstance(inner_data, dict):
        inner_data = inner_data.get("data", [])
    if not isinstance(inner_data, list):
        inner_data = []
    watchlists_list = []
    for w in inner_data:
        if w.get("watchlist_id") is None:
            continue
        watchlists_list.append({
            "watchlist_id": w.get("watchlist_id"),
            "name": w.get("name"),
            "description": w.get("description"),
            "is_default": w.get("is_default"),
            "is_favorite": w.get("is_favorite"),
            "category_type": w.get("category_type")
        })
    if watchlists_list:
        db.insert_watchlists(watchlists_list)


def parse_watchlist_items(db, path, parsed_url, payload, timestamp):
    """Memproses detail saham anggota suatu watchlist."""
    path_parts = path.strip("/").split("/")
    watchlist_id_str = path_parts[-1]
    if watchlist_id_str.isdigit():
        watchlist_id = int(watchlist_id_str)
        inner_data = payload.get("data", {})
        items_list = inner_data.get("result", [])
        symbols = [item.get("symbol") for item in items_list if item.get("symbol")]
        if symbols:
            db.insert_watchlist_items(watchlist_id, symbols)
