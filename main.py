"""
Automatic Leaderboard Maker
For use with "Top 100 Posters, round 2".
No warranties whatsoever. ;)

Changes (outline):
2.0.0: Started from scratch, now scrapes the table by its own
1.2.0 and older: SEE: the replit project

For a more detailed changelog, see the commits.
"""

from os import environ
import logging
from tbgclient import Message, Session, api
from bs4 import BeautifulSoup
import pandas as pd
logger = logging.getLogger(__name__)


def read_table(response):
    from io import StringIO
    with StringIO() as buff:
        doc = BeautifulSoup(response.content, 'html.parser')
        # HACK: Relying on __repr__ giving a canonical representation
        # of the element (forgot a way to stringify elements)
        print(doc.table, file=buff)
        buff.seek(0)
        table = pd.read_html(buff)
    return table


def make_dummy(table):
    copy = table.copy()
    copy.loc[:, "Posts"] = None
    return copy


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    session = Session()
    logger.info(f"Logging in as {environ['USERNAME']}")
    session.login(environ["USERNAME"], environ["PASSWORD"])
    logger.info("Sucessfully logged in")

    params = dict(
        sort="post_count",
        desc=None
    )
    logger.info("Scraping first table")
    table1 = api.do_action(session, "mlist", params={**params, "start": "0"},
                           no_percents=True)
    table1 = read_table(table1)
    logger.info("Scraping second table")
    table2 = api.do_action(session, "mlist", params={**params, "start": "50"},
                           no_percents=True)
    table2 = read_table(table2)

    master_table = pd.concat(table1 + table2)
    master_table = master_table[["Name", "Position", "Posts"]]

    print(make_dummy(master_table).to_string())
else:
    raise ImportError("This script isn't meant to be run as a module.")
