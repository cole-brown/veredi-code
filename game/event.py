# coding: utf-8

'''
Events for the game engine itself.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from .ecs.event import Event


# -----------------------------------------------------------------------------
# Base Class
# -----------------------------------------------------------------------------

class EngineEvent(Event,
                  name_dotted='veredi.game.event.engine',
                  name_string='event.engine'):
    '''
    Base class for Veredi game Engine itself.
    '''

    def __str__(self):
        return f"{self.__class__.__name__}()"

    def __repr__(self):
        return f"{self.__class__.__name__}()"


# -----------------------------------------------------------------------------
# Stop the train!
# -----------------------------------------------------------------------------

class EngineStopRequest(EngineEvent,
                        name_dotted='veredi.game.event.engine.stop',
                        name_string='engine.stop'):
    # TODO: Take in data about requester?
    pass
