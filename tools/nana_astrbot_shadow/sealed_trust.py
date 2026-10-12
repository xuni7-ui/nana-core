"""EMPTY production default. Only offline reviewed builds replace these bytes.

Never load pins from configuration, environment, CLI input or the Shadow DB.
Generated candidates are independently hashed artifacts, not runtime settings.
"""
from types import MappingProxyType
SEAL_MODE = 'EMPTY'
PRODUCTION_REVIEW_PINS = MappingProxyType({})
REAL_RUNTIME_PROOF_PINS = MappingProxyType({})
EXACT_RECEIPT_DIGEST = None
EXACT_STORE_BINDING = None
REVIEW_SOURCE_SHA = None
