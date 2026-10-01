# semantify
Semantification of the CEUR-WS publication workflow

| | |
| :--- | :--- |
| **PyPi** | [![PyPI Status](https://img.shields.io/pypi/v/pyCEURsemantify.svg)](https://pypi.python.org/pypi/pyCEURsemantify/) [![License](https://img.shields.io/github/license/ceurws/semantify.svg)](https://www.apache.org/licenses/LICENSE-2.0) [![pypi](https://img.shields.io/pypi/pyversions/pyCEURsemantify)](https://pypi.org/project/pyCEURsemantify/) [![format](https://img.shields.io/pypi/format/pyCEURsemantify)](https://pypi.org/project/pyCEURsemantify/) [![downloads](https://img.shields.io/pypi/dd/pyCEURsemantify)](https://pypi.org/project/pyCEURsemantify/) |
| **GitHub** | [![Github Actions Build](https://github.com/ceurws/semantify/actions/workflows/build.yml/badge.svg)](https://github.com/ceurws/semantify/actions/workflows/build.yml) [![Release](https://img.shields.io/github/v/release/ceurws/semantify)](https://github.com/ceurws/semantify/releases) [![Contributors](https://img.shields.io/github/contributors/ceurws/semantify)](https://github.com/ceurws/semantify/graphs/contributors) [![Last Commit](https://img.shields.io/github/last-commit/ceurws/semantify)](https://github.com/ceurws/semantify/commits/) [![GitHub issues](https://img.shields.io/github/issues/ceurws/semantify.svg)](https://github.com/ceurws/semantify/issues) [![GitHub closed issues](https://img.shields.io/github/issues-closed/ceurws/semantify.svg)](https://github.com/ceurws/semantify/issues/?q=is%3Aissue+is%3Aclosed) |
| **Code** | [![style-black](https://img.shields.io/badge/%20style-black-000000.svg)](https://github.com/psf/black) [![imports-isort](https://img.shields.io/badge/%20imports-isort-%231674b1)](https://pycqa.github.io/isort/) |
| **Docs** | [![API Docs](https://img.shields.io/badge/API-Documentation-blue)](https://ceurws.github.io/semantify/) [![formatter-docformatter](https://img.shields.io/badge/%20formatter-docformatter-fedcba.svg)](https://github.com/PyCQA/docformatter) [![style-google](https://img.shields.io/badge/%20style-google-3666d6.svg)](https://google.github.io/styleguide/pyguide.html#s3.8-comments-and-docstrings) |

See [Issue #1: Semantify CEUR-WS](https://github.com/ceurws/semantify/issues/1) for the project vision and definition of done.

## Generator
`ceursemantify` generates year and volume pages from the JSON-LD of volumes, see [#24](https://github.com/ceurws/semantify/issues/24).
The year of a volume is the year of the start date of its event.

```bash
ceursemantify examples/Vol-*.jsonld -o /tmp/ceur-ws-yyyy
```

Per volume `yyyy/Vol-N/index.html` and `yyyy/Vol-N/index.jsonld` are written, per year `yyyy/index.html`.
Each volume page carries its JSON-LD as a `json-ld` fence in an HTML comment that
[semantify3](https://github.com/BITPlan/semantify3) extracts again.
Prototype: [2023](https://ceur-ws.wikidata.dbis.rwth-aachen.de/2023/), [2024](https://ceur-ws.wikidata.dbis.rwth-aachen.de/2024/),
[2025](https://ceur-ws.wikidata.dbis.rwth-aachen.de/2025/), [2026](https://ceur-ws.wikidata.dbis.rwth-aachen.de/2026/)

## Related Projects

| Project | Role |
|---------|------|
| [pyCEURmake](https://github.com/WolfgangFahl/pyCEURmake) | CEUR-WS metadata extraction and Volume Browser |
| [ceur-spt](https://github.com/ceurws/ceur-spt) | Single Point of Truth server — content negotiation (FastAPI) |
| [SemPubFlow](https://github.com/WolfgangFahl/SemPubFlow) | Metadata-first publishing workflow (nicegui) |
| [pyLoDStorage](https://github.com/WolfgangFahl/pyLoDStorage) | List-of-Dict storage with named query support |
| [geograpy3](https://github.com/somnathrakshit/geograpy3) | Location NER/NEL with Wikidata linking |
| [semantify3](https://github.com/BITPlan/semantify3) | YAML-to-triples — syntax matters |
| [snapquery](https://github.com/WolfgangFahl/snapquery) | Named parameterized query middleware |

## Papers

| Paper | Venue | Status |
|-------|-------|--------|
| [Semantification of CEUR-WS with Wikidata as a target Knowledge Graph](https://ceur-ws.org/Vol-3447/Text2KG_Paper_13.pdf) | text2kg 2023 | [accepted](https://www.wikidata.org/wiki/Q118799188) |
| [SemPubFlow: a novel Scientific Publishing Workflow using Knowledge Graphs, Wikidata and LLMs](https://www.semantic-web-journal.net/system/files/swj3657.pdf) | Semantic Web Journal | rejected |
| [Semantify CEUR-WS](https://github.com/WolfgangFahl/CEURWS_Semantification_ISWC2026) | [ISWC 2026 In-Use Track](https://iswc2026.semanticweb.org/call-for-in-use-track-papers/) | to be submitted |

## License

Apache 2.0 (under discussion)
