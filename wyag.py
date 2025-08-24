#!/usr/bin/env python3
import argparse
import sys
import libwyag  # your implementation file


# ----------------------------
# Argument parser setup
# ----------------------------
argparser = argparse.ArgumentParser(description="The stupidest content tracker")
argsubparsers = argparser.add_subparsers(title="Commands", dest="command")
argsubparsers.required = True

# --- init ---
sp = argsubparsers.add_parser("init", help="Initialize a new, empty repository")
sp.add_argument("path",
                metavar="directory",
                nargs="?",
                default=".",
                help="Where to create the repository")
sp.set_defaults(func=libwyag.cmd_init)

# --- hash-object ---
sp = argsubparsers.add_parser(
    "hash-object",
    help="Compute object ID and optionally creates a blob from a file"
)
sp.add_argument("-t",
                metavar="type",
                dest="type",
                choices=["blob", "commit", "tag", "tree"],
                default="blob",
                help="Specify the type")
sp.add_argument("-w",
                dest="write",
                action="store_true",
                help="Actually write the object into the database")
sp.add_argument("path", help="Read object from <file>")
sp.set_defaults(func=libwyag.cmd_hash_object)

# --- cat-file ---
sp = argsubparsers.add_parser("cat-file",
                              help="Provide content of repository objects")
sp.add_argument("type",
                metavar="type",
                choices=["blob", "commit", "tag", "tree"],
                help="Specify the type")
sp.add_argument("object",
                metavar="object",
                help="The object to display")
sp.set_defaults(func=libwyag.cmd_cat_file)

# log
argsp = argsubparsers.add_parser("log", help="Display history of a given commit.")
argsp.add_argument("commit",
                   default="HEAD",
                   nargs="?",
                   help="Commit to start at.")
argsp.set_defaults(func=libwyag.cmd_log)



# ----------------------------
# Main entrypoint
# ----------------------------
def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)
    args.func(args)   # dispatch to the correct function


if __name__ == "__main__":
    main()
