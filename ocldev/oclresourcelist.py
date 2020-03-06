""" Classes to manage a list of OCL resources """
import csv
import sys
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
        return _output_resources

    def __eq__(self, other):
        """ Return whether the two objects have the same resource lists """
        if len(self) != len(other):
            return False
        for i in range(len(self)):
            if self[i] != other[i]:
                return False
        return True

    def __ne__(self, other):
        """ Return whether the two objects have different same resource lists """
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
        """ Get the resource list as an OclJsonResourceList with OCL-formatted JSON """
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


class OclCsvResourceList(OclResourceList):
    """ Generic class to manage a list of OCL resources """

    def __init__(self, resources=None):
        """ Initialize the OclCsvResourceList instance """
        OclResourceList.__init__(self, resources=resources)

    def validate(self):
        """ Validate the resource list using the OclCsvValidator """
        oclvalidator.OclCsvValidator.validate(self)

    def get_unique_column_headers(self, default_columns=None):
        default_columns = ['resource_type', 'owner_id', 'id']
        return OclResourceList.get_unique_column_headers(self, default_columns=default_columns)


class OclJsonResourceList(OclResourceList):
    """ Generic class to manage a list of OCL resources """

    def __init__(self, resources=None):
        """ Initialize the OclJsonResourceList instance """
        OclResourceList.__init__(self, resources=resources)

    def validate(self):
        """ Validate the resource list using the OclCsvValidator """
        oclvalidator.OclJsonValidator.validate(self)

    def get_unique_column_headers(self, default_columns=None):
        default_columns = ['type', 'owner', 'id']
        return OclResourceList.get_unique_column_headers(self, default_columns=default_columns)
