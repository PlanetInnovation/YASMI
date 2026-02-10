# -*- coding: utf-8 -*-
# MIT license; Copyright (c) 2021-2025, Planet Innovation
# 436 Elgar Road, Box Hill, 3128, VIC, Australia
# Phone: +61 3 9945 7510
#

"""Yet Another State Machine Implementation (YASMI, in the tradition of YAML)

This is intended to be a minimal state machine *framework* implementation that makes extensive use
of asyncio and supports the following state machine characteristics:

  - an arbitrary number of composite and simple states
  - entry, do and exit actions, which can be async functions, for simple and composite states
  - transition actions
  - initial, final, history and deep history pseudo-states in composite states
  - concurrent states
"""

import logging
import asyncio
from typing import Callable, Optional, Awaitable, TypeVar, Type, Any, List, Set, Generic, Union

logger = logging.getLogger("StateMachine")
logger.setLevel(logging.WARNING)

plantuml_logger = logging.getLogger("PlantUML")
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(message)s"))
handler.setLevel(logging.DEBUG)
plantuml_logger.addHandler(handler)

ActiveStates = List[Union["State", Set["State"]]]

_POLL_INTERVAL_S = 0.05
"""Interval for checking event status.
Too short will increase CPU use.
Too long will increase latency.
"""

T = TypeVar("T")


# MARK: State
class State:
    """The base State class.

    This is to be inherited by all simple states, composite states and the top-level state machine.

    Note:
        A client is prevented from instantiating this class directly.  Rather, it must be sub-classed to create
        an application-specific :py:class:`State`.

    Attributes:
        _super_state:      the super-state of this one, either a composite state or the top-level
                           state machine - optional for the case where :py:class:`State` is a
                           base state of a :py:class:`StateMachine` (which has no :py:attr:`super_state`)
    """

    def __init__(self, super_state: Optional["BaseCompositeState"] = None) -> None:
        """Creates a state.

        Creates a state by initialising its attributes.

        Args:
            super_state: The super composite state of this one if it exists
        """
        self._super_state: BaseCompositeState | None = super_state
        self.name = self.__class__.__name__

    def __str__(self) -> str:
        """Gets the name of this state (its class name).

        Returns:
            state name
        """
        return self.name[1:] if self.name[0] == "_" else self.name

    def __hash__(self) -> int:
        return hash(str(self))

    @property
    def state_machine(self) -> "StateMachine":
        if isinstance(self, StateMachine):
            return self
        else:
            assert self._super_state is not None
            return self._super_state.state_machine

    def activate(self) -> None:
        """Adds the state to the stack of *active* states.

        Adds the state to the stack of *active* states to have their :py:meth:`do` methods executed.
        """
        self.state_machine.active_states.append(self)
        logger.debug("%s activated: %s", str(self), str(self.state_machine.active_state_types))

    def deactivate(self) -> None:
        """Stops the state executing within its :py:meth:`_do_task`."""
        self.state_machine.active_states.pop()
        logger.debug("%s deactivated: %s", str(self), str(self.state_machine.active_state_types))

    def activate_concurrent_state(self) -> None:
        """Starts the state executing within its :py:meth:`_do_task`."""
        if not isinstance(self.state_machine.active_states[-1], set):
            self.state_machine.active_states.append(set())

        assert isinstance(self.state_machine.active_states[-1], set)
        self.state_machine.active_states[-1].add(self)
        logger.debug("%s activated: %s", str(self), str(self.state_machine.active_state_types))

    def deactivate_concurrent_state(self) -> None:
        """Stops the state executing within its :py:meth:`_do_task`."""
        assert isinstance(self.state_machine.active_states[-1], set)
        self.state_machine.active_states[-1].remove(self)

        if not self.state_machine.active_states[-1]:
            self.state_machine.active_states.pop()

        logger.debug("%s deactivated: %s", str(self), str(self.state_machine.active_state_types))

    async def transition(self, new_state: "State", *actions: Callable[[], Awaitable[None]]) -> "State":
        """Manages a transition from this, current state to the specified new state.

        Performs the following:
            1. Exits the current :py:class:`State`, performing any :py:meth:`exit_actions`
            2. Performs any transition `actions`
            3. Enters the `new_state`, performing any :py:meth:`entry_actions`
            4. Activates the `new_state` so its :py:meth:`do_task` resumes (if it is not a :py:class:`FinalState`)

        Args:
            new_state: the target state for the transition
            actions:   an optional list of actions to perform during the transition - intended to be of short duration
                       and non-blocking

        Returns:
            the specified `new_state`
        """
        await self.exit()
        logger.info("%s -> %s", str(self), str(new_state))

        for action in actions:
            await action()

        if not isinstance(new_state, (_InitialState, _FinalState, _BaseHistoryState)):
            await new_state.entry()

        if not isinstance(new_state, _FinalState):
            if isinstance(self._super_state, ConcurrentCompositeState):
                new_state.activate_concurrent_state()
            else:
                new_state.activate()

        return new_state

    async def entry(self) -> None:
        """Generates PlantUML log messages and runs any entry behaviour for this state."""
        plantuml_logger.debug("activate %s", str(self))
        plantuml_logger.debug("%s -> %s : entry()", str(self), str(self))
        await self.entry_actions()

    async def do(self) -> None:
        """Generates a PlantUML log message then runs any :py:meth:`_do` behaviour until deactivated."""
        plantuml_logger.debug("%s -> %s : do()", str(self), str(self))
        await self.do_actions()

    async def exit(self) -> None:
        """Exits this state.

        Exits this state by performing the following actions:

            1. Deactivating the state and wait until it is finished any actions
            2. Performing any exit actions
            3. Removing it from the set of active states

        Raises:
            AssertionError:
                All State and CompositeState instances must have a 'super' state, all the way up
                to a top-level StateMachine instance
        """
        if not isinstance(self, (_InitialState, _FinalState, _BaseHistoryState)):
            plantuml_logger.debug("%s -> %s : exit()", str(self), str(self))
            await self.exit_actions()
            assert self._super_state is not None, "super state is None"

            if isinstance(self._super_state, ConcurrentCompositeState):
                assert isinstance(
                    self.state_machine.active_states[-1], set
                ), "the top of the stack should be a set of concurrent states"
                assert (
                    self in self.state_machine.active_states[-1]
                ), f"{str(self)} is not at top of stack {self.state_machine.active_state_types}"
                self.deactivate_concurrent_state()
            else:
                assert (
                    self == self.state_machine.active_states[-1]
                ), f"{str(self)} is not at top of stack {self.state_machine.active_state_types}"
                self.deactivate()

            plantuml_logger.debug("deactivate %s", str(self))

    async def entry_actions(self) -> None:
        """For the client to override if the sub-classed state has 'entry' actions."""

    async def do_actions(self) -> None:
        """For the client to override if the sub-classed state has 'do' actions.

        These should be functions and coroutines that expect to be repeatedly executed.
        They should not block (in an async way) the current execution thread for too long as this will
        delay exit from the state when it is deactivated.
        """

    async def exit_actions(self) -> None:
        """For the client to override if the sub-classed state has 'exit' actions."""


