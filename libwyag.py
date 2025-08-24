import os
import configparser
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
    else:
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

    assert repo_dir(repo, "branches", mkdir=True)
    assert repo_dir(repo, "objects", mkdir=True)
    assert repo_dir(repo, "refs", "tags", mkdir=True)
    assert repo_dir(repo, "refs", "heads", mkdir=True)

    with open(repo_file(repo, "description"), "w") as f:
        f.write("Unnamed repository; edit this file 'description' to name the repository.\n")

    with open(repo_file(repo, "HEAD"), "w") as f:
        f.write("ref: refs/heads/master\n")

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

    def serialize(self):
        raise Exception("Unimplemented!")

    def deserialize(self, data):
        raise Exception("Unimplemented!")

    def init(self):
        pass


class GitBlob(GitObject):
    fmt = b"blob"
    def serialize(self): return self.blobdata
    def deserialize(self, data): self.blobdata = data


# Commit object ----------------------------
def kvlm_parse(raw, start=0, dct=None):
    if not dct: dct = dict()

    spc = raw.find(b' ', start)
    nl = raw.find(b'\n', start)

    if (spc < 0) or (nl < spc):
        assert nl == start
        dct[None] = raw[start+1:]
        return dct

    key = raw[start:spc]
    end = start
    while True:
        end = raw.find(b'\n', end+1)
        if raw[end+1] != ord(' '): break
    value = raw[spc+1:end].replace(b'\n ', b'\n')

    if key in dct:
        if type(dct[key]) == list:
            dct[key].append(value)
        else:
            dct[key] = [dct[key], value]
    else:
        dct[key] = value

    return kvlm_parse(raw, start=end+1, dct=dct)


def kvlm_serialize(kvlm):
    ret = b''
    for k in kvlm.keys():
        if k is None: continue
        val = kvlm[k]
        if type(val) != list: val = [val]
        for v in val:
            ret += k + b' ' + (v.replace(b'\n', b'\n ')) + b'\n'
    ret += b'\n' + kvlm[None]
    return ret


class GitCommit(GitObject):
    fmt = b'commit'
    def deserialize(self, data): self.kvlm = kvlm_parse(data)
    def serialize(self): return kvlm_serialize(self.kvlm)
    def init(self): self.kvlm = dict()


# Object read/write ----------------------------
def object_write(repo, obj, actually_write=True):
    data = obj.serialize()
    result = obj.fmt + b" " + str(len(data)).encode() + b"\x00" + data
    sha = hashlib.sha1(result).hexdigest()

    if actually_write:
        path = repo_file(repo, "objects", sha[0:2], sha[2:], mkdir=True)
        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(zlib.compress(result))
    return sha


def object_read(repo, sha):
    path = repo_file(repo, "objects", sha[0:2], sha[2:])
    with open(path, "rb") as f:
        raw = zlib.decompress(f.read())

    x = raw.find(b' ')
    fmt = raw[0:x]

    y = raw.find(b'\x00', x)
    size = int(raw[x:y].decode("ascii"))
    if size != len(raw) - y - 1:
        raise Exception(f"Malformed object {sha}: bad length")

    body = raw[y+1:]

    if fmt == b'blob':
        c = GitBlob
    elif fmt == b'commit':
        c = GitCommit
    else:
        raise Exception(f"Unknown type {fmt.decode('ascii')} for object {sha}")

    return c(body)


# ----------------------------
# Commands
# ----------------------------
def cmd_init(args):
    repo_create(args.path)
    print(f"Initialized empty WYAG repository in {os.path.join(args.path, '.git')}")


def object_hash(fd, fmt, repo=None):
    data = fd.read()
    if fmt == b'blob':
        obj = GitBlob(data)
    elif fmt == b'commit':
        obj = GitCommit(data)
    else:
        raise Exception(f"Unknown type {fmt}!")
    return object_write(repo, obj, actually_write=(repo is not None))


def cmd_hash_object(args):
    if args.write:
        repo = repo_find()
    else:
        repo = None
    with open(args.path, "rb") as fd:
        sha = object_hash(fd, args.type.encode(), repo)
        print(sha)


def cat_file(repo, obj, fmt=None):
    obj = object_read(repo, object_find(repo, obj, fmt=fmt))
    sys.stdout.buffer.write(obj.serialize())


def cmd_cat_file(args):
    repo = repo_find()
    cat_file(repo, args.object, fmt=args.type.encode())


def object_find(repo, name, fmt=None, follow=True):
    return name


def repo_find(path=".", required=True):
    path = os.path.realpath(path)
    if os.path.isdir(os.path.join(path, ".git")):
        return GitRepository(path)

    parent = os.path.realpath(os.path.join(path, ".."))
    if parent == path:
        if required: raise Exception("No git directory.")
        else: return None
    return repo_find(parent, required)


# ----------------------------
# Log command
# ----------------------------
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
    if "\n" in message: message = message[:message.index("\n")]

    print(f"  c_{sha} [label=\"{sha[0:7]}: {message}\"]")
    assert commit.fmt == b'commit'

    if not b'parent' in commit.kvlm.keys():
        return
    parents = commit.kvlm[b'parent']
    if type(parents) != list: parents = [parents]

    for p in parents:
        p = p.decode("ascii")
        print(f"  c_{sha} -> c_{p};")
        log_graphviz(repo, p, seen)
