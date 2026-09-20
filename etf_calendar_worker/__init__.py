"""Authoritative scientific-worker package for the isolated ETF calendar proof.

``POSTP1-001V2A-PAD4-R1`` repairs the four authority-anchoring defects that
failed ``POSTP1-002V2A-PAD4`` while preserving the fresh-exec process-isolation
boundary that review found sound.

This package exists *outside* ``btc_predictor`` for one material reason.  The
review requires that installed third-party content is attested **before** any
dependency code executes, and importing ``btc_predictor`` executes
``numpy``, ``scipy``, ``sqlalchemy`` and ``alembic`` through the package
re-export graph.  The worker protocol therefore may not live under
``btc_predictor``: it has to be importable with no third-party side effect at
all, so that the certified-source, semantic-authority and installed-content
verifications can run first.

This module body is deliberately empty of imports and executable statements.
"""