# MARK: _InitialState(State)
class _InitialState(State):
    """Initial pseudo state."""

    def __init__(self, super_state: "BaseCompositeState") -> None:
        super().__init__(super_state)

    def __str__(self) -> str:
        return str(self._super_state) + "_initial"


# MARK: _FinalState(State)
class _FinalState(State):
    """Final pseudo state."""

    def __init__(self, super_state: "BaseCompositeState") -> None:
        super().__init__(super_state)

    def __str__(self) -> str:
        return str(self._super_state) + "_final"


# MARK: _BaseHistoryState(State)
class _BaseHistoryState(State):
    """History pseudo state.

    Attributes:
        states_to_return_to: temporarily stores the active state(s), within the containing :py:class:`CompositeState`,
                             at the time of transition away from the :py:class:`CompositeState`
    """

    def __str__(self) -> str:
        return str(self._super_state) + "_history"


# MARK: _HistoryState(_BaseHistoryState)
class _HistoryState(_BaseHistoryState):
    """History pseudo state.

    Attributes:
        states_to_return_to: temporarily stores the active state(s), within the containing :py:class:`CompositeState`,
                             at the time of transition away from the :py:class:`CompositeState`
    """

    def __init__(self, super_state: "CompositeState") -> None:
        """Creates a `HistoryState`.

        Args:
            super_state: the containing :py:class:`CompositeState` - this should never be None
                         (ie. never use the default value) as it only makes sense in the context of a
                         containing state
        """
        assert super_state is not None
        super().__init__(super_state)
        self.state_to_return_to: State | None = None


