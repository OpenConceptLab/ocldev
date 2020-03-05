import ocldev.oclresourcelist


def test_get_resource():
	resources = ocldev.oclresourcelist.OclResourceList()
	resource = {'resource_type': 'Concept', 'id': 'A', 'name': 'Bob', 'owner': 'PEPFAR', 'source': 'PLM'}
	resources.append(resource)
	print resources[0]
	assert resource == resources[0]


def test_resource_iterator():
	resources = ocldev.oclresourcelist.OclResourceList()
	resource_a = {'resource_type': 'Concept', 'id': 'A', 'name': 'Adam', 'owner': 'PEPFAR', 'source': 'PLM'}
	resource_b = {'resource_type': 'Mapping', 'id': 'B', 'name': 'Bob', 'owner': 'PEPFAR', 'source': 'PLM'}
	resources.append(resource_a)
	resources.append(resource_b)
	count = 0
	for resource in resources:
		count += 1
		print resource
	assert count == len(resources)
