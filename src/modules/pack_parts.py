"""Pack Parts — helpers for a multi-ini pack's per-part identity (id/title/idrange/filename)
and explicit per-photo part assignment. Shared by pack_info_widget.py (Identity tab
Parts editor), picture_widget.py (Image Properties "Belongs to Part" dropdown), and
import_export.py (export-time photo-to-ini splitting).

A pack's parts are stored as four parallel lists on ``pack_data`` — ``id_parts``,
``title_parts``, ``id_range_parts``, ``filename_parts`` — one entry per declared part,
in part order. A photo opts into a specific part by setting its ``part_title`` key to
one of the resolved titles returned by ``get_part_titles()``; an empty/missing
``part_title`` means "auto-assign at export time".
"""

_PART_KEYS = ("id_parts", "title_parts", "id_range_parts", "filename_parts")


def get_part_count(pack_data: dict) -> int:
    """Return how many parts are declared (the longest of the three parallel lists)."""
    return max((len(pack_data.get(key, [])) for key in _PART_KEYS), default=0)


def get_part_titles(pack_data: dict) -> list[str]:
    """Return one resolved display title per declared part, falling back to
    "Part N" for any part the user hasn't given a custom title."""
    n = get_part_count(pack_data)
    title_parts = pack_data.get("title_parts", [])
    titles = []
    for i in range(n):
        custom = title_parts[i].strip() if i < len(title_parts) else ""
        titles.append(custom or f"Part {i + 1}")
    return titles


def get_part_id(pack_data: dict, index: int) -> str:
    id_parts = pack_data.get("id_parts", [])
    base_id = pack_data.get("id", "mypack")
    custom = id_parts[index].strip() if 0 <= index < len(id_parts) else ""
    return custom or f"{base_id}{index + 1}"


def get_part_id_range(pack_data: dict, index: int) -> str:
    id_range_parts = pack_data.get("id_range_parts", [])
    return id_range_parts[index].strip() if 0 <= index < len(id_range_parts) else ""


def get_part_filename(pack_data: dict, index: int) -> str:
    """Return the ini filename for the part at *index* — a user-chosen override
    (``.ini`` appended if missing) or ``"{part_id}.ini"`` by default."""
    filename_parts = pack_data.get("filename_parts", [])
    custom = filename_parts[index].strip() if 0 <= index < len(filename_parts) else ""
    if custom:
        return custom if custom.lower().endswith(".ini") else f"{custom}.ini"
    return f"{get_part_id(pack_data, index)}.ini"


def set_part(
    pack_data: dict, index: int, part_id: str = "", title: str = "", id_range: str = "",
    filename: str = "",
) -> None:
    """Insert/update the part at *index*, padding the four parallel lists with
    blanks as needed so they stay the same length."""
    n = max(get_part_count(pack_data), index + 1)
    id_parts = list(pack_data.get("id_parts", []))
    title_parts = list(pack_data.get("title_parts", []))
    id_range_parts = list(pack_data.get("id_range_parts", []))
    filename_parts = list(pack_data.get("filename_parts", []))
    for lst in (id_parts, title_parts, id_range_parts, filename_parts):
        lst.extend([""] * (n - len(lst)))
    id_parts[index] = part_id
    title_parts[index] = title
    id_range_parts[index] = id_range
    filename_parts[index] = filename
    pack_data["id_parts"] = id_parts
    pack_data["title_parts"] = title_parts
    pack_data["id_range_parts"] = id_range_parts
    pack_data["filename_parts"] = filename_parts


def remove_part(pack_data: dict, index: int) -> None:
    """Remove the part at *index*; photos explicitly pinned to it revert to auto-assignment."""
    n = get_part_count(pack_data)
    if not (0 <= index < n):
        return
    titles = get_part_titles(pack_data)
    removed_title = titles[index] if index < len(titles) else ""
    for key in _PART_KEYS:
        lst = list(pack_data.get(key, []))
        if index < len(lst):
            del lst[index]
        pack_data[key] = lst
    for photo in pack_data.get("photos", []):
        if photo.get("part_title") == removed_title:
            photo.pop("part_title", None)


def move_part(pack_data: dict, index: int, direction: int) -> None:
    """Swap the part at *index* with its neighbor (*direction* -1 = up, +1 = down)."""
    n = get_part_count(pack_data)
    target = index + direction
    if not (0 <= index < n) or not (0 <= target < n):
        return
    for key in _PART_KEYS:
        lst = list(pack_data.get(key, []))
        lst.extend([""] * (n - len(lst)))
        lst[index], lst[target] = lst[target], lst[index]
        pack_data[key] = lst


def split_photos_by_declared_parts(
    pack_data: dict, photos: list[dict], pack_id: str, title: str, range_start: "int | None",
) -> tuple[list[list[dict]], list[tuple[str, str, str, str]]]:
    """Return (chunks, part_meta) — *chunks* is one photo list per output ini part,
    *part_meta* is a parallel list of (part_id, part_title, part_id_range, filename).

    Photos whose ``part_title`` matches a declared part go there; all other photos
    fill each declared part's remaining capacity (its idrange width, or 100 when the
    part has no parseable range) in order. Any photos still left over spill into
    extra auto-numbered parts appended after the declared ones, exactly like the
    normal 100-per-part auto-split.
    """
    from modules.photo_registry import parse_id_range

    n = get_part_count(pack_data)
    titles = get_part_titles(pack_data)
    buckets: list[list[dict]] = [[] for _ in range(n)]
    unassigned: list[dict] = []
    for photo in photos:
        part_title = photo.get("part_title")
        idx = titles.index(part_title) if part_title in titles else -1
        (buckets[idx] if idx >= 0 else unassigned).append(photo)

    for i in range(n):
        rng = parse_id_range(get_part_id_range(pack_data, i))
        capacity = (rng[1] - rng[0] + 1) if rng else 100
        room = max(capacity - len(buckets[i]), 0)
        if room and unassigned:
            buckets[i].extend(unassigned[:room])
            unassigned = unassigned[room:]

    chunks: list[list[dict]] = list(buckets)
    part_meta: list[tuple[str, str, str, str]] = [
        (get_part_id(pack_data, i), titles[i], get_part_id_range(pack_data, i), get_part_filename(pack_data, i))
        for i in range(n)
    ]

    if unassigned:
        last_end = None
        if n:
            rng = parse_id_range(get_part_id_range(pack_data, n - 1))
            if rng:
                last_end = rng[1]
        for k, extra in enumerate(unassigned[i:i + 100] for i in range(0, len(unassigned), 100)):
            part_num = n + k + 1
            if last_end is not None:
                part_start = last_end + 1 + k * 100
                part_range = f"{part_start}-{part_start + 99}"
            elif range_start is not None:
                part_start = range_start + (n + k) * 100
                part_range = f"{part_start}-{part_start + 99}"
            else:
                part_range = ""
            part_id = f"{pack_id}{part_num}"
            chunks.append(extra)
            part_meta.append((part_id, f"{title} Part {part_num}", part_range, f"{part_id}.ini"))

    return chunks, part_meta
