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

    # Mapping descriptors
    MAPPING_TARGET_INTERNAL = 'Internal'
    MAPPING_TARGET_EXTERNAL = 'External'
    MAPPING_TARGETS = [
        MAPPING_TARGET_INTERNAL,
        MAPPING_TARGET_EXTERNAL,
    ]

    # API endpoint stems for owners
    OWNER_STEM_USERS = 'users'
    OWNER_STEM_ORGS = 'orgs'
    OWNER_TYPE_TO_STEM = {
        RESOURCE_TYPE_ORGANIZATION: OWNER_STEM_ORGS,
        RESOURCE_TYPE_USER: OWNER_STEM_USERS,
    }

    # API endpoint stems for repositories
    REPO_STEM_SOURCES = 'sources'
    REPO_STEM_COLLECTIONS = 'collections'
    REPO_TYPE_TO_STEM = {
        RESOURCE_TYPE_SOURCE: REPO_STEM_SOURCES,
        RESOURCE_TYPE_COLLECTION: REPO_STEM_COLLECTIONS,
    }

    @staticmethod
    def get_owner_url(owner_id='', owner_type=RESOURCE_TYPE_ORGANIZATION):
        if owner_type not in OclConstants.OWNER_TYPE_TO_STEM:
            raise Exception('Invalid owner type "%s"' % owner_type)
        return '/%s/%s' % (OclConstants.OWNER_TYPE_TO_STEM[owner_type], owner_id)

    @staticmethod
    def get_repository_url(owner_id='', repository_id='',
                           owner_type=RESOURCE_TYPE_ORGANIZATION,
                           repository_type=RESOURCE_TYPE_SOURCE):
        owner_url = OclConstants.get_owner_url(owner_id=owner_id, owner_type=owner_type)
        if repository_type not in OclConstants.REPO_TYPE_TO_STEM:
            raise Exception('Invalid repository type "%s"' % repository_type)
        return '%s/%s/%s' % (
            owner_url, OclConstants.REPO_TYPE_TO_STEM[repository_type], repository_id)
