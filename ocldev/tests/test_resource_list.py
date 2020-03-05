import ocldev.oclresourcelist


def test_get_resource():
	resources = ocldev.oclresourcelist.OclResourceList()
	resource = {'resource_type': 'Concept', 'id': 'A', 'name': 'Bob', 'owner': 'PEPFAR', 'source': 'PLM'}
	resources.append(resource)
	print resources[0]
	assert resource == resources[0]
