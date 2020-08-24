"""
Objects to work with OCL's export API

Example Code:
import pprint
import ocldev.oclexport

# Load export from OCL server
repo_url = 'https://api.staging.openconceptlab.org/orgs/CIEL/sources/CIEL/'
my_ocl_api_token = ''
export = oclexport.OclExportFactory.load_latest_export(
    repo_url=repo_url, oclapitoken=my_ocl_api_token)

# Load export from JSON file
export_filename = 'my-export.json'
export = oclexport.OclExportFactory.load_from_export_json_file(export_filename)

# Get concepts from export that include mappings
concept_a = export.get_concept_by_index(
    939, include_mappings=True, include_inverse_mappings=True)
concept_b = export.get_concept_by_id(
    '163817', include_mappings=True, include_inverse_mappings=True)
concept_c = export.get_concept_by_uri(
    '/orgs/CIEL/sources/CIEL/concepts/163817/', include_mappings=True,
    include_inverse_mappings=True)
concept_list = export.get_concepts(
    core_attrs={'retired': True, 'concept_class': 'Symptom'},
    include_mappings=True, include_inverse_mappings=True)

pprint.pprint(concept_a)
pprint.pprint(concept_b)
pprint.pprint(concept_c)
pprint.pprint(concept_list)
"""
import json
import zipfile
from io import StringIO
import requests
from . import oclresourcelist


class OclError(Exception):
    """ Base class for exceptions in this module """
    pass


class OclUnknownResourceError(OclError):
    """ Error thrown when an unknown resource type is encountered """
    def __init__(self, expr, msg):
        OclError.__init__(self)
        self.expr = expr
        self.msg = msg


class OclExportNotAvailableError(OclError):
    """ Error thrown when requesting an OCL export that is not available """
    def __init__(self, expr, msg):
        OclError.__init__(self)
        self.expr = expr
        self.msg = msg


class OclExportFactory(object):
    """ Factory class to create OclExport factory objects """

    @staticmethod
    def load_export(repo_version_url='', oclapitoken=''):
        """
        Retrieve a cached repository export from OCL, decompress, parse the JSON, and
        return as a python dictionary. NOTE: The export is decompressed and parsed in
        memory. It may be necessary in the future to handle very large exports using
        the filesystem rather than processing in memory.
        """

        # Prepare the request headers
        oclapiheaders = {'Content-Type': 'application/json'}
        if oclapitoken:
            oclapiheaders['Authorization'] = 'Token ' + oclapitoken

        # Fetch the zipped export from OCL
        repo_export_url = '%sexport/' % repo_version_url
        r = requests.get(repo_export_url, allow_redirects=True, headers=oclapiheaders)
        r.raise_for_status()
        if r.status_code == 204:
            raise OclExportNotAvailableError(
                repo_export_url, 'Export at "%s" not available' % repo_export_url)

        # Decompress "export.json" from the zipfile in memory and return as a python dictionary
        repo_export = None
        export_string_handle = StringIO(r.content)
        zipref = zipfile.ZipFile(export_string_handle, "r")
        if 'export.json' in zipref.namelist():
            repo_export = json.loads(zipref.read('export.json'))
            zipref.close()
        else:
            zipref.close()
            errmsg = 'ERROR: Invalid repository export for "%s": ' % repo_version_url
            errmsg += 'export.json not found in the export response.\n%s' % r.content
            raise Exception(errmsg)
        return OclExport(repo_export)

    @staticmethod
    def load_latest_export(repo_url, oclapitoken=''):
        """
        Load latest export of the specified repository. Repo URL should be of the format:
        https://api.openconceptlab.org/orgs/MyOrg/sources/MySource/
        """
        repo_id = OclExportFactory.get_latest_version_id(repo_url, oclapitoken=oclapitoken)
        if repo_id:
            repo_version_url = '%s%s/' % (repo_url, repo_id)
            return OclExportFactory.load_export(repo_version_url, oclapitoken=oclapitoken)
        return None

    @staticmethod
    def get_latest_version_id(repo_url, oclapitoken=''):
        """
        Get the ID of the most recent released version of the specified repository
        """

        # Prepare the request headers
        oclapiheaders = {'Content-Type': 'application/json'}
        if oclapitoken:
            oclapiheaders['Authorization'] = 'Token ' + oclapitoken

        # Get the latest version ID
        repo_latest_url = '%slatest/' % repo_url
        r = requests.get(repo_latest_url, headers=oclapiheaders)
        repo_version = r.json()
        if repo_version and 'id' in repo_version:
            return repo_version['id']
        else:
            raise OclUnknownResourceError(repo_url, 'Repository "%s" does not exist' % repo_url)

    @staticmethod
    def load_from_export_json_file(filename):
        """ Load previously saved export from a file """
        with open(filename) as input_file:
            export_json = json.loads(input_file.read())
            return OclExport(export_json)


