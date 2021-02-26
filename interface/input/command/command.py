# coding: utf-8

'''
Command object for Veredi.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# ---
# Typing
# ---
from typing import (Optional, Any,
                    Iterable, Mapping,
                    Tuple, Callable,
                    Dict, List)

# ---
# Code
# ---
from veredi.logs         import log
from veredi.base.context import VerediContext

from veredi.base.null    import null_or_none
from .const              import CommandPermission
from ..const             import InputLanguage
from ..context           import InputContext
from .exceptions         import (CommandRegisterError,
                                 CommandExecutionError)

# Input-Related Events & Components
from .event              import CommandRegisterReply
from .args               import (CommandArgType,
                                 CommandArg,
                                 CommandKwarg,
                                 CommandStatus)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# TODO: a "register commands" event that InputSystem can send out once during
# loading phase... Needs to be after systems are done being created so all
# systems get a chance to respond.


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class Command:
    '''
    Command Pattern: Command 'interface'

    Thing registered in Commander to keep track of what kind of command this is
    and how to turn user input into something actionable for command receiver.
    '''

    def __init__(self, event: CommandRegisterReply) -> None:
        '''
        Initialize a Command from its CommandRegisterReply.
        '''
        self._name: str = event.name
        self._permissions: CommandPermission = event.permissions
        self._function: Callable = event.function
        self._args: List[CommandArg] = event.args
        self._kwargs: Dict[CommandKwarg] = event.kwargs
        self._language: InputLanguage = InputLanguage.INVALID

        self._validate_args(event.context)

    def _validate_args(self, context: VerediContext) -> None:
        '''
        Checks arg types for validity.

        Raises a CommandRegisterError if an arg fails validation.
        '''
        if not self._args and not self._kwargs:
            self._language = InputLanguage.NONE
            return

        # TODO [2020-06-15]: Make command creater register a language if we
        # can't auto-decide good.
        for arg in (self._args or ()):
            self._arg_validate(arg, context)

        for key in self._kwargs:
            arg = self._kwargs[key]
            self._arg_validate(arg, context)

    def _arg_validate(self,
                      arg: CommandArg,
                      context: VerediContext) -> InputLanguage:
        '''
        Validate this single arg.

        Raises a CommandRegisterError if it fails.
        '''

        is_kwarg = isinstance(arg, CommandKwarg)
        arg_word = "Arg" if not is_kwarg else "Kwarg"

        if not arg.name:
            msg = "{} must have a name.".format(arg_word)
            error = CommandRegisterError(
                msg,
                context=context,
                data={
                    'arg': arg,
                })
            raise log.exception(error,
                                msg,
                                context=context)

        if arg.type is None:
            msg = "{} '{}' must have a type.".format(arg_word, arg.name)
            error = CommandRegisterError(
                msg,
                context=context,
                data={
                    'arg': arg,
                })
            raise log.exception(error,
                                msg,
                                context=context)

        if is_kwarg and not arg.kwarg:
            msg = "{} '{}' must have a kwarg name."
            msg = msg.format(arg_word, arg.name)
            error = CommandRegisterError(
                msg,
                context=context,
                data={
                    'arg': arg,
                })
            raise log.exception(error,
                                msg,
                                context=context)

        if (isinstance(arg.type, CommandArgType)
            and (arg.type == CommandArgType.MATH
                 or arg.type == CommandArgType.VARIABLE)):
            # If set to a different language, raise error.
            if self._language in (InputLanguage.INVALID,
                                  InputLanguage.MATH):
                # Invalid or already-math, so that's fine.
                self._language = InputLanguage.MATH
            else:
                # Command that was some other lang now wants to be math for
                # this arg. Complain about this.
                msg = ("All args must be for same input type/language. "
                       "Previously had '{}' and now want '{}'.")
                msg = msg.format(self._language, InputLanguage.MATH)
                error = CommandRegisterError(
                    msg,
                    context=context,
                    data={
                        'lang': self._language,
                        'lang_input': InputLanguage.MATH,
                        'arg': arg,
                    })
                raise log.exception(error,
                                    msg,
                                    context=context)

        # Not a math arg, but we're in math mode - error.
        elif self._language == InputLanguage.MATH:
            msg = ("All args must be for same input type/language. "
                   "Previously had '{}' and now want '{}'.")
            msg = msg.format(self._language, InputLanguage.TEXT)
            error = CommandRegisterError(
                msg,
                context=context,
                data={
                    'lang': self._language,
                    'lang_input': InputLanguage.TEXT,
                    'arg': arg,
                })
            raise log.exception(error,
                                msg,
                                context=context)

        else:
            # Only other option right now:
            self._language = InputLanguage.TEXT

    # ---
    # Properties
    # ---

    @property
    def name(self):
        return self._name

    @property
    def permissions(self):
        return self._permissions

    @property
    def language(self):
        return self._language

    # @property
    # def function(self):
    #     return self._function

    # ---
    # Arguments
    # ---

    def parse(self,
              input_safe: str,
              context: VerediContext
              ) -> Tuple[Iterable, Dict[str, Any], CommandStatus]:
        '''
        Parse verified safe/sanitized `input_safe` string into the args &
        kwargs this command wants.

        Returns parsed tuple of: (args, kwargs, CommandStatus of parsing)
          - args is a list in correct order
          - kwargs is a dict
        '''
        if self.language == InputLanguage.NONE:
            # I think just a warning? Could error out, but don't see exactly
            # why I should - would be annoying to be the user in that case?
            if input_safe:
                log.warning(
                    "Command '{}' has no input args but received input.",
                    self.name,
                    context=context)
            return ([], {}, CommandStatus.successful(context))

        elif self.language == InputLanguage.MATH:
            return self._parse_math(input_safe, context)

        elif self.language == InputLanguage.TEXT:
            return self._parse_text(input_safe, context)

        # Er, oops?
        raise NotImplementedError(
            f"TODO: parse() for {self.language} is not implemented yet.",
            self
        )

    def _parse_math(self,
                    input_safe: str,
                    context: VerediContext
                    ) -> Tuple[Iterable, Dict[str, Any], CommandStatus]:
        '''
        Parse verified safe/sanitized `input_safe` string into the args &
        kwargs this math command wants.

        Returns parsed tuple of: (args, kwargs, CommandStatus)
          - args is a list in correct order
          - kwargs is a dict
        '''
        args = []
        kwargs = {}

        # We're a math thing... We let the MathParser loose on the entire
        # input string.
        mather = InputContext.math(context)
        if not mather:
            msg = "No MathParser found in context; cannot process input."
            error = CommandExecutionError(msg,
                                          context=context,
                                          data={
                                              'input_safe': input_safe,
                                              'mather': mather,
                                          })
            raise log.exception(error,
                                msg,
                                context=context)
        tree = mather.parse(input_safe)
        if not tree:
            failure = CommandStatus.parsing(
                input_safe,
                "Failed parsing input into math expression.",
                "Failed parsing input into math expression.")
            return args, kwargs, failure

        args.append(tree)

        return args, kwargs, CommandStatus.successful(context)

    def _parse_text(self,
                    input_safe: str,
                    context: VerediContext
                    ) -> Tuple[Iterable, Dict[str, Any], CommandStatus]:
        '''
        Parse verified safe/sanitized `input_safe` string into the args &
        kwargs this text command wants.

        Returns parsed tuple of: (args, kwargs, CommandStatus)
          - args is a list in correct order
          - kwargs is a dict
        '''
        args = []
        kwargs = {}

        # We're a text thing... so parse it ourself?
        remainder = input_safe
        for cmd_arg in self._args:
            parsed, remainder = cmd_arg.parse(remainder)
            if not null_or_none(parsed):
                args.append(parsed)

        if remainder:
            for cmd_kwarg in self._kwargs:
                parsed, remainder = cmd_kwarg.parse(remainder)
                if not null_or_none(parsed):
                    kwargs[cmd_kwarg.kwarg] = parsed

        return args, kwargs, CommandStatus.successful(context)

    # ---
    # Command Action / Execution
    # ---

    def execute(self,
                *args: Any,
                context: Optional[InputContext] = None,
                **kwargs: Mapping[str, Any]) -> CommandStatus:
        '''
        Execute our function with the args/kwargs supplied... Probably from a
        call to our parse() method.
        '''

        return self._function(*args, context=context, **kwargs)
