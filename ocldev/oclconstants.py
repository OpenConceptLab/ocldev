"""
Shared constants used throughout the ocldev package
"""


class OclConstants:
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

    # API endpoint stems for owners
    OWNER_STEM_USERS = 'users'
    OWNER_STEM_ORGS = 'orgs'

    # API endpoint stems for repositories
    REPO_STEM_SOURCES = 'sources'
    REPO_STEM_COLLECTIONS = 'collections'
