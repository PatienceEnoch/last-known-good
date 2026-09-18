# Security and responsible use

Network Flight Recorder is a defensive administration and observability project. Its collection and recovery features are intentionally narrow.

## Operating boundaries

- Run NFR only on systems and networks you own or are explicitly authorized to administer.
- The collector does not perform port scanning, exploitation, credential collection, or packet capture.
- Review snapshots before sharing them. Hostnames, internal addresses, routes, and service names can expose infrastructure details.
- Never commit production snapshots, credentials, private keys, tokens, or customer data.
- Use deterministic redaction before sharing or uploading diagnostic evidence.
- Retention cleanup is a dry run unless `--apply` is explicitly supplied.

## Remediation safety model

A remediation plan never executes by itself.

- Every plan requires approval.
- Execution requires an explicit `approved=True` decision.
- The requested action ID must pass a fixed allowlist before an executor is called.
- The included executor supports only `renew_network_configuration` in the isolated Docker lab.
- The lab builds one exact `ip route replace default` command from a known-good snapshot; it does not accept arbitrary shell commands.
- A post-change snapshot verifies that the expected gateway and interface were restored.
- The remediation report preserves the before, known-good, and after states.
- If post-remediation verification fails, the isolated lab can execute a rollback path that restores the pre-remediation route state.

Generic production remediation is not implemented. The rollback path is part of the controlled lab workflow, not a general-purpose production recovery engine.

## Docker lab boundary

The lab grants `NET_ADMIN` only to its isolated recorder container. It does not use host networking.

Failure-injection scripts may remove the container's default route, exercise guarded restoration, or intentionally force a failed verification to test rollback. Cleanup logic restores the disposable environment if a demonstration exits early.

Review `compose.yaml`, the scripts under `lab/`, and [docs/docker-lab.md](docs/docker-lab.md) before running failure injection.

## Reporting concerns

Report security concerns privately to the repository owner rather than opening a public issue that contains sensitive infrastructure details.
