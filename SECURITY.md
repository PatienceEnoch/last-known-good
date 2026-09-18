# Security and responsible use

Network Flight Recorder is a defensive administration and observability project.

## Operating boundaries

- Run it only on systems and networks you own or are explicitly authorized to administer.
- The collector performs no port scan, exploitation, credential collection, or packet capture.
- Review snapshots before sharing them; hostnames, internal addresses, routes, and service names
  can reveal sensitive infrastructure details.
- Never commit real production snapshots, credentials, private keys, tokens, or customer data.
- Use deterministic redaction before sharing or uploading diagnostic evidence.
- Retention cleanup is a dry run unless `--apply` is explicitly supplied.

## Current remediation safety model

Network Flight Recorder can generate remediation plans, but a plan does not execute by itself.

- Every plan is marked as requiring approval.
- Execution requires an explicit `approved=True` decision.
- Action IDs must pass a fixed allowlist before an executor is called.
- The included executor supports only `renew_network_configuration` in the isolated Docker lab.
- The lab builds one exact `ip route replace default` command from a known-good snapshot; it does
  not accept an arbitrary shell command.
- A post-change snapshot verifies that the expected gateway and interface were restored.
- A remediation report preserves the before, known-good, and after states.

Generic remediation of production hosts is not implemented. Automatic rollback after failed
verification is also not implemented and remains a roadmap item.

## Docker lab boundary

The demonstration lab grants `NET_ADMIN` only to its isolated container so it can remove the
container's default route and, in the guarded-recovery demonstration, restore it. It does not use
host networking. A cleanup trap restarts the container if a demonstration exits early. Review
`compose.yaml`, `lab/run_demo.sh`, `lab/run_guarded_recovery.sh`, and `docs/docker-lab.md` before
running failure injection.

## Reporting concerns

Report security concerns privately to the repository owner rather than opening a public issue
containing sensitive details.
