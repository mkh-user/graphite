# Contributing to Graphite

Thank you for your interest in **Graphite**.
We welcome contributions of all kinds — code, documentation, design discussions, bug reports, and feature proposals.

This document explains how to contribute effectively and consistently.

---

## Table of Contents

* [Code of Conduct](#code-of-conduct)
* [Ways to Contribute](#ways-to-contribute)
* [Getting Started](#getting-started)
* [Development Workflow](#development-workflow)
* [Branching Strategy](#branching-strategy)
* [Commit Guidelines](#commit-guidelines)
* [Pull Request Process](#pull-request-process)
* [Coding Standards](#coding-standards)
* [Testing Requirements](#testing-requirements)
* [Documentation](#documentation)
* [Issue Guidelines](#issue-guidelines)
* [Design Proposals](#design-proposals)
* [Release Process](#release-process)

---

## Code of Conduct

All contributors must follow our Code of Conduct:

👉 [CODE_OF_CONDUCT](https://github.com/mkh-user/graphite/blob/main/CODE_OF_CONDUCT.md)

Participation in this project implies acceptance of its terms.

---

## Ways to Contribute

You can contribute in several ways:

* Reporting bugs
* Suggesting features
* Participating in design discussions
* Improving documentation
* Submitting bug fixes
* Implementing new features
* Writing tests
* Improving performance

---

## Getting Started

Full setup instructions are available here:

👉 [Development setup page](development-setup)

Basic workflow:

1. Fork the repository.
2. Clone your fork.
3. Create a feature branch from `dev`.
4. Install dependencies.
5. Start development.

---

## Development Workflow

1. Create a new branch from `dev`.
2. Implement your changes.
3. Add tests.
4. Run all tests locally.
5. Ensure formatting and linting pass.
6. Open a Pull Request against `dev`.

Never commit directly to `main`.

---

## Branching Strategy

We follow a structured branching model:

* `main` → Stable production-ready code.
* `dev` → Active development branch.
* `feature/<short-name>` → New features.
* `fix/<short-name>` → Bug fixes.
* `docs/<short-name>` → Documentation updates.
* `refactor/<short-name>` → Refactoring changes.

Example:

```text
feature/query-optimizer
```

---

## Commit Guidelines

We use Conventional Commits format:

```text
type(scope): short description
```

Examples:

```text
feat(parser): add support for nested graph queries
fix(engine): correct edge traversal bug
docs(readme): update installation instructions
refactor(core): simplify node indexing logic
test(api): add edge validation tests
```

Allowed types:

* `feat`
* `fix`
* `docs`
* `refactor`
* `test`
* `chore`
* `perf`

Commit messages must be:

* Clear
* Concise
* Descriptive
* In English

---

## Pull Request Process

Before submitting a PR:

* Ensure all tests pass.
* Ensure linting passes.
* Update documentation if necessary.
* Add tests for new behavior.

PR checklist:

* [ ] Code compiles
* [ ] Tests added/updated
* [ ] Documentation updated
* [ ] No breaking changes (or clearly documented)
* [ ] Clear PR description

PRs must target `dev`, not `main`.

All PRs require review before merging.

---

## Coding Standards

* Follow existing project structure.
* Keep functions small and focused.
* Avoid unnecessary abstraction.
* Write self-documenting code.
* Prefer clarity to cleverness.
* Use explicit naming.

If using Python:

* Follow PEP8.
* Use type hints.
* Avoid wildcard imports.
* Use black/ruff for formatting and linting.

If using Rust (for engine/bytecode components):

* Follow idiomatic Rust style.
* Avoid `unwrap()` in production code.
* Use proper error handling (`Result`).
* Keep unsafe code isolated and justified.

---

## Testing Requirements

All new features must include:

* Unit tests
* Edge case tests
* Regression tests (for bug fixes)

Run tests before submitting:

```bash
pytest
```

No PR will be merged without passing tests.

---

## Documentation

Documentation is part of the codebase quality.

When to update docs:

* New feature added
* Behavior changed
* Public API modified
* Configuration options updated

Documentation areas:

* README
* Inline docstrings
* Examples

Good documentation explains **why**, not only **how**.

---

## Issue Guidelines

When opening an issue:

* Use the appropriate issue template.
* Provide a clear and descriptive title.
* Include a detailed description.
* Add steps to reproduce (for bugs).
* Describe expected vs actual behavior.
* Include environment details when relevant.

Use appropriate labels:

* `type: bug`
* `type: enhancement`
* `type: discussion`
* `type: documentation`
* `type: performance`
* `good first issue`

Incomplete issues may be closed.

---

## Design Proposals

For major architectural changes:

1. Open a Discussion first.
2. Write a short design proposal.
3. Include:

   * Motivation
   * Technical approach
   * Trade-offs
   * Alternatives considered
4. Wait for feedback before implementation.

Large changes without prior discussion may be rejected.

---

## Release Process

* `dev` → ongoing development.
* Stabilized features are merged into `main`.
* Version tags follow semantic versioning:

```text
vMAJOR.MINOR.PATCH
```

Example:

```text
v1.2.0
```

Breaking changes increment MAJOR.

---

## Contribution Philosophy

Graphite prioritizes:

* Simplicity
* Predictability
* Maintainability
* Performance (when justified)
* Clear architecture

We prefer fewer, well-designed features over feature bloat.
