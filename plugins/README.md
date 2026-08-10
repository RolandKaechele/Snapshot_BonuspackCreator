# plugins/

Drop plugin packages or `.py` modules into this folder.

Each plugin must expose a top-level `register(app)` function.
The application discovers and loads them automatically at startup.

Example minimal plugin (`plugins/my_plugin/__init__.py`):

```python
def register(app):
    print("My plugin loaded!")
```
