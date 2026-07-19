# Configuration

Model Canary supports YAML, JSON, and TOML configuration files.

## File Locations

Model Canary looks for configuration in this order:

1. `model-canary.yml` (or `.yaml`, `.json`, `.toml`)
2. `.model-canary.yml` (hidden file)
3. Environment variables with prefix `MODEL_CANARY_`
4. CLI flags

## Configuration Reference

### Top-Level Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `version` | string | `"1"` | Configuration version |
| `project_name` | string | `"model-canary"` | Project identifier |
| `providers` | array | `[]` | LLM provider configurations |
| `test_suites` | array | `[]` | Test suite definitions |
| `storage` | object | `{backend: "sqlite"}` | Storage configuration |
| `alerting` | object | `{enabled: true}` | Alerting configuration |
| `schedule` | string | `null` | Default cron schedule |
| `plugins` | array | `[]` | Plugin module paths |
| `log_level` | string | `"INFO"` | Logging level |
| `max_concurrent` | int | `5` | Maximum concurrent requests |
| `similarity_threshold` | float | `0.85` | Cosine similarity threshold |
| `drift_threshold` | float | `0.1` | Minimum drift score to report |
| `privacy_mode` | bool | `false` | Redact sensitive data in logs |
| `embedding_model` | string | `"all-MiniLM-L6-v2"` | Sentence transformer model |

### Provider Configuration

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `name` | string | yes | Provider reference name |
| `type` | string | yes | Provider type (e.g., `openai`, `anthropic`) |
| `api_key` | string | conditional | API key (can use env vars) |
| `base_url` | string | no | Custom API base URL |
| `default_model` | string | no | Default model to use |
| `models` | array | no | Allowed models list |
| `timeout` | int | no | Request timeout in seconds |

### Prompt Configuration

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `name` | string | yes | Unique prompt identifier |
| `prompt` | string | yes | The prompt text to send |
| `description` | string | no | Human-readable description |
| `expected_output` | string | no | Expected output for comparison |
| `acceptable_outputs` | array | no | List of acceptable outputs |
| `required_json_schema` | object | no | JSON schema for validation |
| `severity` | string | no | `low`, `medium`, `high`, `critical` |
| `category` | string | no | Prompt category for organization |
| `evaluators` | array | no | Evaluators to run on output |
| `model` | string | no | Specific model for this prompt |
| `max_tokens` | int | no | Max tokens for response |
| `temperature` | float | no | Temperature for generation |
