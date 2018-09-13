'''
Convert CSV to OCL-formatted JSON file.

Script to convert a CSV file to an OCL-formatted JSON file based on a provided
set of CSV Resource Definitions. The resulting JSON is intended for the
OclFlexImporter and does not work with the batch concept/mapping importer.

Definitions take the form:
    csv_resource_definitions = [
        'definition_name':'Concept',
        'resource_type':'Concept',
        'id_column':'id',
        'skip_if_empty_column':'id',
        OclCsvToJsonConverter.DEF_CORE_FIELDS:[
            {'resource_type':...}
        ],
        OclCsvToJsonConverter.DEF_SUB_RESOURCES:{
            'names':[],
            'descriptions':[],
        },
        OclCsvToJsonConverter.DEF_KEY_VALUE_PAIRS:{
            'extras':[],
        },
    ]
'''
import csv
import json
import re


class OclCsvToJsonConverter:
    """ Class to convert CSV file to OCL-formatted JSON flex file """

    DEF_CORE_FIELDS = 'core_fields'
    DEF_SUB_RESOURCES = 'subresources'
    DEF_KEY_VALUE_PAIRS = 'key_value_pairs'

    INTERNAL_MAPPING_ID = 'Internal'
    EXTERNAL_MAPPING_ID = 'External'

    # Note that underscores are allowed for a concept ID and the exception is made in the code
    INVALID_CHARS = ' `~!@#$%^&*()_+-=[]{}\\|;:"\',/<>?'
    REPLACE_CHAR = '-'

    def __init__(self, output_filename='', csv_filename='', input_list=None,
                 csv_resource_definitions=None, verbose=False, include_type_attribute=True):
        """
        Initialize this object
        Parameters:
          output_filename <string> - Filename to save results to; results
                returned as list if not provided
          csv_filename <string> - Filename to load CSV data from; use "input_list"
                if CSV already loaded into list
          input_list <list> - List of dictionaries objects representing each row of the CSV file
          csv_resource_definitions <dict> - Properly formatted dictionary defining
                how to convert CSV to OCL-JSON
          verbose <int> - 0=off, 1=some debug info, 2=all debug info
          include_type_attribute <bool> - Whether to include resource type attributes
                (e.g. "type":"Concept") in the output
        """
        self.output_filename = output_filename
        self.csv_filename = csv_filename
        self.input_list = input_list
        if csv_filename:
            self.load_csv(csv_filename)
        self.verbose = verbose
        self.include_type_attribute = include_type_attribute
        self.set_resource_definitions(csv_resource_definitions=csv_resource_definitions)
        self.output_list = []

    def preprocess_csv_row(self, row, attr=None):
        """
        Method intended to be overwritten in classes that extend this
        """
        return row

    def set_resource_definitions(self, csv_resource_definitions=None):
        self.csv_resource_definitions = csv_resource_definitions

    def load_csv(self, csv_filename):
        input_list = []
        with open(csv_filename) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                input_list.append(row)
        self.input_list = input_list

    def process_by_row(self, num_rows=0, attr=None):
        """
        Processes the CSV file applying all definitions to each row before moving to the next row
        """
        if self.csv_filename:
            self.load_csv(self.csv_filename)
        row_i = 0
        self.output_list = []
        for csv_row in self.input_list:
            if num_rows and row_i >= num_rows:
                break
            row_i += 1
            csv_row = self.preprocess_csv_row(csv_row.copy(), attr)
            for csv_resource_def in self.csv_resource_definitions:
                if 'is_active' not in csv_resource_def or csv_resource_def['is_active']:
                    self.process_csv_row_with_definition(csv_row, csv_resource_def, attr=attr)
        return self.output_list

    def process_by_definition(self, num_rows=0, attr=None):
        """ Processes the CSV file by looping through it entirely once for each definition """
        if self.csv_filename:
            self.load_csv(self.csv_filename)
        self.output_list = []
        for csv_resource_def in self.csv_resource_definitions:
            if 'is_active' not in csv_resource_def or csv_resource_def['is_active']:
                row_i = 0
                for csv_row in self.input_list:
                    if num_rows and row_i >= num_rows:
                        break
                    row_i += 1
                    csv_row = self.preprocess_csv_row(csv_row.copy(), attr)
                    self.process_csv_row_with_definition(csv_row, csv_resource_def, attr=attr)
        return self.output_list

    def process_csv_row_with_definition(self, csv_row, csv_resource_def, attr=None):
        """ Process individual CSV row with the provided CSV resource definition """

        # Check if this row should be skipped
        is_skip_row = False
        if 'skip_if_empty_column' in csv_resource_def and csv_resource_def['skip_if_empty_column']:
            skip_columns = csv_resource_def['skip_if_empty_column']
            if not isinstance(skip_columns, list):
                skip_columns = [skip_columns]
            for skip_column in skip_columns:
                if skip_column not in csv_row:
                    raise Exception("skip_if_empty_column '" + skip_column +
                                    "'is not defined in the CSV file")
                if csv_row[skip_column] == '':
                    is_skip_row = True
                    break
        elif 'skip_handler' in csv_resource_def:
            handler = getattr(self, csv_resource_def['skip_handler'])
            if not handler:
                raise Exception(
                    "skip_handler '" + csv_resource_def['skip_handler'] + "' is not defined")
            is_skip_row = handler(csv_resource_def, csv_row)
        if is_skip_row:
            if self.verbose:
                print 'SKIPPING: %s' % (csv_resource_def['definition_name'])
            return

        # Set the resource type
        ocl_resource = {}
        if self.include_type_attribute:
            ocl_resource['type'] = csv_resource_def['resource_type']

        # Resource ID column
        has_id_column = False
        id_column = None
        if 'id_column' in csv_resource_def and csv_resource_def['id_column']:
            has_id_column = True
            id_column = csv_resource_def['id_column']
            if id_column not in csv_row or not csv_row[id_column]:
                raise Exception('ID column %s not set or empty in row %s' % (id_column, csv_row))
            if 'resource_type' in csv_resource_def and csv_resource_def['resource_type'] == 'Concept':
                ocl_resource['id'] = self.format_identifier(csv_row[id_column], allow_underscore=True)
            else:
                ocl_resource['id'] = self.format_identifier(csv_row[id_column])

        # Core fields
        if self.DEF_CORE_FIELDS in csv_resource_def and csv_resource_def[self.DEF_CORE_FIELDS]:
            for field_def in csv_resource_def[self.DEF_CORE_FIELDS]:
                if 'resource_field' not in field_def:
                    raise Exception(
                        'Expected key "resource_field" in standard column definition, but none found: %s' % field_def)
                if 'column' in field_def:
                    ocl_resource[field_def['resource_field']] = csv_row[field_def['column']]
                elif 'value' in field_def:
                    ocl_resource[field_def['resource_field']] = field_def['value']
                elif 'csv_to_json_processor' in field_def and 'data_column' in field_def:
                    method_to_call = getattr(self, field_def['csv_to_json_processor'])
                    ocl_resource[field_def['resource_field']] = method_to_call(csv_row, field_def)
                else:
                    raise Exception(
                        'Expected "column", "value", or "csv_to_json_processor" key in standard column definition, but none found: %s' % field_def)

        # Dictionary columns
        if self.DEF_SUB_RESOURCES in csv_resource_def and csv_resource_def[self.DEF_SUB_RESOURCES]:
            for group_name in csv_resource_def[self.DEF_SUB_RESOURCES]:
                ocl_resource[group_name] = []
                for dict_def in csv_resource_def[self.DEF_SUB_RESOURCES][group_name]:
                    current_dict = {}
                    for field_def in dict_def:
                        if 'resource_field' not in field_def:
                            raise Exception(
                                'Expected key "resource_field" in subresource definition, but none found: %s' % field_def)
                        if 'column' in field_def:
                            current_dict[field_def['resource_field']] = csv_row[field_def['column']]
                        elif 'value' in field_def:
                            current_dict[field_def['resource_field']] = field_def['value']
                        else:
                            raise Exception(
                                'Expected "column" or "value" key in subresource definition, but none found: %s' % field_def)
                    if current_dict:
                        ocl_resource[group_name].append(current_dict)

        # Key value pairs
        if self.DEF_KEY_VALUE_PAIRS in csv_resource_def and csv_resource_def[self.DEF_KEY_VALUE_PAIRS]:
            for group_name in csv_resource_def[self.DEF_KEY_VALUE_PAIRS]:
                ocl_resource[group_name] = {}
                for kvp_def in csv_resource_def[self.DEF_KEY_VALUE_PAIRS][group_name]:
                    # Key
                    key = None
                    if 'key' in kvp_def and kvp_def['key']:
                        key = kvp_def['key']
                    elif 'key_column' in kvp_def and kvp_def['key_column']:
                        if kvp_def['key_column'] in csv_row and csv_row[kvp_def['key_column']]:
                            key = csv_row[kvp_def['key_column']]
                        else:
                            raise Exception('key_column "%s" must be non-empty in CSV within key_value_pair: %s' % (kvp_def['key_column'], kvp_def))
                    else:
                        raise Exception('Expected "key" or "key_column" key in key_value_pair definition, but neither found: %s' % kvp_def)

                    # Value
                    if 'value' in kvp_def:
                        value = kvp_def['value']
                    elif 'value_column' in kvp_def and kvp_def['value_column']:
                        if kvp_def['value_column'] in csv_row:
                            value = csv_row[kvp_def['value_column']]
                        else:
                            raise Exception('value_column "%s" does not exist in CSV for key_value_pair: %s' % (kvp_def['value_column'], kvp_def))
                    else:
                        raise Exception('Expected "value" or "value_column" key in key_value_pair definition, but neither found: %s' % kvp_def)

                    # Set the key-value pair
                    if not key:
                        pass
                    elif value == '' and 'omit_if_empty_value' in kvp_def and kvp_def['omit_if_empty_value']:
                        pass
                    else:
                        ocl_resource[group_name][key] = value

        # Output
        if self.output_filename:
            output_file = open(self.output_filename, 'a')
            output_file.write(json.dumps(ocl_resource))
            output_file.write('\n')
        else:
            self.output_list.append(ocl_resource)
            #print json.dumps(ocl_resource)

    def process_reference(self, csv_row, field_def):
        """
        Processes a reference in the CSV row
        """
        result = None
        if ('data_column' in field_def and field_def['data_column'] and
                field_def['data_column'] in csv_row):
            result = {'expressions': [csv_row[field_def['data_column']]]}
        return result

    def format_identifier(self, unformatted_id, allow_underscore=False):
        """
        Format a string according to the OCL ID rules: Everything in INVALID_CHARS goes,
        except that underscores are allowed for the concept_id
        """
        formatted_id = list(unformatted_id)
        if allow_underscore:
            chars_to_remove = self.INVALID_CHARS.replace('_', '')
        else:
            chars_to_remove = self.INVALID_CHARS
        for index in range(len(unformatted_id)):
            if unformatted_id[index] in chars_to_remove:
                formatted_id[index] = self.REPLACE_CHAR
        return ''.join(formatted_id)
