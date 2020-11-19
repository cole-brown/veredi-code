# coding: utf-8

'''
Events related to input from user. All input from user should be either
packaged up into an event or perhaps fed directly/firstly into InputSystem.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Any, Mapping
import enum

from veredi.game.ecs.event          import Event

from veredi.data.codec.encodable    import (Encodable,
                                            EncodableRegistry,
                                            EncodedSimple,
                                            EncodedComplex)
from veredi.base.enum               import (FlagCheckMixin,
                                            FlagSetMixin,
                                            FlagEncodeValueMixin)
from veredi.base.context            import VerediContext
from veredi.game.ecs.base.identity  import EntityId
from veredi.base.identity           import SerializableId
from veredi.interface.input.context import InputContext


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

@enum.unique
class Recipient(FlagEncodeValueMixin, FlagCheckMixin, FlagSetMixin, enum.Flag):
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

    # -------------------------------------------------------------------------
    # Encodable
    # -------------------------------------------------------------------------

    @classmethod
    def dotted(klass: 'Recipient') -> str:
        '''
        Unique dotted name for this class.
        '''
        return 'veredi.interface.output.recipient'

    @classmethod
    def _type_field(klass: 'Recipient') -> str:
        '''
        A short, unique name for encoding an instance into a field in a dict.
        '''
        return 'v.io.recip'


# Register ourself manually with the Encodable registry.
Recipient.register_manually()


# -----------------------------------------------------------------------------
# Base Output Event
# -----------------------------------------------------------------------------

class OutputEvent(Event, Encodable, dotted='veredi.interface.output.event'):
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

    # ------------------------------
    # Constants: Encodable
    # ------------------------------

    _ENCODE_NAME: str = 'event.output'
    '''Name for this class when encoding/decoding.'''

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

    @classmethod
    def _type_field(klass: 'OutputEvent') -> str:
        return klass._ENCODE_NAME

    def _encode_simple(self) -> EncodedSimple:
        '''
        Don't support simple for OutputEvents.
        '''
        msg = (f"{self.__class__.__name__} doesn't support encoding to a "
               "simple string.")
        raise NotImplementedError(msg)

    @classmethod
    def _decode_simple(klass: 'OutputEvent',
                       data: EncodedSimple) -> 'OutputEvent':
        '''
        Don't support simple by default.
        '''
        msg = (f"{klass.__name__} doesn't support decoding from a "
               "simple string.")
        raise NotImplementedError(msg)

    def _encode_complex(self) -> EncodedComplex:
        '''
        Encode ourself as an EncodedComplex, return that value.
        '''

        # Source ID can be an int or an EntityId.
        source_id = self.source_id
        if not isinstance(source_id, int):
            source_id = source_id.encode(None)

        # Source Type can be an int or an enum.
        source_type = self.source_type
        if not isinstance(source_type, int):
            source_type = source_type.encode(None)

        # Build output with our instance data.
        encoded = {
            'source_id': source_id,
            'source_type': source_type,
            'output': self.output.encode(None),
            'sid': self.serial_id.encode(None),
        }

        # Let these stick themselves into the data.
        self.desired_recipients.encode(encoded)

        # TODO [2020-11-06]: Leave out context or should we encode it?

        return encoded

    @classmethod
    def _decode_super(klass:    'OutputEvent',
                      instance: Optional['OutputEvent'],
                      data:     EncodedComplex) -> 'OutputEvent':
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
            source_id = EntityId.decode(source_id)
        instance._id = source_id

        # Source Type can be an enum or an int.
        source_type = data['source_type']
        if not isinstance(source_type, int):
            source_type = EncodableRegistry.decode(source_type)
        instance._type = source_type

        # Serial ID can be any SerializableId.
        serial_id = EncodableRegistry.decode(data['sid'],
                                             data_type=SerializableId,
                                             fallback=data['sid'])
        instance._serial_id = serial_id

        # Output is any old Encodable.
        output = EncodableRegistry.decode(data['output'],
                                          fallback=data['output'])
        instance._output = output

        # Recipients encoded themselves into data so they'll get themselves out
        # again.
        recipients = Recipient.decode(data)
        instance._recipients = recipients

        # Create and return a decoded instance.
        return instance

    @classmethod
    def _decode_complex(klass: 'OutputEvent',
                        data: EncodedComplex) -> 'OutputEvent':
        '''
        Use data and EncodableRegistry to figure out what OutputEvent subclass
        the data is, then decode the data using the subclass.

        Return a new instance of `klass` as the result of the decoding.
        '''
        actual_class = EncodableRegistry.get_from_data(data)

        # Not sure if this class is going to be an actual class or just base
        # class... So allow being an actual class.
        if actual_class == klass:
            return actual_class._decode_super(None, data)

        instance = actual_class._decode_complex(data)
        return instance

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return "OutEvent"
