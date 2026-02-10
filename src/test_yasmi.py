# -*- coding: utf-8 -*-
# MIT license; Copyright (c) 2021-2025, Planet Innovation
# 436 Elgar Road, Box Hill, 3128, VIC, Australia
# Phone: +61 3 9945 7510
#

# pyright: reportPrivateUsage=false

"""YASMI Unit tests.

Each of these creates a simple state machine and runs through a simple scenario.
For each, there are diagrams representing the state machine as well as
the sequence performed by the test.

These tests should be used as a guide for implementing one's own state machine on top of YASMI.
"""

import logging
import unittest
import asyncio
from typing import Tuple

import yasmi
from testing_support import async_test, Mock, plantuml_logging, plantuml_logger

logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(message)s')
logger = logging.getLogger("TestYASMI")


# MARK: TestStateMachine1
class TestStateMachine1(unittest.TestCase):
    """Tests the simplest state machine.

    This is the simplest state machine, with a single state.
    """

    class NewState(yasmi.State):
        """A basic, empty state."""

    class NewStateMachine(yasmi.StateMachine):
        """A state machine containing a single state."""

        def __init__(self) -> None:
            """Instantiates the single state."""
            super().__init__()
            self._state_1 = self._create_child(TestStateMachine1.NewState)

            self._set_transitions_per_state(
                {
                    self._initial: self._initial_transitions,
                }
            )

        async def dummy_action(self) -> None:
            """Dummy action for executing during a transition."""

        async def _initial_transitions(self) -> None:
            """Transition from the initial state to the New State."""
            await self._transition_to(self._state_1, self.dummy_action)

    @async_test
    @plantuml_logging
    async def test_state_machine_1(self) -> None:
        """Tests that the state machine correctly initialises and transitions to the single state."""
        state_machine, state_machine_mock = self._setup()

        # Run the test
        await state_machine.start()
        self.assertEqual(state_machine.active_state_types, ["NewState"])
        state_machine_mock.assert_called_once("async_dummy_action")
        state_machine_mock.assert_called_once("async_entry_actions")
        state_machine_mock.assert_called_once("async_do_actions")
        await state_machine.stop_ticker()

    def _setup(self) -> Tuple[NewStateMachine, Mock]:
        state_machine = self.NewStateMachine()
        state_machine_mock = Mock()
        state_machine.dummy_action = state_machine_mock.async_dummy_action
        state_machine._state_1.entry_actions = state_machine_mock.async_entry_actions
        state_machine._state_1.do_actions = state_machine_mock.async_do_actions
        state_machine._state_1.exit_actions = state_machine_mock.async_exit_actions
        return state_machine, state_machine_mock


