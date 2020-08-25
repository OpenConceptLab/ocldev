"""
Classes to validate JSON or CSV resource definitions

https://python-jsonschema.readthedocs.io/en/latest/

Code Example:
import json
import ocldev.oclvalidator
import ocldev.oclresourcelist
filename = 'my_import_file.json'
resource_list = ocldev.oclresourcelist.OclJsonResourcelist.load_from_file(filename)
resource_list.validate()
"""
import jsonschema
from . import oclresourcelist
from . import oclconstants


class OclJsonValidator:
    """ Class to validate OCL-formatted JSON resource definitions """

    @staticmethod
    def validate(resources, do_skip_unknown_resource_type=False):
        """ Validate list of resources """
        if isinstance(resources, dict):
            resources = [resources]
        if isinstance(resources, (list, oclresourcelist.OclResourceList)):
            for resource in resources:
                OclJsonValidator.validate_resource(
                    resource, do_skip_unknown_resource_type=do_skip_unknown_resource_type)
        else:
            raise TypeError("Expected OclResourceList, list of resources, or a single dictionary resource."
                            " '%s' given." % str(type(resources)))

    @staticmethod
    def validate_resource(resource, resource_type='', do_skip_unknown_resource_type=False):
        """ Validate resource against schema """
        if not resource_type:
            if 'type' in resource:
                resource_type = resource['type']
        if not resource_type:
            if do_skip_unknown_resource_type:
                return
            raise Exception("Must provide 'type' as a resource attribute or "
                            "specify as an argument. Neither provided.")
        elif resource_type not in OclJsonValidator.VALIDATION_SCHEMAS:
            if do_skip_unknown_resource_type:
                return
            raise Exception("Unrecognized resource type '%s'" % resource_type)
        jsonschema.validate(
            instance=resource, schema=OclJsonValidator.VALIDATION_SCHEMAS[resource_type])

    # Validation schemas
    VALIDATION_SCHEMA_CONCEPT = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "http://openconceptlab.org/json_concept.schema.json",
        "title": "JSON_Concept",
        "description": "A JSON-based OCL concept",
        "type": "object",
        "properties": {
            "type": {
                "description": "OCL resource type, eg \"Concept\" or \"Mapping\"",
                "type": "string"
            },
            "owner": {
                "description": "ID for the owner of this resource",
                "type": "string"
            },
            "owner_type": {
                "description": ("Resource type for the owner of this resource, "
                                "either \"Organization\" or \"User\"."),
                "type": "string"
            },
            "source": {
                "description": "OCL source for this concept",
                "type": "string"
            },
            "concept_class": {
                "description": "Class for this concpet, eg Symptom, Diagnosis",
                "type": "string"
            },
            "datatype": {
                "description": "Datatype for this concpet, eg Numeric, Text, Coded",
                "type": "string"
            },
            "id": {
                "description": "ID of this resource",
                "type": "string"
            },
            "external_id": {
                "description": "External identifier of this resource",
                "type": "string"
            }
        },
        "required": ["type", "id", "owner", "source", "concept_class", "datatype"]
    }
    VALIDATION_SCHEMA_MAPPING = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "http://openconceptlab.org/json_mapping.schema.json",
        "title": "JSON_Mapping",
        "description": "A JSON-based OCL mapping",
        "type": "object",
        "properties": {
            "type": {
                "description": "OCL resource type, eg \"Concept\" or \"Mapping\"",
                "type": "string"
            },
            "owner": {
                "description": "ID for the owner of this resource",
                "type": "string"
            },
            "owner_type": {
                "description": ("Resource type for the owner of this resource, "
                                "either an \"Organization\" or \"User\"."),
                "type": "string"
            },
            "source": {
                "description": "OCL source for this mapping",
                "type": "string"
            },
            "map_type": {
                "description": "Map type for this mapping, eg \"Same As\" or \"Narrower Than\"",
                "type": "string"
            },
            "id": {
                "description": "ID of this resource. Automatically assigned if omitted.",
                "type": "string"
            },
            "from_concept_url": {
                "description": "Relative URL of the from_concept, eg \"/orgs/OCL/sources/Datatypes/concepts/Numeric/\"",
                "type": "string"
            },
            "to_concept_url": {
                "description": "Relative URL of the to_concept, eg \"/orgs/OCL/sources/Datatypes/concepts/Numeric/\"",
                "type": "string"
            },
            "to_source_url": {
                "description": "Relative URL of the to_source, eg \"/orgs/WHO/sources/ICD-10/\"",
                "type": "string"
            },
        },
        "required": ["type", "owner", "source", "from_concept_url", "map_type"]
    }
    VALIDATION_SCHEMA_REFERENCE = {}
    VALIDATION_SCHEMA_SOURCE_VERSION = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "http://openconceptlab.org/json_source_version.schema.json",
        "title": "JSON_Source_Version",
        "description": "A JSON-based OCL Source Version",
        "type": "object",
        "properties": {
            "resource_type": {
                "description": "OCL resource type",
                "type": "string"
            },
            "owner": {
                "description": "ID for the owner of this resource",
                "type": "string"
            },
            "owner_type": {
                "description": ("Resource type for the owner of this resource, "
                                "either an Organization (default) or User."),
                "type": "string"
            },
            "source": {
                "description": "ID of the OCL source for this resource",
                "type": "string"
            },
            "id": {
                "description": "ID of this source version",
                "type": "string"
            },
            "description": {
                "description": "Description for this source version.",
                "type": "string"
            },
            "released": {
                "description": "True if this source version is intended for use",
            },
            "retired": {
                "description": "True if use of this source version is discouraged",
            },
        },
        "required": ["type", "owner", "source", "id", "description"]
    }
    VALIDATION_SCHEMA_COLLECTION_VERSION = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "http://openconceptlab.org/json_collection_version.schema.json",
        "title": "JSON_Collection_Version",
        "description": "A JSON-based OCL Collection Version",
        "type": "object",
        "properties": {
            "resource_type": {
                "description": "OCL resource type",
                "type": "string"
            },
            "owner": {
                "description": "ID for the owner of this resource",
                "type": "string"
            },
            "owner_type": {
                "description": ("Resource type for the owner of this resource, "
                                "either an Organization (default) or User."),
                "type": "string"
            },
            "collection": {
                "description": "ID of the OCL collection for this resource",
                "type": "string"
            },
            "id": {
                "description": "ID of this collection version",
                "type": "string"
            },
            "description": {
                "description": "Description for this collection version.",
                "type": "string"
            },
            "released": {
                "description": "True if this collection version is intended for use",
            },
            "retired": {
                "description": "True if use of this collection version is discouraged",
            },
        },
        "required": ["type", "owner", "collection", "id", "description"]
    }
    VALIDATION_SCHEMA_COLLECTION = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "http://openconceptlab.org/json_collection.schema.json",
        "title": "JSON_Collection",
        "description": "A JSON-based OCL Collection",
        "type": "object",
        "properties": {
            "type": {
                "description": "OCL resource type",
                "type": "string"
            },
            "owner": {
                "description": "ID for the owner of this resource",
                "type": "string"
            },
            "owner_type": {
                "description": ("Resource type for the owner of this resource, "
                                "either an Organization (default) or User."),
                "type": "string"
            },
            "id": {
                "description": "ID of this collection",
                "type": "string"
            },
            "name": {
                "description": "Name of the collection",
                "type": "string"
            },
            "short_code": {
                "description": "Short code of the collection",
                "type": "string"
            },
            "full_name": {
                "description": "Fully specified name of the collection",
                "type": "string"
            },
            "external_id": {
                "description": "External ID for the collection",
                "type": "string"
            },
            "public_access": {
                "description": "Public access setting: View, Edit, or None",
                "type": "string"
            },
            "collection_type": {
                "description": "Collection type, eg Dictionary, Interface Terminology, etc",
                "type": "string"
            },
            "website": {
                "description": "Website URL",
                "type": "string"
            },
            "description": {
                "description": "Description of this repository",
                "type": "string"
            },
            "default_locale": {
                "description": "Default locale, eg 'en', for new content in this repository",
                "type": "string"
            },
            "supported_locales": {
                "description": "List of supported locales for this repository, eg \"en, es, fr\"",
                "type": "string"
            },
            "custom_validation_schema": {
                "description": "Custom validation schema for this repository",
                "type": "string"
            },
        },
        "required": ["type", "owner", "id", "name"]
    }
    VALIDATION_SCHEMA_SOURCE = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "http://openconceptlab.org/json_source.schema.json",
        "title": "JSON_Source",
        "description": "A JSON-based OCL Source",
        "type": "object",
        "properties": {
            "type": {
                "description": "OCL resource type",
                "type": "string"
            },
            "owner": {
                "description": "ID for the owner of this resource",
                "type": "string"
            },
            "owner_type": {
                "description": ("Resource type for the owner of this resource, "
                                "either an Organization (default) or User."),
                "type": "string"
            },
            "id": {
                "description": "ID of this source",
                "type": "string"
            },
            "name": {
                "description": "Name of the source",
                "type": "string"
            },
            "short_code": {
                "description": "Short code of the source",
                "type": "string"
            },
            "full_name": {
                "description": "Fully specified name of the source",
                "type": "string"
            },
            "external_id": {
                "description": "External ID for the source",
                "type": "string"
            },
            "public_access": {
                "description": "Public access setting: View, Edit, or None",
                "type": "string"
            },
            "source_type": {
                "description": "Source type, eg Dictionary, Interface Terminology, etc",
                "type": "string"
            },
            "website": {
                "description": "Website URL",
                "type": "string"
            },
            "description": {
                "description": "Description of this repository",
                "type": "string"
            },
            "default_locale": {
                "description": "Default locale, eg 'en', for new content in this repository",
                "type": "string"
            },
            "supported_locales": {
                "description": "List of supported locales for this repository, eg \"en, es, fr\"",
                "type": "string"
            },
            "custom_validation_schema": {
                "description": "Custom validation schema for this repository",
                "type": "string"
            },
        },
        "required": ["type", "owner", "id", "name"]
    }
    VALIDATION_SCHEMA_ORGANIZATION = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "http://openconceptlab.org/json_organization.schema.json",
        "title": "JSON_Organization",
        "description": "A JSON-based OCL Organization",
        "type": "object",
        "properties": {
            "type": {
                "description": "OCL resource type",
                "type": "string"
            },
            "id": {
                "description": "ID of this resource",
                "type": "string"
            },
            "name": {
                "description": "Name of the organization",
                "type": "string"
            },
            "company": {
                "description": "Company name",
                "type": "string"
            },
            "website": {
                "description": "Website URL",
                "type": "string"
            },
            "location": {
                "description": "Location",
                "type": "string"
            },
            "public_access": {
                "description": "Public access setting: View, Edit, or None",
                "type": "string"
            },
        },
        "required": ["type", "id", "name"]
    }
    VALIDATION_SCHEMAS = {
        oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION: VALIDATION_SCHEMA_ORGANIZATION,
        oclconstants.OclConstants.RESOURCE_TYPE_SOURCE: VALIDATION_SCHEMA_SOURCE,
        oclconstants.OclConstants.RESOURCE_TYPE_COLLECTION: VALIDATION_SCHEMA_COLLECTION,
        oclconstants.OclConstants.RESOURCE_TYPE_CONCEPT: VALIDATION_SCHEMA_CONCEPT,
        oclconstants.OclConstants.RESOURCE_TYPE_MAPPING: VALIDATION_SCHEMA_MAPPING,
        oclconstants.OclConstants.RESOURCE_TYPE_REFERENCE: VALIDATION_SCHEMA_REFERENCE,
        oclconstants.OclConstants.RESOURCE_TYPE_SOURCE_VERSION: VALIDATION_SCHEMA_SOURCE_VERSION,
        oclconstants.OclConstants.RESOURCE_TYPE_COLLECTION_VERSION:
            VALIDATION_SCHEMA_COLLECTION_VERSION,
    }


