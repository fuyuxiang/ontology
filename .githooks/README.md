# Git Hooks

This repository uses versioned hooks in `.githooks`.

Enable them in a clone with:

```sh
git config core.hooksPath .githooks
```

The `post-commit` hook warns when a commit leaves additional uncommitted
changes behind. It does not create commits automatically because running
`git commit` inside Git hooks can recurse and can commit unrelated work.