# MARK: TestStateMachine2
class TestStateMachine2(unittest.TestCase):
    """Tests the simplest state machine with a composite state.

    This is the simplest state machine, with a single composite state and sub-state
    and no entry action, do actions, exit actions or transition actions.
    """

    class NewState(yasmi.State):
        """A basic, empty state."""

    class NewCompositeState(yasmi.CompositeState):
        def __init__(self, super_state: yasmi.CompositeState | None):
            """Instantiates the single sub-state."""
            super().__init__(super_state)
            self._state_1 = self._create_child(TestStateMachine2.NewState)

            self._set_transitions_per_state(
                {
                    self._initial: self._initial_transitions,
                }
            )

        async def dummy_action(self) -> None:
            """Dummy action for executing during a transition."""

        async def _initial_transitions(self) -> None:
            """Transition from the initial state to New State."""
            await self._transition_to(self._state_1, self.dummy_action)

    class NewStateMachine(yasmi.StateMachine):
        def __init__(self):
            """Instantiates the single composite state."""
            super().__init__()
            self._state_1 = self._create_child(TestStateMachine2.NewCompositeState)

            self._set_transitions_per_state(
                {
                    self._initial: self._initial_transitions,
                }
            )

        async def dummy_action(self) -> None:
            """Dummy action for executing during a transition."""

        async def _initial_transitions(self) -> None:
            """Transition from the initial state to New Composite State."""
            await self._transition_to(self._state_1, self.dummy_action)

    @async_test
    @plantuml_logging
    async def test_state_machine_2(self) -> None:
        """Tests that the state machine correctly initialises runs correctly.

        Tests that the state machine transitions into the composite state then to the basic state.
        """
        state_machine, state_machine_mock, state_machine_state_1_mock = self._setup()

        # Run the test
        await state_machine.start()
        self.assertEqual(state_machine.active_state_types, ["NewCompositeState", "NewState"])
        state_machine_mock.assert_called_once("async_dummy_action")
        state_machine_mock.assert_called_once("async_entry_actions")
        state_machine_mock.assert_called_once("async_do_actions")
        state_machine_state_1_mock.assert_called_once("async_dummy_action")
        state_machine_state_1_mock.assert_called_once("async_entry_actions")
        state_machine_state_1_mock.assert_called_once("async_do_actions")
        await state_machine.stop_ticker()

    def _setup(self) -> Tuple[NewStateMachine, Mock, Mock]:
        state_machine = self.NewStateMachine()
        state_machine_mock = Mock()
        state_machine.dummy_action = state_machine_mock.async_dummy_action
        state_machine._state_1.entry_actions = state_machine_mock.async_entry_actions
        state_machine._state_1.do_actions = state_machine_mock.async_do_actions
        state_machine._state_1.exit_actions = state_machine_mock.async_exit_actions
        state_machine_state_1_mock = Mock()
        state_machine._state_1.dummy_action = state_machine_state_1_mock.async_dummy_action
        state_machine._state_1._state_1.entry_actions = state_machine_state_1_mock.async_entry_actions
        state_machine._state_1._state_1.do_actions = state_machine_state_1_mock.async_do_actions
        state_machine._state_1._state_1.exit_actions = state_machine_state_1_mock.async_exit_actions
        return state_machine, state_machine_mock, state_machine_state_1_mock


# MARK: TestStateMachine3
class TestStateMachine3(unittest.TestCase):
    """Tests a simple state machine with two states.

    This is a simple state machine with two states and transitions between them.
    """


    class NewState1(yasmi.State):
        """A basic, empty state."""

    class NewState2(yasmi.State):
        """A basic, empty state."""

    class NewStateMachine(yasmi.StateMachine):
        """A new state machine with two sub-states."""

        def __init__(self) -> None:
            super().__init__()
            plantuml_logger.debug("participant Events")
            self.event = yasmi.Event(self)
            self._state_1 = self._create_child(TestStateMachine3.NewState1)
            self._state_2 = self._create_child(TestStateMachine3.NewState2)

            self._set_transitions_per_state(
                {
                    self._initial: self._initial_transitions,
                    self._state_1: self._state_1_transitions,
                    self._state_2: self._state_2_transitions,
                }
            )

        async def dummy_action_1(self) -> None:
            """Dummy action for executing during a transition."""

        async def dummy_action_2(self) -> None:
            """Dummy action for executing during a transition."""

        async def dummy_action_3(self) -> None:
            """Dummy action for executing during a transition."""

        async def _initial_transitions(self) -> None:
            """Transition from the initial state to New Composite State."""
            await self._transition_to(self._state_1, self.dummy_action_1)

        async def _state_1_transitions(self) -> None:
            """Transitions from New State 1 to New State 2."""
            if self.event():
                await self._transition_to(self._state_2, self.dummy_action_2)

        async def _state_2_transitions(self) -> None:
            """Transitions from New State 2 to New State 1."""
            if self.event():
                await self._transition_to(self._state_1, self.dummy_action_3)

    @async_test
    @plantuml_logging
    async def test_state_machine_3(self) -> None:
        """Executes the test scenario."""
        state_machine, state_machine_mock = self._setup()

        # Run the test
        await state_machine.start()
        self.assertEqual(state_machine.active_state_types, ["NewState1"])
        state_machine_mock.assert_called_once("async_dummy_action_1")
        state_machine_mock.assert_called_once("async_entry_actions_1")
        state_machine_mock.assert_called_once("async_do_actions_1")

        await state_machine.event.set()
        self.assertEqual(state_machine.active_state_types, ["NewState2"])
        state_machine_mock.assert_called_once("async_exit_actions_1")
        state_machine_mock.assert_called_once("async_dummy_action_2")
        state_machine_mock.assert_called_once("async_entry_actions_2")
        state_machine_mock.assert_called_once("async_do_actions_2")

        state_machine_mock.reset_calls_for("async_entry_actions_1")
        state_machine_mock.reset_calls_for("async_do_actions_1")
        await state_machine.event.set()
        self.assertEqual(state_machine.active_state_types, ["NewState1"])
        state_machine_mock.assert_called_once("async_exit_actions_2")
        state_machine_mock.assert_called_once("async_dummy_action_3")
        state_machine_mock.assert_called_once("async_entry_actions_1")
        state_machine_mock.assert_called_once("async_do_actions_1")

        await state_machine.stop_ticker()

    def _setup(self) -> Tuple[NewStateMachine, Mock]:
        state_machine = self.NewStateMachine()
        state_machine_mock = Mock()
        state_machine.dummy_action_1 = state_machine_mock.async_dummy_action_1
        state_machine.dummy_action_2 = state_machine_mock.async_dummy_action_2
        state_machine.dummy_action_3 = state_machine_mock.async_dummy_action_3
        state_machine._state_1.entry_actions = state_machine_mock.async_entry_actions_1
        state_machine._state_1.do_actions = state_machine_mock.async_do_actions_1
        state_machine._state_1.exit_actions = state_machine_mock.async_exit_actions_1
        state_machine._state_2.entry_actions = state_machine_mock.async_entry_actions_2
        state_machine._state_2.do_actions = state_machine_mock.async_do_actions_2
        state_machine._state_2.exit_actions = state_machine_mock.async_exit_actions_2
        return state_machine, state_machine_mock


