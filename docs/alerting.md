# Alerting

Model Canary supports multiple alerting channels.

## Channels

| Channel | ID | Setup |
|---------|-----|-------|
| Log | `log` | Built-in, no setup needed |
| Slack | `slack` | Webhook URL |
| Discord | `discord` | Webhook URL |
| GitHub Issues | `github` | Token + repository |
| Webhook | `webhook` | URL + optional HMAC secret |

## Configuration

```yaml
alerting:
  enabled: true
  channels:
    - slack
    - discord
  min_severity: medium
  cooldown_minutes: 60
  max_alerts_per_run: 10
```

## Testing

```bash
model-canary alerts --test
```
