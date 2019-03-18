import requests
import json
import zipfile
from pprint import pprint


class OclError(Exception):
    """ Base class for exceptions in this module """
    pass


class OclUnknownResourceError(OclError):
    """ Error thrown when an unknown resource type is encountered """
    def __init__(self, expr, msg):
        self.expr = expr
        self.msg = msg


class OclExportFactory(object):
    """ Factory class to create OclExport factory objects """

    @staticmethod
    def load_export(repo_version_url='', oclapitoken='',
                    compressed_pathname='ocl_temp_repo_export.zip'):
        # Prepare the headers
        oclapiheaders = {'Content-Type': 'application/json'}
        if oclapitoken:
            oclapiheaders['Authorization'] = 'Token ' + oclapitoken

        # Fetch the export and write to file
        repo_export_url = '%sexport/' % (repo_version_url)
        r = requests.get(repo_export_url, allow_redirects=True, headers=oclapiheaders)
        r.raise_for_status()
        open(compressed_pathname, 'wb').write(r.content)

        # Unzip the export
        zip_ref = zipfile.ZipFile(compressed_pathname, 'r')
        zip_ref.extractall()
        zip_ref.close()

        # Load the export and return
        json_filename = 'export.json'
        return OclExportFactory.load_from_export_json_file(json_filename)

    @staticmethod
    def load_latest_export(repo_url):
        repo_id = OclExportFactory.get_latest_version_id(repo_url)
        if repo_id:
            repo_version_url = '%s%s/' % (repo_url, repo_id)
            return OclExportFactory.load_export(repo_version_url)
        else:
            return None

    @staticmethod
    def get_latest_version_id(repo_url):
        # Get the latest version ID
        repo_latest_url = '%slatest/' % (repo_url)
        r = requests.get(repo_latest_url)
        repo_version = r.json()
        if repo_version and 'id' in repo_version:
            return repo_version['id']
        else:
            raise OclUnknownResourceError(repo_url, 'Repository "%s" does not exist' % (repo_url))

    @staticmethod
    def load_from_export_json_file(filename):
        with open(filename) as input_file:
            export_json = json.loads(input_file.read())
            return OclExport(export_json)


class OclExport(object):
    def __init__(self, export_json=None, ocl_export=None):
        self.set_export(export_json=export_json, ocl_export=ocl_export)

    def set_export(self, export_json=None, ocl_export=None):
        if export_json and ocl_export:
            raise Exception('uhoh')
        elif export_json:
            self._export = export_json
            self._concepts = {}
            self._mappings = []
        elif ocl_export:
            if not isinstance(ocl_export, OclExport):
                raise Exception('oh no!')
            self._export = ocl_export._export
            self._concepts = ocl_export._concepts
            self._mappings = ocl_export._mappings
        return None

        for concept in self._export['concepts']:
            self._concepts[concept['id']] = concept
        self._mappings = self._export['mappings']

    def get_concept_by_id(self, concept_id):
        if concept_id in self._concepts:
            return self._concepts[concept_id]
        return None

    def get_concept_by_uri(self, concept_uri):
        for concept in self._concepts:
            if concept['url'] == concept_url:
                return concept
        return None

    def get_concepts(self, concept_class='', datatype='', concept_id='', concept_uri=''):
        concepts = []
        for concept in self._export['concepts']:
            if (concept_id == concept['id'] or not concept_id) and \
                (concept_class == concept['concept_class'] or not concept_class) and \
                (datatype == concept['datatype'] or not datatype) and \
                (concept_uri == concept['url'] or not concept_uri):
                concepts.append(concept)
        return concepts

    def get_mappings(self, from_concept_uri='', to_concept_uri='', map_type=''):
        mappings = []
        for mapping in self._export['mappings']:
            if (mapping['from_concept_url'] == from_concept_uri or not from_concept_uri) and \
                (mapping['to_concept_url'] == to_concept_uri or not to_concept_uri) and \
                (mapping['map_type'] == map_type or not map_type):
                mappings.append(mapping)
        return mappings
