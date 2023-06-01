import json
import os
import unittest

from ocldev.oclexporttoimportconverter import OCLExportToImportConverter


def remove_file(path):
    try:
        os.remove(path)
    except:
        pass


class OCLExportToImportConverterTest(unittest.TestCase):
    def test_convert_source_version_json_export_to_json_import_format(self):
        new_path = os.path.join(os.path.dirname(__file__), '../../', './DemoSource.v1.import_from_export.json')
        remove_file(new_path)
    
        path = os.path.join(os.path.dirname(__file__), './DemoSource.v1.export.json')
        with open(path, 'r', encoding='UTF-8') as out:
            exported_content = out.read()

        converter = OCLExportToImportConverter(
            content=exported_content, out_file_name='DemoSource.v1.import_from_export.json')
        converter.process()
    
        with open(new_path, 'r', encoding='UTF-8') as out:
            converted_content = out.readlines()
            converted_content = [json.loads(content) for content in converted_content]

            self.assertEqual(converted_content[0]['type'], 'Organization')
            self.assertEqual(converted_content[0]['id'], 'DemoOrg')
            self.assertEqual(converted_content[0]['url'], '/orgs/DemoOrg/')

            self.assertEqual(converted_content[1]['type'], 'Source')
            self.assertEqual(converted_content[1]['id'], 'DemoSource')
            self.assertEqual(converted_content[1]['owner'], 'DemoOrg')
            self.assertEqual(converted_content[1]['owner_type'], 'Organization')
            self.assertEqual(converted_content[1]['url'], '/orgs/DemoOrg/sources/DemoSource/')

            self.assertEqual(converted_content[-1]['type'], 'Source Version')
            self.assertEqual(converted_content[-1]['id'], 'v1.0')
            self.assertEqual(converted_content[-1]['owner'], 'DemoOrg')
            self.assertEqual(converted_content[-1]['owner_type'], 'Organization')
            self.assertEqual(converted_content[-1]['source'], 'DemoSource')
    
        remove_file(new_path)

    def test_convert_source_version_json_export_to_json_import_format_with_different_owner(self):
        new_path = os.path.join(os.path.dirname(__file__), '../../', './DemoSource.v1.import_from_export.json')
        remove_file(new_path)
    
        path = os.path.join(os.path.dirname(__file__), './DemoSource.v1.export.json')
        with open(path, 'r', encoding='UTF-8') as out:
            exported_content = out.read()
    
        converter = OCLExportToImportConverter(
            content=exported_content, out_file_name='DemoSource.v1.import_from_export.json',
            owner='foobar', owner_type='Organization'
        )
        converter.process()
    
        with open(new_path, 'r', encoding='UTF-8') as out:
            converted_content = out.readlines()
            converted_content = [json.loads(content) for content in converted_content]

            self.assertEqual(converted_content[0]['type'], 'Organization')
            self.assertEqual(converted_content[0]['id'], 'foobar')
            self.assertEqual(converted_content[0]['url'], '/orgs/foobar/')

            self.assertEqual(converted_content[1]['type'], 'Source')
            self.assertEqual(converted_content[1]['id'], 'DemoSource')
            self.assertEqual(converted_content[1]['owner'], 'foobar')
            self.assertEqual(converted_content[1]['owner_type'], 'Organization')
            self.assertEqual(converted_content[1]['url'], '/orgs/foobar/sources/DemoSource/')

            self.assertEqual(converted_content[-1]['type'], 'Source Version')
            self.assertEqual(converted_content[-1]['id'], 'v1.0')
            self.assertEqual(converted_content[-1]['owner'], 'foobar')
            self.assertEqual(converted_content[-1]['owner_type'], 'Organization')
            self.assertEqual(converted_content[-1]['source'], 'DemoSource')
    
        remove_file(new_path)
