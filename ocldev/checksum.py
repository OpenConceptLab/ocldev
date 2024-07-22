import argparse
import hashlib
import json
from uuid import UUID
from pprint import pprint


class Checksum:
    def __init__(self, resource, data, checksum_type='standard', verbosity=0):
        self.resource = resource
        self.checksum_type = checksum_type
        self.data = self.flatten([data])
        self.verbosity = verbosity
        if not self.resource or self.resource.lower() not in ['concept', 'mapping']:
            raise ValueError(f"Invalid resource: {self.resource}")
        if self.checksum_type not in ['standard', 'smart']:
            raise ValueError(f"Invalid checksum type: {self.checksum_type}")

    def generate(self):
        if self.resource == 'concept':
            data = [self.get_concept_fields(_data) for _data in self.data]
        else:
            data = [self.get_mapping_fields(_data) for _data in self.data]

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

    def get_concept_fields(self, data):
        name_fields = ['locale', 'locale_preferred', 'name', 'name_type', 'external_id']
        description_fields = ['locale', 'locale_preferred', 'description', 'description_type', 'external_id']
        fields = {
            'concept_class': data.get('concept_class', None),
            'datatype': data.get('datatype', None),
            'retired': data.get('retired', False),
        }
        if self.checksum_type == 'standard':
            return {
                **fields,
                'external_id': data.get('external_id', None),
                'extras': data.get('extras', None),
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
                'parent_concept_urls': data.get('parent_concept_urls', []),
                'child_concept_urls': data.get('child_concept_urls', []),
            }
        return {
                **fields,
                'names': self._locales_for_checksums(
                    data,
                    'names',
                    name_fields,
                    lambda locale: self.is_fully_specified_type(locale.get('name_type', None))
                ),
            }

    def get_mapping_fields(self, data):
        fields = {
                'map_type': data.get('map_type', None),
                'from_concept_code': data.get('from_concept_code', None),
                'to_concept_code': data.get('to_concept_code', None),
                'from_concept_name': data.get('from_concept_name', None),
                'to_concept_name': data.get('to_concept_name', None),
                'retired': data.get('retired', False)
            }
        if self.checksum_type == 'standard':
            return {
                **fields,
                'sort_weight': float(data.get('sort_weight', 0)) or None,
                **{
                    field: data.get(field, None) or None for field in [
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
        locales = data.get(relation, [])
        return [{field: locale.get(field, None) for field in fields} for locale in locales if predicate_func(locale)]

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
    print("python3 checksum.py -r <concept|mapping> -c <standard|smart> -d '{...json...}'")


if __name__ == '__main__':
    main()
