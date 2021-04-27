# coding: utf-8

'''
An Attribute-Based Access Control Policy. Should encapsulate everything
about the request that needs conntrolling - subject, resource, action, context.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING, Type
if TYPE_CHECKING:
    from veredi.data.serdes.base import BaseSerdes

import enum

from ...context import SecurityContext

from ..identity import PolicyId


# TODO [2020-10-19]: move to own file
class Rules:
    '''todo'''
    pass


# TODO [2020-10-19]: move to own file
class Request:
    '''todo'''

    @classmethod
    def from_serdes(klass: Type['Request'], serdes: 'BaseSerdes') -> 'Request':
        '''todo'''
        return Request()


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

@enum.unique
class Effect(enum.Enum):
    '''
    Policy effect type. Allow, deny, etc.
    '''

    # ------------------------------
    # This is not a type:
    # ------------------------------

    INVALID = None
    '''No one is allowed to use this. Definitely an error...'''

    # ------------------------------
    # These are valid types:
    # ------------------------------

    ALLOW = 'allow'
    '''Allow specified rules to happen.'''

    DENY = 'deny'
    '''Deny specified rules from happening.'''


# -----------------------------------------------------------------------------
# The Policy Itself
# -----------------------------------------------------------------------------

class Policy:
    '''
    An ABAC Policy. Describes who is allowed to do what, when and where.

    Gets serialized to/from the repository.
    '''

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        self._id: PolicyId = None
        '''
        Identity number of the policy.
        '''

        self._name: str = None
        '''
        Short descriptive name of the policy for display purposes.
        '''

        self._description: str = None
        '''
        Long-form descriptive explanation of the policy.
        '''

        self._effect: 'Effect' = Effect.INVALID
        '''
        Outcome of the policy if the rules are matched.
        '''

        self._rules: 'Rules' = None
        '''
        Rules object for the actual policy rules.
        '''

        self._targets: 'Rules' = None
        '''
        Rules object for the actual policy rules.
        '''


# -----------------------------------------------------------------------------
# The Policy Decision Point aka PDP
# -----------------------------------------------------------------------------

class PolicyDecisionPoint:
    '''
    This class makes the actual yes/no call for allowing something to proceed.

    Caller must instantiate the correct Policy for that point in the code,
    otherwise what's the point?
    '''

    # TODO [2020-10-19]: implement this class. Must start off with __init__
    # that takes params, so we catch all points in the code currently making
    # stubs of this class.

    def allowed(self, request_context: 'SecurityContext') -> bool:
        '''
        Checks the request against our policy and returns:
          - True: You should proceed. Request's access/action/whatever is allow
            by the policy.
          - False: You should fail out, ignore, or otherwise disallow the
            request.
        '''
        # TODO [2020-10-19]: implement this:
        # Get request out of context, or have SecurityContext have direct
        # accessors into request data. That is, have SecurityContext return an
        # abac.Request, or have it be the abac.Request itself.
        return True
