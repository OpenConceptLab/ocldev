# ocldev

[![DPG Badge](https://img.shields.io/badge/Verified-DPG-3333AB?logo=data:image/svg%2bxml;base64,PHN2ZyB3aWR0aD0iMzEiIGhlaWdodD0iMzMiIHZpZXdCb3g9IjAgMCAzMSAzMyIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTE0LjIwMDggMjEuMzY3OEwxMC4xNzM2IDE4LjAxMjRMMTEuNTIxOSAxNi40MDAzTDEzLjk5MjggMTguNDU5TDE5LjYyNjkgMTIuMjExMUwyMS4xOTA5IDEzLjYxNkwxNC4yMDA4IDIxLjM2NzhaTTI0LjYyNDEgOS4zNTEyN0wyNC44MDcxIDMuMDcyOTdMMTguODgxIDUuMTg2NjJMMTUuMzMxNCAtMi4zMzA4MmUtMDVMMTEuNzgyMSA1LjE4NjYyTDUuODU2MDEgMy4wNzI5N0w2LjAzOTA2IDkuMzUxMjdMMCAxMS4xMTc3TDMuODQ1MjEgMTYuMDg5NUwwIDIxLjA2MTJMNi4wMzkwNiAyMi44Mjc3TDUuODU2MDEgMjkuMTA2TDExLjc4MjEgMjYuOTkyM0wxNS4zMzE0IDMyLjE3OUwxOC44ODEgMjYuOTkyM0wyNC44MDcxIDI5LjEwNkwyNC42MjQxIDIyLjgyNzdMMzAuNjYzMSAyMS4wNjEyTDI2LjgxNzYgMTYuMDg5NUwzMC42NjMxIDExLjExNzdMMjQuNjI0MSA5LjM1MTI3WiIgZmlsbD0id2hpdGUiLz4KPC9zdmc+Cg==)](https://digitalpublicgoods.net/r/open-concept-lab)
Development library for working with OCL metadata and APIs

`ocldev` package is published to PyPi, which means you can easily install it with pip, eg:
```
pip install ocldev
```

These classes are implemented currently:
* OclResourceList, OclCsvResourceList, OclJsonResourceList - 
* OclFlexImporter & OclBulkImporter - Used to import JSON resources into OCL
* OclImportResults - Used to process the results of an import
* OclExport & OclExportFactory - Used to fetch exports from OCL
* OclCsvToJsonConverter - Used to convert CSV files to OCL-formatted JSON
* OclValidator - Validates OCL-formatted JSON and CSV resources and resource lists

## Deployment to PyPi
OCL's continuous integration service (Bamboo) offers two custom build plans to deploy the `ocldev` package to the test or the production PyPi servers. PyPi requires that the version number is unique in https://github.com/OpenConceptLab/ocldev/blob/master/setup.py#L8, otherwise PyPi will return an error. A user account is required to access OCL's CI service.


## Development
Setup virtualenv with python3

## Run tests:
`python -m python -m unittest ocldev/tests/*.py`

## License

This repository is part of the [OCL Digital Public Good](https://github.com/OpenConceptLab/.github/blob/main/DIGITAL-PUBLIC-GOOD.md). It is licensed under the [Mozilla Public License 2.0](LICENSE) with the [OCL Healthcare Disclaimer](HEALTHCARE-DISCLAIMER.md).
