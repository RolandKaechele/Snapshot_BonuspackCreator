# Blueprint PNG files

The PNG files in this directory are generated assets and are NOT committed to git.

Generation script: tools/generate_blueprints.py
See also: tools/README_generate_blueprints.md

How to regenerate:
    venv\Scripts\python.exe tools\generate_blueprints.py

The script scans pack.ini files under tests/bonuscontent/exported/, picks up to
9 representative images per (position, type) combination, converts the character
region to a flat silhouette, and writes the result here as
<position>_<type>_<n>.png.

Extra dependencies (not in requirements.txt):
    pip install rembg onnxruntime pillow numpy
