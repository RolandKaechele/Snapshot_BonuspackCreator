"""Central tooltip registry — import and call set_tip(widget, key) anywhere."""

from PyQt6.QtWidgets import QWidget  # type: ignore

# ---------------------------------------------------------------------------
# Tooltip text registry
# ---------------------------------------------------------------------------

TIPS: dict[str, str] = {

    # ── Pack Info ────────────────────────────────────────────────────────
    "pack_id": (
        "Short identifier used internally by the game. Must be unique across all installed packs.\n"
        "Lower-case letters and digits only (e.g. 'myfirstpack').\n"
        "Community convention: avoid prefixes reserved by official packs (pack1–pack50, slimegirls, …)."
    ),
    "pack_title": (
        "Display name shown in the game's Mod Manager.\n"
        "For multi-part exports this title gets 'Part N' appended automatically."
    ),
    "pack_game": (
        "Which game this pack targets.\n"
        "• Snapshot! — sets [Mod] gameID=snapshot (accepted by all games when empty).\n"
        "• Lewd Shores — sets [Pack] gameID=lewdshores."
    ),
    "pack_type": (
        "Pack content category.\n"
        "• Photos — normal collectible photo pack ([Mod] type=photos, default).\n"
        "• Events — city-event pack with dialogue JSON files ([Mod] type=events).\n"
        "• Love Lens — adds Love Lens hypnosis content ([Hypnosis] section)."
    ),
    "pack_idrange": (
        "Photo ID range reserved in the game's PhotoDictionary.\n"
        "Format: START-END, e.g. 100100-100199.\n"
        "Rules enforced by the game:\n"
        "  • Must be ≥ 100000\n"
        "  • Span must be exactly 100 (END = START + 99)\n"
        "  • Must not overlap any other installed pack\n"
        "If left empty or invalid the game auto-assigns the next free slot.\n\n"
        "⚠  Check the Snapshot Discord to request your own unique ID range\n"
        "   so it won't clash with other community packs."
    ),

    # ── Defaults section ─────────────────────────────────────────────────
    "defaults_position": (
        "Default shooting position applied to every photo that does not specify its own.\n"
        "Written to [Defaults] position= in the ini.\n"
        "Common values: upskirt, jogger, xray, bench, bar, event, hypno."
    ),
    "defaults_type": (
        "Default underwear/content type applied to every photo without an explicit type.\n"
        "Written to [Defaults] type= in the ini.\n"
        "Must be one of the game's built-in types or a custom alias defined in Special Traits."
    ),
    "defaults_color": (
        "Default color token for every photo without an explicit color.\n"
        "Written to [Defaults] color= in the ini."
    ),

    # ── Special Category ─────────────────────────────────────────────────
    "special_category": (
        "Optional badge label shown on collection cards from this pack.\n"
        "Written to [Special Category] specialCategory=.\n"
        "Example: 'Bikini', 'Nurse', 'Fantasy'."
    ),
    "special_category_color": (
        "Background colour for the special-category badge (hex, e.g. #ff8800).\n"
        "Written to [Special Category] specialCategoryColor=."
    ),

    # ── Special Traits ───────────────────────────────────────────────────
    "special_traits_intro": (
        "Custom type/color aliases that let you use a descriptive display name\n"
        "while still mapping to a built-in game value.\n\n"
        "Format: Display Label, token, fallback\n"
        "  Display Label — text shown in the UI filter (e.g. 'Nude Beach')\n"
        "  token         — identifier used in per-photo type=/color= keys\n"
        "  fallback      — the built-in game type/color to use (e.g. 'nude', 'none')\n\n"
        "Written as specialType= / specialColor= lines under [Special Traits]."
    ),
    "special_types_list": "List of custom underwear/content type aliases for this pack.",
    "special_colors_list": "List of custom color aliases for this pack.",

    # ── Photos tab ───────────────────────────────────────────────────────
    "photo_position": (
        "Shooting position that triggers this photo in the game world.\n"
        "Built-in Snapshot! positions:\n"
        "  upskirt, jogger, xray, xJogger, xBench, xBar,\n"
        "  bench, bar, flasher, window, angry, police, xPolice,\n"
        "  remote, rPolice, rJogger, rBench, event, hypno (Love Lens)\n\n"
        "Note: bar, yoga, hole, bicycle, photobooth, wc, gym require\n"
        "the player to have unlocked newer game content."
    ),
    "photo_type": (
        "Underwear/content type used to classify and filter this photo.\n"
        "Must be a built-in type or a custom alias defined in Special Traits.\n"
        "Built-in: plain, stripes, dots, frill, kinky, shorts, thong, kimono, pantyhose, none,\n"
        "          plug, piercing, cum, nude, flashing, sex, topless, dildo, mastubrate,\n"
        "          front, back, goth, cumMouth, cumFace, cumButt, cumVag, cumAnal"
    ),
    "photo_color": (
        "Color token for this photo's filter badge.\n"
        "Built-in: pink, blue, black, white, red, green, yellow, orange,\n"
        "          purple, gray, brown, cyan, none, wet, rare, police, mod\n\n"
        "Note: 'rare' is limited to ceil(photoCount / 10) per pack.\n"
        "Excess rare photos are silently downgraded to 'none' by the game."
    ),
    "photo_hypno_type": (
        "Love Lens (hypnosis) route type for this photo.\n"
        "Only used when Position = hypno.\n"
        "Required values for a complete Love Lens pack:\n"
        "  topless, nude, cumMouth, cumFace, cumButt, cumVag, cumAnal\n\n"
        "If no explicit hypnoType is set, the game infers it from the photo's type\n"
        "or from the filename. All seven types must be present for the pack to\n"
        "be eligible as an active Love Lens session."
    ),
    "photo_add": "Add one or more image files to the photo list. Supported: .png .jpg .jpeg .dat .jpa .pna",
    "photo_remove": "Remove the currently selected photo from the list.",

    # ── Events tab ───────────────────────────────────────────────────────
    "event_type": (
        "City-event variant.\n"
        "• normal   — standard event triggered by walking past NPCs\n"
        "• explosion — special explosion-type event\n\n"
        "Written as [Events] eventtype=."
    ),
    "event_backgrounds": (
        "Background images shown behind the event dialogue scene.\n"
        "Add PNG images (recommended 2024×1152). Written to [Events] backgrounds=."
    ),
    "event_overlays": (
        "Overlay images (or videos) composited on top of the background.\n"
        "Supports PNG images and .mp4 / .bytes videos. Written to [Events] overlays=."
    ),
    "event_dialogs": (
        "VIDE dialogue JSON files that drive the event story.\n"
        "Each JSON is registered as a runtime dialogue.\n"
        "The game links photos to events via the 'mod_addEventSellablePhoto' progress key\n"
        "inside the JSON. Written to [Events] dialogs=."
    ),

    # ── Dialog node fields ───────────────────────────────────────────────
    "nd_tag": (
        "Speaker name shown in the dialog box.\n"
        "Use SKIP for scene-setup nodes (no dialog text is shown; commands still run).\n"
        "Common values: Aya · Boy · Girl · Guy · Old Man · Punk Guy · Store Owner · You"
    ),
    "nd_text": "The dialogue line spoken by this character.",
    "nd_extraData": (
        "VIDE NodeData.extraData — a general-purpose string extension field.\n"
        "The game reads it via GetExtraData() and stores it as playerCommentExtraData\n"
        "for 'You'-tagged player-choice nodes (possible condition or cost string).\n"
        "No known addon pack populates this field; leave empty unless you know the value."
    ),
    "nd_oNPC": (
        "Index of the next NPC dialog node in the chain.\n"
        "-1 = end of chain (no further NPC node follows)."
    ),
    "nd_oSet": (
        "Index of a player-choice set node to branch to.\n"
        "-1 = no branch (linear flow)."
    ),
    "nd_oAct": (
        "Index of an action node to trigger alongside this node.\n"
        "-1 = no action."
    ),
    "nd_vars": (
        "Commands executed when this node is shown. Each row is one (Command, Argument) pair.\n"
        "Known commands:\n"
        "  showImage / noImage         — show or hide the background image\n"
        "  showEventPhoto / noPhoto    — show or hide an event photo\n"
        "  noOverlayImage              — hide the overlay image\n"
        "  mod_overlayImage3           — show overlay image slot 3\n"
        "  playSound / stopLoopedSound — play or stop a sound (argument = sound name)\n"
        "  pulseBackground             — flash/pulse the background\n"
        "  mascotMoan1 / mascotMoan2   — trigger mascot moan animations\n"
        "  suckLoop                    — trigger looped suck animation\n"
        "  endEvent                    — end the city event\n"
        "  mod_addEventSellablePhoto   — register a sellable photo for this event"
    ),

    # ── Love Lens tab ────────────────────────────────────────────────────
    "lovelens_model": (
        "3-D body model variant used during the Love Lens sequence.\n"
        "Written to [Hypnosis] model=."
    ),
    "lovelens_hair": (
        "Hair style for the character during the Love Lens sequence.\n"
        "Written to [Hypnosis] hairStyle=."
    ),
    "lovelens_accessories": (
        "Optional accessories to equip. Currently only 'elvenears' is recognised.\n"
        "Written to [Hypnosis] accessories=."
    ),
    "lovelens_hair_color": (
        "Hex colour to tint the hair texture (e.g. #ffa6c6).\n"
        "Written to [Hypnosis] hairColor=. Default is #AD846D."
    ),
    "lovelens_eye_color": (
        "Hex colour to tint the eye texture.\n"
        "Written to [Hypnosis] eyeColor=. Default is #AD846D."
    ),
    "lovelens_overlays": (
        "2-D overlay images or videos composited onto the Love Lens scene for each interaction stage.\n"
        "PNG up to 2048×2048 or .mp4/.bytes video. Written under [Hypnosis] overlay slot keys."
    ),
    "lovelens_textures": (
        "Replacement textures for the 3-D character model during the Love Lens sequence.\n"
        "PNG up to 2048×2048. Written under [Hypnosis Textures]."
    ),

    # ── Passthrough ──────────────────────────────────────────────────────
    "passthrough_info": (
        "INI sections not managed by this tool are preserved verbatim on export.\n"
        "This includes sections like [Localization] or any game-specific section\n"
        "that the tool does not actively edit."
    ),

    # ── Import/Export ────────────────────────────────────────────────────
    "import_btn": (
        "Import a Bonus Content pack from an existing folder.\n"
        "All .ini files in the folder are merged (supports multi-part packs like RentaroFamily).\n"
        "Images are referenced by path; files are not copied."
    ),
    "export_btn": (
        "Export the current pack to a game-ready BonusContent folder.\n"
        "Packs with more than 100 photos are automatically split into numbered .ini files.\n"
        "Each part gets its own ID range (e.g. 100100-100199, 100200-100299, …)."
    ),
}


def set_tip(widget: QWidget, key: str) -> None:
    """Apply tooltip from the registry to *widget* if the key exists."""
    tip = TIPS.get(key)
    if tip:
        widget.setToolTip(tip)


def tip(key: str) -> str:
    """Return the tooltip string for *key*, or an empty string."""
    return TIPS.get(key, "")
