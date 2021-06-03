"""
OCL Importer --
Classes to import a list of resources into OCL. OclFlexImporter processes an import locally,
submitting one resource at a time to the OCL API. OclBulkImporter submits an import script
to an OCL server for higher performance asynchronous processing. See oclapi Bulk Importing
documentation for more information: https://github.com/OpenConceptLab/oclapi/wiki/Bulk-Importing

Verbosity settings:
* 0 = show only responses from server
* 1 = show responses from server and all POSTs
* 2 = show everything except debug output
* 3 = show everything plus debug output

Owner fields: ( owner AND owner_type ) OR ( owner_url )
Repository fields: ( source OR source_url ) OR ( collection OR collection_url )
Concept/Mapping fields: ( id ) OR ( url )

Deviations from OCL API responses:
* Sources/Collections:
    - "supported_locales" response is a list in OCL, but a comma-separated string
      is in this script instead
"""
import json
import sys
import time
from datetime import datetime

import six
import six.moves.urllib.parse as urllib_parse
import requests
from ocldev import oclconstants
from ocldev import oclresourcelist


class OclImportError(Exception):
    """ Base exception for this module """
    def __str__(self):
        return '%s %s' % (self.message, self.expression)


class UnexpectedStatusCodeError(OclImportError):
    """ Exception raised for unexpected status code """
    def __init__(self, expression, message):
        OclImportError.__init__(self)
        self.expression = expression
        self.message = message


class InvalidOwnerError(OclImportError):
    """ Exception raised when owner information is invalid """
    def __init__(self, expression, message):
        OclImportError.__init__(self)
        self.expression = expression
        self.message = message


class InvalidRepositoryError(OclImportError):
    """ Exception raised when repository information is invalid """
    def __init__(self, expression, message):
        OclImportError.__init__(self)
        self.expression = expression
        self.message = message


class InvalidObjectDefinition(OclImportError):
    """ Exception raised when object definition invalid """
    def __init__(self, expression, message):
        OclImportError.__init__(self)
        self.expression = expression
        self.message = message


class UnsupportedActionType(OclImportError):
    """ Exception raised for an unsupported action type """
    def __init__(self, expression, message):
        OclImportError.__init__(self)
        self.expression = expression
        self.message = message


