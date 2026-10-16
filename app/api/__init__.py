"""HTTP API package.

Routers are imported directly by ``app.main``. Keeping this package initializer
free of eager router imports prevents dependency modules from creating circular
imports during authentication.
"""
