# Contributing to white-pepper-core

This repository contains the standalone, headless scanner acquisition and computer vision engine for **white-pepper**.

---

## 1. Coding Conventions
All source code must adhere strictly to:
`D:\Conversations\conventions\python-conventions.md`

- **Universal Type Annotations**: Every variable, function parameter, return value, and class attribute must be typed.
- **Python 3.10+ Generic Forms**: Use `list[str]`, `dict[str, Any]`, `tuple[int, int]`.
- **Initializers**: `__init__` must always be annotated with `-> None`.
- **NumPy / Sphinx Docstrings**: Every module, class, and method must have docstrings with `Parameters`, `Returns`, and `Raises` sections.
- **Descriptive Naming**: No uninformative abbreviations (`index`, `height`, `width`, `temporary_path`).
- **Formatting Standards**: No hanging assignments (`=` at line end), no decorative banners (`# === Helpers ===`).

---

## 2. Git & Commit Guidelines
- Managed with the `/git-revisit` skill (`D:/conversations/skills/git-revisit/SKILL.md`).
- Authorship: `AceBurgundy <Samadriansabalo99@gmail.com>`.
- Decomposes codebase via Python AST into fine-grained, authentic commits.
