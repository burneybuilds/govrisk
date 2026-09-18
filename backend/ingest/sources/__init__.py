"""Adapters for each ingestable data source.

Each module exposes one `Ingestor` class (subclass of `BaseIngestor`) plus its
`fetch`/`parse` implementation. Adding a portal never touches the pipeline.
"""