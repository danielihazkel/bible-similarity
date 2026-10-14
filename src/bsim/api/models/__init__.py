"""Response models of the viewer API (DESIGN.md §10).

Split by feature: one module per route module (`api/routes/`), `common` for what several
share; a route imports from its own module and `common`.
"""