# MARK: _ConcurrentHistoryState(_BaseHistoryState)
class _ConcurrentHistoryState(_BaseHistoryState):
    """History pseudo state.

    Attributes:
        states_to_return_to: temporarily stores the active state(s), within the containing :py:class:`CompositeState`,
                             at the time of transition away from the :py:class:`CompositeState`
    """

    def __init__(self, super_state: "ConcurrentCompositeState", concurrent_state_count: int) -> None:
        """Creates a `HistoryState`.

        Args:
            super_state: the containing :py:class:`CompositeState` - this should never be None
                         (ie. never use the default value) as it only makes sense in the context of a
                         containing state
        """
        assert super_state is not None
        super().__init__(super_state)
        self.states_to_return_to: list[State | None] = [None] * concurrent_state_count


S = TypeVar("S")
C = TypeVar("C")


# MARK: BaseCompositeState(State)
class BaseCompositeState(State):
    """The base CompositeState class.

    This is to be inherited by all composite states and the top-level state machine.
    Along with its own behaviour as a :py:class:`State`, it manages transitions between its sub-states.

    Note:
        A client is prevented from instantiating this class directly.  Rather, it must be sub-classed to create
        an application-specific :py:class:`CompositeState`.

    Attributes:
        _has_history:           whether this contains a :py:class:`HistoryState`
        _initial:               the entry point if there is no history active
        _final:                 the exit point if the state exits under its control, rather than being forced to exit
                                by its super state
        _transitions_per_state: a map of async functions per state to manage the transition from that state
                                - intended to be updated by the subclass of this class
    """

    def __init__(self, super_state: Optional["CompositeState"] = None) -> None:
        """Instantiates a composite state.

        Initialises all attributes and adds the `manage` task to the set of tasks.

        Args:
            super_state:            this state's super state
            has_history:            whether this composite state maintains a history
        """
        super().__init__(super_state)
        self._initial = _InitialState(self)
        self._final = _FinalState(self)
        self._transitions_per_state: dict[State, Callable[[], Awaitable[None]]] = {}

    def _create_child(self, child_state_type: Type[S], *args: Any) -> S:
        return child_state_type(self, *args)  # type: ignore

    def _set_transitions_per_state(self, transitions_per_state: dict[State, Callable[[], Awaitable[None]]]) -> None:
        self._transitions_per_state.update(transitions_per_state)


# MARK: CompositeState(BaseCompositeState)
class CompositeState(BaseCompositeState):
    """The base CompositeState class.

    This is to be inherited by all composite states and the top-level state machine.
    Along with its own behaviour as a :py:class:`State`, it manages transitions between its sub-states.

    Note:
        A client is prevented from instantiating this class directly.  Rather, it must be sub-classed to create
        an application-specific :py:class:`CompositeState`.

    Attributes:
        _has_history:           whether this contains a :py:class:`HistoryState`
        _initial:               the entry point if there is no history active
        _final:                 the exit point if the state exits under its control, rather than being forced to exit
                                by its super state
        _states:                the currently active sub state(s)
        _history:               the state to return to if this composite state keeps a history
        _transitions_per_state: a map of async functions per state to manage the transition from that state
                                - intended to be updated by the subclass of this class
    """

    def __init__(
        self,
        super_state: Optional["CompositeState"] = None,
        has_history: bool = False,
    ) -> None:
        """Instantiates a composite state.

        Initialises all attributes and adds the `manage` task to the set of tasks.

        Args:
            super_state:            this state's super state
            has_history:            whether this composite state maintains a history
            concurrent_state_count: maximum number of concurrent states required for this composite state
        """
        super().__init__(super_state)
        self._history: _HistoryState | None = _HistoryState(self) if has_history else None  # type: ignore
        self._state: State = self._initial

    async def _transition_to(self, new_state: "State", *actions: Callable[[], Awaitable[None]]) -> None:
        """Manages a transition from the current sub state to the specified new one, for each active sub-state.

        Args:
            new_state:   the state to transition to
            state_index: the index of the relevant concurrent state thread
            actions:     actions to perform during the transition
        """
        self._state = await self._state.transition(new_state, *actions)

        if isinstance(self._state, _FinalState):
            await self.state_machine.trigger_tick()

    async def _handle_history(self) -> None:
        """Manages a transition target per whether the composite state has an active history.

        Args:
            concurrent_state_index: the index of the relevant concurrent region
        """
        assert self._history is not None
        assert (target_state := self._history.state_to_return_to) is not None
        logger.debug("history target state = %s", str(target_state))
        await self._transition_to(target_state)
        self._history.state_to_return_to = None

    async def do(self) -> None:
        """Manages :py:meth:`_do` behaviour and internal transitions."""
        await self.do_actions()
        plantuml_logger.debug("%s -> %s : do()", str(self), str(self))
        await self._transitions()

    async def exit(self) -> None:
        """Exits this composite state, after first exiting the active sub states.

        Also clears any pending was_polled event that occurred while the final state was active.
        """
        await self._state.exit()

        if self._history is not None and self._state != self._final:
            self._history.state_to_return_to = self._state
            self._state = self._history
        else:
            self._state = self._initial

        await super().exit()

    def is_at_final_state(self) -> bool:
        """Whether this composite state is at its final state.

        Returns:
            bool: whether at the final state
        """
        return self._state == self._final

    async def _transitions(self) -> None:
        """Finds and executes the transition function for each active state.

        Note: If the active state is the initial or history (of which there is only one per composite state),
        then the transitions to each concurrent state should be specified by the subclass.

        For example:

            async def _initial_transitions(self) -> None:
                await self._transition_to(self._state_1, 0)
                await self._transition_to(self._state_3, 1)

            async def _history_transitions(self) -> None:
                await self._handle_history(0)
                await self._handle_history(1)
        """
        transition_function: Optional[Callable[[], Awaitable[None]]] = self._transitions_per_state.get(self._state)
        if transition_function is not None:
            await transition_function()