class OclExport(object):
    """ Object representing an OCL export of an source or collection version """

    def __init__(self, export_json=None, ocl_export=None):
        """ Initialize this OclExport object """
        self._export_json = None
        self._concepts = []
        self._mappings = []
        self.set_export(export_json=export_json, ocl_export=ocl_export)

    def get_full_export(self):
        """ Return full contents of export as a python dictionary """
        return self._export_json

    def to_resource_list(self):
        """ Return all concepts and mappings as an OclJsonResourceList """
        if not self._export_json:
            return None
        resource_list = oclresourcelist.OclJsonResourceList()
        resource_list.append(self._concepts)
        resource_list.append(self._mappings)
        return resource_list

    def set_export(self, export_json=None, ocl_export=None):
        """
        Set the contents of this export object to the passed OCL export JSON or another
        OclExport object.
        """
        if export_json and ocl_export:
            raise Exception('uhoh')
        elif export_json:
            self._export_json = export_json
        elif ocl_export:
            if not isinstance(ocl_export, OclExport):
                raise Exception('oh no!')
            self._export_json = ocl_export.get_full_export()
        self._concepts = self._export_json['concepts']
        self._mappings = self._export_json['mappings']

    def _add_mappings_to_concept(self, concept, include_mappings=True,
                                 include_inverse_mappings=True):
        """ Adds mappings from this export to a copy of the provided concept """
        return_concept = concept.copy()
        return_concept['mappings'] = []
        concept_uri = concept['url']
        for mapping in self._mappings:
            if include_mappings and mapping['from_concept_url'] == concept_uri:
                return_concept['mappings'].append(mapping)
            if include_inverse_mappings and mapping['to_concept_url'] == concept_uri:
                return_concept['mappings'].append(mapping)
        return return_concept

    def get_concept_by_index(self, index, include_mappings=False, include_inverse_mappings=False):
        """ Return concept corresponding to a specified index """
        if not include_mappings and not include_inverse_mappings:
            return self._concepts[index]
        return self._add_mappings_to_concept(
            self._concepts[index], include_mappings=include_mappings,
            include_inverse_mappings=include_inverse_mappings)

    def get_concept_by_id(self, concept_id, include_mappings=False,
                          include_inverse_mappings=False):
        """ Returns the first concept that matches the specified ID, otherwise returns None """
        for concept in self._concepts:
            if concept['id'] == concept_id:
                if not include_mappings and not include_inverse_mappings:
                    return concept
                return self._add_mappings_to_concept(
                    concept, include_mappings=include_mappings,
                    include_inverse_mappings=include_inverse_mappings)
        return None

    def get_concept_by_uri(self, concept_uri, include_mappings=False,
                           include_inverse_mappings=False):
        """ Returns the first concept that matches the specified URL, otherwise returns None """
        for concept in self._concepts:
            if concept['url'] == concept_uri:
                if not include_mappings and not include_inverse_mappings:
                    return concept
                return self._add_mappings_to_concept(
                    concept, include_mappings=include_mappings,
                    include_inverse_mappings=include_inverse_mappings)
        return None

    def get_concepts(self, concept_id='', concept_uri='', concept_class='', datatype='',
                     core_attrs=None, custom_attrs=None,
                     include_mappings=False, include_inverse_mappings=False):
        """
        Get list of concepts matching all of the specified attributes. While concept ID, URI,
        class, and may be explicitly passed as arguments, any core or custom attribute may be
        passed using the core_attrs and custom_attrs dictionaries.
        """

        # Move explicit filters into the core attributes dictionary
        if not core_attrs:
            core_attrs = {}
        if concept_id:
            core_attrs['concept_id'] = concept_id
        if concept_uri:
            core_attrs['url'] = concept_uri
        if concept_class:
            core_attrs['concept_class'] = concept_class
        if datatype:
            core_attrs['datatype'] = datatype

        # Return matching concepts
        concepts = []
        for concept in self._concepts:
            is_match = True
            if core_attrs:
                for core_attr_key in core_attrs:
                    if (core_attr_key not in concept or
                            concept[core_attr_key] != core_attrs[core_attr_key]):
                        is_match = False
                        break
            if custom_attrs and is_match:
                for custom_attr_key in custom_attrs:
                    if ('extras' not in concept or not concept['extras'] or
                            custom_attr_key not in concept['extras'] or
                            concept['extras'][custom_attr_key] != custom_attrs[custom_attr_key]):
                        is_match = False
                        break
            if is_match:
                if not include_mappings and not include_inverse_mappings:
                    concepts.append(concept)
                else:
                    concepts.append(self._add_mappings_to_concept(
                        concept, include_mappings=include_mappings,
                        include_inverse_mappings=include_inverse_mappings))

        return concepts

    def get_mappings(self, from_concept_uri='', to_concept_uri='', map_type=''):
        """
        Get list of mappings in the export matching the specified filter criteria.
        If no filter criteria are provided, all mappings are returned.
        """
        mappings = []
        for mapping in self._export_json['mappings']:
            if ((not from_concept_uri or mapping['from_concept_url'] == from_concept_uri) and
                    (not to_concept_uri or mapping['to_concept_url'] == to_concept_uri) and
                    (not map_type or mapping['map_type'] == map_type)):
                mappings.append(mapping)
        return mappings

    def get_stats(self):
        """ Get dictionary of the counts of the types of concepts and mappings in the export """

        # Setup the stats dictionary and define for which fields counts are generated
        concept_stat_fields = ['source', 'concept_class', 'datatype']
        mapping_stat_fields = ['source', 'map_type', 'from_source_url', 'to_source_url']
        stats = {
            'Concepts': {
                'Total': len(self._concepts)
            },
            'Mappings': {
                'Subtotal Internal': 0,
                'Subtotal External': 0,
                'Total': len(self._mappings)
            }
        }

        # Concepts
        for concept_stat_field in concept_stat_fields:
            stats['Concepts'][concept_stat_field] = {}
        for concept in self._concepts:
            for concept_stat_field in concept_stat_fields:
                if concept_stat_field not in concept:
                    continue
                if not concept[concept_stat_field] in stats['Concepts'][concept_stat_field]:
                    stats['Concepts'][concept_stat_field][concept[concept_stat_field]] = 0
                stats['Concepts'][concept_stat_field][concept[concept_stat_field]] += 1

        # Mappings
        for mapping_stat_field in mapping_stat_fields:
            stats['Mappings'][mapping_stat_field] = {}
        for mapping in self._mappings:
            # Process the stat fields first
            for mapping_stat_field in mapping_stat_fields:
                if mapping_stat_field not in mapping:
                    continue
                if not mapping[mapping_stat_field] in stats['Mappings'][mapping_stat_field]:
                    stats['Mappings'][mapping_stat_field][mapping[mapping_stat_field]] = 0
                stats['Mappings'][mapping_stat_field][mapping[mapping_stat_field]] += 1

            # Check for internal/external status of this mapping
            is_from_concept_in_export = False
            is_to_concept_in_export = False
            if ('from_concept_url' in mapping and
                    self.get_concept_by_uri(mapping['from_concept_url'])):
                is_from_concept_in_export = True
            if 'to_concept_url' in mapping and self.get_concept_by_uri(mapping['to_concept_url']):
                is_to_concept_in_export = True
            if is_from_concept_in_export and is_to_concept_in_export:
                stats['Mappings']['Subtotal Internal'] += 1
            else:
                stats['Mappings']['Subtotal External'] += 1

        return stats
