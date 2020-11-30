# coding: utf-8

'''
Functions in YAML.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from datetime import timedelta

from . import base
from .. import tags
from .. import registry

from veredi.time import parse


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Tags for Types
# -----------------------------------------------------------------------------

class TimeDuration(base.VerediYamlTag):
    # ---
    # registry / YAML tag
    # ---
    _YAML_TAG_NAME = 'duration'
    yaml_tag = tags.make(_YAML_TAG_NAME)

    def __init__(self, value):
        super().__init__(value)
        self.duration = parse.duration(value)

    @classmethod
    def from_yaml(cls, loader, node):
        # print(FnHas.yaml_tag, "from_yaml", str(cls), str(loader), str(node))
        return cls(node.value)

    def __float__(self):
        '''
        Convert the duration to a float of the total (micro)seconds.
        '''
        return self.duration / timedelta(microseconds=1)


# TODO [2020-10-07]: implicit_rx is bugged, somehow. '5 seconds' doesn't
# get picked up as a TimeDuration even though the regex produces a valid match.


# Register duration with its regex so it can be picked up implicitly
# (e.g. "foo: 5sec" will be picked up as TimeDuration without needing
# "foo: !duration 5sec" explicitly).
registry.register(TimeDuration._YAML_TAG_NAME,
                  TimeDuration,
                  decode_fn=None,
                  encode_fn=None,
                  implicit_rx=parse._TIME_DURATION_REGEX)
