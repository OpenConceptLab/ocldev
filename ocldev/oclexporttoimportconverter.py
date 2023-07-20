import json


class OCLExportToImportConverter:
    def __init__(
            self, content=None, export_file=None, owner=None, owner_type=None, version=None,
            out_file_name=None, return_output=False
    ):
        self.content = json.loads(content) if content else None
        if export_file and not self.content:
            self.content = json.loads(open(export_file, 'r').read())
        self.owner = owner
        self.owner_type = owner_type
        self.version = version
        self.out_file_name = out_file_name or 'importable_export.json'
        self.return_output = return_output
        self.result = []
        self.repo_type = self.get_repo_type()
        self.should_replace_owner = bool(self.owner and self.owner_type)
        self.validate()

    def validate(self):
        if not self.content:
            raise ValueError('No content to convert.')
        if self.owner and not self.owner_type:
            raise ValueError("'owner_type' needs to be either 'User or 'Organization'.")
        if not self.owner and self.owner_type:
            raise ValueError("'owner' needs to be present when 'owner_type' is provided.")
        if self.owner_type and self.owner_type not in ('User', 'Organization'):
            raise ValueError("'owner_type' needs to be either 'User or 'Organization'.")
        if not self.out_file_name:
            raise ValueError("'out_file_name' cannot be null or blank.")

    def get(self, key, default_value=None):
        return self.content.get(key, default_value)

    def write(self, data):
        if self.return_output:
            self.result += data if isinstance(data, list) else [data]
            return

        with open(self.out_file_name, 'a') as out:
            if isinstance(data, list):
                for d in data:
                    self.__write_to(out, d)
            else:
                self.__write_to(out, data)

    def is_head(self):
        return self.get('version') == 'HEAD'

    @staticmethod
    def __write_to(out, data):
        out.write(json.dumps(data))
        out.write("\n")

    def get_repo_type(self):
        export_type = self.get_repo_version_type().lower().replace(' ', '')
        if export_type == 'sourceversion':
            return 'source'
        if export_type == 'collectionversion':
            return 'collection'
        raise ValueError('only source/collection version exports can be converted, for now.')

    def get_repo_version_type(self):
        return self.get('type')

    def process(self):
        self.write(self.get_owner_data())
        self.write(self.get_repo_data())
        self.write(self.get_concepts_data())
        self.write(self.get_mappings_data())
        if not self.is_head():
            self.write(self.get_repo_version_data())

    def get_owner_url(self):
        if self.owner and self.owner_type:
            owner_type = self.owner_type.lower()
            if owner_type == 'organization':
                owner_type = 'orgs'
            elif owner_type == 'user':
                owner_type = 'users'
            return f'/{owner_type}/{self.owner}/'

        return self.get_original_owner_url()

    def get_original_owner_url(self):
        repo = self.get(self.repo_type) or self.content
        return repo.get('owner_url')

    def get_original_owner(self):
        repo = self.get(self.repo_type) or self.content
        return repo.get('owner')

    def get_original_owner_type(self):
        repo = self.get(self.repo_type) or self.content
        return repo.get('owner_type')

    def get_owner_data(self):
        kwargs = self.get_owner_kwargs()
        return {
            'name': kwargs.get('owner'),
            'id': kwargs.get('owner'),
            'type': kwargs.get('owner_type'),
            'url': kwargs.get('owner_url'),
        }

    def get_new_owner(self):
        return self.owner or (self.get(self.repo_type) or self.content).get('owner')

    def get_new_owner_type(self):
        return self.owner_type or (self.get(self.repo_type) or self.content).get('owner_type')

    def get_owner_kwargs(self):
        return {
            'owner': self.get_new_owner(),
            'owner_type': self.get_new_owner_type(),
            'owner_url': self.get_owner_url(),
        }

    def get_repo_url(self):
        owner_url = self.get_owner_url()
        return f'{owner_url}{self.repo_type}s/{self.get("short_code")}/'

    def get_repo_data(self):
        repo = self.get(self.repo_type) or self.content
        return {
            'type': self.get_repo_version_type().replace('Version', '').strip(),
            'id': repo.get('short_code'),
            'url': self.get_repo_url(),
            **self.get_owner_kwargs(),
            **{
                key: self.replace_owner_url(value) for key, value in repo.items() if key in [
                    'description', 'extras',
                    'custom_validation_schema', 'full_name', 'name', 'source_type', 'public_access',
                    'default_locale', 'supported_locales', 'website', 'external_id',
                    'canonical_url', 'identifier', 'publisher', 'contact', 'jurisdiction', 'purpose', 'copyright',
                    'content_type''revision_date', 'text', 'meta', 'experimental', 'case_sensitive',
                    'collection_reference', 'hierarchy_meaning', 'compositional', 'version_needed', 'hierarchy_root_url'
                    'autoid_concept_mnemonic', 'autoid_concept_external_id',
                    'autoid_concept_mnemonic_start_from', 'autoid_concept_external_id_start_from',
                    'autoid_mapping_mnemonic', 'autoid_mapping_external_id',
                    'autoid_mapping_mnemonic_start_from', 'autoid_mapping_external_id_start_from',
                ]
            }
        }

    def get_repo_version_data(self):
        if self.is_head():
            return None

        return {
            'type': self.get('type'),
            'id': self.version or self.get('version'),
            'description': self.get('description'),
            'released': self.get('released'),
            'source': self.get('short_code'),
            **self.get_owner_kwargs(),
        }

    def replace_owner_url(self, val):
        return val.replace(
            self.get_original_owner_url(), self.get_owner_url()
        ) if self.should_replace_owner and isinstance(val, str) else val

    def get_concepts_data(self):
        results = []
        concepts = self.get('concepts', [])
        for concept in concepts:
            data = {
                k: self.replace_owner_url(v) for k, v in concept.items() if
                k not in ['uuid', 'source_url', 'owner_url', 'version', 'created_on', 'updated_on', 'display_name',
                          'display_locale', 'owner', 'owner_type', 'owner_name', 'version_created_on',
                          'version_created_by', 'is_latest_version', 'locale', 'url', 'version_url',
                          'previous_version_url', 'child_concept_urls', 'checksum', 'checksums', 'update_comment',
                          'public_can_view', 'created_by', 'updated_by', 'versioned_object_url']
            }
            names = []
            for name in data['names']:
                names.append(
                    {k: v for k, v in name.items() if k not in ['uuid', 'checksum', 'checksums', 'type']}
                )
            data['names'] = names
            descriptions = []
            for description in descriptions:
                description.append(
                    {k: v for k, v in description.items() if k not in ['uuid', 'checksum', 'checksums', 'type']}
                )
            data['descriptions'] = descriptions
            results.append({**data, **self.get_owner_kwargs()})

        return results

    def get_mappings_data(self):
        results = []
        mappings = self.get('mappings', [])
        for mapping in mappings:
            data = {
                k: self.replace_owner_url(v) for k, v in mapping.items() if
                k not in ['uuid', 'source_url', 'owner_url', 'version', 'created_on', 'updated_on', 'display_name',
                          'display_locale', 'owner', 'owner_type', 'owner_name', 'version_created_on',
                          'version_created_by', 'is_latest_version', 'locale', 'url', 'version_url', 'update_comment',
                          'previous_version_url', 'checksum', 'checksums', 'public_can_view', 'versioned_object_url',
                          'from_concept_name_resolved', 'to_concept_name_resolved', 'created_by', 'updated_by']
            }
            if mapping.get(
                    'from_source_owner_type'
            ) == self.get_original_owner_type() and mapping.get('from_source_owner') == self.get_original_owner():
                data['from_source_owner_type'] = self.get_new_owner_type()
                data['from_source_owner'] = self.get_new_owner()
            if mapping.get(
                    'to_source_owner_type'
            ) == self.get_original_owner_type() and mapping.get('to_source_owner') == self.get_original_owner():
                data['to_source_owner_type'] = self.get_new_owner_type()
                data['to_source_owner'] = self.get_new_owner()
            results.append({**data, **self.get_owner_kwargs()})

        return results
