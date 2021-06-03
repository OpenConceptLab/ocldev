import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='ocldev',
    version='0.1.87',
    author='Open Concept Lab',
    author_email='info@openconceptlab.org',
    description='Python development library for working with OCL resources and APIs',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='http://github.com/OpenConceptLab/ocldev',
    packages=setuptools.find_packages(),
    install_requires=[
        'jsonschema',
        'requests',
    ],
    license='MPL2.0',
    project_urls={
        'Documentation': 'http://github.com/OpenConceptLab/ocldev/wiki',
        'Source': 'http://github.com/OpenConceptLab/ocldev',
        'Tracker': 'https://github.com/OpenConceptLab/ocl_issues/issues',
    },
    classifiers=(
        "Development Status :: 2 - Pre-Alpha",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Operating System :: OS Independent",
    )
)
