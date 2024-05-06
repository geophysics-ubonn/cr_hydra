#!/usr/bin/env python
import time

import logging

from crh_retrieve import retrieve_all_finished_mods_and_invs

logging.basicConfig(
    level=logging.INFO,
    format='{asctime} - {name} - %{levelname} - {message}',
    style='{',
)
logger = logging.getLogger(__name__)


def crh_wait_for_all_sims_to_finish():
    unfinished = True
    while unfinished:
        unfinished = retrieve_all_finished_mods_and_invs()
        if unfinished:
            time.sleep(10)


def main():
    crh_wait_for_all_sims_to_finish()


if __name__ == '__main__':
    main()
