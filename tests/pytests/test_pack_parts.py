from modules import pack_parts


def test_get_part_count_empty():
    assert pack_parts.get_part_count({}) == 0


def test_set_part_and_get_titles_fallback():
    data: dict = {"id": "mypack"}
    pack_parts.set_part(data, 0, "mypack1", "My Pack Part I", "100100-100199")
    pack_parts.set_part(data, 1, "", "", "")  # left blank -> falls back to "Part N"
    assert pack_parts.get_part_count(data) == 2
    assert pack_parts.get_part_titles(data) == ["My Pack Part I", "Part 2"]
    assert pack_parts.get_part_id(data, 0) == "mypack1"
    assert pack_parts.get_part_id(data, 1) == "mypack2"
    assert pack_parts.get_part_id_range(data, 0) == "100100-100199"


def test_remove_part_clears_pinned_photos():
    data: dict = {
        "id": "mypack",
        "id_parts": ["mypack1", "mypack2"],
        "title_parts": ["Part One", "Part Two"],
        "id_range_parts": ["100100-100199", "100200-100299"],
        "photos": [{"name": "a", "part_title": "Part One"}, {"name": "b", "part_title": "Part Two"}],
    }
    pack_parts.remove_part(data, 0)
    assert pack_parts.get_part_count(data) == 1
    assert pack_parts.get_part_titles(data) == ["Part Two"]
    assert data["photos"][0].get("part_title") is None
    assert data["photos"][1]["part_title"] == "Part Two"


def test_move_part_swaps_neighbors():
    data: dict = {
        "id": "mypack",
        "id_parts": ["mypack1", "mypack2"],
        "title_parts": ["First", "Second"],
        "id_range_parts": ["100100-100199", "100200-100299"],
    }
    pack_parts.move_part(data, 1, -1)
    assert pack_parts.get_part_titles(data) == ["Second", "First"]


def test_split_photos_by_declared_parts_fills_capacity_in_order():
    data = {
        "id": "pk",
        "id_parts": ["pk1", "pk2"],
        "title_parts": ["Part One", "Part Two"],
        "id_range_parts": ["100100-100101", "100200-100201"],  # capacity 2 each
    }
    photos = [{"name": f"p{i}"} for i in range(4)]
    chunks, part_meta = pack_parts.split_photos_by_declared_parts(data, photos, "pk", "Title", 100100)
    assert [len(c) for c in chunks] == [2, 2]
    assert part_meta[0] == ("pk1", "Part One", "100100-100101", "pk1.ini")
    assert part_meta[1] == ("pk2", "Part Two", "100200-100201", "pk2.ini")


def test_split_photos_by_declared_parts_honors_explicit_assignment():
    data = {
        "id": "pk",
        "id_parts": ["pk1", "pk2"],
        "title_parts": ["Part One", "Part Two"],
        "id_range_parts": ["100100-100101", "100200-100201"],
    }
    photos = [
        {"name": "a", "part_title": "Part Two"},
        {"name": "b"},
        {"name": "c"},
    ]
    chunks, _part_meta = pack_parts.split_photos_by_declared_parts(data, photos, "pk", "Title", 100100)
    assert [p["name"] for p in chunks[0]] == ["b", "c"]
    assert [p["name"] for p in chunks[1]] == ["a"]


def test_split_photos_by_declared_parts_overflow_creates_extra_part():
    data = {
        "id": "pk",
        "id_parts": ["pk1"],
        "title_parts": ["Part One"],
        "id_range_parts": ["100100-100101"],  # capacity 2
    }
    photos = [{"name": f"p{i}"} for i in range(3)]
    chunks, part_meta = pack_parts.split_photos_by_declared_parts(data, photos, "pk", "Title", 100100)
    assert len(chunks) == 2
    assert len(chunks[0]) == 2
    assert len(chunks[1]) == 1
    assert part_meta[1][0] == "pk2"
    assert part_meta[1][2] == "100102-100201"


def test_get_part_filename_fallback_and_override():
    data: dict = {"id": "mypack"}
    pack_parts.set_part(data, 0, "mypack1", "Part One", "100100-100199")
    assert pack_parts.get_part_filename(data, 0) == "mypack1.ini"
    pack_parts.set_part(data, 0, "mypack1", "Part One", "100100-100199", "pack 1.ini")
    assert pack_parts.get_part_filename(data, 0) == "pack 1.ini"
    pack_parts.set_part(data, 0, "mypack1", "Part One", "100100-100199", "pack 1")
    assert pack_parts.get_part_filename(data, 0) == "pack 1.ini"
