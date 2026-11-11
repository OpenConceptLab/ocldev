import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='ocldev',
    version='0.2.4',
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
    license_files=['LICENSE', 'HEALTHCARE-DISCLAIMER.md'],
    project_urls={
        'Documentation': 'http://github.com/OpenConceptLab/ocldev/wiki',
        'Source': 'http://github.com/OpenConceptLab/ocldev',
        'Tracker': 'https://github.com/OpenConceptLab/ocl_issues/issues',
    },
    python_requires='>=3.10',
    classifiers=(
        "Development Status :: 2 - Pre-Alpha",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Operating System :: OS Independent",
    )
)
