# coding: utf-8

'''
Event for Coding/Decoding data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Any, Optional, Set, Type

from ..ecs.base.component import Component


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Base Codec Components
# -----------------------------------------------------------------------------

class EncoderComponent(Component):
    def __init__(self,
                 component_id: ComponentId,
                 *args: Any,
                 **kwargs: Any) -> None:
        super().__init__(component_id, *args, **kwargs)

    def encode(self) -> None:
        '''
        Turns our in-game data into an encoded stream of data for serialization.

        Returns a stream for successful encoding, or None for failure.
        '''
        return None


class DecoderComponent(Component):
    def __init__(self,
                 component_id: ComponentId,
                 *args: Any,
                 **kwargs: Any) -> None:
        super().__init__(component_id, *args, **kwargs)

    def decode(self) -> None:
        '''
        Turns our deserialized stream of encoded data into in-game data.

        Returns data for successful decoding, or None for failure.
        '''
        return None


# -----------------------------------------------------------------------------
# YAML Codec Components
# -----------------------------------------------------------------------------

class YamlEncoderComponent(EncoderComponent):
    def __init__(self,
                 component_id: ComponentId,
                 *args: Any,
                 **kwargs: Any) -> None:
        super().__init__(component_id, *args, **kwargs)

    def encode(self) -> None:
        '''
        Turns our in-game data into an encoded stream of YAML for serialization.

        Returns a stream for successful encoding, or None for failure.
        '''
        # TODO: return a stream type of thing, not just string.
        return None


class YamlDecoderComponent(EncoderComponent):
    def __init__(self,
                 component_id: ComponentId,
                 *args: Any,
                 **kwargs: Any) -> None:
        super().__init__(component_id, *args, **kwargs)

    def decode(self) -> None:
        '''
        Turns our deserialized stream of YAML data into in-game data.

        Returns data for successful encoding, or None for failure.
        '''
        return None
