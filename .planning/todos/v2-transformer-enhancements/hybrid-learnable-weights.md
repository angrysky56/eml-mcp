---
title: "Support Hybrid-Learnable (Analytical + Delta) EML Weights"
created_at: "2026-04-16"
status: pending
area: transformer-enhancements
priority: high
---

# Support Hybrid-Learnable (Analytical + Delta) EML Weights

## Problem
Pure analytical initialization might be too rigid for real-world datasets that deviate slightly from theoretical EML forms.

## Proposed Solution
Implement a hybrid weight structure: $W = W_{fixed} + \Delta W_{trainable}$.
The analytical EML weights provide the "structural prior," while the trainable delta allows the model to fine-tune the function during backpropagation.
