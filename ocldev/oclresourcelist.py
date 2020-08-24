""" Classes to manage a list of OCL resources """
import csv
import sys
import json
from . import oclconstants
from . import oclvalidator
from . import oclcsvtojsonconverter


class OclResourceList(object):
    """ Generic class to manage a list of OCL resources """

    def __init__(self, resources=None):
        """ Initialize the OclResourceList instance """
        self._urls = []
        self._resources = []
        self._current_iter = 0
        if resources:
            self.append(resources)

    def __iter__(self):
        """ Iterator for the OclResourceList class """
        self._current_iter = 0
        return self

    def __len__(self):
        """ Number of resources in this list """
        return len(self._resources)

    def __add__(self, new_resources):
        """ Add two resource lists together """
        _output_resources = list(self._resources)
        for resource in new_resources:
            _output_resources.append(resource)
        return OclResourceList(_output_resources)

    def __iadd__(self, new_resources):
        self.append(new_resources)
        return self

    def __eq__(self, other):
        """ Return whether the two objects are equal, i.e. have the same resource lists """
        if len(self) != len(other):
            return False
        for i in range(len(self)):
            if self[i] != other[i]:
                return False
        return True

    def __ne__(self, other):
        """ Return whether the two objects have different resource lists """
        return not self.__eq__(other)

    def chunk(self, chunk_size):
        """
        Return the OclResourceList as a list of OclResourceList objects with maximum
        size of chunk_size.
        """
        chunked_lists = [
            self._resources[i:i + chunk_size] for i in range(0, len(self._resources), chunk_size)]
        chunked_resource_lists = []
        for chunked_list in chunked_lists:
            chunked_resource_lists.append(OclResourceList(chunked_list))
        return chunked_resource_lists

    def __next__(self):
        """ Get the next item in the list """
        if self._current_iter >= len(self._resources):
            raise StopIteration
        else:
            self._current_iter += 1
            return self._resources[self._current_iter - 1]

    def refresh_index(self):
        """
        Refresh the URL index. This is required if resource ID and URL-related fields are edited
        outside of this object
        """
        self._urls = []
        for resource in self._resources:
            self._urls.append(OclResourceList.get_resource_url(resource))

    def append(self, resources):
        """
        Add one resource or a list of resources to this object
        :param resources: <dict>, <list>, <OclResourceList>
        """
        if isinstance(resources, dict):
            resources = [resources]
        if isinstance(resources, list) or isinstance(resources, OclResourceList):
            for resource in resources:
                if not isinstance(resource, dict):
                    raise TypeError("Cannot append resource of type '%s'" % type(resource))
                self._urls.append(OclResourceList.get_resource_url(resource))
                self._resources.append(resource)
        else:
            raise TypeError("Cannot append resource of type '%s'" % type(resources))

    def __getitem__(self, index):
        """ Get an item from the list """
        return self._resources[index]

    def to_json(self):
        """
        DEPRECATED: Return JSON representation of the resource list, which is simply a copy of
        the resources in this list.
        """
        return list(self._resources)

    def to_list(self):
        """
        Return a (shallow) copy of all resources as a simple python list.
        """
        return list(self._resources)

    def convert_to_ocl_formatted_json(self):
        """ Convert a CSV-formatted resource list as an OclJsonResourceList """
        csv_converter = oclcsvtojsonconverter.OclStandardCsvToJsonConverter(input_list=self)
        return OclJsonResourceList(csv_converter.process())

    def display_as_csv(self):
        """ Display the resource list as CSV """
        output_stream = sys.stdout
        columns = self.get_unique_column_headers()
        writer = csv.DictWriter(output_stream, fieldnames=columns)
        writer.writeheader()
        for resource in self._resources:
            writer.writerow(resource)

    def get_unique_column_headers(self, default_columns=None):
        """ Get a list of unique column headers in the resource list """
        columns = []
        if default_columns:
            columns = default_columns
        for resource in self._resources:
            for key in resource:
                if key not in columns:
                    columns.append(key)
        return columns

    def summarize(self, core_attr_key='', custom_attr_key=''):
        """
        Return a dictionary summarizing the number of occurrences of each value for the specified
        custom attribute key. Only one attribute key may be provided.
        """
        summary = {}
        for resource in self._resources:
            if core_attr_key:
                if core_attr_key in resource:
                    attr_value = resource[core_attr_key]
                else:
                    attr_value = None
            elif custom_attr_key:
                if 'extras' in resource and custom_attr_key in resource['extras']:
                    attr_value = resource['extras'][custom_attr_key]
                else:
                    attr_value = None
            else:
                attr_value = None
            if attr_value not in summary:
                summary[attr_value] = 0
            summary[attr_value] += 1
        return summary

    def _get_resources(self, core_attrs=None, custom_attrs=None, do_return_first=False,
                       do_return_index=False):
        """
        Get list of resources matching all of the specified attributes.  Any core or custom
        attribute may be passed using the core_attrs and custom_attrs dictionaries.
        """
        resources = []
        current_index = 0
        for resource in self._resources:
            is_match = True
            if core_attrs:
                for core_attr_key in core_attrs:
                    if (core_attr_key not in resource or
                            resource[core_attr_key] != core_attrs[core_attr_key]):
                        is_match = False
                        break
            if custom_attrs and is_match:
                for custom_attr_key in custom_attrs:
                    if ('extras' not in resource or not resource['extras'] or
                            custom_attr_key not in resource['extras'] or
                            resource['extras'][custom_attr_key] != custom_attrs[custom_attr_key]):
                        is_match = False
                        break
            if is_match:
                if do_return_first:
                    return resource if not do_return_index else current_index
                resources.append(resource if not do_return_index else current_index)
            current_index += 1
        return resources if not do_return_index else resources

    def get_resources(self, core_attrs=None, custom_attrs=None):
        """
        Get list of resources matching all of the specified attributes.  Any core or custom
        attribute may be passed using the core_attrs and custom_attrs dictionaries.
        """
        result = self._get_resources(core_attrs=core_attrs, custom_attrs=custom_attrs)
        if result:
            return OclResourceList(result)
        return None

    def get_resource(self, core_attrs=None, custom_attrs=None):
        """ Returns first matching resource """
        result = self._get_resources(
            core_attrs=core_attrs, custom_attrs=custom_attrs, do_return_first=True)
        if result:
            return result
        return None

    def get_index(self, core_attrs=None, custom_attrs=None):
        """ Returns 0-based index of first matching resource. Returns -1 if no match. """
        result = self._get_resources(
            core_attrs=core_attrs, custom_attrs=custom_attrs,
            do_return_index=True, do_return_first=True)
        if isinstance(result, int):
            return result
        return -1

    def pop(self, resource_index):
        """ Remove and return a resource at the specified index """
        self._urls.pop(resource_index)
        return self._resources.pop(resource_index)

    @staticmethod
    def get_resource_url(resource, include_trailing_slash=True):
        """
        Return URL of a resource. If URL is specified explicitly as a URL field, that is returned.
        Otherwise, it attempts to build a URL using inline attributes. For JSON resources, this
        includes: type, owner_id, owner_type, source_id, and id. For CSV resources, this includes:
        resource_type, owner, owner_type, source, and id. Returns None if unable to generate URL.
        Currently supports Concepts, Mappings, Sources, Collections, Owners, and Users.
        """
        if 'url' in resource and resource['url']:
            if include_trailing_slash and resource['url'][len(resource['url']) - 1] != '/':
                return '%s/' % resource['url']
            elif not include_trailing_slash and resource['url'][len(resource['url']) - 1] == '/':
                return resource['url'][:-1]
            return resource['url']
        resource_type = resource.get('type') or resource.get('resource_type')
        url = None
        if (resource_type == oclconstants.OclConstants.RESOURCE_TYPE_CONCEPT or
                resource_type == oclconstants.OclConstants.RESOURCE_TYPE_MAPPING):
                url = oclconstants.OclConstants.get_resource_url(
                    owner_id=resource.get('owner') or resource.get('owner_id'),
                    owner_type=resource.get('owner_type') or oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION,
                    repository_id=resource.get('source') or resource.get('source_id'),
                    repository_type=oclconstants.OclConstants.RESOURCE_TYPE_SOURCE,
                    resource_type=resource_type,
                    resource_id=resource.get('id'),
                    include_trailing_slash=include_trailing_slash)
        elif (resource_type == oclconstants.OclConstants.RESOURCE_TYPE_SOURCE or
                resource_type == oclconstants.OclConstants.RESOURCE_TYPE_COLLECTION):
            url = oclconstants.OclConstants.get_repository_url(
                owner_id=resource.get('owner') or resource.get('owner_id'),
                owner_type=resource.get('owner_type') or oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION,
                repository_id=resource.get('id'),
                repository_type=resource_type,
                include_trailing_slash=include_trailing_slash)
        elif (resource_type == oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION or
                resource_type == oclconstants.OclConstants.RESOURCE_TYPE_USER):
            url = oclconstants.OclConstants.get_owner_url(
                owner_id=resource.get('id'),
                owner_type=resource_type,
                include_trailing_slash=include_trailing_slash)
        if url:
            return url
        return None

    def get_resource_by_url(self, url):
        """ Return the first resource that matches the specified URL. """
        if isinstance(url, str) and url:
            url_needle = url.strip()
        else:
            return None
        if url_needle[len(url_needle) - 1] != '/':
            url_needle += '/'
        if url_needle in self._urls:
            return self._resources[self._urls.index(url_needle)]
        return None

    def get_concept_name_by_url(self, resource_url, name_type):
        """
        Get concept name by name_type or return None. Concept is identified by the provided
        resource URL. If name_type is a list, name_types are processed in the order specified.
        """
        return OclResourceList.get_concept_name_by_type(
            self.get_resource_by_url(resource_url), name_type)

    @staticmethod
    def get_concept_name_by_type(concept, name_type):
        """
        Get concept name by name_type or return None. If name_type is a list, name_types are
        processed in the order specified.
        """
        if not concept or 'names' not in concept:
            return None
        if isinstance(name_type, str):
            name_type = [name_type]
        if not isinstance(name_type, list):
            raise TypeError("Invalid name_type argument '%s'. Expected string or list." % type(name_type))
        for current_name_type in name_type:
            for concept_name in concept['names']:
                if 'name_type' in concept_name and concept_name['name_type'] == current_name_type:
                    return concept_name['name']
        return None