# MARK: ConcurrentCompositeState(BaseCompositeState)
class ConcurrentCompositeState(BaseCompositeState):
    """The base CompositeState class.

    This is to be inherited by all composite states and the top-level state machine.
    Along with its own behaviour as a :py:class:`State`, it manages transitions between its sub-states.

    Note:
        A client is prevented from instantiating this class directly.  Rather, it must be sub-classed to create
        an application-specific :py:class:`CompositeState`.

    Attributes:
        _has_history:           whether this contains a :py:class:`HistoryState`
        _initial:               the entry point if there is no history active
        _final:                 the exit point if the state exits under its control, rather than being forced to exit
                                by its super state
        _states:                the currently active sub state(s)
        _history:               the state to return to if this composite state keeps a history
        _transitions_per_state: a map of async functions per state to manage the transition from that state
                                - intended to be updated by the subclass of this class
    """

    def __init__(
        self,
        concurrent_state_count: int,
        super_state: Optional["CompositeState"] = None,
        has_history: bool = False,
    ) -> None:
        """Instantiates a composite state.

        Initialises all attributes and adds the `manage` task to the set of tasks.

        Args:
            super_state:            this state's super state
            has_history:            whether this composite state maintains a history
            concurrent_state_count: maximum number of concurrent states required for this composite state
        """
        super().__init__(super_state)

        self._history: _ConcurrentHistoryState | None = (
            _ConcurrentHistoryState(self, concurrent_state_count) if has_history else None  # type: ignore
        )

        self._states: list[State] = [self._initial] * concurrent_state_count

    async def _transition_to(
        self, new_state: "State", state_index: int = 0, *actions: Callable[[], Awaitable[None]]
    ) -> None:
        """Manages a transition from the current sub state to the specified new one, for each active sub-state.

        Args:
            new_state:   the state to transition to
            state_index: the index of the relevant concurrent state thread
            actions:     actions to perform during the transition
        """
        self._states[state_index] = await self._states[state_index].transition(new_state, *actions)

    async def _handle_history(self, concurrent_state_index: int) -> None:
        """Manages a transition target per whether the composite state has an active history.

        Args:
            concurrent_state_index: the index of the relevant concurrent region
        """
        assert self._history is not None
        assert (target_state := self._history.states_to_return_to[concurrent_state_index]) is not None
        await self._transition_to(target_state, concurrent_state_index)
        self._history.states_to_return_to[concurrent_state_index] = None

    async def do(self) -> None:
        """Manages :py:meth:`_do` behaviour and internal transitions."""
        await self.do_actions()
        plantuml_logger.debug("%s -> %s : do()", str(self), str(self))
        await self._transitions()

    async def exit(self) -> None:
        """Exits this composite state, after first exiting the active sub states.

        Also clears any pending was_polled event that occurred while the final state was active.
        """
        for state in self._states:
            await state.exit()

        if self._history is not None and any(state != self._final for state in self._states):
            for i, state in enumerate(self._states):
                self._history.states_to_return_to[i] = state
                self._states[i] = self._history
        else:
            for i, state in enumerate(self._states):
                self._states[i] = self._initial

        await super().exit()

    def is_at_final_state(self) -> bool:
        """Whether this composite state is at its final state.

        Returns:
            bool: whether at the final state
        """
        return all(state == self._final for state in self._states)

    async def _transitions(self) -> None:
        """Finds and executes the transition function for each active state.

        Note: If the active state is the initial or history (of which there is only one per composite state),
        then the transitions to each concurrent state should be specified by the subclass.

        For example:

            async def _initial_transitions(self) -> None:
                await self._transition_to(self._state_1, 0)
                await self._transition_to(self._state_3, 1)

            async def _history_transitions(self) -> None:
                await self._handle_history(0)
                await self._handle_history(1)
        """
        transition_functions: list[Optional[Callable[[], Awaitable[None]]]] = (
            [self._transitions_per_state.get(state) for state in self._states]
            if self._states[0] not in (self._initial, self._history)
            else [self._transitions_per_state.get(self._states[0])]
        )

        transitions: list[Awaitable[None]] = [
            transition_function() for transition_function in transition_functions if transition_function is not None
        ]
        await asyncio.gather(*transitions)


