"""README.txt template generator for exported bonus content pack ZIPs.

Wording matches the official Bonus Content pack zips (see the "Import Packages"
style README found in recent Snapshot!/Lewd Shores/Naughty Nightmares packs).
"""

_GAME_TITLES = {
    "snapshot": "Snapshot!",
    "lewdshores": "Snapshot: Lewd Shores",
    "naughtynightmares": "Snapshot! Naughty Nightmares",
}

_DISCORD_URL = "https://discord.com/invite/KtRr4WSyks"


def build_readme(game: str) -> str:
    """Return the README.txt content for a bonus content pack ZIP for *game*
    ("snapshot" | "lewdshores" | "naughtynightmares")."""
    title = _GAME_TITLES.get(game, _GAME_TITLES["snapshot"])
    return (
        f"{title} Bonus Content Pack\n"
        "\n"
        f"This archive contains only bonus content assets and a configuration file for {title}.\n"
        "No executable files are included.\n"
        "\n"
        "How to Install\n"
        "\n"
        f"1. Install the latest version of {title}. (Either on Windows or on Android)\n"
        "2. Download the zip file to a common place, like your system's Download folder.\n"
        "3. Open the Bonus Content dialog in the game and use the \"Import Packages\" button.\n"
        "4. Select the zip file of the pack you want to add to the game.\n"
        "\n"
        "Notes\n"
        f"- Bonus Content Packs cannot run on their own. You need {title} to play it.\n"
        "- You can install multiple packs at the same time.\n"
        "- Removing a pack does not damage your save data.\n"
        "\n"
        "Need Help?\n"
        "Visit the official Snapshot Discord:\n"
        f"{_DISCORD_URL}\n"
    )
