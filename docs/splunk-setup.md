# Splunk Setup for CM3 Audit Logs

## Audit log source

CM3 emits structured JSON audit events to a configurable path:

- Env var: `AUDIT_LOG_PATH`
- Default: `logs/audit.log`

Configure your Splunk Universal Forwarder to monitor the chosen path.

Example `inputs.conf`:

```ini
[monitor:///opt/cm3-batch-automations/logs/audit.log]
disabled = false
index = cm3_batch
sourcetype = cm3:audit:json
```

## Recommended index and sourcetype

- **index**: `cm3_batch`
- **sourcetype**: `cm3:audit:json`

Use `INDEXED_EXTRACTIONS=json` (or equivalent parsing config) if your Splunk deployment requires explicit JSON extraction.

## Sample searches

### All completed test runs (last 24h)

```spl
index=cm3_batch sourcetype=cm3:audit:json event_type="cli.test_run.completed" earliest=-24h
| stats count by detail.status
```

### API auth failures by source IP

```spl
index=cm3_batch sourcetype=cm3:audit:json event_type="api.auth_failure" earliest=-7d
| stats count by source_ip, detail.path
| sort -count
```

### Failed runs with report location

```spl
index=cm3_batch sourcetype=cm3:audit:json event_type="cli.test_run.completed" detail.status="FAILED"
| table timestamp detail.suite detail.env detail.run_id detail.report_path detail.report_hash
```
