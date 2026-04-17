name: Bug Report
description: Report a bug or issue
title: "[BUG] "
labels: ["bug"]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for taking the time to fill out this bug report!
  - type: textarea
    id: description
    attributes:
      label: Description
      description: Clear and concise description of the bug
      placeholder: What happened?
    validations:
      required: true
  - type: textarea
    id: reproduction
    attributes:
      label: Steps to Reproduce
      description: Steps to reproduce the behavior
      placeholder: |
        1. 
        2. 
        3.
    validations:
      required: true
  - type: textarea
    id: expected
    attributes:
      label: Expected Behavior
      description: What should happen
    validations:
      required: true
  - type: textarea
    id: actual
    attributes:
      label: Actual Behavior
      description: What actually happens
    validations:
      required: true
  - type: input
    id: environment
    attributes:
      label: Environment
      description: Python version, OS, etc.
      placeholder: "Python 3.9, macOS 12"
