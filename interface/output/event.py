# coding: utf-8

'''
Events related to input from user. All input from user should be either
packaged up into an event or perhaps fed directly/firstly into InputSystem.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Any, Type, Mapping
import enum


from veredi.logs                    import log
from veredi.game.ecs.event          import Event
from veredi.data.codec              import (Encodable,
                                            EncodedSimple,
                                            EncodedComplex)
from veredi.base.enum               import FlagCheckMixin, FlagSetMixin
from veredi.base.context            import VerediContext
from veredi.game.ecs.base.identity  import EntityId
from veredi.base.identity           import SerializableId


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

@enum.unique
class Recipient(FlagCheckMixin, FlagSetMixin, enum.Flag):
    '''
    has() and any() provided by FlagCheckMixin.
    '''

    INVALID = 0

    # ------------------------------
    # Output to Users Types:
    # ------------------------------
    GM = enum.auto()
    '''Send this to the GM due to some special GM-only data.'''

    USER = enum.auto()
    '''Send this to the user who is responsible for it.'''

    BROADCAST = enum.auto()
    '''Send this to all users in the game.'''

    # ------------------------------
    # Other Output Types to Flag:
    # ------------------------------
    LOG = enum.auto()
    '''Send this output (formatted as would be for text client) to the log.'''


# -----------------------------------------------------------------------------
# Base Output Event
# -----------------------------------------------------------------------------

# [2021-03-09] Changed to disallow OutputEvent as a directly encodable class.
# class OutputEvent(Event, Encodable,
#                   name_dotted='veredi.interface.output.event',
#                   name_string='output'):
class OutputEvent(Event, Encodable):
    '''
    An event that should be show to the outside world (users?). Something that
    isn't just apparent in some other way.

    E.g. maybe an attack has an OutputEvent with how much damage the attack
    dealt, but how many hit points the target lost is only known via their
    health bar (or not at all if the gm is hiding that info).
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 source_id:   Union[int, EntityId],
                 source_type: Union[int, enum.Enum],
                 output:      Encodable,
                 context:     VerediContext,
                 serial_id:   SerializableId,
                 recipients: 'Recipient') -> None:
        self.set(source_id, source_type, output, context,
                 serial_id, recipients)

    def set(self,
            source_id:   Union[int, EntityId],
            source_type: Union[int, enum.Enum],
            output:      Encodable,
            context:     VerediContext,
            serial_id:   SerializableId,
            recipients: 'Recipient') -> None:
        super().set(source_id, source_type, context)
        self._output = output
        self._serial_id = serial_id
        self._recipients = recipients
        # self._designations = {
        #     str(source_id): InputContext.source_designation(context),
        # }

    def reset(self) -> None:
        super().reset()
        self._output = None
        self._serial_id = None
        self._recipients = None
        # self._designations = None

    # -------------------------------------------------------------------------
    # Output Things
    # -------------------------------------------------------------------------

    @property
    def output(self) -> Any:
        '''
        Returns the event's raw output (string, MathTree, whatever).
        '''
        return self._output

    # @property
    # def designations(self) -> Mapping[str, str]:
    #     '''
    #     Returns a dictionary of identifiers (dotted strs, IDs, etc.) to
    #     designations (entity display names, feat display names, etc).
    #     '''
    #     return self._designations
    #
    # @property
    # def title(self) -> str:
    #     '''
    #     Display Name / Title of this event.
    #
    #     e.g. "Skill Check"
    #     '''
    #     return self._title_main
    #
    # @property
    # def subtitle(self) -> str:
    #     '''
    #     Second Display Name / Sub-Title of this event.
    #
    #     e.g. "Sneakery"
    #     '''
    #     return self._title_sub

    @property
    def serial_id(self) -> SerializableId:
        '''
        SerializableId of this event - likely its InputId.
        '''
        return self._serial_id

    @property
    def source_type(self) -> Union[int, enum.Enum]:
        '''
        EntityTypeId of the entity responsible for this OutputEvent.
        '''
        return self.type

    @property
    def source_id(self) -> Union[int, EntityId]:
        '''
        EntityId of the entity responsible for this OutputEvent.
        '''
        return self.id

    @property
    def desired_recipients(self) -> 'Recipient':
        '''
        Desired recipients of this OutputEvent.
        '''
        return self._recipients

    # -------------------------------------------------------------------------
    # Encodable API
    # -------------------------------------------------------------------------

    def encode_simple(self, codec: 'Codec') -> EncodedSimple:
        '''
        Don't support simple for OutputEvents.
        '''
        msg = (f"{self.klass} doesn't support encoding to a "
               "simple string.")
        raise NotImplementedError(msg)

    @classmethod
    def decode_simple(klass: Type['OutputEvent'],
                      data:  EncodedSimple,
                      codec: 'Codec') -> 'OutputEvent':
        '''
        Don't support simple by default.
        '''
        msg = (f"{klass.klass} doesn't support decoding from a "
               "simple string.")
        raise NotImplementedError(msg)

    def encode_complex(self, codec: 'Codec') -> EncodedComplex:
        '''
        Encode ourself as an EncodedComplex, return that value.
        '''

        # Source ID can be an int or an EntityId.
        source_id = self.source_id
        if not isinstance(source_id, int):
            source_id = codec.encode(source_id)

        # Source Type can be an int or an enum.
        source_type = self.source_type
        if not isinstance(source_type, int):
            source_type = codec.encode(source_type)

        # Build output with our instance data.
        encoded = {
            'source_id': source_id,
            'source_type': source_type,
            'output': codec.encode(self.output),
            'sid': codec.encode(self.serial_id),
        }

        # Let these stick themselves into the data.
        codec.encode(self.desired_recipients,
                     encode_in_progress=encoded)

        # TODO [2020-11-06]: Leave out context or should we encode it?

        return encoded

    @classmethod
    def decode_complex(klass:    Type['OutputEvent'],
                       data:     EncodedComplex,
                       codec:    'Codec',
                       instance: Optional['OutputEvent'] = None
                       ) -> 'OutputEvent':
        '''
        Decode our vars from data into the instance and return it.
        '''
        # Check claims.
        klass.error_for(data,
                        keys=['source_id', 'source_type', 'output', 'sid'])
        Recipient.error_for_claim(data)

        # If no instance, we're decoding for ourself.
        if instance is None:
            instance = klass(None,
                             None,
                             None,
                             None,
                             None,
                             None)
        # ---
        # Decode this class's fields.
        # ---
        # Source ID can be int or EntityId.
        source_id = data['source_id']
        if not isinstance(source_id, int):
            source_id = codec.decode(EntityId, source_id)
        instance._id = source_id

        # Source Type can be an enum or an int.
        source_type = data['source_type']
        if not isinstance(source_type, int):
            source_type = codec.decode(None, source_type)
        instance._type = source_type

        # Serial ID can be any SerializableId.
        serial_id = codec.decode(None,
                                 data['sid'],
                                 reg_find_data_type=SerializableId,
                                 reg_fallback=data['sid'])
        instance._serial_id = serial_id

        # Output is any old Encodable.
        output = codec.decode(None,
                              data['output'],
                              reg_fallback=data['output'])
        instance._output = output

        # Recipients encoded themselves into data so they'll get themselves out
        # again.
        recipients = codec.decode(Recipient, data)
        instance._recipients = recipients

        # Create and return a decoded instance.
        return instance

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return "OutEvent"
