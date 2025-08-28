#!/usr/bin/env python3
import argparse
import sys
import libwyag   # your core implementation

# ======================================================
# Argument parser setup
# ======================================================
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
sp = argsubparsers.add_parser("hash-object",
                              help="Compute object ID and optionally create a blob from a file")
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

# --- log ---
argsp = argsubparsers.add_parser("log", help="Display history of a given commit.")
argsp.add_argument("commit",
                   default="HEAD",
                   nargs="?",
                   help="Commit to start at.")
argsp.set_defaults(func=libwyag.cmd_log)

# --- ls-tree ---
argsp = argsubparsers.add_parser("ls-tree", help="Pretty-print a tree object.")
argsp.add_argument("-r",
                   dest="recursive",
                   action="store_true",
                   help="Recurse into sub-trees")
argsp.add_argument("tree",
                   help="A tree-ish object.")
argsp.set_defaults(func=libwyag.cmd_ls_tree)

# --- checkout ---
argsp = argsubparsers.add_parser("checkout", help="Checkout a commit inside of a directory.")
argsp.add_argument("commit", help="The commit or tree to checkout.")
argsp.add_argument("path", help="The EMPTY directory to checkout on.")
argsp.set_defaults(func=libwyag.cmd_checkout)


# ======================================================
# Main entrypoint
# ======================================================
def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)
    args.func(args)

if __name__ == "__main__":
    main()