class OclImportResults(object):
    """ Class to capture and process the results of processing an import script """

    # Constants for import results modes
    OCL_IMPORT_RESULTS_MODE_SUMMARY = 'summary'
    OCL_IMPORT_RESULTS_MODE_REPORT = 'report'
    OCL_IMPORT_RESULTS_MODE_JSON = 'json'
    OCL_IMPORT_RESULTS_MODES = [
        OCL_IMPORT_RESULTS_MODE_SUMMARY,
        OCL_IMPORT_RESULTS_MODE_REPORT,
        OCL_IMPORT_RESULTS_MODE_JSON,
    ]
    OCL_IMPORT_RESULTS_MODE_DEFAULT = 'report'

    # Helper constants
    SKIP_KEY = 'skip'
    NO_OBJECT_TYPE_KEY = 'NO-OBJECT-TYPE'
    ORGS_RESULTS_ROOT = '/orgs/'
    USERS_RESULTS_ROOT = '/users/'

    def __init__(self, total_lines=0):
        """ Initialize this object """
        self._results = {}
        self.count = 0
        self.num_skipped = 0
        self.total_lines = total_lines
        self.elapsed_seconds = 0
        self.queue = ''
        self.username = ''
        self.state = ''
        self.task = ''
        self.details = None

    def add(self, obj_url='', action_type='', obj_type='', obj_repo_url='',
            http_method='', obj_owner_url='', status_code=None, text='', message=''):
        """
        Add a result to this OclImportResults object
        :param obj_url:
        :param action_type:
        :param obj_type:
        :param obj_repo_url:
        :param http_method:
        :param obj_owner_url:
        :param status_code:
        :return:
        """

        # Determine the first dimension (the "logging root") of the results object
        logging_root = '/'
        if obj_type in [oclconstants.OclConstants.RESOURCE_TYPE_CONCEPT,
                        oclconstants.OclConstants.RESOURCE_TYPE_MAPPING,
                        oclconstants.OclConstants.RESOURCE_TYPE_REFERENCE]:
            logging_root = obj_repo_url
        elif obj_type in [oclconstants.OclConstants.RESOURCE_TYPE_SOURCE,
                          oclconstants.OclConstants.RESOURCE_TYPE_COLLECTION]:
            logging_root = obj_owner_url
        elif obj_type == oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION:
            logging_root = self.ORGS_RESULTS_ROOT
        elif obj_type == oclconstants.OclConstants.RESOURCE_TYPE_USER:
            logging_root = self.USERS_RESULTS_ROOT

        # Setup the results dictionary to accept this new result
        if logging_root not in self._results:
            self._results[logging_root] = {}
        if action_type not in self._results[logging_root]:
            self._results[logging_root][action_type] = {}
        if not status_code:
            status_code = self.SKIP_KEY
        if status_code not in self._results[logging_root][action_type]:
            self._results[logging_root][action_type][status_code] = []

        # Add the result to the results object
        new_result = {
            'obj_type': obj_type,
            'obj_url': obj_url,
            'action_type': action_type,
            'method': http_method,
            'obj_repo_url': obj_repo_url,
            'obj_owner_url': obj_owner_url,
            'status_code': status_code,
            'text': text,
            'message': message
        }
        self._results[logging_root][action_type][status_code].append(new_result)
        self.count += 1

    def has(self, root_key='', limit_to_success_codes=False):
        """
        Return whether this OclImportResults object contains a
        result matching the specified root_key
        :param root_key: Key to match
        :param limit_to_success_codes: Set to true to only match a successful import result
        :return: True if a match found; False otherwise
        """
        if root_key in self._results and not limit_to_success_codes:
            return True
        elif root_key in self._results and limit_to_success_codes:
            for action_type in self._results[root_key]:
                for status_code in self._results[root_key][action_type]:
                    if int(status_code) >= 200 and int(status_code) < 300:
                        return True
        return False

    def has_error_status_code(self):
        """
        Return True if at least one error HTTP response code (e.g. >= 300) is in the results.
        Otherwise return False.
        """
        for root_key in self._results:
            for action_type in self._results[root_key]:
                for status_code in self._results[root_key][action_type]:
                    try:
                        status_code_int = int(status_code)
                    except Exception:
                        status_code_int = 0
                    if status_code == OclImportResults.SKIP_KEY:
                        return True
                    elif status_code_int and status_code_int >= 300:
                        return True
        return False

    def __str__(self):
        """ Get a concise summary of this results object """
        return self.get_summary()

    def get_logging_keys(self):
        """ Returns list of logging keys stored in the results object """
        return list(self._results.keys())

    def get_import_results(self, results_mode='summary', root_key=None):
        """
        Single method to fetch import results in one of the supported formats
        in OclImportResults.OCL_IMPORT_RESULTS_MODES
        """
        results_mode = results_mode.lower()
        if results_mode not in OclImportResults.OCL_IMPORT_RESULTS_MODES:
            results_mode = OclImportResults.OCL_IMPORT_RESULTS_MODE_DEFAULT
        if results_mode == OclImportResults.OCL_IMPORT_RESULTS_MODE_SUMMARY:
            return self.get_detailed_summary(root_key=root_key)
        elif results_mode == OclImportResults.OCL_IMPORT_RESULTS_MODE_REPORT:
            return self.display_report(root_key=root_key)
        elif results_mode == OclImportResults.OCL_IMPORT_RESULTS_MODE_JSON:
            return self.to_json()
        return None

    def get_summary(self, root_key=None):
        """
        Get a concise summary of this results object, optionally filtering by a specific root_key
        :param root_key: Optional root_key to filter the summary results
        :return:
        """
        if not root_key:
            return 'Processed %s of %s total' % (self.count, self.total_lines)
        elif self.has(root_key=root_key):
            num_processed = 0
            for action_type in self._results[root_key]:
                for status_code in self._results[root_key][action_type]:
                    num_processed += len(self._results[root_key][action_type][status_code])
            return 'Processed %s for key "%s"' % (num_processed, root_key)
        return ''

    def get_detailed_summary(self, root_key=None, limit_to_success_codes=False):
        """ Get a detailed summary of the results, optionally filtering by a specific root_key """

        # Apply root_key filter or use all keys if no filter specified
        if root_key:
            keys = [root_key]
        else:
            keys = list(self._results.keys())

        # Build results summary dictionary - organized by action type instead of root
        results_summary = {}
        total_count = 0
        for k in keys:
            for action_type in self._results[k]:
                if action_type not in results_summary:
                    results_summary[action_type] = {}
                for status_code in self._results[k][action_type]:
                    if limit_to_success_codes and (
                            int(status_code) < 200 or int(status_code) >= 300):
                        continue
                    status_code_count = len(self._results[k][action_type][status_code])
                    if status_code not in results_summary[action_type]:
                        results_summary[action_type][status_code] = 0
                    results_summary[action_type][status_code] += status_code_count
                    total_count += status_code_count

        # Turn the results summary dictionary into a string
        output = ''
        for action_type in results_summary:
            if output:
                output += '; '
            status_code_summary = ''
            action_type_count = 0
            for status_code in results_summary[action_type]:
                action_type_count += results_summary[action_type][status_code]
                if status_code_summary:
                    status_code_summary += ', '
                status_code_summary += '%s:%s' % (
                    status_code, results_summary[action_type][status_code])
            output += '%s %s (%s)' % (action_type_count, action_type, status_code_summary)

        # Polish it all off
        if limit_to_success_codes:
            process_str = 'Successfully Processed'
        else:
            process_str = 'Processed'
        if root_key:
            output = '%s %s for key "%s"' % (process_str, output, root_key)
        else:
            output = '%s %s of %s -- %s in %s secs' % (
                process_str, total_count, self.total_lines, output, self.elapsed_seconds
            )

        return output

    def display_report(self, root_key=None):
        """ Display a full report of the results, optionally filtering by a specific root_key """

        # Apply root_key filter or use all keys if no filter specified
        if root_key:
            logging_keys = [root_key]
            output = 'REPORT OF IMPORT RESULTS FOR KEY "%s":' % root_key
        else:
            logging_keys = list(self._results.keys())
            output = 'REPORT OF IMPORT RESULTS:\n'

        # Iterate through logging keys and prepare report
        for logging_key in logging_keys:
            output += '%s:\n' % logging_key
            for action_type in self._results[logging_key]:
                for status_code in self._results[logging_key][action_type]:
                    if action_type == status_code == self.SKIP_KEY:
                        output += '  %s:\n' % (self.SKIP_KEY)
                    else:
                        output += '  %s %s:\n' % (action_type, status_code)
                    for result in self._results[logging_key][action_type][status_code]:
                        output += '    %s  %s\n' % (result['message'], result['text'])

        return output

    def get_stats(self):
        """ Returns dict of stats about the import results """
        return {
            'count': self.count,
            'num_skipped': self.num_skipped,
            'total_lines': self.total_lines,
            'elapsed_seconds': self.elapsed_seconds,
        }

    def to_json(self):
        """ Return serialized JSON of the results object. Works with the load_from_json method """
        return_obj = self.get_stats()
        return_obj['results'] = self._results
        return json.dumps(return_obj)

    @staticmethod
    def load_from_json(json_results):
        """ Load serialized JSON results into this object. Works with the to_json method """
        if isinstance(json_results, six.string_types):
            json_results = json.loads(json_results)
        if isinstance(json_results, dict):
            results_obj = OclImportResults()
            results_obj._results = json_results.get('results', {})
            results_obj.count = json_results.get('count', 0)
            results_obj.num_skipped = json_results.get('num_skipped', 0)
            results_obj.total_lines = json_results.get('total_lines', 0)
            results_obj.elapsed_seconds = json_results.get('elapsed_seconds', 0)
            results_obj.queue = json_results.get('queue', '')
            results_obj.queue = json_results.get('username', '')
            results_obj.queue = json_results.get('state', '')
            results_obj.queue = json_results.get('task', '')
            results_obj.queue = json_results.get('details', None)
            return results_obj
        else:
            raise TypeError('Expected string or dict. "%s" received.' % str(type(json_results)))


