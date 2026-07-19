# GitHub Actions

## Scheduled Monitoring

```yaml
name: Model Canary
on:
  schedule:
    - cron: "*/30 * * * *"
  workflow_dispatch:

jobs:
  canary:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: model-canary/action@v1
        with:
          config: model-canary.yml
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
```

## CI Integration

```yaml
name: CI
on: [push, pull_request]
jobs:
  canary:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Canary Tests
        uses: model-canary/action@v1
        with:
          fail-on-drift: true
```
