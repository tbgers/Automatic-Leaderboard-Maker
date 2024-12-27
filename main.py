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
import re
from tbgclient import Message, Session, api
from bs4 import BeautifulSoup
import pandas as pd
import argparse
from datetime import datetime, timezone
from warnings import warn

logger = logging.getLogger(__name__)
parser = argparse.ArgumentParser(
    prog='Automatic Leaderboard Maker',
    description='Makes and posts a leaderboard for the '
                '"Top 100 Posters, round 2" topic.',
)
parser.add_argument('-s', '--simulate',
                    action='store_true',
                    help="Scrape only, don't save and publish")
parser.add_argument('-f', '--file',
                    type=str, default="leaderboard.json",
                    help="Save this month's leaderboard to this file")
args = parser.parse_args()


def read_table(response):
    from io import StringIO
    with StringIO() as buff:
        doc = BeautifulSoup(response.content, 'html.parser')
        table = doc.table
        table.thead.th.a.replace_with("User ID")
        for row in table.tbody.find_all("tr"):
            # Reuse the Status column for user IDs
            username = row.contents[3].a  # XXX: contents also includes spaces
            user_id = re.search(
                r"u=(\d+)",
                username.get("href")
            )[1]
            row.contents[1].span.replace_with(user_id)
        # HACK: Relying on __repr__ giving a canonical representation
        # of the element (forgot a way to stringify elements)
        print(table, file=buff)
        buff.seek(0)
        table = pd.read_html(buff, index_col=0)[0]
    return table


def get_reader_writer():
    import pathlib
    match pathlib.PurePath(args.file).suffix:
        case ".csv":
            return pd.read_csv, pd.DataFrame.to_csv
        case ".json":
            return pd.read_json, pd.DataFrame.to_json
        case ".xls" | ".xlsx" | ".xlsb":
            return pd.read_excel, pd.DataFrame.to_excel
        case ".h5":
            return pd.read_hdf, pd.DataFrame.to_hdf
        case ".pickle":
            return pd.read_pickle, pd.DataFrame.to_pickle
        case _:
            warn("No extension given; ALM will pickle the current "
                 "leaderboard. This may be undesired.")
            return pd.read_pickle, pd.DataFrame.to_pickle


def make_dummy(table):
    copy = table.copy()
    copy.loc[:, "Posts"] = pd.NA
    return copy


def tbg_type(type):
    # Self explanatory.
    if type == "Banned":
        return "BAN"
    elif "Retired" in type:
        return "RET"
    elif "Moderator" in type:
        return "MOD"
    elif "Team" in type:
        return "TEA"
    elif "TBGer" in type:
        return "TBG"
    else:
        return "OTH"


def to_intensity(posts):
    if posts is pd.NA:
        return "(NA)"
    BRAILLE = "⠀⡀⡄⡆⡇⣇⣧⣷⣿"
    posts //= 10
    first = BRAILLE[min(posts, 8)]
    posts //= 8
    second = BRAILLE[min(max(0, posts - 1), 8)]
    posts //= 9
    third = BRAILLE[min(max(0, posts - 1), 8)]
    posts //= 9
    fourth = " .:"[min(max(0, posts - 1), 2)]
    return first + second + third + fourth


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Log in to the TBGs
    session = Session()
    logger.info(f"Logging in as {environ['USERNAME']}")
    session.login(environ["USERNAME"], environ["PASSWORD"])
    logger.info("Sucessfully logged in")

    # Scrape the memberlist tables (the leaderboard)
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
    master_table = pd.concat([table1, table2])
    master_table = master_table[["Name", "Position", "Posts"]]

    # Compare with the past leaderboard
    reader, writer = get_reader_writer()
    try:
        prev_board = reader(args.file)
    except FileNotFoundError:
        prev_board = make_dummy(master_table)
    for row in master_table.itertuples():
        try:
            diff = prev_board.loc[row.Index, "Posts"] - row.Posts
        except (IndexError, TypeError):
            diff = None
        master_table.loc[row.Index, "Difference"] = diff

    # Make the leaderboard
    leaderboard = (
        "[size=3][b]"
        f"Leaderboard at {datetime.now(timezone.utc):%d %B %Y, %H %M %Z}"
        "[/b][/size]\n[code]"
    )
    rank = 1
    for row in master_table.itertuples():
        # TODO: Rank change
        leaderboard += (
            f"{tbg_type(row.Position)} --- {to_intensity(row.Difference)} "
            f"{rank:03d}. {row.Name} ({row.Posts})\n"
        )
        rank += 1
    leaderboard += "[/code]"

    if args.simulate:
        logger.info("Simulation only: no data is sent or saved")
        print(leaderboard)
    else:
        raise NotImplementedError("TODO: save and publish")
else:
    raise ImportError("This script isn't meant to be run as a module.")
