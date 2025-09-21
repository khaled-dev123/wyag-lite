import libwyag

# Find the repository
repo = libwyag.repo_find()

# Create a commit manually
commit = libwyag.GitCommit()
commit.kvlm[b'tree'] = b"78de91050ec6dcb77404f03e00759c6268b8648d"  # SHA of your blob
commit.kvlm[None] = b"Initial commit\n"

# Write commit to repo
commit_sha = libwyag.object_write(repo, commit)

# Update HEAD to point to this commit
libwyag.ref_create(repo, "refs/heads/master", commit_sha)

print("Commit SHA:", commit_sha)