# MARK: TestStateMachine3a
class TestStateMachine3a(unittest.TestCase):
    """Tests a simple state machine with two states and custom actions.

    This is the same as StateMachine3 but with the entry, do and exit actions customised.
    """

    class NewState1(yasmi.State):
        async def entry_actions(self) -> None:
            self._my_entry_function()

        async def do_actions(self) -> None:
            self._my_do_function()

        async def exit_actions(self) -> None:
            self._my_exit_function()

        def _my_entry_function(self) -> None:
            pass

        def _my_do_function(self) -> None:
            pass

        def _my_exit_function(self) -> None:
            pass

    class NewState2(yasmi.State):
        async def entry_actions(self) -> None:
            self._my_entry_function()

        async def do_actions(self) -> None:
            self._my_do_function()

        async def exit_actions(self) -> None:
            self._my_exit_function()

        def _my_entry_function(self) -> None:
            pass

        def _my_do_function(self) -> None:
            pass

        def _my_exit_function(self) -> None:
            pass

    class NewStateMachine(yasmi.StateMachine):
        """A new state machine with two sub-states."""

        def __init__(self) -> None:
            super().__init__()
            plantuml_logger.debug("participant Events")
            self.event = yasmi.Event(self)
            self._state_1 = self._create_child(TestStateMachine3a.NewState1)
            self._state_2 = self._create_child(TestStateMachine3a.NewState2)

            self._set_transitions_per_state(
                {
                    self._initial: self._initial_transitions,
                    self._state_1: self._state_1_transitions,
                    self._state_2: self._state_2_transitions,
                }
            )

        async def dummy_action_1(self) -> None:
            """Dummy action for executing during a transition."""

        async def dummy_action_2(self) -> None:
            """Dummy action for executing during a transition."""

        async def dummy_action_3(self) -> None:
            """Dummy action for executing during a transition."""

        async def _initial_transitions(self) -> None:
            """Transition from the initial state to New Composite State."""
            await self._transition_to(self._state_1, self.dummy_action_1)

        async def _state_1_transitions(self) -> None:
            """Transitions from New State 1 to New State 2."""
            if self.event():
                await self._transition_to(self._state_2, self.dummy_action_2)

        async def _state_2_transitions(self) -> None:
            """Transitions from New State 2 to New State 1."""
            if self.event():
                await self._transition_to(self._state_1, self.dummy_action_3)

    @async_test
    @plantuml_logging
    async def test_state_machine_3a(self) -> None:
        """Executes the test scenario."""
        state_machine, state_machine_mock = self._setup()

        # Run the test
        await state_machine.start()
        self.assertEqual(state_machine.active_state_types, ["NewState1"])
        state_machine_mock.assert_called_once("async_dummy_action_1")
        state_machine_mock.assert_called_once("entry_function_1")
        state_machine_mock.assert_called_once("do_function_1")

        await state_machine.event.set()
        self.assertEqual(state_machine.active_state_types, ["NewState2"])
        state_machine_mock.assert_called_once("exit_function_1")
        state_machine_mock.assert_called_once("async_dummy_action_2")
        state_machine_mock.assert_called_once("entry_function_2")
        state_machine_mock.assert_called_once("do_function_2")

        state_machine_mock.reset_calls_for("entry_function_1")
        state_machine_mock.reset_calls_for("do_function_1")
        await state_machine.event.set()
        self.assertEqual(state_machine.active_state_types, ["NewState1"])
        state_machine_mock.assert_called_once("exit_function_2")
        state_machine_mock.assert_called_once("async_dummy_action_3")
        state_machine_mock.assert_called_once("entry_function_1")
        state_machine_mock.assert_called_once("do_function_1")

        await state_machine.stop_ticker()

    def _setup(self) -> Tuple[NewStateMachine, Mock]:
        state_machine = self.NewStateMachine()
        state_machine_mock = Mock()
        state_machine.dummy_action_1 = state_machine_mock.async_dummy_action_1
        state_machine.dummy_action_2 = state_machine_mock.async_dummy_action_2
        state_machine.dummy_action_3 = state_machine_mock.async_dummy_action_3
        state_machine._state_1._my_entry_function = state_machine_mock.entry_function_1
        state_machine._state_1._my_do_function = state_machine_mock.do_function_1
        state_machine._state_1._my_exit_function = state_machine_mock.exit_function_1
        state_machine._state_2._my_entry_function = state_machine_mock.entry_function_2
        state_machine._state_2._my_do_function = state_machine_mock.do_function_2
        state_machine._state_2._my_exit_function = state_machine_mock.exit_function_2
        return state_machine, state_machine_mock


