# EML-MCP Architecture

This document describes the high-level architecture of `eml-mcp`, a continuous-math Model Context Protocol (MCP) server.

## Overview

The `eml-mcp` server provides tools and agents with the ability to perform symbolic regression, expression simplification, and targeted mathematical discovery using a universal continuous operator (`exp(x) - ln(y)`). 

The system exposes its capabilities through the Model Context Protocol (MCP) using `FastMCP`. 

## Core Components

### 1. Primitives (`primitives.py`)

At the lowest level, `eml-mcp` works with the EML (Exp-Minus-Log) Sheffer operator function:
`eml(x, y) = exp(x) - ln(y)`

This is implemented using `cmath.exp` and `cmath.log` with safeguards handling precision and branch cuts across the complex plane. 

### 2. Expression Trees (`trees.py`)

Every function translates into a binary tree composed of `EMLNode`s. 
There are three fundamental types of nodes in the system (`NodeType`):
- `CONST`: Represents a literal coefficient (usually complex).
- `VAR`: Represents an independent variable (e.g., `x`, `y`).
- `EML`: Represents the binary operation `eml(left, right)`.
- `CALL`: A function call context, handled in later improvements to opacity logic.

### 3. Equality Graph Simplifier (`simplifier.py`)

The Simplifier sits on top of trees to reduce `k` (the complexity/node count of a formula) via equality saturation.
It operates via an internal `EGraph` that recursively deduplicates isomorphic topological subtrees and rewrites known algebraic identities (e.g., `exp(ln(z)) -> z`).
The system utilizes a topological pattern-matcher `egraph_matches()` that identifies subgraphs matching simplifiable forms and applies substitutions. Finally, a Bellman-Ford traversal (`extract_best()`) identifies the minimal `k` valid representation embedded in the graph.

### 4. Database (`database.py` and `formula_db.py`)

A local SQLite database stores discovered formulas, expressions, their depths, and MSE test valuations. `EMLFormulaDB` serves as a semantic cache of verified EML identities mapped against traditional arithmetic identifiers.

### 5. Symbolic Regression & Discovery (`discovery.py`, `symbolic_regression.py`)

A multi-threaded discovery engine operates via evolutionary mutation to explore target behaviors. The target python expressions are converted using AST logic into measurable fitness criteria, after which trees are iteratively permuted, evaluated with test sequences, and tested against given targets (measured using MSE - Mean Squared Error).

When a close approximation is reached, it is stored or passed down for exact structural reduction.

## Data Flow

1. Tools like `eml_simplify` or `eml_symbolic_regression` receive input.
2. Formatted inputs translate dynamically into internal `EMLNode` architectures.
3. The algorithms manipulate the subtrees locally or against the `EMLFormulaDB` catalog.
4. Output representations convert back to structured JSON responses, alongside `rpn` and metadata `k` values, returning through the MCP protocol back to the reasoning client.
