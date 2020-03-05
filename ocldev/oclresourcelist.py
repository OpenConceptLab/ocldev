""" Classes to manage a list of OCL resources """
import json
import csv
import sys
import oclvalidator


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

    def next(self):
        """ Get the next item in the list """
        if self._current_iter >= len(self._resources):
            raise StopIteration
        else:
            self._current_iter += 1
            return self._resources.get(self._current_iter - 1)

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

    def display_as_json(self):
        """ Display the resource list as JSON """
        for resource in self._resources:
            print json.dumps(resource)

    def display_as_csv(self):
        """ Display the resource list as CSV """
        output_stream = sys.stdout
        columns = self.get_unique_column_headers()
        writer = csv.DictWriter(output_stream, fieldnames=columns)
        writer.writeheader()
        for resource in self._resources:
            writer.writerow(resource)

    def get_unique_column_headers(self):
        """ Get a list of unique column headers in the resource list """
        columns = ['resource_type', 'owner', 'id']
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


class OclJsonResourceList(OclResourceList):
    """ Generic class to manage a list of OCL resources """

    def __init__(self, resources=None):
        """ Initialize the OclJsonResourceList instance """
        OclResourceList.__init__(self, resources=resources)

    def validate(self):
        """ Validate the resource list using the OclCsvValidator """
        oclvalidator.OclJsonValidator.validate(self)
