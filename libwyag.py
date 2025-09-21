import os
import configparser
import hashlib
import zlib
import sys
import re

# ============================================================
# Repository Abstraction
# ============================================================

class GitRepository:
    """A git repository"""

    def __init__(self, path, force=False):
        self.worktree = path
        self.gitdir = os.path.join(path, ".git")

        if not (force or os.path.isdir(self.gitdir)):
            raise Exception(f"Not a Git repository {path}")

        # Read configuration
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
    return os.path.join(repo.gitdir, *path)


def repo_file(repo, *path, mkdir=False):
    if repo_dir(repo, *path[:-1], mkdir=mkdir):
        return repo_path(repo, *path)


def repo_dir(repo, *path, mkdir=False):
    path = repo_path(repo, *path)
    if os.path.exists(path):
        if os.path.isdir(path):
            return path
        else:
            raise Exception(f"Not a directory {path}")
    if mkdir:
        os.makedirs(path)
        return path
    return None


def repo_default_config():
    ret = configparser.ConfigParser()
    ret.add_section("core")
    ret.set("core", "repositoryformatversion", "0")
    ret.set("core", "filemode", "false")
    ret.set("core", "bare", "false")
    return ret


def repo_create(path):
    repo = GitRepository(path, True)

    if os.path.exists(repo.worktree):
        if not os.path.isdir(repo.worktree):
            raise Exception(f"{path} is not a directory!")
        if os.path.exists(repo.gitdir) and os.listdir(repo.gitdir):
            raise Exception(f"{path} is not empty!")
    else:
        os.makedirs(repo.worktree)

    # Directories
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


def repo_find(path=".", required=True):
    path = os.path.realpath(path)
    if os.path.isdir(os.path.join(path, ".git")):
        return GitRepository(path)

    parent = os.path.realpath(os.path.join(path, ".."))
    if parent == path:
        if required:
            raise Exception("No git directory.")
        return None
    return repo_find(parent, required)


# ============================================================
# Git Objects
# ============================================================

class GitObject:
    """Base class for Git objects"""
    def __init__(self, data=None):
        if data is not None:
            self.deserialize(data)
        else:
            self.init()

    def serialize(self):
        raise Exception("Unimplemented!")

    def deserialize(self, data):
        raise Exception("Unimplemented!")

    def init(self):
        pass


class GitBlob(GitObject):
    fmt = b"blob"

    def serialize(self):
        return self.blobdata

    def deserialize(self, data):
        self.blobdata = data


class GitCommit(GitObject):
    fmt = b"commit"

    def deserialize(self, data):
        self.kvlm = kvlm_parse(data)

    def serialize(self):
        return kvlm_serialize(self.kvlm)

    def init(self):
        self.kvlm = dict()


class GitTreeLeaf:
    def __init__(self, mode, path, sha):
        self.mode = mode
        self.path = path
        self.sha = sha


class GitTree(GitObject):
    fmt = b"tree"

    def deserialize(self, data):
        self.items = tree_parse(data)

    def serialize(self):
        return tree_serialize(self)

    def init(self):
        self.items = []


class GitTag(GitObject):
    fmt = b'tag'

    def deserialize(self, data):
        self.kvlm = kvlm_parse(data)

    def serialize(self):
        return kvlm_serialize(self.kvlm)

    def init(self):
        self.kvlm = dict()


# ============================================================
# Object read/write
# ============================================================

def object_write(repo, obj, actually_write=True):
    data = obj.serialize()
    result = obj.fmt + b" " + str(len(data)).encode() + b"\x00" + data
    sha = hashlib.sha1(result).hexdigest()

    if actually_write:
        path = repo_file(repo, "objects", sha[:2], sha[2:], mkdir=True)
        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(zlib.compress(result))
    return sha



def object_resolve(repo, name):
    """Resolve a name to one or more object hashes in repo."""
    candidates = []
    hashRE = re.compile(r"^[0-9A-Fa-f]{4,40}$")

    if not name.strip():
        return None

    # HEAD literal
    if name == "HEAD":
        return [ref_resolve(repo, "HEAD")]

    # Short or full hash
    if hashRE.match(name):
        name = name.lower()
        prefix = name[:2]
        path = repo_dir(repo, "objects", prefix, mkdir=False)
        if path:
            rem = name[2:]
            for f in os.listdir(path):
                if f.startswith(rem):
                    candidates.append(prefix + f)

    # Check tags
    as_tag = ref_resolve(repo, "refs/tags/" + name)
    if as_tag:
        candidates.append(as_tag)

    # Check branches
    as_branch = ref_resolve(repo, "refs/heads/" + name)
    if as_branch:
        candidates.append(as_branch)

    # Check remote branches
    as_remote = ref_resolve(repo, "refs/remotes/" + name)
    if as_remote:
        candidates.append(as_remote)

    return candidates



