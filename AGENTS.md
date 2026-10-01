# AGENTS.md

## PLAN AND ASK BEFORE DO

**CRITICAL: NEVER EVER DO ANY ACTION READING, MODIFYING OR RUNNING without explaining the plan.**

Each set of intended actions needs to be explained in the format:

> I understood that `<YOUR ANALYSIS>` so that I plan to `<GOALS YOU PURSUE>` by `<ACTIONS TO BE CONFIRMED>` estimating `<# of ITEMS>` `<ITEMS>` to be worked on. Confirm with go!

**YOU WILL NEVER PROCEED WITHOUT POSITIVE CONFIRMATION by go!**

## Efficiency

- Do NOT do unneeded file lookups based on guessing or assuming typos.
- Do NOT use TodoWrite for tasks with fewer than 4 steps.
- Do NOT read files you already have contents for.
- Keep summaries to 2-3 lines max unless asked for detail.
- Minimize tool calls. Batch parallel calls. Avoid redundant calls.

## Security

**CRITICAL: NEVER leak credentials, passwords, hashes, internal hostnames, IPs, or any infrastructure details to public platforms (GitHub, Discourse, etc.). Firing offense.**

## Project

Python project `pyCEURsemantify`, package `ceursemantify`. General conventions: Agent/Guido/BITPlan on the BITPlan wiki; this section holds the project specifics.

## Build, test, format

```bash
scripts/install      # pip install .
scripts/test         # unittest discover; -g green, -m modulewise, -t tox
scripts/blackisort   # isort + black on ceursemantify and tests, before every commit
scripts/doc          # API documentation with mkdocs
checkos -o ceurws -p semantify --local -v   # compliance check
```

## Style

- hatchling build, version in `ceursemantify/__init__.py`
- black with line length 120, isort
- unittest with `basemkit.basetest.Basetest`, files `tests/test_<module>.py`, no pytest fixtures
- type hints and Google style docstrings on every public function and class
- every command line interface subclasses `basemkit.base_cmd.BaseCmd`

## Structure

- `ceursemantify/` package
- `tests/` unit tests
- `ontology/` CEUR-WS proceedings ontology and JSON-LD context
- `docs/workflow/` workflow diagrams

