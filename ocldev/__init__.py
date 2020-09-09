""" ocldev module """
name = "ocldev"

import six
if six.PY2:
    import oclconstants
    import oclcsvtojsonconverter
    import oclexport
    import oclfleximporter
    import oclresourcelist
