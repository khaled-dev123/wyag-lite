#!/usr/bin/env python3
import argparse
import sys
import os
import libwyag   # your core WYAG implementation


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
sp = argsubparsers.add_parser("log", help="Display history of a given commit.")
sp.add_argument("commit",
                default="HEAD",
                nargs="?",
                help="Commit to start at.")
sp.set_defaults(func=libwyag.cmd_log)


# --- ls-tree ---
sp = argsubparsers.add_parser("ls-tree", help="Pretty-print a tree object.")
sp.add_argument("-r",
                dest="recursive",
                action="store_true",
                help="Recurse into sub-trees")
sp.add_argument("tree",
                help="A tree-ish object.")
sp.set_defaults(func=libwyag.cmd_ls_tree)


# --- checkout ---
sp = argsubparsers.add_parser("checkout", help="Checkout a commit inside of a directory.")
sp.add_argument("commit", help="The commit or tree to checkout.")
sp.add_argument("path", help="The EMPTY directory to checkout on.")
sp.set_defaults(func=libwyag.cmd_checkout)


# ======================================================
# Reference handling helpers
# ======================================================
def ref_resolve(repo, ref):
    """Resolve a ref (HEAD, branch, etc.) to a SHA-1, following indirections."""
    path = libwyag.repo_file(repo, ref)
    if not os.path.isfile(path):
        return None
    with open(path, "r") as fp:
        data = fp.read().strip()
    if data.startswith("ref: "):
        return ref_resolve(repo, data[5:])
    else:
        return data  # direct SHA-1


def ref_list(repo, path=None):
    """Return all refs in a dict (recursively)."""
    if not path:
        path = libwyag.repo_dir(repo, "refs")
    if path is None:
        return {}
    ret = {}
    for f in sorted(os.listdir(path)):
        can = os.path.join(path, f)
        if os.path.isdir(can):
            ret[f] = ref_list(repo, can)
        else:
            ret[f] = ref_resolve(repo, can)
    return ret


# --- show-ref ---
def show_ref(repo, refs, with_hash=True, prefix=""):
    """Pretty-print refs recursively."""
    if prefix:
        prefix = prefix + "/"
    for k, v in refs.items():
        if isinstance(v, str):
            if with_hash:
                print(f"{v} {prefix}{k}")
            else:
                print(f"{prefix}{k}")
        else:
            show_ref(repo, v, with_hash=with_hash, prefix=f"{prefix}{k}")


def cmd_show_ref(args):
    repo = libwyag.repo_find()
    refs = ref_list(repo)
    show_ref(repo, refs, prefix="refs")


sp = argsubparsers.add_parser("show-ref", help="List references.")
sp.set_defaults(func=cmd_show_ref)


# --- tag ---
def cmd_tag(args):
    repo = libwyag.repo_find()
    if args.name:
        libwyag.tag_create(repo,
                          args.name,
                          args.object,
                          create_tag_object=args.create_tag_object)
    else:
        refs = ref_list(repo)
        if "tags" in refs:
            show_ref(repo, refs["tags"], with_hash=False)


sp = argsubparsers.add_parser("tag", help="List and create tags")
sp.add_argument("-a",
                action="store_true",
                dest="create_tag_object",
                help="Whether to create a tag object")
sp.add_argument("name",
                nargs="?",
                help="The new tag's name")
sp.add_argument("object",
                default="HEAD",
                nargs="?",
                help="The object the new tag will point to")
sp.set_defaults(func=cmd_tag)


# --- rev-parse ---
def cmd_rev_parse(args):
    repo = libwyag.repo_find()
    fmt = args.type.encode() if args.type else None
    print(libwyag.object_find(repo, args.name, fmt=fmt, follow=True))


sp = argsubparsers.add_parser(
    "rev-parse",
    help="Parse revision (or other objects) identifiers"
)
sp.add_argument("--wyag-type",
                metavar="type",
                dest="type",
                choices=["blob", "commit", "tag", "tree"],
                default=None,
                help="Specify the expected type")
sp.add_argument("name",
                help="The name to parse")
sp.set_defaults(func=cmd_rev_parse)


# ======================================================
# Main entrypoint
# ======================================================
def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
