# Common setup.py code shared between all the projects in this repository
import os


def common_setup(src_dir):
    this_dir = os.path.dirname(__file__)
    readme_file = os.path.join(this_dir, 'README.md')
    changelog_file = os.path.join(this_dir, 'CHANGES.md')
    version_file = os.path.join(this_dir, 'VERSION')

    long_description = open(readme_file).read()
    changelog = open(changelog_file).read()

    return dict(
        # Version is shared between all the projects in this repo
        version=open(version_file).read().strip(),
        long_description='\n'.join((long_description, changelog)),
        long_description_content_type='text/markdown',
        url='https://github.com/man-group/pytest-plugins',
        license='MIT license',
        platforms=['unix', 'linux'],
        include_package_data=True,
        python_requires='>=3.6',
    )
