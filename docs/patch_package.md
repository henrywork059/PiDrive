# Batch 3 — R53 candidate package integrity (first implementation)

Source baseline: 8c979f34533da2e7f6051925cba797957863a734, PR #87, prior CI 45359079601 (4/4). Versions unchanged: shared release tooling only. Reviewed PiSD 0.11.27–24, PiServer 0.4.31–28, piTrainer 0.11.11–8 notes. No runtime or persisted files changed.

Use only independently reviewed full Git commit SHAs, with both commits and full Git history available in a local checkout. From repository root:

```sh
python tools/patch_package.py build --component PiSD --base BASE_SHA --target TARGET_SHA --archive PiSD_patch.zip
python tools/patch_package.py dry-run --component PiSD --base BASE_SHA --target TARGET_SHA --archive PiSD_patch.zip
```

For dry-run, use a checkout at the exact baseline commit. The manifest is reconstructed from trusted Git objects, not trusted merely because it is in the archive. A forward target version and new target patch note are required; recent baseline note hashes must match. Only regular changed/new text files on explicit component paths are supported. Config, model/recording/generated directories, credentials-named files, binaries, deletes and mode changes fail closed; no unchanged files are packaged. Exact reuse of a different historical file snapshot from the last five file-changing commits is rejected. Review source diffs manually for semantic rollback and secrets; file path checks cannot detect embedded credentials. Normalized checkout line endings may require a clean byte-exact checkout. Dry-run checks archive members and exact installed preimages; it performs no extraction, writes or deployment. The tool does not authenticate Git commits, authorize a target, guarantee rollback-free semantics, or apply patches. A Git checkout is required; arbitrary ZIP-installed trees are not supported yet.

Tests: python -m unittest discover -s tests -p test_patch_package.py -v. New exact-commit CI required; no hardware, native Windows or release acceptance claimed. The CI manifest job also builds and validates actual current candidate patches in disposable Git baseline worktrees. Batch 3 stays incomplete until F9 clean installs and the full exact-candidate regression gate pass.
