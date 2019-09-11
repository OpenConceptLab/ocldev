"""
Convert CSV to OCL-formatted JSON file.

Script to convert a CSV file to an OCL-formatted JSON file based on a provided
set of CSV Resource Definitions. The resulting JSON is intended for the
OclFlexImporter and does not work with the batch concept/mapping importer.

Definitions take the form:
    csv_resource_definitions = [
        'definition_name': 'My Concept Definition',
        'resource_type': oclconstants.OclConstants.RESOURCE_TYPE_CONCEPT,
        'id_column':'id',
        'skip_if_empty_column':'id',
        OclCsvToJsonConverter.DEF_CORE_FIELDS:[
            {'resource_field':...}
        ],
        OclCsvToJsonConverter.DEF_SUB_RESOURCES:{
            'names':[],
            'descriptions':[],
        },
        OclCsvToJsonConverter.DEF_KEY_VALUE_PAIRS:{
            'extras':[],
        },
    ]

Note that all defined resource_fields are required unless "required": False or a "default"
is included in their definition.

Things that are missing:
- Standalone Mappings, Concept Mappings, Concept/Mappings References
- Improve type conversion functionality (e.g. datatype: bool)
- No script-level validation supported (meaning, validation occurs when submitting to OCL)
"""
import csv
import json
import re
import oclconstants


