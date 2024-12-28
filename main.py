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
from functools import reduce
import operator

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
parser.add_argument('-E', '--exclude-file',
                    type=str, default="exclude.txt",
                    help="File containing a list of user IDs to be excluded")
parser.add_argument('-m', '--message',
                    type=str, default="message.txt",
                    help="File containing a footer message")
parser.add_argument('-t', '--topic',
                    type=int, default=5703,
                    help="Which topic ID to post the leaderboard")
args = parser.parse_args()


# read the exclude file
exclude = []
try:
    if args.exclude_file == "":
        raise ValueError("No filename given")
    with open(args.exclude_file, "r") as f:
        for line in f:
            exclude.append(int(line))
except ValueError:
    pass
except IOError:
    warn(f"Cannot read exclude file {args.exclude_file}")


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
    from functools import partial as part

    def col(func):
        return part(func, index_col="User ID")

    def label(func):
        return part(func, index_label="User ID")

    def labels(func):
        return part(func, index_labels="User ID")

    def orient(func):
        return part(func, orient="index")

    def key(func):
        return part(func, key="leaderboard")

    match pathlib.PurePath(args.file).suffix:
        case ".csv":
            return col(pd.read_csv), labels(pd.DataFrame.to_csv)
        case ".json":
            return orient(pd.read_json), orient(pd.DataFrame.to_json)
        case ".xls" | ".xlsx" | ".xlsb":
            return col(pd.read_excel), label(pd.DataFrame.to_excel)
        case ".h5":
            return key(pd.read_hdf), key(pd.DataFrame.to_hdf)
        case ".pickle":
            return (pd.read_pickle), (pd.DataFrame.to_pickle)
        case _:
            warn("No extension given; ALM will pickle the current "
                 "leaderboard. This may be undesired.")
            return (pd.read_pickle), (pd.DataFrame.to_pickle)


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
    # we only care about these rows
    master_table = master_table[["Name", "Position", "Posts"]]
    # only pick users we don't exclude
    master_table = master_table.loc[~reduce(
        operator.__or__,
        (master_table.index == x for x in exclude)
    )]

    # Compare with the past leaderboard
    reader, writer = get_reader_writer()
    try:
        prev_board = reader(args.file)
    except FileNotFoundError:
        prev_board = make_dummy(master_table)
    rank_diff = {}
    idxed_prev_board = prev_board.reset_index()
    for i, row in enumerate(master_table.itertuples()):
        # Find the post count difference
        try:
            diff = prev_board.loc[row.Index, "Posts"] - row.Posts
        except (IndexError, TypeError):
            diff = None
        master_table.loc[row.Index, "Difference"] = diff
        # Find the rank difference
        try:
            prev_rank = idxed_prev_board.loc[
                idxed_prev_board["User ID"] == row.Index
            ].index[0]
            rank_diff[row.Index] = prev_rank - i  # lower = better
        except (IndexError, TypeError):
            rank_diff[row.Index] = None

    # Make the leaderboard
    leaderboard = (
        "[size=3][b]"
        f"Leaderboard at {datetime.now(timezone.utc):%d %B %Y, %H %M %Z}"
        "[/b][/size]\n[code]\n"
    )
    rank = 1
    max_length = master_table["Name"].map(len).max()
    for row in master_table.itertuples():
        # DONE: Rank change
        leaderboard += (
            f"{tbg_type(row.Position)}"
            + (
                f" {rank_diff[row.Index]: =+3d} "
                .replace("+ 0", "===")
                .replace("+", "↑")
                .replace("-", "↓")
            ) +
            f"{to_intensity(row.Difference)} "
            f"{rank:=3d}. {row.Name.ljust(max_length)} "
            f"{row.Posts} "
            f"({'N/A' if row.Difference is pd.NA else row.Difference})\n"
        )
        rank += 1
    leaderboard += "[/code]"
    # Add the optional message
    try:
        if args.message != "":
            with open(args.message, "r") as f:
                message = f.read()
                if message != "":
                    leaderboard += "\n"
                    leaderboard += message
    except FileNotFoundError:
        warn(f"Message file {args.message} not found")

    if args.simulate:
        logger.info("Simulation only: no data is sent or saved")
        print(leaderboard)
    else:
        # Publish the leaderboard to the topic
        logger.info("Publishing leaderboard")
        with session:
            # To be honest, I kinda hate this way of submitting posts
            # I need to implement posting a la scratchattach or something
            Message(content=leaderboard, tid=args.topic).submit_post()
        # Save the leaderboard
        logger.info("Saving leaderboard")
        writer(master_table)
else:
    raise ImportError("This script isn't meant to be run as a module.")
