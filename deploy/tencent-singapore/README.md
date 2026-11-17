# Tencent Singapore CPA runtime

This deployment records the existing, verified 2 CPU / 4 GB runtime. The core
is pinned to v7.2.95, commit f71ec0eb, matching the source mirrored in this
repository. It deliberately does not upgrade or restart the core or OpenClaw.

Run `python3 deploy.py <git-commit>` on the Kubernetes host after copying this
directory. The script verifies host size, binary hash, the running proxy, and
per-account Antigravity routing. It installs the non-secret proxy supervisor
and ensures the startup ConfigMap invokes it before starting CPA. Repeated
execution is safe. A deployed revision is recorded on the persistent volume.

The proxy listener is loopback-only. Its node credentials remain exclusively in
the existing persistent `gemini-egress/config.yaml`, with mode 0600. They are
not included in Git. The CPA config, OAuth records, API and management keys,
plugin data and usage databases are also excluded. This deployment requires
the existing initialized runtime; it is not a credential bootstrap utility.

The installed plugins are CPA Usage Statistics 0.6.1 and CPA Quota Estimator
0.21.4. Their data stays under `/home/node/.cli-proxy-api/plugin-data`. The
OpenClaw proxy already exposes `/v0/resource/plugins/` and its `/cpa/` alias.

Validate after deployment with a small streaming Responses request through
CPA-helper and an Antigravity request. Never print or commit request keys.
Rollback a changed supervisor using its adjacent timestamped backup. ConfigMap
backups, if changed, are stored in the host's private `.cpa-maintenance` folder.
