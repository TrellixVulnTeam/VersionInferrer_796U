#!/usr/bin/env python3
import logging
from concurrent.futures import ThreadPoolExecutor
from traceback import print_exc
from typing import Set, Tuple

from backends.software_version import SoftwareVersion
from backends.model import Model
from definitions.definition import SoftwareDefinition
from definitions import definitions
from indexing import indexing
from settings import BACKEND, LOG_FORMAT, MAX_WORKERS, STEP_LIMIT


logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)


def handle_definition(
        definition: SoftwareDefinition,
        indexed_versions: Set[SoftwareVersion]) -> Tuple[
            Set[Model], SoftwareVersion]:
    store_objects = set()

    logging.info('handling software package %s', definition.software_package)
    
    available_versions = definition.provider.get_versions()

    missing_versions = available_versions - indexed_versions
    logging.info('%d versions not yet indexed', len(missing_versions))
    for step in range(min(len(missing_versions), STEP_LIMIT)):
        version = missing_versions.pop()
        store_objects.add(version)
        static_files = indexing.collect_static_files(definition, version)
        logging.info('indexing %d static files', len(static_files))
        for static_file in static_files:
            store_objects.add(static_file)
    return store_objects, version


while True:
    changed = False
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = set()
        for definition in definitions:
            # Ensure that software package is in the database
            BACKEND.store(definition.software_package)
            indexed_versions = BACKEND.retrieve_versions(
                definition.software_package)

            futures.add(
                executor.submit(handle_definition, definition, indexed_versions))
        for future in futures:
            store_objects, version = future.result()
            if store_objects:
                changed = True
                logging.info('storing %d elements to backend', len(store_objects))
                for element in store_objects:
                    BACKEND.store(element)
            BACKEND.mark_indexed(version)
    if not changed:
        break