def object_read(repo, sha):
    path = repo_file(repo, "objects", sha[:2], sha[2:])
    with open(path, "rb") as f:
        raw = zlib.decompress(f.read())

    x = raw.find(b' ')
    fmt = raw[0:x]

    y = raw.find(b'\x00', x)
    size = int(raw[x:y].decode("ascii"))
    if size != len(raw) - y - 1:
        raise Exception(f"Malformed object {sha}: bad length")

    body = raw[y + 1:]

    if fmt == b'blob': cls = GitBlob
    elif fmt == b'commit': cls = GitCommit
    elif fmt == b'tree': cls = GitTree
    elif fmt == b'tag': cls = GitTag
    else:
        raise Exception(f"Unknown type {fmt.decode('ascii')} for object {sha}")

    return cls(body)


def object_find(repo, name, fmt=None, follow=True):
    sha_list = object_resolve(repo, name)

    if not sha_list:
        raise Exception(f"No such reference {name}.")

    if len(sha_list) > 1:
        raise Exception(f"Ambiguous reference {name}: Candidates are:\n - " + "\n - ".join(sha_list))

    sha = sha_list[0]

    if not fmt:
        return sha

    while True:
        obj = object_read(repo, sha)

        if obj.fmt == fmt:
            return sha

        if not follow:
            return None

        # Follow tags
        if obj.fmt == b'tag':
            sha = obj.kvlm[b'object'].decode("ascii")
        elif obj.fmt == b'commit' and fmt == b'tree':
            sha = obj.kvlm[b'tree'].decode("ascii")
        else:
            return None


# ============================================================
# KVLM parse/serialize
# ============================================================

def kvlm_parse(raw, start=0, dct=None):
    if dct is None:
        dct = dict()

    spc = raw.find(b' ', start)
    nl = raw.find(b'\n', start)

    if (spc < 0) or (nl < spc):
        assert nl == start
        dct[None] = raw[start + 1:]
        return dct

    key = raw[start:spc]
    end = start
    while True:
        end = raw.find(b'\n', end + 1)
        if raw[end + 1] != ord(' '):
            break
    value = raw[spc + 1:end].replace(b'\n ', b'\n')

    if key in dct:
        if isinstance(dct[key], list):
            dct[key].append(value)
        else:
            dct[key] = [dct[key], value]
    else:
        dct[key] = value

    return kvlm_parse(raw, start=end + 1, dct=dct)


def kvlm_serialize(kvlm):
    ret = b''
    for k, v in kvlm.items():
        if k is None:
            continue
        if not isinstance(v, list):
            v = [v]
        for val in v:
            ret += k + b' ' + val.replace(b'\n', b'\n ') + b'\n'
    ret += b'\n' + kvlm[None]
    return ret


# ============================================================
# Tree functions
# ============================================================

def tree_parse_one(raw, start=0):
    x = raw.find(b' ', start)
    assert x - start in (5, 6)

    mode = raw[start:x]
    if len(mode) == 5:
        mode = b"0" + mode

    y = raw.find(b'\x00', x)
    path = raw[x + 1:y]
    raw_sha = int.from_bytes(raw[y + 1:y + 21], "big")
    sha = format(raw_sha, "040x")

    return y + 21, GitTreeLeaf(mode, path.decode("utf8"), sha)


def tree_parse(raw):
    pos = 0
    ret = []
    while pos < len(raw):
        pos, leaf = tree_parse_one(raw, pos)
        ret.append(leaf)
    return ret


def tree_leaf_sort_key(leaf):
    if leaf.mode.startswith(b"10"):
        return leaf.path
    return leaf.path + "/"


def tree_serialize(obj):
    obj.items.sort(key=tree_leaf_sort_key)
    ret = b''
    for leaf in obj.items:
        ret += leaf.mode
        ret += b' '
        ret += leaf.path.encode("utf8")
        ret += b'\x00'
        sha = int(leaf.sha, 16)
        ret += sha.to_bytes(20, byteorder="big")
    return ret


# ============================================================
# Reference functions
# ============================================================

def ref_resolve(repo, ref):
    path = repo_file(repo, ref)
    if not os.path.isfile(path):
        return None
    with open(path, "r") as f:
        data = f.read().strip()
    if data.startswith("ref: "):
        return ref_resolve(repo, data[5:])
    return data


def ref_list(repo, path=None):
    if not path:
        path = repo_dir(repo, "refs")

    ret = dict()
    for f in sorted(os.listdir(path)):
        can = os.path.join(path, f)
        if os.path.isdir(can):
            ret[f] = ref_list(repo, can)
        else:
            ret[f] = ref_resolve(repo, can)
    return ret


def ref_create(repo, ref_name, sha):
    path = repo_file(repo, ref_name, mkdir=True)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as fp:
        fp.write(sha + "\n")


# ============================================================
# Tag functions
# ============================================================

