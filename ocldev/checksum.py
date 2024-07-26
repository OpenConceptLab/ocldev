import argparse
import hashlib
import json
from uuid import UUID
from pprint import pprint


def getvalue(obj, key, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class Checksum:
    def __init__(self, resource, data, checksum_type='standard', verbosity=0):
        self.resource = resource
        self.checksum_type = checksum_type
        self.data = self.flatten([data])
        self.verbosity = verbosity
        if self.resource and self.resource.lower() not in [
            'concept', 'mapping', 'source', 'collection', 'organization', 'org', 'user', 'userprofile']:
            raise ValueError(f"Invalid resource: {self.resource}")
        if self.checksum_type not in ['standard', 'smart']:
            raise ValueError(f"Invalid checksum type: {self.checksum_type}")

    def generate(self):
        data = self._get_data_by_resource()

        if self.verbosity:
            print("\n")
            print("Fields for Checksum:")
            pprint(data)

            print("\n")
            print("After Cleanup:")
            pprint([self._cleanup(_data) for _data in data])

        checksums = [
            self._generate(self._cleanup(_data)) for _data in data
        ] if isinstance(data, list) else [self._generate(self._cleanup(data))]
        if len(checksums) == 1:
            return checksums[0]
        return self._generate(checksums)

    def _get_data_by_resource(self):
        if self.resource == 'concept':
            data = [self.get_concept_fields(_data) for _data in self.data]
        elif self.resource == 'mapping':
            data = [self.get_mapping_fields(_data) for _data in self.data]
        elif self.resource in ['organization', 'org']:
            data = [self.get_organization_fields(_data) for _data in self.data]
        elif self.resource in ['user', 'userprofile']:
            data = [self.get_user_fields(_data) for _data in self.data]
        elif self.resource == 'source':
            data = [self.get_source_fields(_data) for _data in self.data]
        elif self.resource == 'collection':
            data = [self.get_collection_fields(_data) for _data in self.data]
        else:
            data = self.data
        return data

    def get_concept_fields(self, data):
        name_fields = ['locale', 'locale_preferred', 'name', 'name_type', 'external_id']
        description_fields = ['locale', 'locale_preferred', 'description', 'description_type', 'external_id']
        fields = {
            'concept_class': getvalue(data, 'concept_class', None),
            'datatype': getvalue(data, 'datatype', None),
            'retired': getvalue(data, 'retired', False),
        }
        if self.checksum_type == 'standard':
            return {
                **fields,
                'external_id': getvalue(data, 'external_id', None),
                'extras': getvalue(data, 'extras', None),
                'names': self._locales_for_checksums(
                    data,
                    'names',
                    name_fields,
                    lambda _: True
                ),
                'descriptions': self._locales_for_checksums(
                    data,
                    'descriptions',
                    description_fields,
                    lambda _: True
                ),
                'parent_concept_urls': getvalue(data, 'parent_concept_urls', []),
                'child_concept_urls': getvalue(data, 'child_concept_urls', []),
            }
        return {
                **fields,
                'names': self._locales_for_checksums(
                    data,
                    'names',
                    name_fields,
                    lambda locale: self.is_fully_specified_type(getvalue(locale, 'name_type', None))
                ),
            }

    def get_mapping_fields(self, data):
        fields = {
                'map_type': getvalue(data, 'map_type', None),
                'from_concept_code': getvalue(data, 'from_concept_code', None),
                'to_concept_code': getvalue(data, 'to_concept_code', None),
                'from_concept_name': getvalue(data, 'from_concept_name', None),
                'to_concept_name': getvalue(data, 'to_concept_name', None),
                'retired': getvalue(data, 'retired', False)
            }
        if self.checksum_type == 'standard':
            return {
                **fields,
                'sort_weight': float(getvalue(data, 'sort_weight', 0)) or None,
                **{
                    field: getvalue(data, field, None) or None for field in [
                        'extras',
                        'external_id',
                        'from_source_url',
                        'from_source_version',
                        'to_source_url',
                        'to_source_version'
                    ]
                }
            }
        return fields

    def get_organization_fields(self, data):
        fields = {
            'name': getvalue(data, 'name', None),
            'company': getvalue(data, 'company', None),
            'location': getvalue(data, 'location', None),
            'website': getvalue(data, 'website', None),
        }
        if self.checksum_type == 'standard':
            return {
                **fields,
                'extras': getvalue(data, 'extras', None),
            }
        return {
            **fields,
            'is_active': getvalue(data, 'is_active', True)
        }

    def get_user_fields(self, data):
        fields = {
            'first_name': getvalue(data, 'first_name', None),
            'last_name': getvalue(data, 'last_name', None),
            'username': getvalue(data, 'username', None),
            'company': getvalue(data, 'company', None),
            'location': getvalue(data, 'location', None),
        }
        if self.checksum_type == 'standard':
            return {
                **fields,
                'website': getvalue(data, 'website', None),
                'preferred_locale': getvalue(data, 'preferred_locale', None),
                'extras': getvalue(data, 'extras', None)
            }
        return {
            **fields,
            'is_active': getvalue(data, 'is_active', True)
        }

    def get_collection_fields(self, data):
        fields = {
            'collection_type': getvalue(data, 'collection_type', None),
            'canonical_url': getvalue(data, 'canonical_url', None),
            'custom_validation_schema': getvalue(data, 'custom_validation_schema', None),
            'default_locale': getvalue(data, 'default_locale', None),
        }
        if self.checksum_type == 'standard':
            return {
                **fields,
                'supported_locales': getvalue(data, 'supported_locales', None),
                'website': getvalue(data, 'website', None),
                'extras': getvalue(data, 'extras', None),
            }

        return {
            **fields,
            'released': getvalue(data, 'released', False),
            'retired': getvalue(data, 'retired', False),
        }

    def get_source_fields(self, data):
        fields = {
            'source_type': getvalue(data, 'collection_type', None),
            'canonical_url': getvalue(data, 'canonical_url', None),
            'custom_validation_schema': getvalue(data, 'custom_validation_schema', None),
            'default_locale': getvalue(data, 'default_locale', None),
        }
        if self.checksum_type == 'standard':
            return {
                **fields,
                'hierarchy_meaning': getvalue(data, 'hierarchy_meaning', None),
                'supported_locales': getvalue(data, 'supported_locales', None),
                'website': getvalue(data, 'website', None),
                'extras': getvalue(data, 'extras', None),
            }

        return {
            **fields,
            'released': getvalue(data, 'released', False),
            'retired': getvalue(data, 'retired', False),
        }

    @staticmethod
    def generic_sort(_list):
        def compare(item):
            if isinstance(item, (int, float, str, bool)):
                return item
            return str(item)
        return sorted(_list, key=compare)

    @staticmethod
    def is_fully_specified_type(_type):
        if not _type:
            return False
        if _type in ('FULLY_SPECIFIED', "Fully Specified"):
            return True
        _type = _type.replace(' ', '').replace('-', '').replace('_', '').lower()
        return _type == 'fullyspecified'

    @staticmethod
    def flatten(input_list, depth=1):
        result = []
        for item in input_list:
            if isinstance(item, list) and depth > 0:
                result.extend(Checksum.flatten(item, depth - 1))
            else:
                result.append(item)
        return result

    def _serialize(self, obj):
        if isinstance(obj, list) and len(obj) == 1:
            obj = obj[0]
        if isinstance(obj, list):
            return f"[{','.join(map(self._serialize, self.generic_sort(obj)))}]"
        if isinstance(obj, dict):
            keys = self.generic_sort(obj.keys())
            acc = f"{{{json.dumps(keys)}"
            for key in keys:
                acc += f"{self._serialize(obj[key])},"
            return f"{acc}}}"
        if isinstance(obj, UUID):
            return json.dumps(str(obj))
        return json.dumps(obj)

    @staticmethod
    def _cleanup(fields):
        result = fields
        if isinstance(fields, dict):  # pylint: disable=too-many-nested-blocks
            result = {}
            for key, value in fields.items():
                if value is None:
                    continue
                if key in [
                    'retired', 'parent_concept_urls', 'child_concept_urls', 'descriptions', 'extras', 'names',
                    'locale_preferred', 'name_type', 'description_type'
                ] and not value:
                    continue
                if key in ['names', 'descriptions']:
                    value = [Checksum._cleanup(val) for val in value]
                if key in ['is_active'] and value:
                    continue
                if not isinstance(value, bool) and isinstance(value, (int, float)):
                    if int(value) == float(value):
                        value = int(value)
                if key in ['extras']:
                    if isinstance(value, dict) and any(key.startswith('__') for key in value):
                        value_copied = value.copy()
                        for extra_key in value:
                            if extra_key.startswith('__'):
                                value_copied.pop(extra_key)
                        value = value_copied
                result[key] = value
        return result

    @staticmethod
    def _locales_for_checksums(data, relation, fields, predicate_func):
        locales = getvalue(data, relation, [])
        return [{field: getvalue(locale, field, None) for field in fields} for locale in locales if predicate_func(locale)]

    def _generate(self, obj, hash_algorithm='MD5'):
        # hex encoding is used to make the hash more readable
        serialized_obj = self._serialize(obj)
        if self.verbosity:
            print("\n")
            print("After Serialization")
            print(serialized_obj)

        serialized_obj = serialized_obj.encode('utf-8')

        hash_func = hashlib.new(hash_algorithm)
        hash_func.update(serialized_obj)

        return hash_func.hexdigest()


def main():
    parser = argparse.ArgumentParser(description='Generate checksum for resource data.')
    parser.add_argument(
        '-r', '--resource', type=str, choices=['concept', 'mapping'], help='The type of resource (concept, mapping)')
    parser.add_argument(
        '-c', '--checksum_type', type=str, default='standard', choices=['standard', 'smart'],
        help='The type of checksum to generate (default: standard)')
    parser.add_argument(
        '-d', '--data', type=str, help='The data for which checksum needs to be generated')
    parser.add_argument(
        '-v', '--verbosity', type=int, help='Verbosity level (default: 0)')

    args = parser.parse_args()


    try:
        checksum = Checksum(args.resource, json.loads(args.data), args.checksum_type, args.verbosity)
        result = checksum.generate()
        print("\n")
        print('\x1b[6;30;42m' + f'{checksum.checksum_type.title()} Checksum: {result}' + '\x1b[0m')
        print("\n")
    except Exception as e:
        print(e)
        print()
        usage()


def usage() -> None:
    print("Use this as:")
    print("python3 checksum.py -r <concept|mapping|org|user|source|collection> -c <standard|smart> -d '{...json...}'")


if __name__ == '__main__':
    main()
