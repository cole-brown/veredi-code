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
from veredi.logger       import log
from veredi.base.context import VerediContext

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
            error = "{} must have a name."
            error.format(arg_word)
            raise log.exception(TypeError(error, arg),
                                CommandRegisterError,
                                None,
                                context=context)
        if arg.type is None:
            error = "{} '{}' must have a type.".format(arg_word, arg.name)
            raise log.exception(TypeError(error, arg),
                                CommandRegisterError,
                                None,
                                context=context)

        if is_kwarg and not arg.kwarg:
            error = "{} '{}' must have a kwarg name."
            error = error.format(arg_word, arg.name)
            raise log.exception(TypeError(error, arg),
                                CommandRegisterError,
                                None,
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
                error = ("All args must be for same input type/language. "
                         "Previously had '{}' and now want '{}'.")
                error = error.format(self._language, InputLanguage.MATH)
                raise log.exception(TypeError(error, arg),
                                    CommandRegisterError,
                                    None,
                                    context=context)

        # Not a math arg, but we're in math mode - error.
        elif self._language == InputLanguage.MATH:
            error = ("All args must be for same input type/language. "
                     "Previously had '{}' and now want '{}'.")
            error = error.format(self._language, InputLanguage.TEXT)
            raise log.exception(TypeError(error, arg),
                                CommandRegisterError,
                                None,
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

        Returns parsed tuple of: (args, kwargs)
          - args is a list in correct order
          - kwargs is a dict
        '''
        args = []
        kwargs = {}

        if self.language == InputLanguage.MATH:
            # We're a math thing... We let the MathParser loose on the entire
            # input string.
            mather = InputContext.math(context)
            if not mather:
                error = ("No MathParser found in context; "
                         "cannot process input.")
                raise log.exception(AttributeError(error, input_safe),
                                    CommandExecutionError,
                                    None,
                                    context=context)
            tree = mather.parse(input_safe)
            if not tree:
                failure = CommandStatus.parsing(
                    input_safe,
                    "Failed parsing input into math expression.")
                return args, kwargs, failure

            args.append(tree)

        else:
            raise NotImplementedError(
                "TODO: Command.parse() for {} is not implemented yet.",
                self.language, self
            )

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
