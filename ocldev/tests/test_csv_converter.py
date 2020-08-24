import ocldev.oclcsvtojsonconverter


def convert_csv_to_json(csv_input):
    csv_converter = ocldev.oclcsvtojsonconverter.OclStandardCsvToJsonConverter(input_list=csv_input, verbose=2)
    return csv_converter.process_by_definition()


def test_convert_org():
    csv_input = [{
        "resource_type": "Organization",
        "id": "TestOrg",
        "name": "Test Org",
        "attr:org_extra": "test value"
    }]
    expected_json_output = [{
        "public_access": "View",
        "extras": {"org_extra": "test value"},
        "type": "Organization",
        "id": "TestOrg",
        "name": "Test Org"
    }]
    actual_json_output = convert_csv_to_json(csv_input)
    print(actual_json_output)
    assert actual_json_output == expected_json_output, "Converted JSON does not match expected output"


def test_convert_source():
    csv_input = [{
        "resource_type": "Source",
        "id": "TestSource",
        "name": "Test Source",
        "owner": "TestOrg",
        "owner_type": "Organization"
    }]
    expected_json_output = [{
        'name': 'Test Source',
        'default_locale': 'en',
        'short_code': 'TestSource',
        'full_name': 'Test Source',
        'public_access': 'View',
        'owner_type': 'Organization',
        'type': 'Source',
        'id': 'TestSource',
        'supported_locales': 'en'
    }]
    actual_json_output = convert_csv_to_json(csv_input)
    print(actual_json_output)
    assert actual_json_output == expected_json_output, "Converted JSON does not match expected output"


def test_convert_collection():
    csv_input = [{
        "resource_type": "Collection",
        "id": "TestCollection",
        "name": "Test Collection",
        "owner": "TestOrg",
        "owner_type": "Organization"
    }]
    expected_json_output = [{
        'name': 'Test Collection',
        'default_locale': 'en',
        'short_code': 'TestCollection',
        'full_name': 'Test Collection',
        'public_access': 'View',
        'owner_type': 'Organization',
        'type': 'Collection',
        'id': 'TestCollection',
        'supported_locales': 'en'
    }]
    actual_json_output = convert_csv_to_json(csv_input)
    print(actual_json_output)
    assert actual_json_output == expected_json_output, "Converted JSON does not match expected output"


def test_convert_concept():
    csv_input = [{
        "resource_type": "Concept",
        "id": "12",
        "name": "Test Concept",
        "owner": "TestOrg",
        "owner_type": "Organization",
        "source": "Test Source",
        "concept_class": "Misc",
        "datatype": "None",
    }]
    expected_json_output = [{
        'source': 'Test Source',
        'names': [{'locale': 'en', 'locale_preferred': True, 'name': 'Test Concept', 'name_type': 'Fully Specified'}],
        'datatype': 'None',
        'concept_class': 'Misc',
        'owner_type': 'Organization',
        'type': 'Concept',
        'id': '12'
    }]
    actual_json_output = convert_csv_to_json(csv_input)
    print(actual_json_output)
    assert actual_json_output == expected_json_output, "Converted JSON does not match expected output"