# MARK: TestStateMachine4
class TestStateMachine4(unittest.TestCase):
    """Tests composite states and history states.

    Tests a state machine with two composite states as follows:

      - Composite State 1 has two sub-states and transitions to a final state, triggering
        a default transition to Composite State 2.
      - Composite State 2 has a history state as well as two sub-states.
    """

    class NewState1(yasmi.State):
        """A basic, empty state."""

    class NewState2(yasmi.State):
        """A basic, empty state."""

    class NewState3(yasmi.State):
        """A basic, empty state."""

    class NewState4(yasmi.State):
        """A basic, empty state."""

    class NewCompositeState1(yasmi.CompositeState):
        def __init__(self, super_state: yasmi.CompositeState | None, event: yasmi.Event):
            yasmi.CompositeState.__init__(self, super_state)
            self._event = event
            self._state_1 = TestStateMachine4.NewState1(self)
            self._state_2 = TestStateMachine4.NewState2(self)

            self._set_transitions_per_state(
                {
                    self._initial: self._initial_transitions,
                    self._state_1: self._state_1_transitions,
                    self._state_2: self._state_2_transitions,
                }
            )

        async def dummy_action_3(self) -> None:
            """Dummy action for executing during a transition."""

        async def _initial_transitions(self) -> None:
            """Transition from the initial state to New Composite State."""
            await self._transition_to(self._state_1)

        async def _state_1_transitions(self) -> None:
            """Transitions from New State 1 to New State 2."""
            if self._event():
                await self._transition_to(self._state_2, self.dummy_action_3)

        async def _state_2_transitions(self) -> None:
            """Transitions from New State 2 to final."""
            if self._event():
                await self._transition_to(self._final)

    class NewCompositeState2(yasmi.CompositeState):
        def __init__(self, super_state: yasmi.CompositeState | None, event: yasmi.Event) -> None:
            yasmi.CompositeState.__init__(self, super_state, has_history=True)
            self._event = event
            self._state_1 = TestStateMachine4.NewState3(self)
            self._state_2 = TestStateMachine4.NewState4(self)
            assert self._history is not None

            self._set_transitions_per_state(
                {
                    self._initial: self._initial_transitions,
                    self._history: self._history_transitions,
                    self._state_1: self._state_1_transitions,
                    self._state_2: self._state_2_transitions,
                }
            )

        async def dummy_action_4(self) -> None:
            """Dummy action for executing during a transition."""

        async def dummy_action_5(self) -> None:
            """Dummy action for executing during a transition."""

        async def dummy_action_6(self) -> None:
            """Dummy action for executing during a transition."""

        async def _initial_transitions(self) -> None:
            """Transition from the initial state to New Composite State."""
            await self._transition_to(self._state_1, self.dummy_action_4)

        async def _history_transitions(self) -> None:
            """Transition from the initial state to New Composite State."""
            await self._handle_history()

        async def _state_1_transitions(self) -> None:
            """Transitions from New State 3 to New State 4."""
            if self._event():
                await self._transition_to(self._state_2, self.dummy_action_5)

        async def _state_2_transitions(self) -> None:
            """Transitions from New State 4 to New State 3."""
            if self._event():
                await self._transition_to(self._final, self.dummy_action_6)

    class NewStateMachine(yasmi.StateMachine):
        """A state machine with two composite states, with the second one having a history state."""

        def __init__(self) -> None:
            """Creates both sub composite states and the transition event."""
            super().__init__()
            plantuml_logger.debug("participant Events")
            self.event_1 = yasmi.Event(self, "event 1")
            self.event_2 = yasmi.Event(self, "event 2")
            self._state_1 = TestStateMachine4.NewCompositeState1(self, self.event_1)
            self._state_2 = TestStateMachine4.NewCompositeState2(self, self.event_1)

            self._set_transitions_per_state(
                {
                    self._initial: self._initial_transitions,
                    self._state_1: self._state_1_transitions,
                    self._state_2: self._state_2_transitions,
                }
            )

        async def dummy_action_1(self) -> None:
            """Dummy action for executing during a transition."""

        async def dummy_action_2(self) -> None:
            """Dummy action for executing during a transition."""

        async def _initial_transitions(self) -> None:
            """Transition from the initial state to New Composite State."""
            await self._transition_to(self._state_1)

        async def _state_1_transitions(self) -> None:
            """Transitions from New State 1 to New State 2."""
            if self._state_1.is_at_final_state():
                await self._transition_to(self._state_2, self.dummy_action_1)
            elif self.event_2():
                await self._transition_to(self._state_2)

        async def _state_2_transitions(self) -> None:
            """Transitions from New State 2 to New State 1."""
            if self._state_2.is_at_final_state():
                await self._transition_to(self._state_1)
            elif self.event_2():
                await self._transition_to(self._state_1, self.dummy_action_2)

    @async_test
    @plantuml_logging
    async def test_state_machine_4(self) -> None:
        """Tests a transition sequence through the state machine.

        Tests the following transition sequence:

            1. Start the state machine and expect it to go to NewCompositeState1:NewState1
            2. Trigger a transition to NewCompositeState1:NewState2
            3. Trigger a transition to the NewCompositeState1:Final pseudo-state

               a. Should then automatically transition to NewCompositeState2, then
               b. NewCompositeState2:Initial pseudo-state, then
               c. NewCompositeState2:NewState3

            4. Trigger a transition to NewCompositeState2:NewState4
            5. Trigger a transition from NewCompositeState2 to NewCompositeState1

               a. Should exit NewCompositeState2:NewState4 directly (not via
                  the NewCompositeState2:Final pseudo-state), then
               b. Should automatically trigger a transition to NewCompositeState1:NewState1 then

            6. Trigger a transition from NewCompositeState1:NewState1 to NewCompositeState2

               a. Should transition directly to NewCompositeState2:NewState4 (not via
                  the NewCompositeState2:Initial pseudo-state and NewCompositeState2:NewState3)
                  due to the NewCompositeState2:History pseudo-state.

        Args:
            mocker: facilitates mocking of state entry, exit, do and transition actions
        """
        state_machine, state_machine_mock = self._setup()

        # Run the test
        await state_machine.start()
        self.assertEqual(state_machine.active_state_types, ["NewCompositeState1", "NewState1"])
        state_machine_mock.assert_called_once("async_entry_actions_1")
        state_machine_mock.assert_called_once("async_do_actions_1")
        state_machine_mock.assert_called_once("async_entry_actions_11")
        state_machine_mock.assert_called_once("async_do_actions_11")

        await state_machine.event_1.set()
        self.assertEqual(state_machine.active_state_types, ["NewCompositeState1", "NewState2"])
        state_machine_mock.assert_called_once("async_exit_actions_11")
        state_machine_mock.assert_called_once("async_dummy_action_3")
        state_machine_mock.assert_called_once("async_entry_actions_12")
        state_machine_mock.assert_called_once("async_do_actions_12")

        await state_machine.event_1.set()
        await asyncio.sleep(0)  # need this extra yield to complete the transition from the 'final' state
        self.assertEqual(state_machine.active_state_types, ["NewCompositeState2", "NewState3"])
        state_machine_mock.assert_called_once("async_exit_actions_12")
        state_machine_mock.assert_called_once("async_exit_actions_1")
        state_machine_mock.assert_called_once("async_dummy_action_1")
        state_machine_mock.assert_called_once("async_entry_actions_2")
        state_machine_mock.assert_called_once("async_do_actions_2")
        state_machine_mock.assert_called_once("async_dummy_action_4")
        state_machine_mock.assert_called_once("async_entry_actions_21")
        state_machine_mock.assert_called_once("async_do_actions_21")

        await state_machine.event_1.set()
        self.assertEqual(state_machine.active_state_types, ["NewCompositeState2", "NewState4"])
        state_machine_mock.assert_called_once("async_exit_actions_21")
        state_machine_mock.assert_called_once("async_dummy_action_5")
        state_machine_mock.assert_called_once("async_entry_actions_22")
        state_machine_mock.assert_called_once("async_do_actions_22")

        state_machine_mock.reset_calls_for("async_do_actions_1")
        await state_machine.event_2.set()
        self.assertEqual(state_machine.active_state_types, ["NewCompositeState1", "NewState1"])
        state_machine_mock.assert_called_once("async_exit_actions_22")
        state_machine_mock.assert_called_once("async_exit_actions_2")
        state_machine_mock.assert_called_once("async_dummy_action_2")
        state_machine_mock.assert_called_once("async_entry_actions_1")
        state_machine_mock.assert_called_once("async_do_actions_1")
        state_machine_mock.assert_called_once("async_entry_actions_11")
        state_machine_mock.assert_called_once("async_do_actions_11")

        state_machine_mock.reset_calls_for("async_do_actions_2")
        await state_machine.event_2.set()
        self.assertEqual(state_machine.active_state_types, ["NewCompositeState2", "NewState4"])
        state_machine_mock.assert_called_once("async_exit_actions_1")
        state_machine_mock.assert_called_once("async_entry_actions_2")
        state_machine_mock.assert_called_with("async_do_actions_2")
        state_machine_mock.assert_called_once("async_entry_actions_22")
        state_machine_mock.assert_called_once("async_do_actions_22")

        await state_machine.stop_ticker()

    def _setup(self) -> Tuple[NewStateMachine, Mock]:
        state_machine = self.NewStateMachine()
        state_machine_mock = Mock()
        state_machine.dummy_action_1 = state_machine_mock.async_dummy_action_1
        state_machine.dummy_action_2 = state_machine_mock.async_dummy_action_2
        state_machine._state_1.dummy_action_3 = state_machine_mock.async_dummy_action_3
        state_machine._state_2.dummy_action_4 = state_machine_mock.async_dummy_action_4
        state_machine._state_2.dummy_action_5 = state_machine_mock.async_dummy_action_5
        state_machine._state_2.dummy_action_6 = state_machine_mock.async_dummy_action_6
        state_machine._state_1.entry_actions = state_machine_mock.async_entry_actions_1
        state_machine._state_1.do_actions = state_machine_mock.async_do_actions_1
        state_machine._state_1.exit_actions = state_machine_mock.async_exit_actions_1
        state_machine._state_2.entry_actions = state_machine_mock.async_entry_actions_2
        state_machine._state_2.do_actions = state_machine_mock.async_do_actions_2
        state_machine._state_2.exit_actions = state_machine_mock.async_exit_actions_2
        state_machine._state_1._state_1.entry_actions = state_machine_mock.async_entry_actions_11
        state_machine._state_1._state_1.do_actions = state_machine_mock.async_do_actions_11
        state_machine._state_1._state_1.exit_actions = state_machine_mock.async_exit_actions_11
        state_machine._state_1._state_2.entry_actions = state_machine_mock.async_entry_actions_12
        state_machine._state_1._state_2.do_actions = state_machine_mock.async_do_actions_12
        state_machine._state_1._state_2.exit_actions = state_machine_mock.async_exit_actions_12
        state_machine._state_2._state_1.entry_actions = state_machine_mock.async_entry_actions_21
        state_machine._state_2._state_1.do_actions = state_machine_mock.async_do_actions_21
        state_machine._state_2._state_1.exit_actions = state_machine_mock.async_exit_actions_21
        state_machine._state_2._state_2.entry_actions = state_machine_mock.async_entry_actions_22
        state_machine._state_2._state_2.do_actions = state_machine_mock.async_do_actions_22
        state_machine._state_2._state_2.exit_actions = state_machine_mock.async_exit_actions_22
        return state_machine, state_machine_mock