class OclCsvValidator:
    """ Class to validate OCL-formatted CSV resource definitions """

    @staticmethod
    def validate(resources, do_skip_unknown_resource_type=True):
        """ Validate list of resources """
        if isinstance(resources, dict):
            resources = [resources]
        if isinstance(resources, (list, oclresourcelist.OclResourceList)):
            for resource in resources:
                OclCsvValidator.validate_resource(
                    resource, do_skip_unknown_resource_type=do_skip_unknown_resource_type)
        else:
            raise TypeError("Expected OclResourceList, list of resources, or a single dictionary resource. "
                            "'%s' given." % str(type(resources)))

    @staticmethod
    def validate_resource(resource, resource_type='', do_skip_unknown_resource_type=True):
        """ Validate resource against schema """
        if not resource_type:
            if 'resource_type' in resource:
                resource_type = resource['resource_type']
        if not resource_type:
            if do_skip_unknown_resource_type:
                return
            raise Exception("Must provide 'resource_type' as a resource attribute or specify "
                            "as an argument. Neither provided.")
        elif resource_type not in OclCsvValidator.VALIDATION_SCHEMAS:
            if do_skip_unknown_resource_type:
                return
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
                "description": "OCL resource type",
                "type": "string"
            },
            "owner_id": {
                "description": "ID for the owner of this resource",
                "type": "string"
            },
            "owner_type": {
                "description": ("Resource type for the owner of this resource, "
                                "either an Organization (default) or User."),
                "type": "string"
            },
            "source": {
                "description": "OCL source for this resource",
                "type": "string"
            },
            "concept_class": {
                "description": "Class for this concpet, eg Symptom, Diagnosis",
                "type": "string"
            },
            "id": {
                "description": "ID of this resource",
                "type": "string"
            },
            "name": {
                "description": "Primary name of the concept",
                "type": "string"
            }
        },
        "required": ["resource_type", "id", "owner_id", "source", "concept_class", "name"]
    }
    VALIDATION_SCHEMA_MAPPING = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "http://openconceptlab.org/csv_mapping.schema.json",
        "title": "CSV_Mapping",
        "description": "A CSV-based OCL mapping",
        "type": "object",
        "properties": {
            "resource_type": {
                "description": "OCL resource type",
                "type": "string"
            },
            "owner_id": {
                "description": "ID for the owner of this resource",
                "type": "string"
            },
            "owner_type": {
                "description": ("Resource type for the owner of this resource, "
                                "either an Organization (default) or User."),
                "type": "string"
            },
            "source": {
                "description": "OCL source for this resource",
                "type": "string"
            },
            "map_type": {
                "description": "Map type for this mapping, eg \"Same As\" or \"Narrower Than\"",
                "type": "string"
            },
            "id": {
                "description": "ID of this resource. Automatically assigned if omitted.",
                "type": "string"
            },
            "from_concept_url": {
                "description": "Relative URL of the from_concept",
                "type": "string"
            },
            "to_concept_url": {
                "description": "Relative URL of the to_concept",
                "type": "string"
            },
            "to_source_url": {
                "description": "Relative URL of the to_source",
                "type": "string"
            },
        },
        "required": ["resource_type", "owner_id", "source", "from_concept_url", "map_type"]
    }
    VALIDATION_SCHEMA_REFERENCE = {}
    VALIDATION_SCHEMA_SOURCE_VERSION = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "http://openconceptlab.org/csv_source_version.schema.json",
        "title": "CSV_Source_Version",
        "description": "A CSV-based OCL Source Version",
        "type": "object",
        "properties": {
            "resource_type": {
                "description": "OCL resource type",
                "type": "string"
            },
            "owner_id": {
                "description": "ID for the owner of this resource",
                "type": "string"
            },
            "owner_type": {
                "description": ("Resource type for the owner of this resource, "
                                "either an Organization (default) or User."),
                "type": "string"
            },
            "source": {
                "description": "ID of the OCL source for this resource",
                "type": "string"
            },
            "id": {
                "description": "ID of this source version",
                "type": "string"
            },
            "description": {
                "description": "Description for this source version.",
                "type": "string"
            },
            "released": {
                "description": "True if this source version is intended for use",
            },
            "retired": {
                "description": "True if use of this source version is discouraged",
            },
        },
        "required": ["resource_type", "owner_id", "source", "id", "description"]
    }
    VALIDATION_SCHEMA_COLLECTION_VERSION = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "http://openconceptlab.org/csv_collection_version.schema.json",
        "title": "CSV_Collection_Version",
        "description": "A CSV-based OCL Collection Version",
        "type": "object",
        "properties": {
            "resource_type": {
                "description": "OCL resource type",
                "type": "string"
            },
            "owner_id": {
                "description": "ID for the owner of this resource",
                "type": "string"
            },
            "owner_type": {
                "description": ("Resource type for the owner of this resource, "
                                "either an Organization (default) or User."),
                "type": "string"
            },
            "collection": {
                "description": "ID of the OCL collection for this resource",
                "type": "string"
            },
            "id": {
                "description": "ID of this collection version",
                "type": "string"
            },
            "description": {
                "description": "Description for this collection version.",
                "type": "string"
            },
            "released": {
                "description": "True if this collection version is intended for use",
            },
            "retired": {
                "description": "True if use of this collection version is discouraged",
            },
        },
        "required": ["resource_type", "owner_id", "collection", "id", "description"]
    }
    VALIDATION_SCHEMA_COLLECTION = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "http://openconceptlab.org/csv_collection.schema.json",
        "title": "CSV_Collection",
        "description": "A CSV-based OCL Collection",
        "type": "object",
        "properties": {
            "resource_type": {
                "description": "OCL resource type",
                "type": "string"
            },
            "owner_id": {
                "description": "ID for the owner of this resource",
                "type": "string"
            },
            "owner_type": {
                "description": ("Resource type for the owner of this resource, "
                                "either an Organization (default) or User."),
                "type": "string"
            },
            "id": {
                "description": "ID of this resource",
                "type": "string"
            },
            "name": {
                "description": "Name of the collection",
                "type": "string"
            },
            "short_code": {
                "description": "Short code of the collection",
                "type": "string"
            },
            "full_name": {
                "description": "Fully specified name of the collection",
                "type": "string"
            },
            "external_id": {
                "description": "External ID for the collection",
                "type": "string"
            },
            "public_access": {
                "description": "Public access setting: View, Edit, or None",
                "type": "string"
            },
            "collection_type": {
                "description": "Collection type, eg Dictionary, Interface Terminology, etc",
                "type": "string"
            },
            "website": {
                "description": "Website URL",
                "type": "string"
            },
            "description": {
                "description": "Description of this repository",
                "type": "string"
            },
            "default_locale": {
                "description": "Default locale, eg 'en', for new content in this repository",
                "type": "string"
            },
            "supported_locales": {
                "description": "List of supported locales for this repository, eg \"en, es, fr\"",
                "type": "string"
            },
            "custom_validation_schema": {
                "description": "Custom validation schema for this repository",
                "type": "string"
            },
        },
        "required": ["resource_type", "owner_id", "id", "name"]
    }
    VALIDATION_SCHEMA_SOURCE = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "http://openconceptlab.org/csv_source.schema.json",
        "title": "CSV_Source",
        "description": "A CSV-based OCL Source",
        "type": "object",
        "properties": {
            "resource_type": {
                "description": "OCL resource type",
                "type": "string"
            },
            "owner_id": {
                "description": "ID for the owner of this resource",
                "type": "string"
            },
            "owner_type": {
                "description": ("Resource type for the owner of this resource, "
                                "either an Organization (default) or User."),
                "type": "string"
            },
            "id": {
                "description": "ID of this resource",
                "type": "string"
            },
            "name": {
                "description": "Name of the source",
                "type": "string"
            },
            "short_code": {
                "description": "Short code of the source",
                "type": "string"
            },
            "full_name": {
                "description": "Fully specified name of the source",
                "type": "string"
            },
            "external_id": {
                "description": "External ID for the source",
                "type": "string"
            },
            "public_access": {
                "description": "Public access setting: View, Edit, or None",
                "type": "string"
            },
            "source_type": {
                "description": "Source type, eg Dictionary, Interface Terminology, etc",
                "type": "string"
            },
            "website": {
                "description": "Website URL",
                "type": "string"
            },
            "description": {
                "description": "Description of this repository",
                "type": "string"
            },
            "default_locale": {
                "description": "Default locale, eg 'en', for new content in this repository",
                "type": "string"
            },
            "supported_locales": {
                "description": "List of supported locales for this repository, eg \"en, es, fr\"",
                "type": "string"
            },
            "custom_validation_schema": {
                "description": "Custom validation schema for this repository",
                "type": "string"
            },
        },
        "required": ["resource_type", "owner_id", "id", "name"]
    }
    VALIDATION_SCHEMA_ORGANIZATION = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "http://openconceptlab.org/csv_organization.schema.json",
        "title": "CSV_Organization",
        "description": "A CSV-based OCL Organization",
        "type": "object",
        "properties": {
            "resource_type": {
                "description": "OCL resource type",
                "type": "string"
            },
            "id": {
                "description": "ID of this resource",
                "type": "string"
            },
            "name": {
                "description": "Name of the organization",
                "type": "string"
            },
            "company": {
                "description": "Company name",
                "type": "string"
            },
            "website": {
                "description": "Website URL",
                "type": "string"
            },
            "location": {
                "description": "Location",
                "type": "string"
            },
            "public_access": {
                "description": "Public access setting: View, Edit, or None",
                "type": "string"
            },
        },
        "required": ["resource_type", "id", "name"]
    }
    VALIDATION_SCHEMAS = {
        oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION: VALIDATION_SCHEMA_ORGANIZATION,
        oclconstants.OclConstants.RESOURCE_TYPE_SOURCE: VALIDATION_SCHEMA_SOURCE,
        oclconstants.OclConstants.RESOURCE_TYPE_COLLECTION: VALIDATION_SCHEMA_COLLECTION,
        oclconstants.OclConstants.RESOURCE_TYPE_CONCEPT: VALIDATION_SCHEMA_CONCEPT,
        oclconstants.OclConstants.RESOURCE_TYPE_MAPPING: VALIDATION_SCHEMA_MAPPING,
        oclconstants.OclConstants.RESOURCE_TYPE_REFERENCE: VALIDATION_SCHEMA_REFERENCE,
        oclconstants.OclConstants.RESOURCE_TYPE_SOURCE_VERSION: VALIDATION_SCHEMA_SOURCE_VERSION,
        oclconstants.OclConstants.RESOURCE_TYPE_COLLECTION_VERSION:
            VALIDATION_SCHEMA_COLLECTION_VERSION,
    }