class OclCsvToJsonConverter(object):
    """ Class to convert CSV file to OCL-formatted JSON flex file """

    # Constants for explicitly defined resource definitions
    DEF_CORE_FIELDS = 'core_fields'
    DEF_SUB_RESOURCES = 'subresources'
    DEF_KEY_VALUE_PAIRS = 'key_value_pairs'

    # Constants for automatic resource definitions
    DEF_AUTO_CONCEPT_NAMES = 'auto_concept_names'
    DEF_AUTO_CONCEPT_DESCRIPTIONS = 'auto_concept_descriptions'
    DEF_AUTO_ATTRIBUTES = 'auto_attributes'
    DEF_AUTO_CONCEPT_MAPPINGS = 'auto_concept_mappings'

    # Constants for specific attribute names
    DEF_KEY_RESOURCE_FIELD = 'resource_field'
    DEF_KEY_RESOURCE_TYPE = 'resource_type'
    DEF_KEY_ID_COLUMN = 'id_column'
    DEF_KEY_IS_ACTIVE = 'is_active'
    DEF_KEY_SKIP_IF_EMPTY = 'skip_if_empty_column'
    DEF_KEY_TRIGGER_COLUMN = '__trigger_column'
    DEF_KEY_TRIGGER_VALUE = '__trigger_value'

    # Mapping descriptors
    INTERNAL_MAPPING_ID = 'Internal'
    EXTERNAL_MAPPING_ID = 'External'

    # Note that underscores are allowed for a concept ID and the exception is made in the code
    INVALID_CHARS = ' `~!@#$%^&*()_+-=[]{}\\|;:"\',/<>?'
    REPLACE_CHAR = '-'

    def __init__(self, output_filename='', csv_filename='', input_list=None,
                 csv_resource_definitions=None, verbose=False):
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
        """
        self.output_filename = output_filename
        self.csv_filename = csv_filename
        self.input_list = input_list
        if csv_filename:
            self.load_csv(csv_filename)
        self.verbose = verbose
        self.set_resource_definitions(csv_resource_definitions=csv_resource_definitions)
        self.output_list = []

    def preprocess_csv_row(self, row, attr=None):
        """ Method intended to be overwritten in classes that extend this object """
        return row

    def set_resource_definitions(self, csv_resource_definitions=None):
        """ Set CSV resource definitions to use to convert to JSON """
        self.csv_resource_definitions = csv_resource_definitions

    def load_csv(self, csv_filename):
        """ Load CSV file into the input_list """
        input_list = []
        with open(csv_filename) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                input_list.append(row)
        self.input_list = input_list

    def process_by_row(self, num_rows=0, attr=None):
        """ Process CSV by applying all definitions to each row before moving to the next row """
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
                if self.DEF_KEY_IS_ACTIVE not in csv_resource_def or csv_resource_def[self.DEF_KEY_IS_ACTIVE]:
                    self.process_csv_row_with_definition(csv_row, csv_resource_def, attr=attr)
        return self.output_list

    def process_by_definition(self, num_rows=0, attr=None):
        """ Process the CSV file by looping through it entirely once for each definition """
        if self.csv_filename:
            self.load_csv(self.csv_filename)
        self.output_list = []
        for csv_resource_def in self.csv_resource_definitions:
            if self.DEF_KEY_IS_ACTIVE not in csv_resource_def or csv_resource_def[self.DEF_KEY_IS_ACTIVE]:
                if self.verbose:
                    print '\n%s' % ('*' * 100)
                    print 'Processing definition: %s' % csv_resource_def['definition_name']
                    print '*' * 100
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
        ocl_resource = {}

        # TRIGGER: Skip row if the trigger column does not equal trigger_value
        if self.DEF_KEY_TRIGGER_COLUMN in csv_resource_def:
            if csv_resource_def[self.DEF_KEY_TRIGGER_COLUMN] not in csv_row:
                # if self.verbose:
                #     print "SKIPPING: Trigger column '%s' not found in CSV row: %s" % (
                #         csv_resource_def[self.DEF_KEY_TRIGGER_COLUMN], csv_row)
                return
            if csv_row[csv_resource_def[self.DEF_KEY_TRIGGER_COLUMN]] != csv_resource_def[
                    self.DEF_KEY_TRIGGER_VALUE]:
                # if self.verbose:
                #     print "SKIPPING: Trigger column '%s' doesn't match trigger value '%s': %s" % (
                #         csv_resource_def[self.DEF_KEY_TRIGGER_COLUMN],
                #         csv_resource_def[self.DEF_KEY_TRIGGER_VALUE],
                #         csv_row[csv_resource_def[self.DEF_KEY_TRIGGER_COLUMN]])
                return
            # if self.verbose:
            #     print "INFO: Trigger column '%s' matches trigger value '%s'. Continuing..." % (
            #         csv_resource_def[self.DEF_KEY_TRIGGER_COLUMN],
            #         csv_resource_def[self.DEF_KEY_TRIGGER_VALUE])

        # SKIP_IF_EMPTY: Skip if SKIP_IF_EMPTY column has a blank value
        is_skip_row = False
        if self.DEF_KEY_SKIP_IF_EMPTY in csv_resource_def and csv_resource_def[self.DEF_KEY_SKIP_IF_EMPTY]:
            skip_columns = csv_resource_def[self.DEF_KEY_SKIP_IF_EMPTY]
            if not isinstance(skip_columns, list):
                skip_columns = [skip_columns]
            for skip_column in skip_columns:
                if skip_column not in csv_row:
                    raise Exception("%s '%s' is not defined in the CSV file" % (
                        self.DEF_KEY_SKIP_IF_EMPTY, skip_column))
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

        # Determine the OCL resource type, e.g. Concept, Mapping, Source, etc.
        if self.DEF_KEY_RESOURCE_TYPE not in csv_resource_def:
            raise Exception(
                'Missing required "resource_type" in row definition:' % csv_resource_def)
        ocl_resource_type = ocl_resource['type'] = csv_resource_def[self.DEF_KEY_RESOURCE_TYPE]

        # Determine resource's ID and auto-replace invalid ID characters
        has_id_column = False
        id_column = None
        if self.DEF_KEY_ID_COLUMN in csv_resource_def and csv_resource_def[self.DEF_KEY_ID_COLUMN]:
            has_id_column = True
            id_column = csv_resource_def[self.DEF_KEY_ID_COLUMN]
            if id_column not in csv_row or not csv_row[id_column]:
                raise Exception('ID column %s not set or empty in row %s' % (id_column, csv_row))
            if ocl_resource_type == oclconstants.OclConstants.RESOURCE_TYPE_CONCEPT:
                ocl_resource['id'] = self.format_identifier(
                    csv_row[id_column], allow_underscore=True)
            else:
                ocl_resource['id'] = self.format_identifier(csv_row[id_column])

        # Set core fields, eg concept_class, datatype, external_id, etc.
        if self.DEF_CORE_FIELDS in csv_resource_def and csv_resource_def[self.DEF_CORE_FIELDS]:
            for field_def in csv_resource_def[self.DEF_CORE_FIELDS]:
                value = self.get_resource_field(csv_row, field_def)
                if value is not None:
                    # Only save the value if it is not None
                    ocl_resource[field_def[self.DEF_KEY_RESOURCE_FIELD]] = value

        # Set sub-resources, eg concept names/descriptions
        if self.DEF_SUB_RESOURCES in csv_resource_def and csv_resource_def[self.DEF_SUB_RESOURCES]:
            for group_name in csv_resource_def[self.DEF_SUB_RESOURCES]:  # eg "names","descriptions"
                ocl_resource[group_name] = []
                for dict_def in csv_resource_def[self.DEF_SUB_RESOURCES][group_name]:
                    ocl_sub_resource = {}
                    for field_def in dict_def:
                        value = self.get_resource_field(csv_row, field_def)
                        if value is not None:
                            # Only save the value if it is not None
                            ocl_resource[field_def[self.DEF_KEY_RESOURCE_FIELD]] = value
                    if ocl_sub_resource:
                        ocl_resource[group_name].append(ocl_sub_resource)

        # Key value pairs, eg custom attributes
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
                            err_msg = 'key_column "%s" must be non-empty in CSV within key_value_pair: %s' % (kvp_def['key_column'], kvp_def)
                            raise Exception(err_msg)
                    else:
                        err_msg = 'Expected "key" or "key_column" key in key_value_pair definition, but neither found: %s' % kvp_def
                        raise Exception(err_msg)

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
                    if key and (value or ('omit_if_empty_value' in kvp_def and not kvp_def['omit_if_empty_value'])):
                        ocl_resource[group_name][key] = value

        # Handle auto-names
        if self.DEF_AUTO_CONCEPT_NAMES in csv_resource_def:
            concepts_names = self.get_auto_sub_resources(
                csv_row, csv_resource_def[self.DEF_AUTO_CONCEPT_NAMES])
            if concepts_names:
                ocl_resource['names'] = concepts_names

        # Handle auto-descriptions
        if self.DEF_AUTO_CONCEPT_DESCRIPTIONS in csv_resource_def:
            concepts_descriptions = self.get_auto_sub_resources(
                csv_row, csv_resource_def[self.DEF_AUTO_CONCEPT_DESCRIPTIONS])
            if concepts_descriptions:
                ocl_resource['descriptions'] = concepts_descriptions

        # Handle auto-attributes
        if self.DEF_AUTO_ATTRIBUTES in csv_resource_def:
            extra_attr = self.get_auto_extra_attributes(
                csv_row, csv_resource_def[self.DEF_AUTO_ATTRIBUTES])
            if extra_attr:
                ocl_resource['extras'] = extra_attr

        # Output the OCL resource JSON
        if self.verbose:
            print json.dumps(ocl_resource)
        if self.output_filename:
            output_file = open(self.output_filename, 'a')
            output_file.write(json.dumps(ocl_resource))
            output_file.write('\n')
        else:
            self.output_list.append(ocl_resource)

    def get_auto_extra_attributes(self, csv_row, auto_attributes_def):
        """
        Get a dictionary of auto-extra ("custom") attributes in the given CSV row.
        Two models supported:
        1) Standard column: If column name is "attr:Key1", then "Key1" is the key, and the
           cell in each row is the value. By default, this is omitted if the value is empty
           unless "omit_if_empty_value" is set to False in the field definition.
        2) Separated key/value pair: This model allows the custom attribute key to be adjusted
           for each row by separating the key and value into their own columns sharing a common
           index. E.g. if column name is "attr_key[001]", the cell in each row is the key. A
           separate column with the name "attr_value[001]" must be defined, and the cell in each
           row is the corresponding value. If the key is blank it is omitted. If value is blank,
           it is omitted by default, unless "omit_if_empty_value" is set to False in the field
           definition.

        Brief CSV example:
        attr:my-custom-attribute, attr_key[1], attr_value[1], attr_key[27], attr_value[27]
        value for my-custom-attribute, My unique key for this row, the for "My unique key for this row", Another key, Another value
        """
        extra_attributes = {}
        keyless_values = {}
        valueless_keys = {}

        # Determine whether to omit blank values (default = True)
        omit_if_empty_value = True
        if 'omit_if_empty_value' in auto_attributes_def and not auto_attributes_def['omit_if_empty_value']:
            omit_if_empty_value = False

        # Prepare search strings
        standard_needle = '%s%s' % (
            auto_attributes_def['standard_column_prefix'], auto_attributes_def['separator'])
        key_needle = '^%s%s(%s)%s$' % (
            auto_attributes_def['key_column_prefix'],
            re.escape(auto_attributes_def['index_prefix']),
            auto_attributes_def['index_regex'],
            re.escape(auto_attributes_def['index_postfix']))
        value_needle = '^%s%s(%s)%s$' % (
            auto_attributes_def['value_column_prefix'],
            re.escape(auto_attributes_def['index_prefix']),
            auto_attributes_def['index_regex'],
            re.escape(auto_attributes_def['index_postfix']))

        # Process CSV columns
        for column_name in csv_row:
            if column_name[:len(standard_needle)] == standard_needle:
                # Check if standard attr (e.g. attr:my-custom-attr)
                if not omit_if_empty_value or (omit_if_empty_value and csv_row[column_name]):
                    key_name = column_name[len(standard_needle):]
                    extra_attributes[key_name] = csv_row[column_name]
            else:
                key_regex_match = re.search(key_needle, column_name)
                value_regex_match = re.search(value_needle, column_name)
                if key_regex_match:
                    key_index = key_regex_match.group(1)
                    if not key_index:
                        # Invalid (ie blank) auto index
                        raise Exception("Auto indexes must be non-empty")
                    elif not csv_row[column_name]:
                        # Skip if the key is empty
                        continue
                    elif key_index in keyless_values:
                        # We now have a key/value pair
                        extra_attributes[csv_row[column_name]] = keyless_values.pop(key_index)
                    else:
                        # Save and continue processing columns
                        key_name = csv_row[column_name]
                        valueless_keys[key_index] = key_name
                elif value_regex_match:
                    value_index = value_regex_match.group(1)
                    if not value_index:
                        # Invalid (ie blank) auto index
                        raise Exception("Auto indexes must be non-empty")
                    elif not csv_row[column_name] and omit_if_empty_value:
                        # Optionally skip if empty value
                        continue
                    elif value_index in valueless_keys:
                        # We now have a key/value pair
                        key_name = valueless_keys.pop(value_index)
                        extra_attributes[key_name] = csv_row[column_name]
                    else:
                        # Save and continue processing columns
                        value = csv_row[column_name]
                        keyless_values[value_index] = value

        # TODO: Handle orphaned keys and values

        return extra_attributes

    def get_auto_sub_resources(self, csv_row, auto_sub_resources_def):
        """ Auto-generate sub_resources for the CSV row based on the specified definition """
        if 'sub_resource_type' not in auto_sub_resources_def:
            raise Exception('Missing required "sub_resource_type" in auto_sub_resources definition')

        sub_resources = []

        # Add primary sub resource (if defined)
        if 'primary_sub_resource' in auto_sub_resources_def:
            sub_resource = {}
            for field_def in auto_sub_resources_def['primary_sub_resource']:
                value = self.get_resource_field(csv_row, field_def)
                if value is not None:
                    sub_resource[field_def[self.DEF_KEY_RESOURCE_FIELD]] = value
            if sub_resource:
                sub_resources.append(sub_resource)

        if 'auto_sub_resources' in auto_sub_resources_def:
            unique_auto_resource_indexes = self.get_unique_csv_row_auto_indexes(
                auto_sub_resources_def, csv_row)
            for auto_resource_index in unique_auto_resource_indexes:
                sub_resource = {}
                sub_resource_def = self.generate_sub_resource_def(
                    auto_resource_index, auto_sub_resources_def['auto_sub_resources'])
                for field_def in sub_resource_def:
                    value = self.get_resource_field(csv_row, field_def)
                    if value is not None:
                        sub_resource[field_def[self.DEF_KEY_RESOURCE_FIELD]] = value
                if sub_resource:
                    sub_resources.append(sub_resource)

        return sub_resources

    def generate_sub_resource_def(self, auto_resource_index, auto_sub_resources_def):
        """ Get a set of traditional CSV resource definitions for the specified auto index """
        traditional_sub_resource_def = []
        for field_def in auto_sub_resources_def:
            new_field_def = field_def.copy()
            new_field_def.pop('column_prefix')
            new_field_def['column'] = '%s%s%s%s' % (
                auto_sub_resources_def['column_prefix'],
                auto_sub_resources_def['index_prefix'],
                auto_resource_index,
                auto_sub_resources_def['index_prefix'])
            traditional_sub_resource_def.append(new_field_def)
        return traditional_sub_resource_def

    def get_unique_csv_row_auto_indexes(self, auto_sub_resources_def, csv_row):
        """
        Return list of unique auto indexes in the CSV row as defined by the auto_sub_resources_def
        """
        unique_auto_resource_indexes = []
        for column_name in csv_row:
            for field_def in auto_sub_resources_def['auto_sub_resources']:
                if column_name[:len(field_def['column_prefix'])] == field_def['column_prefix']:
                    search_exp = r'^%s%s(%s)%s$' % (
                        field_def['column_prefix'],
                        re.escape(auto_sub_resources_def['index_prefix']),
                        auto_sub_resources_def['index_regex'],
                        re.escape(auto_sub_resources_def['index_postfix']))
                    regex_match = re.search(search_exp, column_name)
                    if regex_match:
                        index = regex_match.group(1)
                        if index and index not in unique_auto_resource_indexes:
                            unique_auto_resource_indexes.append(index)
        return unique_auto_resource_indexes

    def get_resource_field(self, csv_row, field_def):
        """ Processes a single resource field definition for the given CSV row """
        if self.DEF_KEY_RESOURCE_FIELD not in field_def:
            raise Exception(
                'Expected key "%s" in subresource definition, but none found: %s' % (
                    self.DEF_KEY_RESOURCE_FIELD, field_def))
        return self.get_csv_value(csv_row, field_def)

    def get_csv_value(self, csv_row, field_def):
        """
        Return a value from a csv_row for the specified field definition.
        field_def must include 'resource_type' and either a 'column' or 'value' key or
        both a 'csv_to_json_processor' and 'data_column' keys.
        Optional keys include 'required', 'default', and 'datatype'
        """
        if 'column' in field_def:
            if field_def['column'] not in csv_row and 'default' in field_def:
                # Return 'default' if 'column' is not in CSV row
                # TODO: If column exists but value is blank? Implement new attr to customize?
                return field_def['default']
            elif field_def['column'] not in csv_row and 'required' in field_def and not field_def['required']:
                # Return None if no 'default' and 'column' is not in CSV and 'required' == False
                return None
            elif 'datatype' in field_def and field_def['column'] in csv_row and field_def['datatype'] == 'bool':
                # Perform type conversion
                return bool(csv_row[field_def['column']])
            # Return the value in 'column', or throw error if not defined in the CSV row
            return csv_row[field_def['column']]
        elif 'value' in field_def:
            # Just return whatever is in the 'value' definition
            return field_def['value']
        elif 'csv_to_json_processor' in field_def and 'data_column' in field_def:
            # Use an externally defined method to generate the value
            method_to_call = getattr(self, field_def['csv_to_json_processor'])
            return method_to_call(csv_row, field_def)
        else:
            raise Exception(
                'Expected "column", "value", or "csv_to_json_processor" key in standard column definition, but none found: %s' % field_def)

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
            # Remove underscore from the invalid characters - Concept IDs are okay with underscores
            chars_to_remove = self.INVALID_CHARS.replace('_', '')
        else:
            chars_to_remove = self.INVALID_CHARS
        for index in range(len(unformatted_id)):
            if unformatted_id[index] in chars_to_remove:
                formatted_id[index] = self.REPLACE_CHAR
        return ''.join(formatted_id)


class OclStandardCsvToJsonConverter(OclCsvToJsonConverter):
    """ Standard CSV to OCL-formatted JSON converter """

    default_csv_resource_definitions = [
        {
            'definition_name': 'Generic Organization',
            'is_active': True,
            'resource_type': oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION,
            'id_column': 'id',
            '__trigger_column': 'resource_type',
            '__trigger_value': oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION,
            'skip_if_empty_column': 'id',
            OclCsvToJsonConverter.DEF_CORE_FIELDS: [
                {'resource_field': 'name', 'column': 'name'},
                {'resource_field': 'company', 'column': 'company', 'required': False},
                {'resource_field': 'website', 'column': 'website', 'required': False},
                {'resource_field': 'location', 'column': 'location', 'required': False},
                {'resource_field': 'public_access', 'column': 'public_access', 'default': 'View'},
            ],
            OclCsvToJsonConverter.DEF_AUTO_ATTRIBUTES: {
                'standard_column_prefix': 'attr',  # e.g. 'attr:Reporting Frequency'
                'separator': ':',
                'key_column_prefix': 'attr_key',  # 2-digit number required, e.g. attr_key[01]
                'value_column_prefix': 'attr_value',  # 2-digit number required, e.g. attr_value[01]
                'index_prefix': '[',
                'index_postfix': ']',
                'index_regex': '[0-9]+',
            }
        },
        {
            'definition_name': 'Generic Source',
            'is_active': True,
            'resource_type': oclconstants.OclConstants.RESOURCE_TYPE_SOURCE,
            'id_column': 'id',
            '__trigger_column': 'resource_type',
            '__trigger_value': oclconstants.OclConstants.RESOURCE_TYPE_SOURCE,
            'skip_if_empty_column': 'id',
            OclCsvToJsonConverter.DEF_CORE_FIELDS: [
                {'resource_field': 'external_id', 'column': 'external_id', 'required': False},
                {'resource_field': 'short_code', 'column': 'short_code', 'required': False},
                {'resource_field': 'name', 'column': 'name'},
                {'resource_field': 'full_name', 'column': 'name', 'required': False},
                {'resource_field': 'source_type', 'column': 'source_type', 'required': False},
                {'resource_field': 'public_access', 'column': 'public_access', 'default': 'View'},
                {'resource_field': 'default_locale', 'column': 'default_locale', 'default': 'en'},
                {'resource_field': 'supported_locales', 'column': 'supported_locales',
                 'default': 'en'},
                {'resource_field': 'website', 'column': 'website', 'required': False},
                {'resource_field': 'description', 'column': 'description', 'required': False},
                {'resource_field': 'custom_validation_schema', 'column': 'custom_validation_schema',
                 'required': False},
                {'resource_field': 'owner', 'column': 'owner_id'},
                {'resource_field': 'owner_type', 'column': 'owner_type',
                 'default': oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION},
            ],
            OclCsvToJsonConverter.DEF_AUTO_ATTRIBUTES: {
                'standard_column_prefix': 'attr',  # e.g. 'attr:Reporting Frequency'
                'separator': ':',
                'key_column_prefix': 'attr_key',  # 2-digit number required, e.g. attr_key[01]
                'value_column_prefix': 'attr_value',  # 2-digit number required, e.g. attr_value[01]
                'index_prefix': '[',
                'index_postfix': ']',
                'index_regex': '[0-9]+',
            }
        },
        {
            'definition_name': 'Generic Collection',
            'is_active': True,
            'resource_type': oclconstants.OclConstants.RESOURCE_TYPE_COLLECTION,
            'id_column': 'id',
            '__trigger_column': 'resource_type',
            '__trigger_value': oclconstants.OclConstants.RESOURCE_TYPE_COLLECTION,
            'skip_if_empty_column': 'id',
            OclCsvToJsonConverter.DEF_CORE_FIELDS: [
                {'resource_field': 'external_id', 'column': 'external_id', 'required': False},
                {'resource_field': 'short_code', 'column': 'short_code', 'required': False},
                {'resource_field': 'name', 'column': 'name'},
                {'resource_field': 'full_name', 'column': 'name', 'required': False},
                {'resource_field': 'collection_type', 'column': 'collection_type',
                 'required': False},
                {'resource_field': 'public_access', 'column': 'public_access', 'default': 'View'},
                {'resource_field': 'default_locale', 'column': 'default_locale', 'default': 'en'},
                {'resource_field': 'supported_locales', 'column': 'supported_locales',
                 'default': 'en'},
                {'resource_field': 'website', 'column': 'website', 'required': False},
                {'resource_field': 'description', 'column': 'description', 'required': False},
                {'resource_field': 'custom_validation_schema', 'column': 'custom_validation_schema',
                 'required': False},
                {'resource_field': 'owner', 'column': 'owner_id'},
                {'resource_field': 'owner_type', 'column': 'owner_type',
                 'default': oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION},
            ],
            OclCsvToJsonConverter.DEF_AUTO_ATTRIBUTES: {
                'standard_column_prefix': 'attr',  # e.g. 'attr:Reporting Frequency'
                'separator': ':',
                'key_column_prefix': 'attr_key',  # 2-digit number required, e.g. attr_key[01]
                'value_column_prefix': 'attr_value',  # 2-digit number required, e.g. attr_value[01]
                'index_prefix': '[',
                'index_postfix': ']',
                'index_regex': '[0-9]+',
            }
        },
        {
            'definition_name': 'Generic Concept',
            'is_active': True,
            'resource_type': oclconstants.OclConstants.RESOURCE_TYPE_CONCEPT,
            'id_column': 'id',
            '__trigger_column': 'resource_type',
            '__trigger_value': oclconstants.OclConstants.RESOURCE_TYPE_CONCEPT,
            'skip_if_empty_column': 'id',
            OclCsvToJsonConverter.DEF_CORE_FIELDS: [
                {'resource_field': 'retired', 'column': 'retired', 'required': False},
                {'resource_field': 'external_id', 'column': 'external_id', 'required': False},
                {'resource_field': 'concept_class', 'column': 'concept_class'},
                {'resource_field': 'datatype', 'column': 'datatype', 'default': 'None'},
                {'resource_field': 'owner', 'column': 'owner_id'},
                {'resource_field': 'owner_type', 'column':'owner_type',
                 'default': oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION},
                {'resource_field': 'source', 'column': 'source'},
            ],
            OclCsvToJsonConverter.DEF_AUTO_CONCEPT_NAMES: {
                'sub_resource_type': 'names',
                'primary_sub_resource': [
                    {'resource_field': 'name', 'column': 'name'},
                    {'resource_field': 'locale', 'column': 'name_locale', 'default': 'en'},
                    {'resource_field': 'locale_preferred', 'column': 'name_locale_preferred',
                     'required': False},
                    {'resource_field': 'name_type', 'column': 'name_type', 'required': False},
                    {'resource_field': 'external_id', 'column': 'name_external_id',
                     'required': False},
                ],
                'index_prefix': '[',
                'index_postfix': ']',
                'index_regex': '[0-9]+',
                'auto_sub_resources': [
                    {'resource_field': 'name', 'column_prefix': 'name'},
                    {'resource_field': 'locale', 'column_prefix': 'name_locale', 'default': 'en'},
                    {'resource_field': 'locale_preferred', 'column_prefix': 'name_locale_preferred',
                     'required': False},
                    {'resource_field': 'name_type', 'column_prefix': 'name_type',
                     'required': False},
                    {'resource_field': 'external_id', 'column_prefix': 'name_external_id',
                     'required': False},
                ]
            },
            OclCsvToJsonConverter.DEF_AUTO_CONCEPT_DESCRIPTIONS: {
                'sub_resource_type': 'descriptions',
                'primary_sub_resource': [
                    {'resource_field':'description', 'column':'description'},
                    {'resource_field':'locale', 'column':'description_locale', 'default': 'en'},
                    {'resource_field':'locale_preferred', 'column':'description_locale_preferred',
                     'required': False},
                    {'resource_field':'description_type', 'column':'description_type',
                     'required': False},
                    {'resource_field':'external_id', 'column':'description_external_id',
                     'required': False},
                ],
                'index_prefix': '[',
                'index_postfix': ']',
                'index_regex': '[0-9]+',
                'auto_sub_resources': [
                    {'resource_field': 'description', 'column_prefix': 'description'},
                    {'resource_field': 'locale', 'column_prefix': 'description_locale',
                     'default': 'en'},
                    {'resource_field': 'locale_preferred',
                     'column_prefix': 'description_locale_preferred', 'required': False},
                    {'resource_field': 'description_type', 'column_prefix': 'description_type',
                     'required': False},
                    {'resource_field': 'external_id', 'column_prefix': 'description_external_id',
                     'required': False},
                ],
            },
            OclCsvToJsonConverter.DEF_AUTO_ATTRIBUTES: {
                'standard_column_prefix': 'attr',  # e.g. 'attr:Reporting Frequency'
                'separator': ':',
                'key_column_prefix': 'attr_key',  # 2-digit number required, e.g. attr_key[01]
                'value_column_prefix': 'attr_value',  # 2-digit number required, e.g. attr_value[01]
                'index_prefix': '[',
                'index_postfix': ']',
                'index_regex': '[0-9]+',
            }
        },
        {
            'definition_name': 'Generic Source Version',
            'is_active': True,
            'resource_type': oclconstants.OclConstants.RESOURCE_TYPE_SOURCE_VERSION,
            'id_column': 'id',
            '__trigger_column': 'resource_type',
            '__trigger_value': oclconstants.OclConstants.RESOURCE_TYPE_SOURCE_VERSION,
            'skip_if_empty_column': 'id',
            OclCsvToJsonConverter.DEF_CORE_FIELDS: [
                {'resource_field': 'description', 'column': 'description'},
                {'resource_field': 'released', 'column': 'released', 'required': False,
                 'datatype': 'bool'},
                {'resource_field': 'owner', 'column': 'owner_id'},
                {'resource_field': 'owner_type', 'column':'owner_type',
                 'default': oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION},
                {'resource_field': 'source', 'column': 'source'},
            ],
        },
        {
            'definition_name': 'Generic Collection Version',
            'is_active': True,
            'resource_type': oclconstants.OclConstants.RESOURCE_TYPE_COLLECTION_VERSION,
            'id_column': 'id',
            '__trigger_column': 'resource_type',
            '__trigger_value': oclconstants.OclConstants.RESOURCE_TYPE_COLLECTION_VERSION,
            'skip_if_empty_column': 'id',
            OclCsvToJsonConverter.DEF_CORE_FIELDS: [
                {'resource_field': 'description', 'column': 'description'},
                {'resource_field': 'released', 'column': 'released', 'required': False,
                 'datatype': 'bool'},
                {'resource_field': 'owner', 'column': 'owner_id'},
                {'resource_field': 'owner_type', 'column':'owner_type',
                 'default': oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION},
                {'resource_field': 'collection', 'column': 'collection'},
            ],
        },
        {
            'definition_name': 'Generic Concept Mapping',
            'is_active': False,
            'resource_type': oclconstants.OclConstants.RESOURCE_TYPE_MAPPING,
            '__trigger_column': 'resource_type',
            '__trigger_value': oclconstants.OclConstants.RESOURCE_TYPE_CONCEPT,
            'skip_if_empty_column': 'parent_ocl_id_1',
            OclCsvToJsonConverter.DEF_AUTO_CONCEPT_MAPPINGS: {
            },
            OclCsvToJsonConverter.DEF_CORE_FIELDS: [
                {'resource_field': 'from_concept_url', 'column': 'from_concept_url_1'},
                {'resource_field': 'map_type', 'column': 'map_type'},
                {'resource_field': 'to_concept_url', 'column': 'to_concept_url'},
                {'resource_field': 'owner', 'column': 'ocl_org_id'},
                {'resource_field': 'owner_type', 'column':'owner_type',
                 'default': oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION},
                {'resource_field': 'source', 'column': 'ocl_source_id'},
            ]
        },
        {
            'definition_name': 'Generic Standalone Mapping',
            'is_active': False,
            'resource_type': oclconstants.OclConstants.RESOURCE_TYPE_MAPPING,
            '__trigger_column': 'resource_type',
            '__trigger_value': oclconstants.OclConstants.RESOURCE_TYPE_MAPPING,
            'skip_if_empty_column': 'parent_ocl_id_1',
            OclCsvToJsonConverter.DEF_CORE_FIELDS: [
                {'resource_field': 'from_concept_url', 'column': 'from_concept_url_1'},
                {'resource_field': 'map_type', 'column': 'map_type'},
                {'resource_field': 'to_concept_url', 'column': 'to_concept_url'},
                {'resource_field': 'owner', 'column': 'owner_id'},
                {'resource_field': 'owner_type', 'column':'owner_type',
                 'default': oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION},
                {'resource_field': 'source', 'column': 'ocl_source_id'},
            ]
        },
    ]

    def __init__(self, output_filename='', csv_filename='', input_list=None, verbose=False):
        """ Initialize the object with the standard CSV resource definition """
        OclCsvToJsonConverter.__init__(
            self, output_filename=output_filename, csv_filename=csv_filename, input_list=input_list,
            csv_resource_definitions=self.default_csv_resource_definitions, verbose=verbose)
