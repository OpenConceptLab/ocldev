# ocldev
Development library for working with OCL metadata and APIs

`ocldev` package is published to PyPi, which means you can easily install it with pip, eg:
```
pip install ocldev
```

Three main classes (and several supporting classes) are implemented currently:
* OclFlexImporter - Used to import a list of JSON resources into OCL
* OclImportResults - Optionally returned by the OclFlexImporter to process the results of the import
* OclExport - Used to fetch an export from OCL