class OclBulkImporter(object):
    """
    Helper class to use the OCL bulk import API to process an OCL-formatted JSON lines file.
    The OCL bulk import API simply runs the OclFlexImporter object asynchronously on the server
    for much higher performance processing.

    Currently, bulk import can only be run in live mode (test_mode=False) with limit set to zero
    and updating objects set to False.

    Example use:
    oclfleximporter.OclBulkImporter()
    """

    OCL_BULK_IMPORT_API_ENDPOINT = '/importers/bulk-import/'
    OCL_BULK_IMPORT_PARALLEL_API_ENDPOINT = '/importers/bulk-import-parallel-inline/'
    OCL_BULK_IMPORT_MAX_WAIT_SECONDS = 120 * 60
    OCL_BULK_IMPORT_MINIMUM_DELAY_SECONDS = 5

    OCL_BULK_IMPORT_STATUS_PENDING = 'PENDING'
    OCL_BULK_IMPORT_STATUS_STARTED = 'STARTED'
    OCL_BULK_IMPORT_STATUSES = [
        OCL_BULK_IMPORT_STATUS_PENDING,
        OCL_BULK_IMPORT_STATUS_STARTED,
    ]

    @staticmethod
    def post(file_path='', input_list=None, api_url_root='', api_token='', queue='',
             test_mode=False, parallel=False):
        """
        Post the import to the OCL bulk import API endpoint and return the request object
        :param file_path: Full path to a file to import
        :param input_list: Python list of JSON dictionaries to import
        :param api_url_root: e.g. https://api.openconceptlab.org
        :param api_token: OCL API token for the user account that will run the import
        :param queue: Optional bulk import queue key
        :param test_mode: Set to True to simulate the import
        :param parallel: Set to True to process resources of same type in parallel
        """

        # Prepare the body (import JSON) of the post request
        if isinstance(input_list, (list, oclresourcelist.OclResourceList)):
            # change to a string with line separators
            post_data = ''
            for line in input_list:
                post_data += json.dumps(line) + '\n'
        elif file_path:
            # load the file as a string
            file_handle = open(file_path, 'rb')
            post_data = file_handle.read()

        # Submit the import
        if parallel:
            url = '%s%s' % (api_url_root, OclBulkImporter.OCL_BULK_IMPORT_PARALLEL_API_ENDPOINT)
        else:
            url = '%s%s' % (api_url_root, OclBulkImporter.OCL_BULK_IMPORT_API_ENDPOINT)
        if queue:
            url += '%s/' % queue
        api_headers = {'Authorization': 'Token ' + api_token}
        import_response = requests.post(url, headers=api_headers, data=post_data)

        return import_response

    @staticmethod
    def get_queued_imports(api_url_root='', api_token='', queue='', status_filter=None):
        """
        :param api_url_root:
        :param api_token:
        :param queue: Optional queue filter. If empty, returns results across all user's queues.
        :param status_filter: Optional status filter. Can be a string or list of strings
            corresponding to values status values that are still returned.
        """
        # Retrieve the queued imports
        url = '%s%s' % (api_url_root, OclBulkImporter.OCL_BULK_IMPORT_API_ENDPOINT)
        if queue:
            url += '%s/' % queue
        api_headers = {}
        if api_token:
            api_headers['Authorization'] = 'Token %s' % api_token
        queued_imports_response = requests.get(url, headers=api_headers)
        queued_imports_response.raise_for_status()
        queued_imports = queued_imports_response.json()

        # Optionally filter the queued imports by status
        if status_filter:
            filtered_queued_imports = []
            if isinstance(status_filter, str):
                status_filter = [status_filter]
            if not isinstance(status_filter, list):
                raise TypeError(
                    "status_filter argument must be list or string. %s provided." % type(status_filter))
            for queued_import in queued_imports:
                if "state" in queued_import and queued_import["state"] in status_filter:
                    filtered_queued_imports.append(queued_import)
            return filtered_queued_imports

        return queued_imports

    @staticmethod
    def get_bulk_import_results(task_id=None, api_url_root='', api_token='',
                                max_wait_seconds=0, delay_seconds=15):
        """
        Get an OclImportResults object representing the results of a bulk import API process
        submit to OCL as identified by a task_id.
        If the import is still being processed, the method will continue to try after
        delay_seconds (default is 15 seconds) until the time elapsed is greater than
        max_wait_seconds. delay_seconds must be greater than or equal to
        OclBulkImporter.OCL_BULK_IMPORT_MINIMUM_DELAY_SECONDS seconds. Set max_wait_seconds
        to zero (the default) to only request results once. max_wait_seconds
        must be less than OclBulkImporter.OCL_BULK_IMPORT_MAX_WAIT_SECONDS.
        """

        # Setup the request
        max_wait_seconds = min(OclBulkImporter.OCL_BULK_IMPORT_MAX_WAIT_SECONDS, max_wait_seconds)
        delay_seconds = max(OclBulkImporter.OCL_BULK_IMPORT_MINIMUM_DELAY_SECONDS, delay_seconds)
        start_time = time.time()
        url = api_url_root + OclBulkImporter.OCL_BULK_IMPORT_API_ENDPOINT
        url_params = {'task': task_id, 'result': 'json'}
        api_headers = {'Authorization': 'Token ' + api_token}

        # Do the initial request and return if successful and import is complete
        import_results_response = requests.get(url, params=url_params, headers=api_headers)
        import_results_response.raise_for_status()
        results_json = import_results_response.json()
        if 'state' not in results_json or (
                'state' in results_json and
                results_json['state'] not in OclBulkImporter.OCL_BULK_IMPORT_STATUSES):
            return OclImportResults.load_from_json(results_json)

        # Import results were not ready, so start looping
        while time.time() - start_time + delay_seconds < max_wait_seconds:
            # print 'Delaying %s seconds...' % str(delay_seconds)
            time.sleep(delay_seconds)
            import_results_response = requests.get(url, params=url_params, headers=api_headers)
            import_results_response.raise_for_status()
            results_json = import_results_response.json()
            if 'state' not in results_json or (
                    'state' in results_json and
                    results_json['state'] not in OclBulkImporter.OCL_BULK_IMPORT_STATUSES):
                return OclImportResults.load_from_json(results_json)

        return None


