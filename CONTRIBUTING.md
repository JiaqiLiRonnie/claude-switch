# Contributing

- Pure Python 3 standard library, single file `claude-switch`. Keep it that way.
- Every command that changes anything must be a dry run by default and take `--go`.
- Never delete: move to Trash or `_backups/`.
- Add or update a sandbox test in `tests/` for any behaviour change. Tests run against a temp directory and must never touch a real `~/Library/Application Support/Claude`.

```sh
for t in tests/test_*.py; do python3 "$t" || exit 1; done
```

Bug reports are most useful with the output of `claude-switch status` and `claude-switch doctor` (redact titles if needed).