# MARK: TestStateMachine5
class TestStateMachine5(unittest.TestCase):
    """Tests composite states, history states and concurrency.

    Tests a state machine with two composite states as follows:

      - Composite State 1 transitions to a final state, triggering a default transition to Composite State 2.
      - Composite State 2 has a history state as well as two, concurrent regions, each with two sub-states.
    """

    class NewState1(yasmi.State):
        """A basic, empty state."""

    class NewState2(yasmi.State):
        """A basic, empty state."""

    class NewState3(yasmi.State):
        """A basic, empty state."""

    class NewState4(yasmi.State):
        """A basic, empty state."""

    class NewState5(yasmi.State):
        """A basic, empty state."""

    class NewState6(yasmi.State):
        """A basic, empty state."""

    class NewCompositeState1(yasmi.CompositeState):
        def __init__(self, super_state: yasmi.CompositeState | None, event_1: yasmi.Event) -> None:
            yasmi.CompositeState.__init__(self, super_state)
            self._event_1 = event_1
            self._state_1 = TestStateMachine5.NewState1(self)
            self._state_2 = TestStateMachine5.NewState2(self)

            self._set_transitions_per_state(
                {
                    self._initial: self._initial_transitions,
                    self._state_1: self._state_1_transitions,
                    self._state_2: self._state_2_transitions,
                }
            )

        async def _initial_transitions(self) -> None:
            await self._transition_to(self._state_1)

        async def _state_1_transitions(self) -> None:
            if self._event_1():
                await self._transition_to(self._state_2)

        async def _state_2_transitions(self) -> None:
            if self._event_1():
                await self._transition_to(self._final)

    class NewCompositeState2(yasmi.ConcurrentCompositeState):
        def __init__(self, super_state: yasmi.CompositeState | None, event_1: yasmi.Event, event_3: yasmi.Event) -> None:
            yasmi.ConcurrentCompositeState.__init__(self, 2, super_state)
            self._event_1 = event_1
            self._event_3 = event_3
            self._state_1 = TestStateMachine5.NewState3(self)
            self._state_2 = TestStateMachine5.NewState4(self)
            self._state_3 = TestStateMachine5.NewState5(self)
            self._state_4 = TestStateMachine5.NewState6(self)

            self._set_transitions_per_state(
                {
                    self._initial: self._initial_transitions,
                    self._state_1: self._state_1_transitions,
                    self._state_2: self._state_2_transitions,
                    self._state_3: self._state_3_transitions,
                    self._state_4: self._state_4_transitions,
                }
            )

        async def _initial_transitions(self) -> None:
            await self._transition_to(self._state_1, 0)
            await self._transition_to(self._state_3, 1)

        async def _state_1_transitions(self) -> None:
            if self._event_1():
                await self._transition_to(self._state_2, 0)

        async def _state_2_transitions(self) -> None:
            if self._event_1():
                await self._transition_to(self._final, 0)

        async def _state_3_transitions(self) -> None:
            if self._event_3():
                await self._transition_to(self._state_4, 1)

        async def _state_4_transitions(self) -> None:
            if self._event_3():
                await self._transition_to(self._final, 1)

    class NewStateMachine(yasmi.StateMachine):
        """A state machine with two composite states, with the second one having a history state."""

        def __init__(self) -> None:
            """Creates both sub composite states and the transition event."""
            yasmi.StateMachine.__init__(self)
            self.event_1 = yasmi.Event(self)
            self.event_2 = yasmi.Event(self)
            self.event_3 = yasmi.Event(self)
            self._state_1 = TestStateMachine5.NewCompositeState1(self, self.event_1)
            self._state_2 = TestStateMachine5.NewCompositeState2(self, self.event_1, self.event_3)

            self._set_transitions_per_state(
                {
                    self._initial: self._initial_transitions,
                    self._state_1: self._state_1_transitions,
                    self._state_2: self._state_2_transitions,
                }
            )

        async def dummy_action(self) -> None:
            """Dummy action for executing during a transition."""

        async def _initial_transitions(self) -> None:
            await self._transition_to(self._state_1)

        async def _state_1_transitions(self) -> None:
            if self._state_1.is_at_final_state():
                await self._transition_to(self._state_2)
            elif self.event_2():
                await self._transition_to(self._state_2)

        async def _state_2_transitions(self) -> None:
            if self._state_2.is_at_final_state():
                await self._transition_to(self._state_1)
            if self.event_2():
                await self._transition_to(self._state_1)

    @async_test
    async def test_state_machine_5(self) -> None:
