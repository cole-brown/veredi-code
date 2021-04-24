# coding: utf-8

'''
Integration Test for a server and clients talking to each other over
websockets.

Only really tests the websockets and Mediator.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from .base                                  import Test_WebSockets_Base
from veredi.parallel                        import multiproc
from veredi.zest.base.multiproc             import ProcTest
from veredi.logs                            import log


# ---
# Mediation
# ---
from veredi.interface.mediator.const        import MsgType
from veredi.interface.mediator.message      import Message
from veredi.interface.mediator.context      import MessageContext
from veredi.interface.mediator.payload.bare import BarePayload


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

LOG_LEVEL = log.Level.INFO
'''Test should set this to desired during set_up()'''


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_WebSockets_Connect(Test_WebSockets_Base):

    # -------------------------------------------------------------------------
    # Set-Up & Tear-Down
    # -------------------------------------------------------------------------

    def set_up(self) -> None:
        self.DISABLED_TESTS = set({
            # Nothing, ideally.

            # # ---
            # # This is cheating.
            # # ---
            # 'test_ignored_tests',

            # # ---
            # # Simplest test.
            # # ---
            # 'test_nothing',

            # # ---
            # # More complex tests.
            # # ---
            # 'test_connect',
        })

        default_flags_server = ProcTest.NONE  # ProcTest.DNE
        default_flags_client = ProcTest.NONE  # ProcTest.DNE
        super().set_up(LOG_LEVEL,
                       default_flags_server,
                       default_flags_client)

    def tear_down(self):
        super().tear_down(LOG_LEVEL)

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    # ------------------------------
    # Check to see if we're blatently ignoring anything...
    # ------------------------------

    def test_ignored_tests(self):
        self.assert_test_ran(
            self.runner_of_test(self.do_test_ignored_tests))

    # ------------------------------
    # Test doing nothing and cleaning up.
    # ------------------------------

    def test_nothing(self):
        # No checks for this, really. Just "does it properly not explode"?
        self.assert_test_ran(
            self.runner_of_test(self.do_test_nothing))

    # ------------------------------
    # Test Client Requesting Connection to Server.
    # ------------------------------

    def test_connect(self):
        # self.debugging = True
        with log.LoggingManager.on_or_off(self.debugging):
            self.assert_test_ran(
                self.runner_of_test(self.do_test_connect, *self.proc.clients))


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi run zest/integration/communication/zest_cs_websocket_connect

if __name__ == '__main__':
    import unittest
    unittest.main()
