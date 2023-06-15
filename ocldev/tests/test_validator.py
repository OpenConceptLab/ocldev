import os
import unittest

import ocldev.oclresourcelist


class OclCsvResourceListTest(unittest.TestCase):
    def test_validate_csv_organization(self):
        resources = [
            {
                "resource_type": "Organization",
                "id": "MyOrg",
                "name": "MyOrg Name",
                "location": 'Wichita, KS, USA',
                "company": "My company",
            },
            {
                "resource_type": "Source",
                "id": "MySource",
                "name": "MySource Name",
                "owner_id": "MyOrg",
                "external_id": "my external id",
            },
        ]

        resource_list = ocldev.oclresourcelist.OclCsvResourceList(resources)
        resource_list.validate()

    def test_validate_csv_file(self):
        filename = os.path.join(os.path.dirname(__file__), './sample.csv')
        resource_list = ocldev.oclresourcelist.OclCsvResourceList.load_from_file(filename)
        resource_list.validate()
