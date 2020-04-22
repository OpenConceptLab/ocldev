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

    # API endpoint stems for resources
    RESOURCE_STEM_CONCEPTS = 'concepts'
    RESOURCE_STEM_MAPPINGS = 'mappings'
    RESOURCE_STEM_REFERENCES = 'references'
    RESOURCE_TYPE_TO_STEM = {
        RESOURCE_TYPE_CONCEPT: RESOURCE_STEM_CONCEPTS,
        RESOURCE_TYPE_MAPPING: RESOURCE_STEM_MAPPINGS,
        RESOURCE_TYPE_REFERENCE: RESOURCE_STEM_REFERENCES,
    }

    @staticmethod
    def get_owner_type_stem(owner_type):
        """ Get the URL stem for the specified owner type (eg Organization-->orgs) """
        if owner_type in OclConstants.OWNER_TYPE_TO_STEM:
            return OclConstants.OWNER_TYPE_TO_STEM[owner_type]
        return ''

    @staticmethod
    def get_owner_url(owner_id='', include_trailing_slash=False,
                      owner_type=RESOURCE_TYPE_ORGANIZATION):
        """ Returns relative URL for an owner (eg owner or user) """
        if owner_type not in OclConstants.OWNER_TYPE_TO_STEM:
            raise Exception('Invalid owner type "%s"' % owner_type)
        owner_url = '/%s/%s' % (OclConstants.OWNER_TYPE_TO_STEM[owner_type], owner_id)
        if include_trailing_slash:
            owner_url += '/'
        return owner_url

    @staticmethod
    def get_repo_type_stem(repo_type):
        """ Get the URL stem for the specified repository type (eg Source-->sources) """
        if repo_type in OclConstants.REPO_TYPE_TO_STEM:
            return OclConstants.REPO_TYPE_TO_STEM[repo_type]
        return ''

    @staticmethod
    def get_resource_type_stem(resource_type):
        """ Get the URL stem for the specified resource type (eg Concept-->concepts) """
        if resource_type in OclConstants.RESOURCE_TYPE_TO_STEM:
            return OclConstants.RESOURCE_TYPE_TO_STEM[resource_type]
        return ''

    @staticmethod
    def get_repository_url(owner_id='', repository_id='', include_trailing_slash=False,
                           owner_type=RESOURCE_TYPE_ORGANIZATION,
                           repository_type=RESOURCE_TYPE_SOURCE):
        """ Returns relative URL for a repository (eg source or collection) """
        owner_url = OclConstants.get_owner_url(owner_id=owner_id, owner_type=owner_type)
        if not owner_url:
            return ''
        if repository_type not in OclConstants.REPO_TYPE_TO_STEM:
            raise Exception('Invalid repository type "%s"' % repository_type)
        repo_url = '%s/%s/%s' % (
            owner_url, OclConstants.REPO_TYPE_TO_STEM[repository_type], repository_id)
        if include_trailing_slash:
            repo_url += '/'
        return repo_url

    @staticmethod
    def get_resource_url(owner_id='', repository_id='', resource_id='',
                         include_trailing_slash=False, owner_type=RESOURCE_TYPE_ORGANIZATION,
                         repository_type=RESOURCE_TYPE_SOURCE,
                         resource_type=RESOURCE_TYPE_CONCEPT):
        """ Returns relative URL for a resource (eg concept or mapping) """
        repo_url = OclConstants.get_repository_url(
            owner_id=owner_id, repository_id=repository_id,
            owner_type=owner_type, repository_type=repository_type)
        if not repo_url:
            return ''
        if resource_type not in OclConstants.RESOURCE_TYPE_TO_STEM:
            raise Exception('Invalid resource type "%s"' % repository_type)
        resource_url = '%s/%s/%s' % (
            repo_url, OclConstants.RESOURCE_TYPE_TO_STEM[resource_type], resource_id)
        if include_trailing_slash:
            resource_url += '/'
        return resource_url
