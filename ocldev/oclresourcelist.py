""" Classes to manage a list of OCL resources """
import csv
import sys
import json
import oclconstants
import oclvalidator
import oclcsvtojsonconverter


class OclResourceList(object):
    """ Generic class to manage a list of OCL resources """

    def __init__(self, resources=None):
        """ Initialize the OclResourceList instance """
        self._resources = []
        self._current_iter = 0
        if resources:
            self.load_resources(resources)

    def load_resources(self, resources):
        """ Load resource list """
        if not isinstance(resources, list):
            raise TypeError('Invalid type. List required.')
        self._resources = resources

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
            _output_resources.append(resource.copy())
        return OclResourceList(_output_resources)

    def __eq__(self, other):
        """ Return whether the two objects have the same resource lists """
        if len(self) != len(other):
            return False
        for i in range(len(self)):
            if self[i] != other[i]:
                return False
        return True

    def __ne__(self, other):
        """ Return whether the two objects have different resource lists """
        return not self.__eq__(other)

    def next(self):
        """ Get the next item in the list """
        if self._current_iter >= len(self._resources):
            raise StopIteration
        else:
            self._current_iter += 1
            return self._resources[self._current_iter - 1]

    def append(self, resources):
        """ Add one resource or a list of resources to the list """
        if not isinstance(resources, list):
            resources = [resources]
        for resource in resources:
            if not isinstance(resource, dict):
                raise TypeError("Cannot append resource of type '%s'" % type(resource))
            self._resources.append(resource)

    def __getitem__(self, index):
        """ Get an item from the list """
        return self._resources[index]

    def to_json(self):
        """
        Return JSON representation of the resource list, which is simply a copy of
        the resources in this list.
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

    def _get_resources(self, core_attrs=None, custom_attrs=None, do_return_first=False,
                       do_return_index=False):
        """
        Get list of resources matching all of the specified attributes.  Any core or custom
        attribute may be passed using the core_attrs and custom_attrs dictionaries.
        """

        # Move explicit filters into the core attributes dictionary
        # if not core_attrs:
        #     core_attrs = {}
        # if resource_type:
        #     core_attrs['type'] = resource_type
        # if resource_id:
        #     core_attrs['id'] = resource_id
        # if resource_url:
        #     core_attrs['url'] = resource_url

        # Return matching resources
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
        return self._resources.pop(resource_index)


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
