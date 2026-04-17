name: Feature Request
description: Suggest an idea for the project
title: "[FEATURE] "
labels: ["enhancement"]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for taking the time to suggest a feature!
  - type: textarea
    id: description
    attributes:
      label: Description
      description: Clear description of the feature
      placeholder: What would you like to see?
    validations:
      required: true
  - type: textarea
    id: motivation
    attributes:
      label: Motivation
      description: Why this feature is needed
      placeholder: Describe the problem it solves
    validations:
      required: true
  - type: textarea
    id: implementation
    attributes:
      label: Possible Implementation
      description: Ideas on how to implement it
      placeholder: Optional - your suggestions
