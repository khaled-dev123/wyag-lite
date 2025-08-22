import argparse
import sys
import libwyag  

# Argument parser setup
argparser = argparse.ArgumentParser(description="The stupidest content tracker")
argsubparsers = argparser.add_subparsers(title="Commands", dest="command")
argsubparsers.required = True

# init
sp = argsubparsers.add_parser("init", help="Initialize a new, empty repository")
sp.add_argument("path",
                metavar="directory",
                nargs="?",
                default=".",
                help="Where to create the repository")
sp.set_defaults(func=libwyag.cmd_init)

# hash-object
argsp = argsubparsers.add_parser(
    "hash-object", help="Compute object ID and optionally creates a blob from a file"
)
argsp.add_argument("path", help="Path to file")
argsp.add_argument(
    "-w", "--write",
    action="store_true",
    help="Actually write the object into the database"
)
argsp.set_defaults(func=libwyag.cmd_hash_object)

# cat-file
argsp = argsubparsers.add_parser("cat-file",
                                 help="Provide content of repository objects")
argsp.add_argument("type",
                   metavar="type",
                   choices=["blob", "commit", "tag", "tree"],
                   help="Specify the type")
argsp.add_argument("object",
                   metavar="object",
                   help="The object to display")
argsp.set_defaults(func=libwyag.cmd_cat_file)


def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)
    args.func(args)   # <-- simpler and extensible


if __name__ == "__main__":
    main()
