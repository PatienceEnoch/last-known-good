# Security and responsible use

Network Flight Recorder is a defensive administration and observability project.

- Run it only on systems and networks you own or are explicitly authorized to administer.
- The collector performs no port scan, exploitation, credential collection, or packet capture.
- Review snapshots before sharing them; hostnames, internal addresses, routes, and service names
  can reveal sensitive infrastructure details.
- Never commit real production snapshots, credentials, private keys, tokens, or customer data.
- Automated remediation is intentionally outside the MVP. Future actions must require explicit
  approval, use an allowlist, preserve an audit trail, and support rollback.

Report security concerns privately to the repository owner rather than opening a public issue
containing sensitive details.

