#!/usr/bin/env python
"""The setup script."""

from setuptools import find_packages, setup  # type: ignore

with open("README.md", encoding="utf-8") as readme_file:
    readme = readme_file.read()

# Since new process created by multiprocessing calls setuptools.setup method
# when the test is executed via setup.py and this affects something.
# see:
#   - Answer: How to get `setup.py test` working with `multiprocessing` on Windows?
#     https://stackoverflow.com/a/50402381/12721873
if __name__ == "__main__":
    setup(
        author="Yukihiko Shinoda",
        author_email="yuk.hik.future@gmail.com",
        classifiers=[
            "Development Status :: 5 - Production/Stable",
            "Framework :: AsyncIO",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: MIT License",
            "Natural Language :: English",
            "Operating System :: OS Independent",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Topic :: Software Development :: Libraries",
            "Topic :: Software Development :: Libraries :: Python Modules",
            "Typing :: Typed",
        ],
        dependency_links=[],
        description="Supports async / await pattern for CPU-bound operations.",  # noqa: E501 pylint: disable=line-too-long
        exclude_package_data={"": ["__pycache__", "*.py[co]", ".pytest_cache"]},
        include_package_data=True,
        install_requires=["psutil"],
        keywords="asynccpu",
        long_description=readme,
        long_description_content_type="text/markdown",
        name="asynccpu",
        packages=find_packages(include=["asynccpu", "asynccpu.*"]),
        package_data={"asynccpu": ["py.typed"]},
        python_requires=">=3.8",
        test_suite="tests",
        tests_require=["pytest>=3"],
        url="https://github.com/yukihiko-shinoda/asynccpu",
        version="1.2.0",
        zip_safe=False,
    )