#         """Tests a transition sequence through the state machine.

#         Tests the following transition sequence:

#             1. Start the state machine and expect it to go to NewCompositeState1:NewState1
#             2. Trigger a transition to NewCompositeState1:NewState2
#             3. Trigger a transition to the NewCompositeState1:Final pseudo-state

#                a. Should then automatically transition to NewCompositeState2, then
#                b. NewCompositeState2:Initial pseudo-state, then
#                c. NewCompositeState2:NewState3,NewState5

#             4. Trigger a transition from NewState3 to NewState4
#             5. Trigger a transition from NewCompositeState2 to NewCompositeState1

#                a. Should exit NewCompositeState2:NewState4 directly (not via
#                   the NewCompositeState2:Final pseudo-state), then
#                b. Should automatically trigger a transition to NewCompositeState1:NewState1 then

#             6. Trigger a transition from NewCompositeState1:NewState1 to NewCompositeState2

#                a. Should transition directly to NewCompositeState2:NewState4 (not via
#                   the NewCompositeState2:Initial pseudo-state and NewCompositeState2:NewState3)
#                   due to the NewCompositeState2:History pseudo-state.
#         """
        state_machine = self._setup()

        # Run the test
        await state_machine.start()
        self.assertEqual(state_machine.active_state_types, ["NewCompositeState1", "NewState1"])

        await state_machine.event_1.set()
        self.assertEqual(state_machine.active_state_types, ["NewCompositeState1", "NewState2"])

        await state_machine.event_1.set()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        self.assertEqual(state_machine.active_state_types, ["NewCompositeState2", ["NewState3", "NewState5"]])

        await state_machine.event_1.set()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        self.assertEqual(state_machine.active_state_types, ["NewCompositeState2", ["NewState4", "NewState5"]])

        await state_machine.event_3.set()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        self.assertEqual(state_machine.active_state_types, ["NewCompositeState2", ["NewState4", "NewState6"]])

        await state_machine.event_1.set()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        self.assertEqual(state_machine.active_state_types, ["NewCompositeState2", ["NewState6"]])

        await state_machine.event_3.set()
        await state_machine.trigger_tick()  # needed to trigger detection of concurrent final state
        await asyncio.sleep(0.1)
        await state_machine.trigger_tick()  # trigger again to process the final state transition
        await asyncio.sleep(0.1)
        self.assertEqual(state_machine.active_state_types, ["NewCompositeState1", "NewState1"])

        await state_machine.stop_ticker()

    def _setup(self) -> NewStateMachine:
        return self.NewStateMachine()



if __name__ == "__main__":
    unittest.main()
