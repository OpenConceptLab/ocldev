"""
Script to convert a CSV file to an OCL-formatted JSON file based on a provided set of CSV Resource
Definitions. The resulting JSON is intended for the OclFlexImporter. See
OclStandardCsvToJsonConverter.default_csv_resource_definitions in this file for examples.
Note that resource_fields are required unless "required": False or a "default" is included.
Next steps:
- Bring handling of resource IDs into alignment with updated OCLAPI ID implementation
- Implement support for: (1) Generic Auto Concept References, (2) Generic Standalone References
- Implement import script validation
"""
import csv
import json
import re

import six

from distutils import util

from ocldev import oclconstants


class OclCsvToJsonConverter(object):
    """ Class to convert CSV file to OCL-formatted JSON flex file """

    # Constants for method of processing the CSV
    PROCESS_BY_DEFINITION = 'process_by_definition'
    PROCESS_BY_ROW = 'process_by_row'

    # Constants for explicitly defined field definitions
    DEF_CORE_FIELDS = 'core_fields'
    DEF_SUB_RESOURCES = 'subresources'
    DEF_KEY_VALUE_PAIRS = 'key_value_pairs'
    DEF_RESOURCE_FIELD_TYPES = [
        DEF_CORE_FIELDS,
        DEF_SUB_RESOURCES,
        DEF_KEY_VALUE_PAIRS,
    ]

    # Constants for specific attribute names
    DEF_KEY_RESOURCE_FIELD = 'resource_field'
    DEF_KEY_RESOURCE_TYPE = 'resource_type'
    DEF_KEY_ID_COLUMN = 'id_column'
    DEF_KEY_IS_ACTIVE = 'is_active'
    DEF_KEY_SKIP_IF_EMPTY = 'skip_if_empty_column'
    DEF_KEY_TRIGGER_COLUMN = '__trigger_column'
    DEF_KEY_TRIGGER_VALUE = '__trigger_value'
    DEF_KEY_SKIP_HANDLER = 'skip_handler'

    # Constants for automatic resource definitions
    DEF_TYPE_AUTO_RESOURCE = 'AUTO-RESOURCE'
    DEF_AUTO_CONCEPT_NAMES = 'auto_concept_names'
    DEF_AUTO_CONCEPT_DESCRIPTIONS = 'auto_concept_descriptions'
    DEF_AUTO_ATTRIBUTES = 'auto_attributes'
    DEF_AUTO_RESOURCE_TEMPLATE = 'auto_resource_template'
    DEF_KEY_TRIGGER_COLUMN_PREFIX = '__trigger_column_prefix'
    DEF_KEY_SKIP_IF_EMPTY_PREFIX = 'skip_if_empty_column_prefix'
    DEF_KEY_AUTO_INDEX_PREFIX = 'index_prefix'
    DEF_KEY_AUTO_INDEX_POSTFIX = 'index_postfix'
    DEF_KEY_AUTO_INDEX_REGEX = 'index_regex'
    AUTO_REPLACEMENT_FIELDS = {
        DEF_KEY_TRIGGER_COLUMN_PREFIX: DEF_KEY_TRIGGER_COLUMN,
        DEF_KEY_SKIP_IF_EMPTY_PREFIX: DEF_KEY_SKIP_IF_EMPTY,
    }

    # Note that underscores are allowed for a concept ID and the exception is made in the code
    INVALID_CHARS = ' `~!@#$%^&*()_+-=[]{}\\|;:"\',/<>?'
    REPLACE_CHAR = '-'

    def __init__(self, csv_filename='', input_list=None,
                 csv_resource_definitions=None, verbose=False, allow_special_characters=False):
        """
        Initialize this object
        :param csv_filename: <string> Filename to load CSV data from; use "input_list"
            if CSV already loaded into list
        :param input_list: <list> List of dictionaries objects representing each row of the CSV file
        :param csv_resource_definitions: <dict> Properly formatted dictionary defining
            how to convert CSV to OCL-JSON
        :param verbose: <int> 0=off, 1=some debug info, 2=all debug info
        :param allow_special_characters: <bool> concept id special characters will not be replaced by `-`
        """
        self.allow_special_characters = allow_special_characters
        self.csv_filename = csv_filename
        self.input_list = input_list
        if csv_filename:
            self.load_csv(csv_filename)
        self.verbose = verbose
        self.set_resource_definitions(csv_resource_definitions=csv_resource_definitions)
        self.output_list = []
        self._current_row_num = 0
        self._total_rows = 0

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

    def process(self, method=PROCESS_BY_DEFINITION, num_rows=0, attr=None):
        """ Process CSV into OCL-formatted JSON """
        if method == OclCsvToJsonConverter.PROCESS_BY_ROW:
            return self.process_by_row(num_rows=num_rows, attr=attr)
        return self.process_by_definition(num_rows=num_rows, attr=attr)

    def process_by_row(self, num_rows=0, attr=None):
        """ Process CSV by applying all definitions to each row before moving to the next row """
        if self.csv_filename:
            self.load_csv(self.csv_filename)
        self._current_row_num = 0
        self._total_rows = len(self.input_list)
        self.output_list = []
        for csv_row in self.input_list:
            if num_rows and self._current_row_num >= num_rows:
                break
            self._current_row_num += 1
            csv_row = self.preprocess_csv_row(csv_row.copy(), attr)
            for csv_resource_def in self.csv_resource_definitions:
                if (self.DEF_KEY_IS_ACTIVE in csv_resource_def and not csv_resource_def[
                        self.DEF_KEY_IS_ACTIVE]):
                    continue
                ocl_resources = self.process_csv_row_with_definition(
                    csv_row, csv_resource_def, attr=attr)
                if ocl_resources and isinstance(ocl_resources, dict):  # Single OCL resource
                    self.output_list.append(ocl_resources)
                elif ocl_resources and isinstance(ocl_resources, list):  # List of OCL resources
                    self.output_list += ocl_resources
        return self.output_list

    def process_by_definition(self, num_rows=0, attr=None):
        """ Process the CSV file by looping through it entirely once for each definition """
        if self.csv_filename:
            self.load_csv(self.csv_filename)
        self.output_list = []
        self._total_rows = len(self.input_list)
        for csv_resource_def in self.csv_resource_definitions:
            if self.DEF_KEY_IS_ACTIVE in csv_resource_def and not csv_resource_def[
                    self.DEF_KEY_IS_ACTIVE]:
                continue
            if self.verbose:
                six.print_(('\n%s' % ('*' * 120)))
                six.print_(('Processing definition: %s' % csv_resource_def['definition_name']))
                # print csv_resource_def
                six.print_(('*' * 120))
            self._current_row_num = 0
            for csv_row in self.input_list:
                if num_rows and self._current_row_num >= num_rows:
                    break
                self._current_row_num += 1
                csv_row = self.preprocess_csv_row(csv_row.copy(), attr)
                ocl_resources = self.process_csv_row_with_definition(
                    csv_row, csv_resource_def, attr=attr)
                if ocl_resources and isinstance(ocl_resources, dict):  # Single OCL resource
                    self.output_list.append(ocl_resources)
                elif ocl_resources and isinstance(ocl_resources, list):  # List of OCL resources
                    self.output_list += ocl_resources
        return self.output_list

    def process_csv_row_with_definition(self, csv_row, csv_resource_def, attr=None):
        """ Process individual CSV row with the provided CSV resource definition """

        # Throw exception if resource_type not in the resource definition
        if self.DEF_KEY_RESOURCE_TYPE not in csv_resource_def:
            err_msg = 'Missing required "%s" in row definition: %s' % (
                self.DEF_KEY_RESOURCE_TYPE, csv_resource_def)
            raise Exception(err_msg)

        # TRIGGER: Skip row if the trigger column does not equal trigger_value
        if self.DEF_KEY_TRIGGER_COLUMN in csv_resource_def:
            if csv_resource_def[self.DEF_KEY_TRIGGER_COLUMN] not in csv_row:
                return None
            if csv_row[csv_resource_def[self.DEF_KEY_TRIGGER_COLUMN]] != csv_resource_def[
                    self.DEF_KEY_TRIGGER_VALUE]:
                return None

        # SKIP_IF_EMPTY: Skip if all SKIP_IF_EMPTY columns have blank values
        is_skip_row = self.is_skip_row(csv_resource_def, csv_row)
        if is_skip_row:
            if self.verbose:
                # print 'SKIPPING: %s' % (csv_resource_def['definition_name'])
                pass
            return None

        # Either process batch of auto resources or build individual resource
        ocl_resource_type = csv_resource_def[self.DEF_KEY_RESOURCE_TYPE]
        if ocl_resource_type == OclCsvToJsonConverter.DEF_TYPE_AUTO_RESOURCE:
            auto_resource_def_template = csv_resource_def[
                OclCsvToJsonConverter.DEF_AUTO_RESOURCE_TEMPLATE]
            unique_auto_resource_indexes = OclCsvToJsonConverter.get_unique_csv_row_auto_indexes(
                index_prefix=auto_resource_def_template[self.DEF_KEY_AUTO_INDEX_PREFIX],
                index_postfix=auto_resource_def_template[self.DEF_KEY_AUTO_INDEX_POSTFIX],
                index_regex=auto_resource_def_template[self.DEF_KEY_AUTO_INDEX_REGEX],
                resource_def_template=auto_resource_def_template,
                csv_row=csv_row)
            ocl_resources = []
            for auto_index in unique_auto_resource_indexes:
                resource_def = OclCsvToJsonConverter.generate_resource_def_from_template(
                    auto_resource_index=auto_index,
                    index_prefix=auto_resource_def_template[self.DEF_KEY_AUTO_INDEX_PREFIX],
                    index_postfix=auto_resource_def_template[self.DEF_KEY_AUTO_INDEX_POSTFIX],
                    resource_def_template=auto_resource_def_template)
                ocl_resource = self.process_csv_row_with_definition(
                    csv_row, resource_def, attr=attr)
                if ocl_resource:
                    ocl_resources.append(ocl_resource)
            return ocl_resources
        return self.build_resource(csv_row, csv_resource_def, attr=attr)

    def is_skip_row(self, csv_resource_def, csv_row):
        """
        Determine if a skip row based on the DEF_KEY_SKIP_IF_EMPTY columns. Returns TRUE
        only if all columns are empty.
        TODO: Provide attribute to skip if ANY column is blank instead of ALL
        """
        is_skip_row = False
        if self.DEF_KEY_SKIP_IF_EMPTY in csv_resource_def and csv_resource_def[
                self.DEF_KEY_SKIP_IF_EMPTY]:
            has_non_empty_cell = False
            skip_columns = csv_resource_def[self.DEF_KEY_SKIP_IF_EMPTY]
            if not isinstance(skip_columns, list):
                skip_columns = [skip_columns]
            for skip_column in skip_columns:
                if skip_column in csv_row and csv_row[skip_column] != '':
                    has_non_empty_cell = True
                    break
            if not has_non_empty_cell:
                is_skip_row = True
        elif OclCsvToJsonConverter.DEF_KEY_SKIP_HANDLER in csv_resource_def:
            handler = getattr(self, csv_resource_def[OclCsvToJsonConverter.DEF_KEY_SKIP_HANDLER])
            if not handler:
                err_msg = "skip_handler '%s' is not defined" % csv_resource_def[
                    OclCsvToJsonConverter.DEF_KEY_SKIP_HANDLER]
                raise Exception(err_msg)
            is_skip_row = handler(csv_resource_def, csv_row)
        return is_skip_row

    def build_resource(self, csv_row, csv_resource_def, attr=None):
        """ Build an OCL resource """

        # Start building the resource
        ocl_resource_type = csv_resource_def[self.DEF_KEY_RESOURCE_TYPE]
        ocl_resource = {'type': ocl_resource_type}

        # Determine resource's ID and auto-replace invalid ID characters
        id_column = None
        if self.DEF_KEY_ID_COLUMN in csv_resource_def and csv_resource_def[self.DEF_KEY_ID_COLUMN]:
            id_column = csv_resource_def[self.DEF_KEY_ID_COLUMN]
            if id_column not in csv_row or not csv_row[id_column]:
                raise Exception('ID column %s not set or empty in row %s' % (id_column, csv_row))
            if ocl_resource_type in [
                    oclconstants.OclConstants.RESOURCE_TYPE_CONCEPT,
                    oclconstants.OclConstants.RESOURCE_TYPE_MAPPING]:
                ocl_resource['id'] = self.format_identifier(
                    csv_row[id_column], allow_underscore=True)
            else:
                ocl_resource['id'] = self.format_identifier(csv_row[id_column])

        # Set core fields, eg concept_class, datatype, external_id, etc.
        if self.DEF_CORE_FIELDS in csv_resource_def and csv_resource_def[self.DEF_CORE_FIELDS]:
            ocl_resource.update(self.process_resource_def(
                csv_row, csv_resource_def[self.DEF_CORE_FIELDS]))

        # Build mapping to/from concept URLs if not provided
        if ocl_resource_type == oclconstants.OclConstants.RESOURCE_TYPE_MAPPING:
            # Determine whether mapping target is internal or external
            map_target = ocl_resource.pop(
                oclconstants.OclConstants.MAPPING_TARGET,
                oclconstants.OclConstants.MAPPING_TARGET_INTERNAL)
            if map_target not in oclconstants.OclConstants.MAPPING_TARGETS:
                map_target = oclconstants.OclConstants.MAPPING_TARGET_INTERNAL

            # Build from_concept_url if not provided
            ocl_resource[oclconstants.OclConstants.MAPPING_FROM_CONCEPT_URL] = OclCsvToJsonConverter.get_concept_url(
                concept_url=ocl_resource.pop(oclconstants.OclConstants.MAPPING_FROM_CONCEPT_URL, ''),
                owner_id=ocl_resource.pop(oclconstants.OclConstants.MAPPING_FROM_CONCEPT_OWNER_ID, ''),
                owner_type=ocl_resource.pop(
                    oclconstants.OclConstants.MAPPING_FROM_CONCEPT_OWNER_TYPE,
                    oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION),
                source=ocl_resource.pop(oclconstants.OclConstants.MAPPING_FROM_SOURCE_ID, ''),
                concept_id=ocl_resource.pop(oclconstants.OclConstants.MAPPING_FROM_CONCEPT_ID, ''))

            # Handle to_concept_url based on Internal or External map target
            if map_target == oclconstants.OclConstants.MAPPING_TARGET_INTERNAL:
                # JSON internal mapping requires map_type, from_concept_url, and to_concept_url
                ocl_resource[oclconstants.OclConstants.MAPPING_TO_CONCEPT_URL] = OclCsvToJsonConverter.get_concept_url(
                    concept_url=ocl_resource.pop(oclconstants.OclConstants.MAPPING_TO_CONCEPT_URL, ''),
                    owner_id=ocl_resource.pop(oclconstants.OclConstants.MAPPING_TO_CONCEPT_OWNER_ID, ''),
                    owner_type=ocl_resource.pop(
                        oclconstants.OclConstants.MAPPING_TO_CONCEPT_OWNER_TYPE,
                        oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION),
                    source=ocl_resource.pop(oclconstants.OclConstants.MAPPING_TO_SOURCE_ID, ''),
                    concept_id=ocl_resource.pop(oclconstants.OclConstants.MAPPING_TO_CONCEPT_ID, ''))
            elif map_target == oclconstants.OclConstants.MAPPING_TARGET_EXTERNAL:
                # JSON external mapping needs map_type, from_concept_url, to_source_url and
                # to_concept_code. to_concept_name is optional.
                if oclconstants.OclConstants.MAPPING_TO_CONCEPT_URL in ocl_resource and ocl_resource[oclconstants.OclConstants.MAPPING_TO_CONCEPT_URL]:
                    err_msg = ('External mapping must not have a '
                               '"to_concept_url": %s' % ocl_resource[oclconstants.OclConstants.MAPPING_TO_CONCEPT_URL])
                    raise Exception(err_msg)
                ocl_resource[oclconstants.OclConstants.MAPPING_TO_SOURCE_URL] = OclCsvToJsonConverter._get_external_mapping_to_source_url(
                    to_source_url=ocl_resource.pop(oclconstants.OclConstants.MAPPING_TO_SOURCE_URL, ''),
                    to_concept_owner_id=ocl_resource.pop(oclconstants.OclConstants.MAPPING_TO_CONCEPT_OWNER_ID, ''),
                    to_concept_owner_type=ocl_resource.pop(
                        oclconstants.OclConstants.MAPPING_TO_CONCEPT_OWNER_TYPE,
                        oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION),
                    to_concept_source=ocl_resource.pop(oclconstants.OclConstants.MAPPING_TO_SOURCE_ID, ''))

        # Set sub-resources, eg concept names/descriptions
        if self.DEF_SUB_RESOURCES in csv_resource_def and csv_resource_def[self.DEF_SUB_RESOURCES]:
            for group_name in csv_resource_def[self.DEF_SUB_RESOURCES]:  # eg "names","descriptions"
                ocl_resource[group_name] = []
                for dict_def in csv_resource_def[self.DEF_SUB_RESOURCES][group_name]:
                    ocl_sub_resource = self.process_resource_def(csv_row, dict_def)
                    if ocl_sub_resource:
                        ocl_resource[group_name].append(ocl_sub_resource)

        # Key value pairs, eg custom attributes
        if self.DEF_KEY_VALUE_PAIRS in csv_resource_def and csv_resource_def[
                self.DEF_KEY_VALUE_PAIRS]:
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
                            err_msg = ('key_column "%s" must be non-empty in CSV within '
                                       'key_value_pair: %s' % (kvp_def['key_column'], kvp_def))
                            raise Exception(err_msg)
                    else:
                        err_msg = ('Expected "key" or "key_column" key in key_value_pair '
                                   'definition, but neither found: %s' % kvp_def)
                        raise Exception(err_msg)

                    # Value
                    if 'value' in kvp_def:
                        value = kvp_def['value']
                    elif 'value_column' in kvp_def and kvp_def['value_column']:
                        if kvp_def['value_column'] in csv_row:
                            value = csv_row[kvp_def['value_column']]
                        else:
                            err_msg = ('value_column "%s" does not exist in CSV for '
                                       'key_value_pair: %s' % (kvp_def['value_column'], kvp_def))
                            raise Exception(err_msg)
                    else:
                        err_msg = ('Expected "value" or "value_column" key in key_value_pair '
                                   'definition, but neither found: %s' % kvp_def)
                        raise Exception(err_msg)

                    # Set the key-value pair
                    if key and (value or ('omit_if_empty_value' in kvp_def and not kvp_def[
                            'omit_if_empty_value'])):
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

        # Optionally display debug info
        if self.verbose:
            if self._current_row_num:
                six.print_(('[Row %s of %s] %s' % (self._current_row_num, self._total_rows,
                                             json.dumps(ocl_resource))))
            else:
                six.print_((json.dumps(ocl_resource)))

        return ocl_resource

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
        attr:my-attribute,attr_key[1],attr_value[1],attr_key[27],attr_value[27]
        my-attribute value,This row's key,"This row's key",Another key,Another value
        """
        extra_attributes = {}
        keyless_values = {}
        valueless_keys = {}

        # Determine whether to omit blank values (default = True)
        omit_if_empty_value = True
        if 'omit_if_empty_value' in auto_attributes_def and not auto_attributes_def[
                'omit_if_empty_value']:
            omit_if_empty_value = False

        # Prepare search strings
        standard_needle = '%s%s' % (
            auto_attributes_def['standard_column_prefix'], auto_attributes_def['separator'])
        key_needle = '^%s%s(%s)%s$' % (
            auto_attributes_def['key_column_prefix'],
            re.escape(auto_attributes_def[self.DEF_KEY_AUTO_INDEX_PREFIX]),
            auto_attributes_def[self.DEF_KEY_AUTO_INDEX_REGEX],
            re.escape(auto_attributes_def[self.DEF_KEY_AUTO_INDEX_POSTFIX]))
        value_needle = '^%s%s(%s)%s$' % (
            auto_attributes_def['value_column_prefix'],
            re.escape(auto_attributes_def[self.DEF_KEY_AUTO_INDEX_PREFIX]),
            auto_attributes_def[self.DEF_KEY_AUTO_INDEX_REGEX],
            re.escape(auto_attributes_def[self.DEF_KEY_AUTO_INDEX_POSTFIX]))

        data_types = ['bool', 'str', 'int', 'float', 'list', 'json']

        # Process CSV columns
        for column_name in csv_row:
            data_type = 'str'
            if column_name.count(':') == 2:
                suffix_part = column_name.split(':')[2].strip()
                if suffix_part in data_types:
                    data_type = suffix_part
            if column_name[:len(standard_needle)] == standard_needle:
                # Check if standard attr (e.g. attr:my-custom-attr)
                if not omit_if_empty_value or (omit_if_empty_value and csv_row[column_name]):
                    key_name = column_name[len(standard_needle):]
                    if key_name.endswith(":" + data_type):
                        key_name = key_name.replace(":" + data_type, "")
                    extra_attributes[key_name] = self.do_datatype_conversion(csv_row[column_name], data_type)
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
        """
        Get a list of auto-generated sub_resources for the CSV row based on the specified definition
        """
        sub_resources = []
        if 'sub_resource_type' not in auto_sub_resources_def:
            raise Exception('Missing required "sub_resource_type" in auto_sub_resources definition')

        # Add primary sub resource (if defined)
        if 'primary_sub_resource' in auto_sub_resources_def:
            sub_resource = self.process_resource_def(
                csv_row, auto_sub_resources_def['primary_sub_resource'])
            is_skip_row = self.is_skip_row(auto_sub_resources_def, csv_row)
            if sub_resource and not is_skip_row:
                sub_resources.append(sub_resource)

        # Add auto sub resources
        if 'auto_sub_resources' in auto_sub_resources_def:
            unique_auto_resource_indexes = OclCsvToJsonConverter.get_unique_csv_row_auto_indexes(
                index_prefix=auto_sub_resources_def[self.DEF_KEY_AUTO_INDEX_PREFIX],
                index_postfix=auto_sub_resources_def[self.DEF_KEY_AUTO_INDEX_POSTFIX],
                index_regex=auto_sub_resources_def[self.DEF_KEY_AUTO_INDEX_REGEX],
                resource_def_template=auto_sub_resources_def['auto_sub_resources'],
                csv_row=csv_row)
            for auto_resource_index in unique_auto_resource_indexes:
                sub_resource_def = OclCsvToJsonConverter.generate_resource_def_from_template(
                    index_prefix=auto_sub_resources_def[self.DEF_KEY_AUTO_INDEX_PREFIX],
                    index_postfix=auto_sub_resources_def[self.DEF_KEY_AUTO_INDEX_POSTFIX],
                    auto_resource_index=auto_resource_index,
                    resource_def_template=auto_sub_resources_def['auto_sub_resources'])
                sub_resource = self.process_resource_def(csv_row, sub_resource_def)
                is_skip_row = self.is_skip_row(auto_sub_resources_def, sub_resource)
                if sub_resource and not is_skip_row:
                    sub_resources.append(sub_resource)

        return sub_resources

    @staticmethod
    def replace_auto_field(prefix_field_to_replace, new_field_name, index_prefix, index_postfix,
                           auto_resource_index, resource_def_template):
        """
        Replaces prefix fields (eg. 'skip_if_empty_column_prefix': 'map_to_concept_id') with an
        indexed field (eg. 'skip_if_empty_column': 'map_to_concept_id[07]')
        """
        if prefix_field_to_replace in resource_def_template:
            field_prefixes = resource_def_template.pop(prefix_field_to_replace)
            new_field_prefixes = []
            if not isinstance(field_prefixes, list):
                field_prefixes = [field_prefixes]
            for field_prefix in field_prefixes:  # eg. field_prefix => 'map_to_concept_id'
                auto_field_name = '%s%s%s%s' % (
                    field_prefix, index_prefix, auto_resource_index, index_postfix)
                new_field_prefixes.append(auto_field_name)
            if len(new_field_prefixes) > 1:
                resource_def_template[new_field_name] = new_field_prefixes
            elif len(new_field_prefixes) == 1:
                resource_def_template[new_field_name] = new_field_prefixes[0]

    @staticmethod
    def _get_external_mapping_to_source_url(to_source_url='', to_concept_owner_id='',
                                            to_concept_owner_type='', to_concept_source=''):
        if to_source_url:
            return to_source_url
        return oclconstants.OclConstants.get_repository_url(
            owner_id=to_concept_owner_id, repository_id=to_concept_source,
            owner_type=to_concept_owner_type, include_trailing_slash=True)

    @staticmethod
    def generate_resource_def_from_template(index_prefix, index_postfix, auto_resource_index,
                                            resource_def_template):
        """
        Get a resource definition for the specified resource definition template and auto index
        """
        if isinstance(resource_def_template, dict):
            resource_def_template = resource_def_template.copy()
            # Replace the resource definition prefix fields
            for prefix_field_to_replace in OclCsvToJsonConverter.AUTO_REPLACEMENT_FIELDS:
                OclStandardCsvToJsonConverter.replace_auto_field(
                    prefix_field_to_replace=prefix_field_to_replace,
                    new_field_name=OclCsvToJsonConverter.AUTO_REPLACEMENT_FIELDS[
                        prefix_field_to_replace],
                    index_prefix=index_prefix, index_postfix=index_postfix,
                    auto_resource_index=auto_resource_index,
                    resource_def_template=resource_def_template)
            # Replace the field definition prefix fields
            for resource_field_type in OclCsvToJsonConverter.DEF_RESOURCE_FIELD_TYPES:
                if resource_field_type in resource_def_template:
                    resource_def_template[resource_field_type] = OclCsvToJsonConverter.generate_resource_def_from_template(
                        index_prefix=index_prefix, index_postfix=index_postfix,
                        auto_resource_index=auto_resource_index,
                        resource_def_template=resource_def_template[resource_field_type])
            return resource_def_template
        elif isinstance(resource_def_template, list):
            new_field_defs = []
            for current_field_def in resource_def_template:
                new_field_def = current_field_def.copy()
                if 'column_prefix' in new_field_def:
                    column_prefix = new_field_def.pop('column_prefix')
                    new_column_name = '%s%s%s%s' % (
                        column_prefix, index_prefix, auto_resource_index, index_postfix)
                    if 'column' in new_field_def and new_field_def['column']:
                        if not isinstance(new_field_def['column'], list):
                            new_field_def['column'] = [new_field_def['column']]
                        # Add new column to beginning of list so that it is searched first
                        new_field_def['column'].insert(0, new_column_name)
                    else:
                        new_field_def['column'] = new_column_name
                new_field_defs.append(new_field_def)
            return new_field_defs
        else:
            err_msg = ('Invalid type "%s" for resource_def_template. '
                       'Expected <list> or <dict>.') % str(type(resource_def_template))
            raise Exception(err_msg)

    @staticmethod
    def get_unique_csv_row_auto_indexes(index_prefix, index_postfix, index_regex,
                                        resource_def_template, csv_row):
        """
        Return list of unique auto indexes in the CSV row as defined by the resource_def_template.
        Note that resource_def_template may be either a full resource_def (dict) or a
        sub_resource_def (list).
        """
        unique_auto_resource_indexes = []
        if isinstance(resource_def_template, dict):
            for resource_field_type in OclCsvToJsonConverter.DEF_RESOURCE_FIELD_TYPES:
                if resource_field_type in resource_def_template:
                    unique_auto_resource_indexes += OclCsvToJsonConverter.get_unique_csv_row_auto_indexes(
                        index_prefix=index_prefix, index_postfix=index_postfix,
                        index_regex=index_regex,
                        resource_def_template=resource_def_template[resource_field_type],
                        csv_row=csv_row)
            # Dedup the list so that each auto-index only appears once
            unique_auto_resource_indexes = [i for n, i in enumerate(
                unique_auto_resource_indexes) if i not in unique_auto_resource_indexes[n + 1:]]
        elif isinstance(resource_def_template, list):
            for column_name in csv_row:
                for field_def in resource_def_template:
                    if 'column_prefix' not in field_def:
                        continue
                    if column_name[:len(field_def['column_prefix'])] == field_def['column_prefix']:
                        search_exp = r'^%s%s(%s)%s$' % (
                            field_def['column_prefix'], re.escape(index_prefix),
                            index_regex, re.escape(index_postfix))
                        regex_match = re.search(search_exp, column_name)
                        if regex_match:
                            index = regex_match.group(1)
                            if index and index not in unique_auto_resource_indexes:
                                unique_auto_resource_indexes.append(index)
        else:
            err_msg = ('Invalid type "%s" for resource_def_template. '
                       'Expected <list> or <dict>.') % str(type(resource_def_template))
            raise Exception(err_msg)
        return unique_auto_resource_indexes

    def process_resource_def(self, csv_row, resource_def):
        """
        Returns a resource by processing a resource definition. A resource definition is a
        list of field definitions.
        """
        new_resource = {}
        for field_def in resource_def:
            value = self.process_field_def(csv_row, field_def)
            if value is not None:
                new_resource[field_def[self.DEF_KEY_RESOURCE_FIELD]] = value
        return new_resource

    def process_field_def(self, csv_row, field_def):
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
        both a 'csv_to_json_processor' and 'data_column' keys. If 'column' is a list, then
        the first non-empty column in the list that is present in the CSV row is used.
        Set 'skip_empty_value' to False to not skip non-empty values.
        Optional keys include 'required', 'default', and 'datatype'
        """
        if 'column' in field_def:
            columns = field_def['column']
            if not isinstance(field_def['column'], list):
                columns = [columns]
            skip_empty_value = True

            if 'skip_empty_value' in field_def:
                skip_empty_value = bool(skip_empty_value)
            for column in columns:
                if column in csv_row and (
                        skip_empty_value and csv_row[column] or not skip_empty_value):
                    if 'datatype' in field_def:
                        return self.do_datatype_conversion(csv_row[column], field_def['datatype'])
                    return csv_row[column]

            # No value found from 'column', so apply default/required
            if 'default' in field_def:
                # Return 'default' if 'column' is not in CSV row
                return field_def['default']
            elif 'required' in field_def and field_def['required']:
                err_msg = 'Missing required column %s in CSV row: %s' % (
                    field_def['column'], csv_row)
                raise Exception(err_msg)

            # Return None if no value found and not required
            return None
        elif 'value' in field_def:
            # Just return whatever is in the 'value' definition
            return field_def['value']
        elif 'csv_to_json_processor' in field_def and field_def['csv_to_json_processor']:
            # Use a custom method to generate the value
            method_to_call = getattr(self, field_def['csv_to_json_processor'])
            return method_to_call(csv_row, field_def)
        else:
            err_msg = ('Expected "column", "value", or "csv_to_json_processor" key in field'
                       'definition, but none found: %s' % field_def)
            raise Exception(err_msg)

    def do_datatype_conversion(self, value, datatype):
        """
        Convert the value to the specified datatype, where datatype is a string of the name of the
        desired datatype (e.g. datatype="bool", "int", "float").
        """
        if datatype == 'bool':
            return bool(util.strtobool(str(value)))
        elif datatype == 'int':
            return int(value)
        elif datatype == 'float':
            return float(value)
        elif datatype == 'list':
            return [v.strip() for v in value.strip('][').split(',')]
        elif datatype == 'json':
            try:
                return json.loads(value)
            except:
                return value
        return value

    def process_auto_concept_reference(self, csv_row, field_def):
        """ Returns a concept reference expression, e.g. {'expressions': [<concept_url>]} """
        # TODO: the concept url variables are not stored in the field_def or csv_row, they're evaluated
        concept_url = OclCsvToJsonConverter.get_concept_url(
            owner_id=field_def.pop('ref_target_owner'),
            owner_type=field_def.pop('ref_target_owner_type'),
            source=field_def.pop('ref_target_source'),
            concept_id=field_def.pop('ref_target_concept_id'))
        if concept_url:
            return {'expressions': [concept_url]}
        return None

    def process_reference(self, csv_row, field_def):
        """ (DEPRECATED) Processes a reference in the CSV row """
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
        if self.allow_special_characters:
            return unformatted_id

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

    @staticmethod
    def get_concept_url(concept_url='', owner_id='', owner_type='', source='', concept_id=''):
        """ Returns a concept URL """
        if concept_url:
            return concept_url
        return '%s/concepts/%s/' % (oclconstants.OclConstants.get_repository_url(
            owner_id=owner_id, owner_type=owner_type, repository_id=source,
            repository_type=oclconstants.OclConstants.RESOURCE_TYPE_SOURCE), concept_id)


