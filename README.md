# ocldev
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
