"""Runtime generation lifecycle: construction, publication, background work, shutdown.

Modules are imported directly (``bootstrap.runtime.generations`` etc.); this
package intentionally re-exports nothing to keep import cycles impossible
between the reload path and ``bootstrap.tools``.
"""