class OclStandardCsvToJsonConverter(OclCsvToJsonConverter):
    """ Standard CSV to OCL-formatted JSON converter """

    # Standard auto index constants
    AUTO_INDEX_STANDARD_PREFIX = '['
    AUTO_INDEX_STANDARD_POSTFIX = ']'
    AUTO_INDEX_STANDARD_REGEX = '[a-zA-Z0-9\\-_]+'

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
                'index_prefix': AUTO_INDEX_STANDARD_PREFIX,
                'index_postfix': AUTO_INDEX_STANDARD_POSTFIX,
                'index_regex': AUTO_INDEX_STANDARD_REGEX,
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
                {'resource_field': 'short_code', 'column': ['short_code', 'id'], 'required': False},
                {'resource_field': 'name', 'column': 'name'},
                {'resource_field': 'full_name', 'column': ['full_name', 'name'], 'required': False},
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
                'index_prefix': AUTO_INDEX_STANDARD_PREFIX,
                'index_postfix': AUTO_INDEX_STANDARD_POSTFIX,
                'index_regex': AUTO_INDEX_STANDARD_REGEX,
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
                {'resource_field': 'short_code', 'column': ['short_code', 'id'], 'required': False},
                {'resource_field': 'name', 'column': 'name'},
                {'resource_field': 'full_name', 'column': ['full_name', 'name'], 'required': False},
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
                'index_prefix': AUTO_INDEX_STANDARD_PREFIX,
                'index_postfix': AUTO_INDEX_STANDARD_POSTFIX,
                'index_regex': AUTO_INDEX_STANDARD_REGEX,
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
                {'resource_field': 'retired', 'column': 'retired', 'required': False, 'datatype': 'bool'},
                {'resource_field': 'external_id', 'column': 'external_id', 'required': False},
                {'resource_field': 'concept_class', 'column': 'concept_class'},
                {'resource_field': 'parent_concept_urls', 'column': 'parent_concept_urls',
                 'default': None, 'datatype': 'list'},
                {'resource_field': 'datatype', 'column': 'datatype', 'default': 'None'},
                {'resource_field': 'owner', 'column': 'owner_id'},
                {'resource_field': 'update_comment', 'column': 'update_comment'},
                {'resource_field': 'owner_type', 'column': 'owner_type',
                 'default': oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION},
                {'resource_field': 'source', 'column': 'source'},
            ],
            OclCsvToJsonConverter.DEF_AUTO_CONCEPT_NAMES: {
                'sub_resource_type': 'names',
                'skip_if_empty_column': 'name',
                'primary_sub_resource': [
                    {'resource_field': 'name', 'column': 'name'},
                    {'resource_field': 'locale', 'column': 'name_locale', 'default': 'en'},
                    {'resource_field': 'locale_preferred', 'column': 'name_locale_preferred',
                     'default': True},
                    {'resource_field': 'name_type', 'column': 'name_type',
                     'default': 'Fully Specified'},
                    {'resource_field': 'external_id', 'column': 'name_external_id',
                     'required': False},
                ],
                'index_prefix': AUTO_INDEX_STANDARD_PREFIX,
                'index_postfix': AUTO_INDEX_STANDARD_POSTFIX,
                'index_regex': AUTO_INDEX_STANDARD_REGEX,
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
                'skip_if_empty_column': 'description',
                'primary_sub_resource': [
                    {'resource_field': 'description', 'column': 'description'},
                    {'resource_field': 'locale', 'column': 'description_locale', 'default': 'en'},
                    {'resource_field': 'locale_preferred', 'column': 'description_locale_preferred',
                     'required': False},
                    {'resource_field': 'description_type', 'column': 'description_type',
                     'required': False},
                    {'resource_field': 'external_id', 'column': 'description_external_id',
                     'required': False},
                ],
                'index_prefix': AUTO_INDEX_STANDARD_PREFIX,
                'index_postfix': AUTO_INDEX_STANDARD_POSTFIX,
                'index_regex': AUTO_INDEX_STANDARD_REGEX,
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
                'index_prefix': AUTO_INDEX_STANDARD_PREFIX,
                'index_postfix': AUTO_INDEX_STANDARD_POSTFIX,
                'index_regex': AUTO_INDEX_STANDARD_REGEX,
            }
        },
        {
            'definition_name': 'Generic Auto Concept Internal Mappings',
            'is_active': True,
            'resource_type': OclCsvToJsonConverter.DEF_TYPE_AUTO_RESOURCE,
            '__trigger_column': 'resource_type',
            '__trigger_value': oclconstants.OclConstants.RESOURCE_TYPE_CONCEPT,
            OclCsvToJsonConverter.DEF_AUTO_RESOURCE_TEMPLATE: {
                'definition_name': 'Generic Concept Internal Mapping',
                'resource_type': oclconstants.OclConstants.RESOURCE_TYPE_MAPPING,
                'index_prefix': AUTO_INDEX_STANDARD_PREFIX,
                'index_postfix': AUTO_INDEX_STANDARD_POSTFIX,
                'index_regex': AUTO_INDEX_STANDARD_REGEX,
                'skip_if_empty_column_prefix': ['map_to_concept_id', 'map_to_concept_url'],
                OclCsvToJsonConverter.DEF_CORE_FIELDS: [
                    {'resource_field': 'retired', 'column': 'retired', 'required': False, 'datatype': 'bool'},
                    {'resource_field': 'map_target', 'column_prefix': 'map_target',
                     'default': oclconstants.OclConstants.MAPPING_TARGET_INTERNAL},
                    {'resource_field': 'map_type', 'column_prefix': 'map_type',
                     'default': 'Same As'},
                    {'resource_field': 'update_comment', 'column': 'update_comment'},
                    {'resource_field': 'external_id', 'column_prefix': 'map_external_id',
                     'required': False},
                    {'resource_field': 'from_concept_url', 'column_prefix': 'map_from_concept_url',
                     'required': False},
                    {'resource_field': oclconstants.OclConstants.MAPPING_FROM_CONCEPT_ID,
                     'column_prefix': 'map_from_concept_id',
                     'column': 'id', 'required': False},
                    {'resource_field': 'from_concept_owner_id', 'column': 'owner_id',
                     'column_prefix': 'map_from_concept_owner_id', 'required': False},
                    {'resource_field': 'from_concept_owner_type', 'column': 'owner_type',
                     'column_prefix': 'map_from_concept_owner_type',
                     'default': oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION},
                    {'resource_field': 'from_concept_source', 'column': 'source',
                     'column_prefix': 'map_from_concept_source', 'required': False},
                    {'resource_field': 'to_concept_url', 'column_prefix': 'map_to_concept_url',
                     'required': False},
                    {'resource_field': 'to_concept_code', 'column_prefix': 'map_to_concept_id',
                     'required': False},
                    {'resource_field': 'to_concept_name', 'column_prefix': 'map_to_concept_name',
                     'required': False},
                    {'resource_field': 'to_concept_owner_id', 'column': 'owner_id',
                     'column_prefix': 'map_to_concept_owner_id', 'required': False},
                    {'resource_field': 'to_concept_owner_type', 'column': 'owner_type',
                     'column_prefix': 'map_to_concept_owner_type',
                     'default': oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION},
                    {'resource_field': 'to_concept_source', 'column': 'source',
                     'column_prefix': 'map_to_concept_source', 'required': False},
                    {'resource_field': 'owner', 'column_prefix': 'map_owner_id',
                     'column': 'owner_id'},
                    {'resource_field': 'owner_type', 'column_prefix': 'map_owner_type',
                     'column': 'owner_type',
                     'default': oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION},
                    {'resource_field': 'source', 'column_prefix': 'map_source', 'column': 'source'},
                ],
            },
        },
        {
            'definition_name': 'Generic Auto Concept External Mappings',
            'is_active': True,
            'resource_type': OclCsvToJsonConverter.DEF_TYPE_AUTO_RESOURCE,
            '__trigger_column': 'resource_type',
            '__trigger_value': oclconstants.OclConstants.RESOURCE_TYPE_CONCEPT,
            OclCsvToJsonConverter.DEF_AUTO_RESOURCE_TEMPLATE: {
                'definition_name': 'Generic Concept External Mapping',
                'resource_type': oclconstants.OclConstants.RESOURCE_TYPE_MAPPING,
                'index_prefix': AUTO_INDEX_STANDARD_PREFIX,
                'index_postfix': AUTO_INDEX_STANDARD_POSTFIX,
                'index_regex': AUTO_INDEX_STANDARD_REGEX,
                'skip_if_empty_column_prefix': ['extmap_to_concept_id', 'extmap_to_concept_url'],
                OclCsvToJsonConverter.DEF_CORE_FIELDS: [
                    {'resource_field': 'retired', 'column': 'retired', 'required': False, 'datatype': 'bool'},
                    {'resource_field': 'map_target', 'column_prefix': 'extmap_target',
                     'default': oclconstants.OclConstants.MAPPING_TARGET_EXTERNAL},
                    {'resource_field': 'map_type', 'column_prefix': 'extmap_type',
                     'default': 'Same As'},
                    {'resource_field': 'update_comment', 'column': 'update_comment'},
                    {'resource_field': 'external_id', 'column_prefix': 'extmap_external_id',
                     'required': False},
                    {'resource_field': 'from_concept_url', 'required': False,
                     'column_prefix': 'extmap_from_concept_url'},
                    {'resource_field': oclconstants.OclConstants.MAPPING_FROM_CONCEPT_ID,
                     'column_prefix': 'extmap_from_concept_id',
                     'column': 'id', 'required': False},
                    {'resource_field': 'from_concept_owner_id', 'column': 'owner_id',
                     'column_prefix': 'extmap_from_concept_owner_id', 'required': False},
                    {'resource_field': 'from_concept_owner_type', 'column': 'owner_type',
                     'column_prefix': 'extmap_from_concept_owner_type',
                     'default': oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION},
                    {'resource_field': 'from_concept_source', 'column': 'source',
                     'column_prefix': 'extmap_from_concept_source', 'required': False},
                    {'resource_field': 'to_concept_url', 'column_prefix': 'extmap_to_concept_url',
                     'required': False},
                    {'resource_field': 'to_concept_code', 'column_prefix': 'extmap_to_concept_id',
                     'required': False},
                    {'resource_field': 'to_concept_name', 'column_prefix': 'extmap_to_concept_name',
                     'required': False},
                    {'resource_field': 'to_concept_owner_id', 'column': 'owner_id',
                     'column_prefix': 'extmap_to_concept_owner_id', 'required': False},
                    {'resource_field': 'to_concept_owner_type', 'column': 'owner_type',
                     'column_prefix': 'extmap_to_concept_owner_type',
                     'default': oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION},
                    {'resource_field': 'to_concept_source', 'column': 'source',
                     'column_prefix': 'extmap_to_concept_source', 'required': False},
                    {'resource_field': 'to_source_url', 'column_prefix': 'extmap_to_source_url',
                     'required': False},
                    {'resource_field': 'owner', 'column_prefix': 'extmap_owner_id',
                     'column': 'owner_id'},
                    {'resource_field': 'owner_type', 'column_prefix': 'extmap_owner_type',
                     'column': 'owner_type',
                     'default': oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION},
                    {'resource_field': 'source', 'column_prefix': 'extmap_source',
                     'column': 'source'},
                ],
            },
        },
        {
            'definition_name': 'Generic Auto Concept Reference',
            'is_active': False,
            'resource_type': OclCsvToJsonConverter.DEF_TYPE_AUTO_RESOURCE,
            '__trigger_column': 'resource_type',
            '__trigger_value': oclconstants.OclConstants.RESOURCE_TYPE_CONCEPT,
            OclCsvToJsonConverter.DEF_AUTO_RESOURCE_TEMPLATE: {
                'definition_name': 'Generic Concept Reference',
                'resource_type': oclconstants.OclConstants.RESOURCE_TYPE_REFERENCE,
                'index_prefix': AUTO_INDEX_STANDARD_PREFIX,
                'index_postfix': AUTO_INDEX_STANDARD_POSTFIX,
                'index_regex': AUTO_INDEX_STANDARD_REGEX,
                'skip_if_empty_column_prefix': ['ref_collection'],
                OclCsvToJsonConverter.DEF_CORE_FIELDS: [
                    {'resource_field': 'owner', 'column_prefix': 'ref_owner_id',
                     'column': 'owner_id'},
                    {'resource_field': 'owner_type', 'column_prefix': 'ref_owner_type',
                     'column': 'owner_type',
                     'default': oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION},
                    {'resource_field': 'collection', 'column_prefix': 'ref_collection'},
                    {'resource_field': 'ref_type', 'column_name': 'ref_type',
                     'default': oclconstants.OclConstants.RESOURCE_TYPE_CONCEPT},
                    {'resource_field': 'ref_target_owner_id',
                     'column_prefix': 'ref_target_owner_id', 'column': 'owner_id'},
                    {'resource_field': 'ref_target_owner_type',
                     'column_prefix': 'ref_target_owner_type', 'column': 'owner_type',
                     'default': oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION},
                    {'resource_field': 'ref_target_source', 'column_prefix': 'ref_target_source',
                     'column': 'source'},
                    {'resource_field': 'ref_target_concept_id', 'column': 'id'},
                    {'resource_field': 'data',
                     'csv_to_json_processor': 'process_auto_concept_reference'},
                ]
            }
        },
        {
            'definition_name': 'Generic Standalone Internal Mapping',
            'is_active': True,
            'resource_type': oclconstants.OclConstants.RESOURCE_TYPE_MAPPING,
            '__trigger_column': 'resource_type',
            '__trigger_value': oclconstants.OclConstants.RESOURCE_TYPE_MAPPING,
            'skip_if_empty_column': ['map_to_concept_id', 'to_concept_id',
                                     'map_to_concept_url', 'to_concept_url'],
            OclCsvToJsonConverter.DEF_CORE_FIELDS: [
                {'resource_field': 'retired', 'column': 'retired', 'required': False, 'datatype': 'bool'},
                {'resource_field': 'map_target', 'column': 'map_target',
                 'default': oclconstants.OclConstants.MAPPING_TARGET_INTERNAL},
                {'resource_field': 'map_type', 'column': 'map_type', 'default': 'Same As'},
                {'resource_field': 'update_comment', 'column': 'update_comment'},
                {'resource_field': 'external_id', 'column': 'external_id',
                 'required': False},
                {'resource_field': 'from_concept_url', 'required': False,
                 'column': ['map_from_concept_url', 'from_concept_url']},
                {'resource_field': oclconstants.OclConstants.MAPPING_FROM_CONCEPT_ID,
                 'column': ['map_from_concept_id', 'from_concept_id', 'from_concept_code'],
                 'required': False},
                {'resource_field': 'from_concept_owner_id', 'required': False,
                 'column': ['map_from_concept_owner_id', 'from_concept_owner_id', 'owner_id']},
                {'resource_field': 'from_concept_owner_type',
                 'column': ['map_from_concept_owner_type', 'from_concept_owner_type', 'owner_type'],
                 'default': oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION},
                {'resource_field': 'from_concept_source', 'required': False,
                 'column': ['map_from_concept_source', 'from_concept_source', 'source']},
                {'resource_field': 'to_concept_url', 'required': False,
                 'column': ['map_to_concept_url', 'to_concept_url']},
                {'resource_field': 'to_concept_code', 'required': False,
                 'column': ['map_to_concept_id', 'to_concept_id', 'to_concept_code']},
                {'resource_field': 'to_concept_name', 'required': False,
                 'column': ['map_to_concept_name', 'to_concept_name']},
                {'resource_field': 'to_concept_owner_id', 'required': False,
                 'column': ['map_to_concept_owner_id', 'to_concept_owner_id', 'owner_id']},
                {'resource_field': 'to_concept_owner_type',
                 'column': ['map_to_concept_owner_type', 'to_concept_owner_type', 'owner_type'],
                 'default': oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION},
                {'resource_field': 'to_concept_source', 'required': False,
                 'column': ['map_to_concept_source', 'to_concept_source', 'source']},
                {'resource_field': 'owner', 'column': ['map_owner_id', 'owner_id']},
                {'resource_field': 'owner_type', 'column': ['map_owner_type', 'owner_type'],
                 'default': oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION},
                {'resource_field': 'source', 'column': ['map_source', 'source']},
            ]
        },
        {
            'definition_name': 'Generic Standalone External Mapping',
            'is_active': True,
            'resource_type': oclconstants.OclConstants.RESOURCE_TYPE_MAPPING,
            '__trigger_column': 'resource_type',
            '__trigger_value': 'External Mapping',  # Note deviation from RESOURCE_TYPE constants
            'skip_if_empty_column': ['map_to_concept_id', 'to_concept_id',
                                     'map_to_concept_url', 'to_concept_url'],
            OclCsvToJsonConverter.DEF_CORE_FIELDS: [
                {'resource_field': 'retired', 'column': 'retired', 'required': False, 'datatype': 'bool'},
                {'resource_field': 'map_target', 'column': 'map_target',
                 'default': oclconstants.OclConstants.MAPPING_TARGET_EXTERNAL},
                {'resource_field': 'map_type', 'column': 'map_type', 'default': 'Same As'},
                {'resource_field': 'update_comment', 'column': 'update_comment'},
                {'resource_field': 'external_id', 'column': 'external_id',
                 'required': False},
                {'resource_field': 'from_concept_url', 'required': False,
                 'column': ['map_from_concept_url', 'from_concept_url']},
                {'resource_field': oclconstants.OclConstants.MAPPING_FROM_CONCEPT_ID,
                 'column': ['map_from_concept_id', 'from_concept_id', 'from_concept_code'],
                 'required': False},
                {'resource_field': 'from_concept_owner_id', 'required': False,
                 'column': ['map_from_concept_owner_id', 'from_concept_owner_id', 'owner_id']},
                {'resource_field': 'from_concept_owner_type',
                 'column': ['map_from_concept_owner_type', 'from_concept_owner_type', 'owner_type'],
                 'default': oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION},
                {'resource_field': 'from_concept_source', 'required': False,
                 'column': ['map_from_concept_source', 'from_concept_source', 'source']},
                {'resource_field': 'to_concept_code', 'required': False,
                 'column': ['map_to_concept_id', 'to_concept_id', 'to_concept_code']},
                {'resource_field': 'to_concept_name', 'required': False,
                 'column': ['map_to_concept_name', 'to_concept_name']},
                {'resource_field': 'to_concept_owner_id', 'required': False,
                 'column': ['map_to_concept_owner_id', 'to_concept_owner_id', 'owner_id']},
                {'resource_field': 'to_concept_owner_type',
                 'column': ['map_to_concept_owner_type', 'to_concept_owner_type', 'owner_type'],
                 'default': oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION},
                {'resource_field': 'to_concept_source', 'required': False,
                 'column': ['map_to_concept_source', 'to_concept_source', 'source']},
                {'resource_field': 'owner', 'column': ['map_owner_id', 'owner_id']},
                {'resource_field': 'owner_type', 'column': ['map_owner_type', 'owner_type'],
                 'default': oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION},
                {'resource_field': 'source', 'column': ['map_source', 'source']},
            ]
        },
        {
            'definition_name': 'Generic Collection Reference',
            'is_active': False,
            'resource_type': oclconstants.OclConstants.RESOURCE_TYPE_REFERENCE,
            'id_column': 'id',
            '__trigger_column': 'resource_type',
            '__trigger_value': oclconstants.OclConstants.RESOURCE_TYPE_REFERENCE,
            'skip_if_empty_column': 'id',

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
                {'resource_field': 'retired', 'column': 'retired', 'required': False,
                 'datatype': 'bool'},
                {'resource_field': 'owner', 'column': 'owner_id'},
                {'resource_field': 'owner_type', 'column': 'owner_type',
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
                {'resource_field': 'retired', 'column': 'retired', 'required': False,
                 'datatype': 'bool'},
                {'resource_field': 'owner', 'column': 'owner_id'},
                {'resource_field': 'owner_type', 'column': 'owner_type',
                 'default': oclconstants.OclConstants.RESOURCE_TYPE_ORGANIZATION},
                {'resource_field': 'collection', 'column': 'collection'},
            ],
        },
    ]

    def __init__(self, csv_filename='', input_list=None, verbose=False, allow_special_characters=False):
        """ Initialize the object with the standard CSV resource definition """
        OclCsvToJsonConverter.__init__(
            self, csv_filename=csv_filename,
            input_list=input_list,
            csv_resource_definitions=self.default_csv_resource_definitions,
            verbose=verbose,
            allow_special_characters=allow_special_characters
        )
