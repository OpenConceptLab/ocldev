import ocldev.oclresourcelist


def test_validate_csv_organization():
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
    assert True == True


def test_validate_csv_file():
    filename = './tests/sample.csv'
    resource_list = ocldev.oclresourcelist.OclCsvResourceList.load_from_file(filename)
    resource_list.validate()
    assert True == True
