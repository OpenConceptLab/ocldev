"""
Classes to validate JSON or CSV resource definitions
"""
import jsonschema
import oclresourcelist


class OclJsonValidator(object):
    """ Class to validate OCL-formatted JSON resource definitions """

    @staticmethod
    def validate(resources):
        """ Validate list of resources """
        if isinstance(resources, dict):
            resources = [resources]
        if isinstance(resources, list) or isinstance(resources, oclresourcelist.OclResourceList):
            for resource in resources:
                OclJsonValidator.validate_resource(resource)
        else:
            raise TypeError("Expected OclResourceList, list of resources, or a single resource. '%s' given." % str(
                type(resources)))

    @staticmethod
    def validate_resource(resource, resource_type=''):
        """ Validate resource against schema """
        if not resource_type:
            if 'resource_type' in resource:
                resource_type = resource['resource_type']
        if not resource_type:
            raise Exception("Must provide 'resource_type' as a resource attribute or "
                            "specify as an argument. Neither provided.")
        elif resource_type not in OclJsonValidator.VALIDATION_SCHEMAS:
            raise Exception("Unrecognized resource type '%s'" % resource_type)
        jsonschema.validate(
            instance=resource, schema=OclJsonValidator.VALIDATION_SCHEMAS[resource_type])

    # Validation schemas
    VALIDATION_SCHEMA_CONCEPT = {}
    VALIDATION_SCHEMA_MAPPING = {}
    VALIDATION_SCHEMA_REFERENCE = {}
    VALIDATION_SCHEMA_REPOSITORY_VERSION = {}
    VALIDATION_SCHEMA_SOURCE = {}
    VALIDATION_SCHEMA_COLLECTION = {}
    VALIDATION_SCHEMA_ORGANIZATION = {}
    VALIDATION_SCHEMAS = {
        'Concept': VALIDATION_SCHEMA_CONCEPT,
        'Mapping': VALIDATION_SCHEMA_MAPPING,
    }

class OclCsvValidator(object):
    """ Class to validate OCL-formatted CSV resource definitions """

    @staticmethod
    def validate(resources):
        """ Validate list of resources """
        if isinstance(resources, dict):
            resources = [resources]
        if isinstance(resources, list) or isinstance(resources, oclresourcelist.OclResourceList):
            for resource in resources:
                OclCsvValidator.validate_resource(resource)
        else:
            raise TypeError("Expected OclResourceList, list of resources, or a single resource. '%s' given." % str(
                type(resources)))

    @staticmethod
    def validate_resource(resource, resource_type=''):
        """ Validate resource against schema """
        if not resource_type:
            if 'resource_type' in resource:
                resource_type = resource['resource_type']
        if not resource_type:
            raise Exception("Must provide 'resource_type' as a resource attribute or specify "
                            "as an argument. Neither provided.")
        elif resource_type not in OclCsvValidator.VALIDATION_SCHEMAS:
            raise Exception("Unrecognized resource type '%s'" % resource_type)
        jsonschema.validate(
            instance=resource, schema=OclCsvValidator.VALIDATION_SCHEMAS[resource_type])

    # Validation schemas
    VALIDATION_SCHEMA_CONCEPT = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "http://openconceptlab.org/csv_concept.schema.json",
        "title": "CSV_Concept",
        "description": "A CSV-based OCL concept",
        "type": "object",
        "properties": {
            "resource_type": {
                "description": "",
                "type": "string"
            },
            "owner_id": {
                "description": "ID of the owner of this concept",
                "type": "string"
            },
            "owner_type": {
                "description": ("Resource type of the owner of this concept, "
                                "either an Organization or User"),
                "type": "string"
            },
            "source": {
                "description": "OCL source",
                "type": "string"
            },
            "id": {
                "description": "ID of the concept",
                "type": "string"
            },
            "name": {
                "description": "Primary name of the concept",
                "type": "string"
            }
        },
        "required": ["resource_type", "id", "owner", "source", "concept_class"]
    }
    VALIDATION_SCHEMA_MAPPING = {}
    VALIDATION_SCHEMA_REFERENCE = {}
    VALIDATION_SCHEMA_REPOSITORY_VERSION = {}
    VALIDATION_SCHEMA_SOURCE = {}
    VALIDATION_SCHEMA_COLLECTION = {}
    VALIDATION_SCHEMA_ORGANIZATION = {}
    VALIDATION_SCHEMAS = {
        'Concept': VALIDATION_SCHEMA_CONCEPT,
        'Mapping': VALIDATION_SCHEMA_MAPPING,
    }
