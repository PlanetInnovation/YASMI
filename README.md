# YASMI for MicroPython

Author: David Fyfe

## Description

Yet Another State Machine Implementation (YASMI) provides a framework for creating a state machine with the following features:

  - A hierarchy of composite and simple states of arbitrary size.
  - All states able to feature entry, do and exit actions.
  - State transitions able to have guard conditions and actions performed on transition.
  - History states
  - Concurrent states

## Test Cases

Several sample implementations are provided as examples and to provide test cases.

## Diagrams

Critical to working with state machines is having accurate state diagrams.  The `docs` folder contains diagrams representing the above test cases, along with the plantuml source used to generate them.  The standard version of plantuml is poor at representing anything more than the simplest state diagrams.  Hence I include a custom `plantuml.jar` binary that I have built from my [custom fork of plantuml](https://github.com/davmf/plantuml).  This, along with the `state_machine_routines.iuml` include file, allow much better state diagrams to be generated.

A future improvement may be to add to the code the means of generating state diagrams.