class OclCsvResourceList(OclResourceList):
    """ Generic class to manage a list of OCL resources """

    def __init__(self, resources=None):
        """ Initialize the OclCsvResourceList instance """
        OclResourceList.__init__(self, resources=resources)

    @staticmethod
    def load_from_file(filename):
        """ Load resource list from CSV file """
        resource_list = []
        with open(filename) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                resource_list.append(row)
        return OclCsvResourceList(resources=resource_list)

    def validate(self):
        """ Validate the resource list using the OclCsvValidator """
        oclvalidator.OclCsvValidator.validate(self)

    def get_unique_column_headers(self, default_columns=None):
        default_columns = ['resource_type', 'owner_id', 'id']
        return OclResourceList.get_unique_column_headers(self, default_columns=default_columns)

    def __add__(self, new_resources):
        """ Add two resource lists together """
        _output_resources = list(self._resources)
        for resource in new_resources:
            _output_resources.append(resource.copy())
        return OclCsvResourceList(_output_resources)


class OclJsonResourceList(OclResourceList):
    """ Generic class to manage a list of OCL resources """

    def __init__(self, resources=None):
        """ Initialize the OclJsonResourceList instance """
        OclResourceList.__init__(self, resources=resources)

    @staticmethod
    def load_from_file(filename):
        """ Load resource list from JSON file """
        resource_list = []
        with open(filename) as jsonfile:
            for line in jsonfile:
                resource_list.append(json.loads(line))
        return OclJsonResourceList(resources=resource_list)

    def validate(self):
        """ Validate the resource list using the OclCsvValidator """
        oclvalidator.OclJsonValidator.validate(self)

    def get_unique_column_headers(self, default_columns=None):
        default_columns = ['type', 'owner', 'id']
        return OclResourceList.get_unique_column_headers(self, default_columns=default_columns)

    def __add__(self, new_resources):
        """ Add two resource lists together """
        _output_resources = list(self._resources)
        for resource in new_resources:
            _output_resources.append(resource.copy())
        return OclJsonResourceList(_output_resources)
