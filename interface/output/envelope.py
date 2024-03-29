# coding: utf-8

'''
Envelope for an output message. Might not contain a message (yet) - might
just contain info for making a message, or for finding/storing a future
message.

Envelope (when ready) will be passed from OutputSystem to MediatorSystem
(probably) via event.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# ---
# Typing
# ---
from typing import (TYPE_CHECKING,
                    Optional, Union, Any, Type, Callable,
                    Set, List, Dict, Iterable)
if TYPE_CHECKING:
    from decimal                   import Decimal

    from veredi.base.context       import VerediContext
    from veredi.game.ecs.component import ComponentManager
    from veredi.game.ecs.entity    import EntityManager
    from veredi.game.ecs.manager   import EcsManager


# ---
# Code
# ---
from veredi.base.strings           import labeler
from veredi.data                   import background
from veredi.data.codec             import (Codec,
                                           Encodable,
                                           EncodedSimple,
                                           EncodedComplex)

from veredi.logs                   import log
from veredi.security               import abac
from veredi.base.identity          import SerializableId

from veredi.game.ecs.base.identity import EntityId
from veredi.data.identity          import UserId, UserKey

from .event                        import OutputEvent, Recipient
from ..user                        import BaseUser

from ..mediator.const              import MsgType
from ..mediator.message            import Message, MsgIdTypes
from ..mediator.payload.base       import BasePayload


# -----------------------------------------------------------------------------
# Envelope Address
# -----------------------------------------------------------------------------

class Address(Encodable,
              name_dotted='veredi.interface.output.address',
              name_string='address'):
    '''
    Info for translating from Recipient to Users of a specific output format,
    which is dictated by `security_subject`. Maybe 'output security level' or
    'output information level' is better than 'output format'.
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Initialization: Instance
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Init instance vars, type hinting, doc strings.
        '''
        self._recipient: Recipient = Recipient.INVALID
        '''Recipient type of this Address.'''

        self._security_subject: abac.Subject = abac.Subject.INVALID
        '''
        Security type of this Address - primarily for deciding all of the data
        these users get sent.
        '''

        self._user_ids: List[UserId] = []
        '''
        The UserIds of the users that qualified as recipient type and passed
        any/all security check(s).
        '''

    def __init__(self,
                 recipient:        Recipient,
                 security_subject: abac.Subject,
                 users:            List[BaseUser]) -> None:
        '''
        Ignores any Falsy users. Saves the UserIds of the rest.
        '''
        self._define_vars()

        self._recipient = recipient
        self._security_subject = security_subject

        for user in users:
            if not user:
                continue
            self._user_ids.append(user.id)

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def recipient(self) -> Recipient:
        '''
        Get recipient type of Address.
        '''
        return self._recipient

    @property
    def security_subject(self) -> abac.Subject:
        '''
        Get security.abac.Subject type of Address.
        '''
        return self._security_subject

    @property
    def user_ids(self) -> List[UserId]:
        '''
        Get list of UserIds for this Address.
        '''
        return self._user_ids

    # -------------------------------------------------------------------------
    # Encodable API
    # -------------------------------------------------------------------------

    def encode_simple(self, codec: 'Codec') -> EncodedSimple:
        '''
        Don't support simple for Addresss.
        '''
        msg = (f"{self.klass} doesn't support encoding to a "
               "simple string.")
        raise NotImplementedError(msg)

    @classmethod
    def decode_simple(klass: Type['Address'],
                      data:  EncodedSimple,
                      codec: 'Codec') -> 'Address':
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

        # Encode our user ids.
        encoded_users = []
        for uid in self.user_ids:
            if not uid:
                continue
            encoded_users.append(codec.encode(uid))

        # Put our data into a dict for encoding.
        encoded = {
            'users': encoded_users,
            'valid_recipients': codec.encode(self._recipient),
            'subject': codec.encode(self._security_subject),
        }

        return encoded

    @classmethod
    def decode_complex(klass: Type['Address'],
                       data:  EncodedComplex,
                       codec: 'Codec',
                       instance: Optional['Address'] = None) -> 'Address':
        '''
        Decode ourself from an EncodedComplex, return a new instance of `klass`
        as the result of the decoding.
        '''
        # Check claims.
        klass.error_for(data,
                        keys=['users'])
        Recipient.error_for_claim(data)
        abac.Subject.error_for_claim(data)

        # Decode users list.
        users = []
        for uid in data['users']:
            users.append(codec.decode(UserId, uid))

        # Have others grab themselves from data.
        recipient = codec.decode(Recipient, data['valid_recipients'])
        subject = codec.decode(abac.Subject, data['subject'])

        # Create and return a decoded instance.
        return klass(recipient, subject, users)

    # -------------------------------------------------------------------------
    # Python Functions
    # -------------------------------------------------------------------------

    def __str__(self) -> str:
        return (
            f"{self.klass}"
            f"[{self._recipient}, "
            f"{self._security_subject}]("
            f"{self._user_ids})"
        )

    def __repr__(self):
        return (
            "<Addr["
            f"{self._recipient}, "
            f"{self._security_subject}]("
            f"{self._user_ids})>"
        )


# -----------------------------------------------------------------------------
# Message Envelope
# -----------------------------------------------------------------------------

class Envelope(Encodable,
               name_dotted='veredi.interface.output.envelope',
               name_string='envelope'):
    '''
    A container for a message, with some meta-data about the message.
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self):
        '''
        Instance vars with type hinting, doc strings, etc.
        '''
        # ------------------------------
        # Basic/Initial Info
        # ------------------------------
        self._event: OutputEvent = None

        # ------------------------------
        # Final Info
        # ------------------------------
        self._recipients: Recipient = Recipient.INVALID
        '''All (validated) Recipients that we will be trying to send to.'''

        self._addresses: Dict[Recipient, Address] = {}
        '''Storage for Recipient -> user info.'''

        # # TODO: Hold multiple messages or just create on demand?
        # self._payloads: Dict[Recipient, Message] = {}
        # '''Message Payloads by each Recipient.'''
        #
        # self._message: Dict[Recipient, Message] = {}
        # '''Messages by each Recipient.'''

    def __init__(self,
                 event: OutputEvent
                 # TODO: SecurityContext?
                 ) -> None:

        self._define_vars()

        self._event = event

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def context(self) -> Optional['VerediContext']:
        '''
        Returns the envelope's intended recipient flags. These are what the
        data source told us were acceptable recipients for the data.
        '''
        return self._event.context

    @property
    def desired_recipients(self) -> Optional[Recipient]:
        '''
        Returns the envelope's intended recipient flags. These are what the
        data source told us were acceptable recipients for the data.
        '''
        return self._event.desired_recipients

    @property
    def valid_recipients(self) -> Optional[Recipient]:
        '''
        Returns the envelope's validated recipient flags. These are what we
        have had verified/authorized by an external source and been reported
        the results of.
        '''
        return self._recipients

    @valid_recipients.setter
    def valid_recipients(self, value: Recipient) -> None:
        '''
        Sets the envelope's validated recipient flags. These are expected to be
        verified/authorized by an external source before this is set.
        '''
        self._recipients = value

    @property
    def data(self) -> Optional[Any]:
        '''
        Returns the envelope's raw data (not Message or Payload - just the data
        that will be used to build payloads and then messages).
        '''
        return self._event.output

    @property
    def source_id(self) -> EntityId:
        '''
        Returns the EntityId of the envelope's raw data's "owner" - the primary
        entity who should know all the Top Secret things about the data if
        there are any.
        '''
        return self._event.source_id

    @property
    def id(self) -> SerializableId:
        '''
        Returns the OutputEvent's `serial_id`. Probably an id pass all the way
        from input.
        '''
        return self._event.serial_id

    # -------------------------------------------------------------------------
    # Addresses
    # -------------------------------------------------------------------------

    def address(self, recipient: Recipient) -> Optional[Address]:
        '''
        Returns Address entry for recipient, or None if not found.
        '''
        # ---
        # Sanity Checks
        # ---
        if not recipient.is_solo:
            err_msg = ("Recipient must be a single receipient value."
                       f"Got: '{recipient}'")
            error = ValueError(err_msg, recipient)
            raise log.exception(error, err_msg)

        return self._addresses.get(recipient, None)

    def set_address(self,
                    recipient:        Recipient,
                    security_subject: 'abac.Subject',
                    users:            Iterable[BaseUser]) -> None:
        '''
        Set/overwrite an address for the recipient.
        '''
        # ---
        # Sanity Checks
        # ---
        if not recipient.is_solo:
            err_msg = ("Recipient must be a single receipient value."
                       f"Got: '{recipient}'")
            error = ValueError(err_msg, recipient)
            raise log.exception(error, err_msg)

        address = Address(recipient, security_subject, users)
        self._addresses[recipient] = address

    # -------------------------------------------------------------------------
    # Messages
    # -------------------------------------------------------------------------

    def message(self,
                msg_id:           MsgIdTypes,
                security_subject: 'abac.Subject',
                user:             BaseUser) -> Optional[Message]:
        '''
        Creates a message for the `user` at `security_subject`.

        Returns None if no message for that recipient.
        '''
        # ---
        # Sanity Checks
        # ---
        if not security_subject.is_solo:
            err_msg = ("security_subject must be a single value."
                       f"Got: '{security_subject}' for user {user}.")
            error = ValueError(err_msg, security_subject, user)
            raise log.exception(error, err_msg)

        # -------------------------------
        # Payload == OutputEvent's Output
        # -------------------------------
        payload = self._event.output

        # -------------------------------
        # Build Message
        # -------------------------------
        message = Message(msg_id,
                          MsgType.ENCODED,
                          payload=payload,
                          # entity_id=user.entity_prime,
                          user_id=user.id,
                          user_key=user.key,
                          subject=security_subject)
        return message

    # -------------------------------------------------------------------------
    # Encodable API
    # -------------------------------------------------------------------------

    def encode_simple(self, codec: 'Codec') -> EncodedSimple:
        '''
        Don't support simple for Envelopes.
        '''
        msg = (f"{self.klass} doesn't support encoding to a "
               "simple string.")
        raise NotImplementedError(msg)

    @classmethod
    def decode_simple(klass: Type['Envelope'],
                      data:  EncodedSimple,
                      codec: 'Codec') -> 'Envelope':
        '''
        Don't support simple for Envelopes.
        '''
        msg = (f"{klass.klass} doesn't support decoding from a "
               "simple string.")
        raise NotImplementedError(msg)

    def encode_complex(self, codec: 'Codec') -> EncodedComplex:
        '''
        Encode ourself as an EncodedComplex, return that value.
        '''

        encoded = {
            'valid_recipients': codec.encode(self.valid_recipients),
            'addresses': codec.encode_map(self._addresses),
            'event': codec.encode(self._event),
        }

        return encoded

    @classmethod
    def decode_complex(klass: Type['Envelope'],
                       data:  EncodedComplex,
                       codec: 'Codec',
                       instance: Optional['Envelope'] = None) -> 'Envelope':
        '''
        Decode ourself from an EncodedComplex, return a new instance of `klass`
        as the result of the decoding.
        '''
        klass.error_for(data,
                        keys=[
                            'valid_recipients',
                            'addresses',
                            'event',
                        ])

        # Decode our fields.
        recipients = codec.decode(Recipient, data['valid_recipients'])
        addresses = codec.decode_map(Address,
                                     data['addresses'],
                                     # Tell it to expect Recipients as keys.
                                     (Recipient,))
        event = codec.decode(None,
                             data['event'],
                             reg_data_type=OutputEvent)

        envelope = klass(event)
        envelope._recipients = recipients
        envelope._addresses = addresses

        return envelope

    # -------------------------------------------------------------------------
    # Python Functions
    # -------------------------------------------------------------------------

    def __str__(self) -> str:
        return (
            f"{self.klass}"
            f"[{self._recipients}, "
            f"{self._addresses}]("
            f"{self._event})"
        )

    def __repr__(self):
        return (
            "<Env["
            f"{self._recipients}, "
            f"{self._addresses}]("
            f"{self._event})>"
        )
