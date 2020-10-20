# coding: utf-8

'''
Attribute-based access control: Policies, policy related stuff.

Policy, Policy Decision Point, Policy Action Point, Policy Information Point

See: https://en.wikipedia.org/wiki/Attribute-based_access_control
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# from .attributes.action import
# from .attributes.context
# from .attributes.object
# from .attributes.subject

# These will be in separate files, but are stubs for now. e.g.
# PolicyDecisionPoint will go in '.decision' once implemented, probably.
from .policy import PolicyDecisionPoint


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    'PolicyDecisionPoint',
]
