import os
import configparser
import libwyag
import hashlib, zlib
import sys
# ----------------------------
# Repository Abstraction
# ----------------------------
class GitRepository(object):
    """A git repository"""

    worktree = None
    gitdir = None
    conf = None

    def __init__(self, path, force=False):
        self.worktree = path
        self.gitdir = os.path.join(path, ".git")

        if not (force or os.path.isdir(self.gitdir)):
            raise Exception(f"Not a Git repository {path}")

        # Read configuration file in .git/config
        self.conf = configparser.ConfigParser()
        cf = repo_file(self, "config")

        if cf and os.path.exists(cf):
            self.conf.read([cf])
        elif not force:
            raise Exception("Configuration file missing")

        if not force:
            vers = int(self.conf.get("core", "repositoryformatversion"))
            if vers != 0:
                raise Exception(f"Unsupported repositoryformatversion: {vers}")


def repo_path(repo, *path):
    """Compute path under repo's gitdir."""
    return os.path.join(repo.gitdir, *path)


def repo_file(repo, *path, mkdir=False):
    """Same as repo_path, but create dirname(*path) if absent."""
    if repo_dir(repo, *path[:-1], mkdir=mkdir):
        return repo_path(repo, *path)


def repo_dir(repo, *path, mkdir=False):
    """Same as repo_path, but mkdir *path if absent if mkdir is True."""
    path = repo_path(repo, *path)

    if os.path.exists(path):
        if os.path.isdir(path):
            return path
        else:
            raise Exception(f"Not a directory {path}")

    if mkdir:
        os.makedirs(path)
        return path
    else:
        return None


def repo_default_config():
    """Default configuration for a new repository"""
    ret = configparser.ConfigParser()

    ret.add_section("core")
    ret.set("core", "repositoryformatversion", "0")
    ret.set("core", "filemode", "false")
    ret.set("core", "bare", "false")

    return ret


def repo_create(path):
    """Create a new repository at path."""
    repo = GitRepository(path, True)

    # Ensure worktree is valid
    if os.path.exists(repo.worktree):
        if not os.path.isdir(repo.worktree):
            raise Exception(f"{path} is not a directory!")
        if os.path.exists(repo.gitdir) and os.listdir(repo.gitdir):
            raise Exception(f"{path} is not empty!")
    else:
        os.makedirs(repo.worktree)

    # Create directory structure
    assert repo_dir(repo, "branches", mkdir=True)
    assert repo_dir(repo, "objects", mkdir=True)
    assert repo_dir(repo, "refs", "tags", mkdir=True)
    assert repo_dir(repo, "refs", "heads", mkdir=True)

    # description
    with open(repo_file(repo, "description"), "w") as f:
        f.write("Unnamed repository; edit this file 'description' to name the repository.\n")

    # HEAD
    with open(repo_file(repo, "HEAD"), "w") as f:
        f.write("ref: refs/heads/master\n")

    # config
    with open(repo_file(repo, "config"), "w") as f:
        config = repo_default_config()
        config.write(f)

    return repo

# ----------------------------
# Object System
# ----------------------------
class GitObject(object):
    def __init__(self, data=None):
        if data is not None:
            self.deserialize(data)
        else:
            self.init()

    def serialize(self, repo):
        """Return bytes representing the object.
           Must be implemented by subclasses.
        """
        raise Exception("Unimplemented!")

    def deserialize(self, data):
        """Initialize object from raw bytes.
           Must be implemented by subclasses.
        """
        raise Exception("Unimplemented!")

    def init(self):
        """Create a new, empty object (default = do nothing)."""
        pass
class GitBlob(GitObject):
    fmt = b"blob"

    def serialize(self):
        return self.blobdata

    def deserialize(self, data):
        self.blobdata = data


def object_write(repo, obj, actually_write=True):
    """Write object to repo. Return SHA-1 object ID."""
    data = obj.serialize()   # <-- remove repo here
    result = obj.fmt + b" " + str(len(data)).encode() + b"\x00" + data

    sha = hashlib.sha1(result).hexdigest()

    if actually_write:
        path = repo_file(repo, "objects", sha[0:2], sha[2:], mkdir=True)
        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(zlib.compress(result))

    return sha




# ----------------------------
# Command Implementations
# ----------------------------


def cmd_init(args):
    repo_create(args.path)
    print(f"Initialized empty WYAG repository in {os.path.join(args.path, '.git')}")

# Stubs for other commands (so wyag.py runs without crashing)
def cmd_add(args): print("add: not implemented yet")
def cmd_cat_file(args): print("cat-file: not implemented yet")
def cmd_check_ignore(args): print("check-ignore: not implemented yet")
def cmd_checkout(args): print("checkout: not implemented yet")
def cmd_commit(args): print("commit: not implemented yet")
def cmd_log(args): print("log: not implemented yet")
def cmd_ls_files(args): print("ls-files: not implemented yet")
def cmd_ls_tree(args): print("ls-tree: not implemented yet")
def cmd_rev_parse(args): print("rev-parse: not implemented yet")
def cmd_rm(args): print("rm: not implemented yet")
def cmd_show_ref(args): print("show-ref: not implemented yet")
def cmd_status(args): print("status: not implemented yet")
def cmd_tag(args): print("tag: not implemented yet")
def cmd_hash_object(args):
    if args.write:
        repo = repo_find()
    else:
        repo = None

    with open(args.path, "rb") as fd:
        sha = object_hash(fd, args.type.encode(), repo)
        print(sha)


def object_hash(fd, fmt, repo=None):
    """Hash object, writing it to repo if provided."""
    data = fd.read()

    # Choose constructor according to fmt argument
    if fmt == b'commit':
        obj = GitCommit(data)
    elif fmt == b'tree':
        obj = GitTree(data)
    elif fmt == b'tag':
        obj = GitTag(data)
    elif fmt == b'blob':
        obj = GitBlob(data)
    else:
        raise Exception(f"Unknown type {fmt}!")

    return object_write(repo, obj, actually_write=(repo is not None))

def cmd_cat_file(args):
    repo = repo_find()
    cat_file(repo, args.object, fmt=args.type.encode())


def cat_file(repo, obj, fmt=None):
    obj = object_read(repo, object_find(repo, obj, fmt=fmt))
    sys.stdout.buffer.write(obj.serialize(repo))


def object_find(repo, name, fmt=None, follow=True):
    # For now, just return the hash unmodified
    return name

def repo_find(path=".", required=True):
    path = os.path.realpath(path)

    if os.path.isdir(os.path.join(path, ".git")):
        return GitRepository(path)

    # go up one directory
    parent = os.path.realpath(os.path.join(path, ".."))

    if parent == path:
        # reached filesystem root
        if required:
            raise Exception("No git directory.")
        else:
            return None

    return repo_find(parent, required)
