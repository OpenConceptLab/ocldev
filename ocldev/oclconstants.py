"""
Shared constants used throughout the ocldev package
"""


class OclConstants(object):
    """ Shared constants used in the ocldev package """

    # OCL resource type constants
    RESOURCE_TYPE_USER = 'User'
    RESOURCE_TYPE_ORGANIZATION = 'Organization'
    RESOURCE_TYPE_SOURCE = 'Source'
    RESOURCE_TYPE_COLLECTION = 'Collection'
    RESOURCE_TYPE_CONCEPT = 'Concept'
    RESOURCE_TYPE_MAPPING = 'Mapping'
    RESOURCE_TYPE_CONCEPT_REF = 'Concept_Ref'
    RESOURCE_TYPE_MAPPING_REF = 'Mapping_Ref'
    RESOURCE_TYPE_REFERENCE = 'Reference'
    RESOURCE_TYPE_SOURCE_VERSION = 'Source Version'
    RESOURCE_TYPE_COLLECTION_VERSION = 'Collection Version'
    RESOURCE_TYPES = [
        RESOURCE_TYPE_USER,
        RESOURCE_TYPE_ORGANIZATION,
        RESOURCE_TYPE_SOURCE,
        RESOURCE_TYPE_COLLECTION,
        RESOURCE_TYPE_CONCEPT,
        RESOURCE_TYPE_MAPPING,
        RESOURCE_TYPE_CONCEPT_REF,
        RESOURCE_TYPE_MAPPING_REF,
        RESOURCE_TYPE_REFERENCE,
        RESOURCE_TYPE_SOURCE_VERSION,
        RESOURCE_TYPE_COLLECTION_VERSION,
    ]

    # API endpoint stems for owners
    OWNER_STEM_USERS = 'users'
    OWNER_STEM_ORGS = 'orgs'

    # API endpoint stems for repositories
    REPO_STEM_SOURCES = 'sources'
    REPO_STEM_COLLECTIONS = 'collections'