# MARK: StateMachine(CompositeState)
class StateMachine(CompositeState):
    """The abstract base State Machine class.

    This is to be inherited by the top-level state machine.

    Note:
        A client is prevented from instantiating this class directly.  Rather, it must be sub-classed to create
        an application-specific :py:class:`StateMachine`.

    Attributes:
        active_states: for tracking the active state (or states if there are concurrent
                       or composite states) in this state machine
    """

    def __init__(self) -> None:
        """Creates a `StateMachine`."""
        super().__init__()
        self._tick_event = asyncio.Event()
        self.active_states: ActiveStates = []

    @property
    def active_state_types(self) -> List[str | List[str]]:  # type: ignore
        """Gets all the currently active states.

        Returns:
            the set of active states
        """
        return [
            (sorted(list(str(state) for state in item)) if isinstance(item, set) else str(item))
            for item in self.active_states
        ][1:]

    async def trigger_tick(self):
        """To trigger the state machine to detect an event.

        The asyncio.sleep() appears to be required to tick over the event loop
        in micropython.
        """
        self._tick_event.set()
        await asyncio.sleep(0)

    def clear_active_states(self) -> None:
        """Gets all the currently active states."""
        self.active_states.clear()

    async def start(self):
        """Starts the state machine.

        Starts the state machine by performing the following:
          1. Adding the state machine to the list of active states
          2. Creating the ticker task
          3. Yielding to allow the ticker task to run through once to process the initial transition.
        """

        async def ticker() -> None:
            """Executes a tick then awaits the next tick event, exiting when cancelled."""

            async def tick():
                """Executes each of the active state `do` methods"""
                logger.debug("Tick...")
                for item in self.active_states:
                    if isinstance(item, set):
                        for state in item:
                            await state.do()
                    else:
                        await item.do()

            try:
                while True:
                    await tick()
                    await self._tick_event.wait()
                    self._tick_event.clear()
            except asyncio.CancelledError:
                logger.debug("Ticker stopped")

        self.activate()
        self.ticker: asyncio.Task[None] = asyncio.create_task(ticker())
        logger.debug("Ticker started")
        await asyncio.sleep(_POLL_INTERVAL_S)
        return self.ticker

    async def stop_ticker(self, stopped_event: asyncio.Event | None = None) -> None:
        """Stops the state machine by cancelling the ticker task."""
        self.ticker.cancel()

        while not self.ticker.done():
            await asyncio.sleep(_POLL_INTERVAL_S)

        if stopped_event:
            stopped_event.set()


# MARK: Event
class Event:
    """An event with an associated name."""

    def __init__(self, state_machine: StateMachine, name: str = "event") -> None:
        super().__init__()
        self._state_machine = state_machine
        self._name = name
        self._event = asyncio.Event()

    def __call__(self) -> bool:
        """Automatically clears the event if set.

        Returns:
            whether the event was set
        """
        if self._event.is_set():
            self.clear()
            return True
        else:
            return False

    async def set(self) -> None:
        self._event.set()
        logger.debug("Event %s set", self._name)
        plantuml_logger.debug("rnote over Events: %s", self._name)
        await self._state_machine.trigger_tick()

    def clear(self) -> None:
        self._event.clear()
        logger.debug("Event %s cleared", self._name)


# MARK: EventWithValue(Generic[T], Event)
class EventWithValue(Generic[T], Event):
    """An event with an optionally attached value."""

    def __init__(self, state_machine: StateMachine, name: str = "") -> None:
        super().__init__(state_machine, name)
        self._value = None

    @property
    def value(self) -> T:
        assert self._value is not None, "value should not be None"
        return self._value

    async def set_value(self, value: T) -> None:
        assert value is not None, "value passed should not be None"
        self._value = value
        await super().set()
