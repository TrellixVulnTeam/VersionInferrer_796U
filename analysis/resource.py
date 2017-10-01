import logging
from typing import Set, Union

import requests
from bs4 import BeautifulSoup

from backends.software_version import SoftwareVersion
from settings import BACKEND, HTML_PARSER


class Resource:
    """
    A resource is any file which can be retrieved from a url.
    """
    url: str

    def __init__(self, url: str):
        self.url = url

    def __repr__(self) -> str:
        return "<{} '{}'>".format(str(self.__class__.__name__), str(self))

    def __str__(self) -> str:
        return self.url

    @property
    def content(self) -> bytes:
        if not self.retrieved:
            self.retrieve()

        return self._content

    def extract_information(self) -> Set[SoftwareVersion]:
        """
        Extract information from resource text source.
        """
        result = set()

        parsed = BeautifulSoup(
            self.content,
            HTML_PARSER)

        # generator tag
        result |= self._extract_generator_tag(parsed)

        return result

    def retrieve(self):
        """Retrieve the resource from its url."""
        logging.info('Retrieving resource %s', self.url)

        self._content = requests.get(self.url).content

    @property
    def retrieved(self) -> bool:
        """Whether the resource has already been retrieved."""
        return hasattr(self, '_content')

    @staticmethod
    def _extract_generator_tag(parsed: BeautifulSoup) -> Set[SoftwareVersion]:
        """Extract information from generator tag."""
        generator_tags = parsed.find_all('meta', {'name': 'generator'})
        if len(generator_tags) != 1:
            # If none or multiple generator tags are found, that is not a
            # reliable source
            return set()

        result = set()

        generator_tag = generator_tags[0].get('content')
        if not generator_tag:
            return set()

        components = generator_tag.split()
        # TODO: Maybe there is already a version in the generator tag ...
        # TODO: Therefore, do not throw non-first components away
        # TODO: Software packages with spaces in name
        matches = BACKEND.retrieve_packages_by_name(components[0])
        for match in matches:
            versions = BACKEND.retrieve_versions(match)
            matching_versions = versions.copy()
            if len(components) > 1:
                # generator tag might contain version information already.
                for version in versions:
                    if components[1].lower().strip() not in version.name.lower().strip():
                        matching_versions.remove(version)
                if not matching_versions:
                    # not a single version matched
                    matching_versions = versions
            result.update(matching_versions)

        logging.info('Generator tag suggests one of: %s', matching_versions)

        return result