class OclFlexImporter(object):
    """
    Class to flexibly import multiple resource types into OCL from JSON lines files via
    the OCL API rather than the batch importer.
    """

    # Default reference batch size -- set to 0 to disable batching by default
    DEFAULT_REFERENCE_BATCH_SIZE = 0

    # Constants for import action types
    ACTION_TYPE_DELETE = 'DELETE'
    ACTION_TYPE_CREATE_OR_UPDATE = 'CREATE_OR_UPDATE'
    ACTION_TYPE_CREATE = 'NEW'
    ACTION_TYPE_UPDATE = 'UPDATE'
    ACTION_TYPE_RETIRE = 'RETIRE'
    ACTION_TYPE_OTHER = 'OTHER'
    ACTION_TYPE_SKIP = 'SKIP'
    ACTION_TYPE_DEFAULT = ACTION_TYPE_CREATE_OR_UPDATE

    # All defined action types used for importing, logging, and future functionality
    ACTION_TYPES = [
        ACTION_TYPE_DELETE,
        ACTION_TYPE_CREATE_OR_UPDATE,
        ACTION_TYPE_CREATE,
        ACTION_TYPE_UPDATE,
        ACTION_TYPE_RETIRE,
        ACTION_TYPE_OTHER,
        ACTION_TYPE_SKIP
    ]

    # Currently supported import action types
    IMPORT_ACTION_TYPES = [
        ACTION_TYPE_DELETE,
        ACTION_TYPE_CREATE_OR_UPDATE,
        ACTION_TYPE_CREATE,
        ACTION_TYPE_UPDATE,
    ]

    # Constants for URL types
    URL_TYPE_RESOURCE_TYPE_ONLY = 'resource_type_only'
    URL_TYPE_RESOURCE_TYPE_AND_ID = 'resource_type_and_id'

    # Constants for mapping supported import action types to url types
    MAP_ACTION_TYPE_TO_URL_TYPE = {
        ACTION_TYPE_DELETE: URL_TYPE_RESOURCE_TYPE_AND_ID,
        ACTION_TYPE_CREATE: URL_TYPE_RESOURCE_TYPE_ONLY,
        ACTION_TYPE_UPDATE: URL_TYPE_RESOURCE_TYPE_AND_ID
    }

    # Constants for HTTP methods
    HTTP_METHOD_POST = "POST"
    HTTP_METHOD_PUT = "PUT"
    HTTP_METHOD_DELETE = "DELETE"
    HTTP_METHOD_GET = "GET"
    HTTP_METHOD_HEAD = "HEAD"

    # Constants for OCL resource definitions
    OBJ_DEF_ATTR_HTTP_IMPORT_METHOD = "http_import_method"

    # Constants for inline resource attributes
    ATTR_RESOURCE_TYPE = 'type'
    ATTR_ACTION = '__action'

    # Resource type definitions
    # TODO: Transition to a single definition per resource that lives in OclDev
    obj_def = {
        oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION: {
            "id_field": "id",
            "url_name": "orgs",
            "has_owner": False,
            "has_source": False,
            "has_collection": False,
            "allowed_fields": [
                "id", "company", "extras", "location", "name",
                "public_access", "extras", "website"
            ],
            OBJ_DEF_ATTR_HTTP_IMPORT_METHOD: {
                ACTION_TYPE_CREATE: HTTP_METHOD_POST,
                ACTION_TYPE_UPDATE: HTTP_METHOD_POST,
                ACTION_TYPE_DELETE: HTTP_METHOD_DELETE
            }
        },
        oclconstants.OclConstants.RESOURCE_TYPE_SOURCE: {
            "id_field": "id",
            "url_name": "sources",
            "has_owner": True,
            "has_source": False,
            "has_collection": False,
            "allowed_fields": [
                "id", "short_code", "name", "full_name", "description",
                "source_type", "custom_validation_schema", "public_access",
                "default_locale", "supported_locales", "website", "extras", "external_id"
            ],
            OBJ_DEF_ATTR_HTTP_IMPORT_METHOD: {
                ACTION_TYPE_CREATE: HTTP_METHOD_POST,
                ACTION_TYPE_UPDATE: HTTP_METHOD_PUT,
                ACTION_TYPE_DELETE: HTTP_METHOD_DELETE
            }
        },
        oclconstants.OclConstants.RESOURCE_TYPE_COLLECTION: {
            "id_field": "id",
            "url_name": "collections",
            "has_owner": True,
            "has_source": False,
            "has_collection": False,
            "allowed_fields": [
                "id", "short_code", "name", "full_name", "description", "collection_type",
                "custom_validation_schema", "public_access", "default_locale", "supported_locales",
                "website", "extras", "external_id"
            ],
            OBJ_DEF_ATTR_HTTP_IMPORT_METHOD: {
                ACTION_TYPE_CREATE: HTTP_METHOD_POST,
                ACTION_TYPE_UPDATE: HTTP_METHOD_PUT,
                ACTION_TYPE_DELETE: HTTP_METHOD_DELETE
            }
        },
        oclconstants.OclConstants.RESOURCE_TYPE_CONCEPT: {
            "id_field": "id",
            "url_name": "concepts",
            "has_owner": True,
            "has_source": True,
            "has_collection": False,
            "allowed_fields": [
                "id", "external_id", "concept_class", "datatype", "names",
                "descriptions", "retired", "extras"
            ],
            OBJ_DEF_ATTR_HTTP_IMPORT_METHOD: {
                ACTION_TYPE_CREATE: HTTP_METHOD_POST,
                ACTION_TYPE_UPDATE: HTTP_METHOD_PUT,
                ACTION_TYPE_DELETE: HTTP_METHOD_DELETE
            }
        },
        oclconstants.OclConstants.RESOURCE_TYPE_MAPPING: {
            "id_field": "id",
            "url_name": "mappings",
            "has_owner": True,
            "has_source": True,
            "has_collection": False,
            "allowed_fields": [
                "id", "map_type", "from_concept_url", "to_source_url", "to_concept_url",
                "to_concept_code", "to_concept_name", "extras", "external_id"
            ],
            OBJ_DEF_ATTR_HTTP_IMPORT_METHOD: {
                ACTION_TYPE_CREATE: HTTP_METHOD_POST,
                ACTION_TYPE_UPDATE: HTTP_METHOD_POST,
                ACTION_TYPE_DELETE: HTTP_METHOD_DELETE
            }
        },
        oclconstants.OclConstants.RESOURCE_TYPE_REFERENCE: {
            "url_name": "references",
            "has_owner": True,
            "has_source": False,
            "has_collection": True,
            "allowed_fields": ["data"],
            OBJ_DEF_ATTR_HTTP_IMPORT_METHOD: {
                ACTION_TYPE_CREATE: HTTP_METHOD_PUT,
                ACTION_TYPE_UPDATE: None,
                ACTION_TYPE_DELETE: HTTP_METHOD_DELETE
            }
        },
        oclconstants.OclConstants.RESOURCE_TYPE_SOURCE_VERSION: {
            "id_field": "id",
            "url_name": "versions",
            "has_owner": True,
            "has_source": True,
            "has_collection": False,
            "omit_resource_name_on_get": True,
            "allowed_fields": ["id", "external_id", "description", "released"],
            OBJ_DEF_ATTR_HTTP_IMPORT_METHOD: {
                ACTION_TYPE_CREATE: HTTP_METHOD_POST,
                ACTION_TYPE_UPDATE: HTTP_METHOD_PUT,
                ACTION_TYPE_DELETE: HTTP_METHOD_DELETE
            }
        },
        oclconstants.OclConstants.RESOURCE_TYPE_COLLECTION_VERSION: {
            "id_field": "id",
            "url_name": "versions",
            "has_owner": True,
            "has_source": False,
            "has_collection": True,
            "omit_resource_name_on_get": True,
            "allowed_fields": ["id", "external_id", "description", "released"],
            OBJ_DEF_ATTR_HTTP_IMPORT_METHOD: {
                ACTION_TYPE_CREATE: HTTP_METHOD_POST,
                ACTION_TYPE_UPDATE: HTTP_METHOD_PUT,
                ACTION_TYPE_DELETE: HTTP_METHOD_DELETE
            }
        },
        oclconstants.OclConstants.RESOURCE_TYPE_USER: {
            "id_field": "username",
            "url_name": "users",
            "has_owner": False,
            "has_source": False,
            "has_collection": False,
            "allowed_fields": [
                "username", "name", "email", "company", "location", "preferred_locale"],
            OBJ_DEF_ATTR_HTTP_IMPORT_METHOD: {
                ACTION_TYPE_CREATE: HTTP_METHOD_POST,
                ACTION_TYPE_UPDATE: HTTP_METHOD_POST,
                ACTION_TYPE_DELETE: HTTP_METHOD_DELETE
            }
        }
    }

    def __init__(self, file_path='', input_list=None, api_url_root='', api_token='', limit=0,
                 test_mode=False, verbosity=1, do_update_if_exists=False, import_delay=0,
                 reference_batch_size=DEFAULT_REFERENCE_BATCH_SIZE, update_progress=None):
        """
        Initialize this object

        :param file_path:
        :param input_list:
        :param api_url_root:
        :param api_token:
        :param limit:
        :param test_mode:
        :param verbosity:
        :param do_update_if_exists:
        :param import_delay:
        :param reference_batch_size:
        :param update_progress: function(str) to call when progress changes
        """

        self.input_list = input_list
        self.file_path = file_path
        if file_path:
            self.load_from_file(file_path)
        self.api_token = api_token
        self.api_url_root = api_url_root
        self.test_mode = test_mode
        self.do_update_if_exists = do_update_if_exists
        self.verbosity = verbosity
        self.limit = limit
        self.import_delay = import_delay
        self.skip_line_count = False
        self.reference_batch_size = reference_batch_size
        self.import_results = None
        self._cache_obj_exists = {}
        self.update_progress = update_progress

        # Prepare the headers
        self.api_headers = {
            'Authorization': 'Token ' + self.api_token,
            'Content-Type': 'application/json'
        }

    def log(self, *args):
        """ Output log information """
        sys.stdout.write('[' + str(datetime.now()) + '] ')
        for arg in args:
            sys.stdout.write(str(arg))
            sys.stdout.write(' ')
        sys.stdout.write('\n')
        sys.stdout.flush()

    def log_settings(self):
        """ Output log of the object settings """
        self.log("**** OCL IMPORT SCRIPT SETTINGS ****",
                 "API Root URL:", self.api_url_root,
                 ", API Token:", self.api_token,
                 ", Import File:", self.file_path,
                 ", Test Mode:", self.test_mode,
                 ", Update Resource if Exists:", self.do_update_if_exists,
                 ", Verbosity:", self.verbosity,
                 ", Import Delay: ", self.import_delay)

    def load_from_file(self, file_path):
        """ Load the OCL-formatted JSON file from the specified path """
        self.file_path = file_path
        self.input_list = []
        with open(self.file_path) as json_file:
            for json_line_raw in json_file:
                self.input_list.append(json.loads(json_line_raw))

    def report_progress(self):
        """ Save current progress string to instance """
        if self.update_progress:
            self.update_progress("%s of %s" % (
                self.import_results.count,
                self.import_results.total_lines))

    def process(self):
        """
        Import a list of OCL-formatted JSON resources using the OCL API
        :return: int Number of JSON lines processed
        """

        # Start timer
        start_time = time.time()

        # Display global settings
        if self.verbosity:
            self.log_settings()

        # Count lines
        total_lines = 0
        if not self.skip_line_count:
            total_lines = len(self.input_list)

        # Loop through each JSON object
        self.import_results = OclImportResults(total_lines=total_lines)
        self.report_progress()
        obj_def_keys = list(self.obj_def.keys())
        count = 0
        num_processed = 0
        num_skipped = 0
        for json_line_obj in self.input_list:
            # Copy the object so that the original remains untouched
            json_line_obj = json_line_obj.copy()

            json_line_raw = json.dumps(json_line_obj)
            if self.limit > 0 and count >= self.limit:
                break
            count += 1
            if OclFlexImporter.ATTR_RESOURCE_TYPE in json_line_obj:
                obj_type = json_line_obj.pop(OclFlexImporter.ATTR_RESOURCE_TYPE)
                if (obj_type == oclconstants.OclConstants.RESOURCE_TYPE_REFERENCE and
                        self.reference_batch_size):
                    self.process_reference_object(
                        json_line_obj, batch_size=self.reference_batch_size)
                    num_processed += 1
                elif obj_type in obj_def_keys:
                    self.process_object(obj_type, json_line_obj)
                    num_processed += 1
                else:
                    # Invalid resource type attribute
                    message = "Unrecognized '%s' attribute '%s' for object: %s" % (
                        OclFlexImporter.ATTR_RESOURCE_TYPE, obj_type, json_line_raw)
                    self.import_results.add(action_type=self.ACTION_TYPE_SKIP, obj_type=obj_type,
                                            text=json_line_raw, message=message)
                    self.log('**** SKIPPING: %s' % message)
                    num_skipped += 1
            else:
                # Missing the resource type attribute
                message = "No '%s' attribute: %s" % (
                    OclFlexImporter.ATTR_RESOURCE_TYPE, json_line_raw)
                self.import_results.add(
                    action_type=self.ACTION_TYPE_SKIP, text=json_line_raw, message=message)
                self.log('**** SKIPPING: %s' % message)
                num_skipped += 1

            self.import_results.elapsed_seconds = self.get_elapsed_seconds_from(start_time)
            self.log('[%s]' % self.import_results.get_detailed_summary())
            self.report_progress()

            # Optionally delay before processing next row
            if self.import_delay and not self.test_mode:
                time.sleep(self.import_delay)

        self.import_results.elapsed_seconds = self.get_elapsed_seconds_from(start_time)
        return count

    @staticmethod
    def get_elapsed_seconds_from(start_time):
        return time.time() - start_time

    def does_object_exist(self, obj_url, use_cache=True):
        """ Returns whether a resource at the specified URL already exists. """

        # If we already know the resource exists, then just return True
        if use_cache and obj_url in self._cache_obj_exists and self._cache_obj_exists[obj_url]:
            return True

        # Object existence not cached, so use OCL API to check if it exists
        request_existence = requests.head(self.api_url_root + obj_url, headers=self.api_headers)
        if request_existence.status_code == requests.codes.ok:
            self._cache_obj_exists[obj_url] = True
            return True
        elif 400 <= request_existence.status_code < 500:
            return False
        else:
            raise UnexpectedStatusCodeError(
                "GET " + self.api_url_root + obj_url,
                "Unexpected status code returned: " + str(request_existence.status_code))

    def does_mapping_exist(self, obj_url, obj):
        """
        Returns whether a mapping already exists by finding a matching source from_concept,
        to_concept, and map_type, or by finding a matching mapping ID (if provided).
        """

        # # Return false if correct fields not set
        # mapping_target = None
        # if ('from_concept_url' not in obj or not obj['from_concept_url']
        #         or 'map_type' not in obj or not obj['map_type']):
        #     # Invalid mapping -- no from_concept or map_type
        #     return False
        # if 'to_concept_url' in obj:
        #     mapping_target = self.INTERNAL_MAPPING
        # elif 'to_source_url' in obj and 'to_concept_code' in obj:
        #     mapping_target = self.EXTERNAL_MAPPING
        # else:
        #     # Invalid to_concept
        #     return False

        # # Build query parameters
        # params = {
        #     'fromConceptOwner': '',
        #     'fromConceptOwnerType': '',
        #     'fromConceptSource': '',
        #     'fromConcept': obj['from_concept_url'],
        #     'mapType': obj['map_type'],
        #     'toConceptOwner': '',
        #     'toConceptOwnerType': '',
        #     'toConceptSource': '',
        #     'toConcept': '',
        # }
        # #if mapping_target == self.INTERNAL_MAPPING:
        # #    params['toConcept'] = obj['to_concept_url']
        # #else:
        # #    params['toConcept'] = obj['to_concept_code']

        # # Use API to check if mapping exists
        # request_existence = requests.head(
        #     self.api_url_root + obj_url, headers=self.api_headers, params=params)
        # if request_existence.status_code == requests.codes.ok:
        #     if 'num_found' in request_existence.headers and int(
        #             request_existence.headers['num_found']) >= 1:
        #         return True
        #     else:
        #         return False
        # elif request_existence.status_code == requests.codes.not_found:
        #     return False
        # else:
        #     raise UnexpectedStatusCodeError(
        #         "GET " + self.api_url_root + obj_url,
        #         "Unexpected status code returned: " + str(request_existence.status_code))

        return False

    def does_reference_exist(self, obj_url, obj):
        """ Returns whether the specified reference already exists """

        # # Return false if no expression
        # if 'expression' not in obj or not obj['expression']:
        #     return False

        # # Use the API to check if object exists
        # params = {'q': obj['expression']}
        # request_existence = requests.head(
        #     self.api_url_root + obj_url, headers=self.api_headers, params=params)
        # if request_existence.status_code == requests.codes.ok:
        #     if 'num_found' in request_existence.headers and int(
        #             request_existence.headers['num_found']) >= 1:
        #         return True
        #     else:
        #         return False
        # elif request_existence.status_code == requests.codes.not_found:
        #     return False
        # else:
        #     raise UnexpectedStatusCodeError(
        #         "GET " + self.api_url_root + obj_url,
        #         "Unexpected status code returned: " + str(request_existence.status_code))
        return False

    @staticmethod
    def batch_reference_object(reference_resource, batch_size=1000):
        """ Split list of references into batches """
        obj_type = oclconstants.OclConstants.RESOURCE_TYPE_REFERENCE
        base_obj = reference_resource.copy()
        base_obj_data = base_obj.pop('data')
        if not batch_size:
            batch_size = len(base_obj_data['expressions'])
        expressions_raw = base_obj_data['expressions']
        expressions_chunked = [
            expressions_raw[i * batch_size:(i + 1) * batch_size] for i in range(
                (len(expressions_raw) + batch_size - 1) // batch_size)]
        new_resources = []
        for chunk in expressions_chunked:
            new_obj = base_obj.copy()
            new_obj['data'] = {'expressions': chunk}
            new_resources.append(new_obj)
        return new_resources

    def process_reference_object(self, obj, batch_size=DEFAULT_REFERENCE_BATCH_SIZE):
        """ Process list of references, optionally splitting into batches """
        batched_resources = OclFlexImporter.batch_reference_object(obj, batch_size=batch_size)
        if len(batched_resources) > 1:
            message = ('INFO: New reference request with %s expressions automatically '
                       'split into %s batches of %s expressions or less') % (
                           str(len(obj['data']['expressions'])),
                           str(len(batched_resources)),
                           str(len(batched_resources[0]['data']['expressions'])))
            self.log(message)
        for batched_resource in batched_resources:
            self.process_object(
                oclconstants.OclConstants.RESOURCE_TYPE_REFERENCE, batched_resource)

    def process_object(self, obj_type, obj):
        """ Processes an individual object in the import file """

        # Grab the object ID
        obj_id = ''
        if 'id_field' in self.obj_def[obj_type] and self.obj_def[obj_type]['id_field'] in obj:
            obj_id = obj[self.obj_def[obj_type]['id_field']]

        # Determine initial action type
        action_type = obj.get(OclFlexImporter.ATTR_ACTION, OclFlexImporter.ACTION_TYPE_DEFAULT)

        # Determine whether this resource has an owner, source, or collection
        has_owner = False
        has_source = False
        has_collection = False
        if self.obj_def[obj_type]["has_owner"]:
            has_owner = True
        if self.obj_def[obj_type]["has_source"] and self.obj_def[obj_type]["has_collection"]:
            err_msg = "Object definition for '%s' must not have both " % obj_type
            err_msg += "'has_source' and 'has_collection' set to True"
            raise InvalidObjectDefinition(obj, err_msg)
        elif self.obj_def[obj_type]["has_source"]:
            has_source = True
        elif self.obj_def[obj_type]["has_collection"]:
            has_collection = True

        # Set owner URL using ("owner_url") OR ("owner" AND "owner_type")
        # e.g. /users/johndoe/ OR /orgs/MyOrganization/
        # NOTE: Owner URL always ends with a forward slash
        obj_owner_url = None
        if has_owner:
            if "owner_url" in obj:
                obj_owner_url = obj.pop("owner_url")
                obj.pop("owner", None)
                obj.pop("owner_type", None)
            elif "owner" in obj and "owner_type" in obj:
                obj_owner_type = obj.pop("owner_type")
                obj_owner = obj.pop("owner")
                if obj_owner_type == oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION:
                    obj_owner_url = "/%s/%s/" % (
                        self.obj_def[
                            oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION]["url_name"],
                        obj_owner)
                elif obj_owner_type == oclconstants.OclConstants.RESOURCE_TYPE_USER:
                    obj_owner_url = "/%s/%s/" % (
                        self.obj_def[oclconstants.OclConstants.RESOURCE_TYPE_USER]["url_name"],
                        obj_owner)
                else:
                    raise InvalidOwnerError(
                        obj, "Valid owner information required for object of type '%s'. '%s' owner type provided." % (
                            obj_owner_type, obj_type))
            elif has_source and 'source_url' in obj and obj['source_url']:
                # Extract owner info from the source URL
                obj_owner_url = obj['source_url'][:OclFlexImporter.find_nth(
                    obj['source_url'], '/', 3) + 1]
            elif has_collection and 'collection_url' in obj and obj['collection_url']:
                # Extract owner info from the collection URL
                obj_owner_url = obj['collection_url'][:OclFlexImporter.find_nth(
                    obj['collection_url'], '/', 3) + 1]
            else:
                raise InvalidOwnerError(
                    obj, "Valid owner information required for object of type '" + obj_type + "'")

        # Set repository URL using ("source_url" OR "source") OR ("collection_url" OR "collection")
        # e.g. /orgs/MyOrganization/sources/MySource/ OR /orgs/CIEL/collections/StarterSet/
        # NOTE: Repository URL always ends with a forward slash
        obj_repo_url = None
        if has_source:
            if "source_url" in obj:
                obj_repo_url = obj.pop("source_url")
                obj.pop("source", None)
            elif "source" in obj:
                obj_repo_url = obj_owner_url + 'sources/' + obj.pop("source") + "/"
            else:
                raise InvalidRepositoryError(
                    obj, "Valid source information required for object of type '%s'" % obj_type)
        elif has_collection:
            if "collection_url" in obj:
                obj_repo_url = obj.pop("collection_url")
                obj.pop("collection", None)
            elif "collection" in obj:
                obj_repo_url = obj_owner_url + 'collections/' + obj.pop("collection") + "/"
            else:
                raise InvalidRepositoryError(
                    obj, "Valid collection information required for object of type '%s'" % obj_type)

        # Build object URLs -- note that these always end with forward slashes
        obj_url = new_obj_url = ''
        if has_source or has_collection:
            if 'omit_resource_name_on_get' in self.obj_def[
                    obj_type] and self.obj_def[obj_type]['omit_resource_name_on_get']:
                # Source or collection version does not use 'versions' in endpoint
                new_obj_url = obj_repo_url + self.obj_def[obj_type]["url_name"] + "/"
                obj_url = obj_repo_url + obj_id + "/"
            elif obj_id:
                # Concept
                new_obj_url = obj_repo_url + self.obj_def[obj_type]["url_name"] + "/"
                obj_url = new_obj_url + obj_id + "/"
            else:
                # Mapping, reference, etc.
                new_obj_url = obj_url = obj_repo_url + self.obj_def[obj_type]["url_name"] + "/"
        elif has_owner:
            # Repositories (source or collection) and anything that also has a repository
            new_obj_url = obj_owner_url + self.obj_def[obj_type]["url_name"] + "/"
            obj_url = new_obj_url + obj_id + "/"
        else:
            # Only orgs/users don't have an owner or repository, and only orgs can be created here
            new_obj_url = '/' + self.obj_def[obj_type]["url_name"] + "/"
            obj_url = new_obj_url + obj_id + "/"

        # Handle query parameters
        # NOTE: This is hard coded just for references for now
        query_params = {}
        if obj_type == oclconstants.OclConstants.RESOURCE_TYPE_REFERENCE:
            if "__cascade" in obj:
                query_params["cascade"] = obj.pop("__cascade")

        # Pull out the fields that aren't allowed
        obj_not_allowed = {}
        for k in list(obj.keys()):
            if k not in self.obj_def[obj_type]["allowed_fields"]:
                obj_not_allowed[k] = obj.pop(k)

        # Display some debug info
        if self.verbosity >= 1:
            self.log("**** %s %s: %s%s ****" % (
                action_type, obj_type, self.api_url_root, obj_url))
            # self.log("**** Importing " + obj_type + ": " + self.api_url_root + obj_url + " ****")
        if self.verbosity >= 2:
            self.log("** Allowed Fields: **", json.dumps(obj))
            self.log("** Removed Fields: **", json.dumps(obj_not_allowed))

        # Check if owner exists, for objects that have owners
        # NOTE: At this point obj_url, obj_owner_url, and obj_repo_url are set
        if has_owner and obj_owner_url:
            try:
                if self.does_object_exist(obj_owner_url):
                    self.log("** INFO: Owner exists at: " + obj_owner_url)
                else:
                    message = "Owner does not exist at: %s" % obj_owner_url
                    self.log("** SKIPPING: %s" % message)
                    self.import_results.add(action_type=self.ACTION_TYPE_SKIP, obj_type=obj_type,
                                            obj_url=obj_url, obj_repo_url=obj_repo_url,
                                            obj_owner_url=obj_owner_url,
                                            text=json.dumps(obj), message=message)
                    if not self.test_mode:
                        return
            except UnexpectedStatusCodeError as err:
                message = "Unexpected error occurred: %s, %s" % (err.expression, err.message)
                self.import_results.add(action_type=self.ACTION_TYPE_SKIP, obj_type=obj_type,
                                        obj_url=obj_url, obj_repo_url=obj_repo_url,
                                        obj_owner_url=obj_owner_url,
                                        text=json.dumps(obj), message=message)
                self.log("** SKIPPING: %s" % message)
                return

        # Check if repository exists, for objects that are saved in a repository
        if (has_source or has_collection) and obj_repo_url:
            try:
                if self.does_object_exist(obj_repo_url):
                    self.log("** INFO: Repository exists at: " + obj_repo_url)
                else:
                    message = "Repository does not exist at: %s" % obj_repo_url
                    self.import_results.add(action_type=self.ACTION_TYPE_SKIP, obj_type=obj_type,
                                            obj_url=obj_url, obj_repo_url=obj_repo_url,
                                            obj_owner_url=obj_owner_url,
                                            text=json.dumps(obj), message=message)
                    self.log("** SKIPPING: %s" % message)
                    if not self.test_mode:
                        return
            except UnexpectedStatusCodeError as err:
                message = "Unexpected error occurred: %s, %s" % (err.expression, err.message)
                self.import_results.add(action_type=self.ACTION_TYPE_SKIP, obj_type=obj_type,
                                        obj_url=obj_url, obj_repo_url=obj_repo_url,
                                        obj_owner_url=obj_owner_url,
                                        text=json.dumps(obj), message=message)
                self.log("** SKIPPING: %s" % message)
                return

        # Check if object already exists: GET self.api_url_root + obj_url
        obj_already_exists = False
        try:
            if obj_type == oclconstants.OclConstants.RESOURCE_TYPE_REFERENCE:
                obj_already_exists = self.does_reference_exist(obj_url, obj)
            elif obj_type == oclconstants.OclConstants.RESOURCE_TYPE_MAPPING:
                obj_already_exists = self.does_mapping_exist(obj_url, obj)
            else:
                obj_already_exists = self.does_object_exist(obj_url)
        except UnexpectedStatusCodeError as err:
            message = "WARNING: Unexpected error occurred: %s, %s" % (err.expression, err.message)
            self.import_results.add(action_type=self.ACTION_TYPE_SKIP, obj_type=obj_type,
                                    obj_url=obj_url, obj_repo_url=obj_repo_url,
                                    obj_owner_url=obj_owner_url,
                                    text=json.dumps(obj), message=message)
            self.log("** SKIPPING: %s" % message)
            return
        if obj_already_exists and not self.do_update_if_exists:
            message = "INFO: Object already exists at: %s%s" % (self.api_url_root, obj_url)
            self.import_results.add(action_type=self.ACTION_TYPE_SKIP, obj_type=obj_type,
                                    obj_url=obj_url, obj_repo_url=obj_repo_url,
                                    obj_owner_url=obj_owner_url,
                                    text=json.dumps(obj), message=message)
            self.log("** SKIPPING: %s" % message)
            if not self.test_mode:
                return
        elif obj_already_exists:
            self.log("** INFO: Object already exists at: %s%s" % (self.api_url_root, obj_url))
        else:
            self.log("** INFO: Object does not exist so we'll create it at: %s%s" % (
                self.api_url_root, obj_url))

        # Perform the action: Create/update/delete the object
        try:
            self.import_resource(
                action_type=action_type, obj_type=obj_type, obj_id=obj_id,
                obj_owner_url=obj_owner_url, obj_repo_url=obj_repo_url, obj_url=obj_url,
                new_obj_url=new_obj_url, obj_already_exists=obj_already_exists, obj=obj,
                obj_not_allowed=obj_not_allowed, query_params=query_params)
        except requests.exceptions.HTTPError as err:
            self.log("ERROR: ", str(err))
        except UnsupportedActionType as err:
            self.log("ERROR: ", str(err))

    def import_resource(self, action_type='', obj_type='', obj_id='', obj_owner_url='',
                        obj_repo_url='', obj_url='', new_obj_url='', obj_already_exists=False,
                        obj=None, obj_not_allowed=None, query_params=None):
        """
        Imports a resource as a create, update, or delete request to the OCL API.
        :param action_type: One of the OclFlexImporter.IMPORT_ACTION_TYPES constants
        :param obj_type: One of the OclConstants.RESOURCE_TYPES constants
        :param obj_id: Unique identifier for the object
        :param obj_repo_url: Relative URL of a resource's repository, if applicable, eg:
            /orgs/MyOrg/sources/MySource/
        :param obj_url: Relative URL of a resource including its identifier, eg:
            /orgs/MyOrg/sources/MySource/concepts/MyConceptId/
        :param new_obj_url: Reelative URL used to create a new object, excluding its identifier.
            For example, for a concept it would be: /orgs/MyOrg/sources/MySource/concepts/
        :param obj_already_exists: Whether an object already exists
        :param obj: JSON object to be imported
        :param obj_not_allowed: Fields removed from the object before importing
        :param query_params: Additional parameters to be included in the import API request
        """

        # Determine the action type
        if not action_type:
            action_type = OclFlexImporter.ACTION_TYPE_DEFAULT
        if action_type == OclFlexImporter.ACTION_TYPE_CREATE_OR_UPDATE:
            if obj_already_exists:
                action_type = OclFlexImporter.ACTION_TYPE_UPDATE
            else:
                action_type = OclFlexImporter.ACTION_TYPE_CREATE
        elif action_type not in OclFlexImporter.IMPORT_ACTION_TYPES:
            raise UnsupportedActionType(obj, "Unsupported import action type '%s'" % action_type)

        # Determine the request URL
        if action_type in OclFlexImporter.MAP_ACTION_TYPE_TO_URL_TYPE:
            url_type = OclFlexImporter.MAP_ACTION_TYPE_TO_URL_TYPE[action_type]
            if url_type == OclFlexImporter.URL_TYPE_RESOURCE_TYPE_ONLY:
                url = new_obj_url
            elif url_type == OclFlexImporter.URL_TYPE_RESOURCE_TYPE_AND_ID:
                url = obj_url

        # Determine which HTTP method to use
        obj_def = self.obj_def[obj_type]
        if (OclFlexImporter.OBJ_DEF_ATTR_HTTP_IMPORT_METHOD in obj_def and
                action_type in obj_def[OclFlexImporter.OBJ_DEF_ATTR_HTTP_IMPORT_METHOD]):
            method = obj_def[OclFlexImporter.OBJ_DEF_ATTR_HTTP_IMPORT_METHOD][action_type]
            if not method:
                err_msg = 'Action type "%s" not supported for resource type of "%s"' % (
                    action_type, obj_type)
                raise UnsupportedActionType(obj, err_msg)
        else:
            err_msg = 'No HTTP method specified for "%s" resource type and action type "%s"' % (
                obj_type, action_type)
            raise InvalidObjectDefinition(obj, err_msg)

        # Add query parameters (if provided)
        if query_params:
            url += '?' + urllib_parse.urlencode(query_params)

        # If delete, then clear the cache of object existence
        if action_type == OclFlexImporter.ACTION_TYPE_DELETE:
            self.clear_cache(obj_url=obj_url, do_clear_children=True)

        # Import the object
        if not self.test_mode:
            endpoint_url = self.api_url_root + url
            self.log(method, " ", endpoint_url + '  ', json.dumps(obj))
            if method == OclFlexImporter.HTTP_METHOD_POST:
                request_result = requests.post(
                    endpoint_url, headers=self.api_headers, data=json.dumps(obj))
            elif method == OclFlexImporter.HTTP_METHOD_PUT:
                request_result = requests.put(
                    endpoint_url, headers=self.api_headers, data=json.dumps(obj))
            elif method == OclFlexImporter.HTTP_METHOD_DELETE:
                # NOTE: Deletes do not include the object in the request body
                endpoint_url += '&inline=true' if '?' in endpoint_url else '?inline=true'  # org non-async delete
                request_result = requests.delete(endpoint_url, headers=self.api_headers)
            self.log("STATUS CODE:", request_result.status_code)
            self.log(request_result.headers)
            self.log(request_result.text)
            self.import_results.add(
                obj_url=obj_url, action_type=action_type, obj_type=obj_type,
                obj_repo_url=obj_repo_url, http_method=method, obj_owner_url=obj_owner_url,
                status_code=request_result.status_code, text=json.dumps(obj),
                message=request_result.text)
            request_result.raise_for_status()
        else:
            self.log("[TEST MODE] Action: %s, Method: %s, URL: %s%s -- %s" % (
                action_type, method, self.api_url_root, url, json.dumps(obj)))

    def clear_cache(self, obj_url, do_clear_children=False):
        """
        Clear the object existence cache of the specified object URL. Optionally
        also clear any occurrences of children of the specified object.
        """
        if not obj_url:
            return
        if not do_clear_children:
            if obj_url in self._cache_obj_exists:
                del self._cache_obj_exists[obj_url]
        else:
            for key in list(self._cache_obj_exists.keys()):
                if key[:len(obj_url)] == obj_url:
                    del self._cache_obj_exists[key]

    @staticmethod
    def find_nth(haystack, needle, n):
        """ Return index of nth occurrence of a substring within a string """
        start = haystack.find(needle)
        while start >= 0 and n > 1:
            start = haystack.find(needle, start+len(needle))
            n -= 1
        return start