def tag_create(repo, name, ref, create_tag_object=False):
    sha = object_find(repo, ref)
    if create_tag_object:
        tag = GitTag()
        tag.kvlm = dict()
        tag.kvlm[b'object'] = sha.encode()
        tag.kvlm[b'type'] = b'commit'
        tag.kvlm[b'tag'] = name.encode()
        tag.kvlm[b'tagger'] = b'Wyag <wyag@example.com>'
        tag.kvlm[None] = b"A tag generated by wyag\n"
        tag_sha = object_write(repo, tag)
        ref_create(repo, f"tags/{name}", tag_sha)
    else:
        ref_create(repo, f"tags/{name}", sha)


# ============================================================
# Command Implementations
# ============================================================

def cmd_init(args):
    repo_create(args.path)
    print(f"Initialized empty WYAG repository in {os.path.join(args.path, '.git')}")


def cmd_hash_object(args):
    repo = repo_find() if args.write else None
    with open(args.path, "rb") as fd:
        data = fd.read()
        if args.type == "blob":
            obj = GitBlob(data)
        elif args.type == "commit":
            obj = GitCommit(data)
        elif args.type == "tree":
            obj = GitTree(data)
        else:
            raise Exception(f"Unknown type {args.type}")
        sha = object_write(repo, obj, actually_write=(repo is not None))
        print(sha)


def cmd_cat_file(args):
    repo = repo_find()
    sha = object_find(repo, args.object, fmt=args.type.encode())
    obj = object_read(repo, sha)
    sys.stdout.buffer.write(obj.serialize())


def cmd_log(args):
    repo = repo_find()
    print("digraph wyaglog{")
    print("  node[shape=rect]")
    log_graphviz(repo, object_find(repo, args.commit), set())
    print("}")


def log_graphviz(repo, sha, seen):
    if sha in seen: return
    seen.add(sha)

    commit = object_read(repo, sha)
    message = commit.kvlm[None].decode("utf8").strip()
    message = message.replace("\\", "\\\\").replace("\"", "\\\"")
    if "\n" in message:
        message = message[:message.index("\n")]

    print(f"  c_{sha} [label=\"{sha[:7]}: {message}\"]")

    if b'parent' not in commit.kvlm:
        return

    parents = commit.kvlm[b'parent']
    if not isinstance(parents, list):
        parents = [parents]

    for p in parents:
        p = p.decode("ascii")
        print(f"  c_{sha} -> c_{p};")
        log_graphviz(repo, p, seen)


def cmd_ls_tree(args):
    repo = repo_find()
    ls_tree(repo, args.tree, args.recursive)


def ls_tree(repo, ref, recursive=False, prefix=""):
    sha = object_find(repo, ref, fmt=b"tree")
    obj = object_read(repo, sha)

    for item in obj.items:
        if len(item.mode) == 5:
            typ = item.mode[0:1]
        else:
            typ = item.mode[0:2]

        if typ == b'04': typ_str = "tree"
        elif typ == b'10': typ_str = "blob"
        elif typ == b'12': typ_str = "blob"
        elif typ == b'16': typ_str = "commit"
        else:
            raise Exception(f"Weird tree leaf mode {item.mode}")

        path_out = os.path.join(prefix, item.path)
        if not (recursive and typ_str == "tree"):
            print(f"{item.mode.decode('ascii')} {typ_str} {item.sha}\t{path_out}")
        else:
            ls_tree(repo, item.sha, recursive, path_out)


def cmd_checkout(args):
    repo = repo_find()
    obj = object_read(repo, object_find(repo, args.commit))

    if obj.fmt == b'commit':
        obj = object_read(repo, obj.kvlm[b'tree'].decode("ascii"))

    if os.path.exists(args.path):
        if not os.path.isdir(args.path):
            raise Exception(f"Not a directory: {args.path}")
        if os.listdir(args.path):
            raise Exception(f"Not empty: {args.path}")
    else:
        os.makedirs(args.path)

    tree_checkout(repo, obj, os.path.realpath(args.path))


def tree_checkout(repo, tree, path):
    for item in tree.items:
        obj = object_read(repo, item.sha)
        dest = os.path.join(path, item.path)

        if obj.fmt == b'tree':
            os.mkdir(dest)
            tree_checkout(repo, obj, dest)
        elif obj.fmt == b'blob':
            with open(dest, "wb") as f:
                f.write(obj.blobdata)


def cmd_show_ref(args):
    repo = repo_find()
    refs = ref_list(repo)
    show_ref(repo, refs, prefix="refs")


def show_ref(repo, refs, with_hash=True, prefix=""):
    if prefix:
        prefix += "/"
    for k, v in refs.items():
        if isinstance(v, str):
            if with_hash:
                print(f"{v} {prefix}{k}")
            else:
                print(f"{prefix}{k}")
        else:
            show_ref(repo, v, with_hash, f"{prefix}{k}")


def cmd_tag(args):
    repo = repo_find()
    if args.name:
        tag_create(repo, args.name, args.object, create_tag_object=args.create_tag_object)
    else:
        refs = ref_list(repo)
        if "tags" in refs:
            show_ref(repo, refs["tags"], with_hash=False)
