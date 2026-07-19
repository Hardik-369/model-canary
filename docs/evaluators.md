# Evaluators

Model Canary includes 11 built-in evaluators.

## Built-in Evaluators

| Evaluator | ID | Description |
|-----------|-----|-------------|
| JSON Validator | `json` | Validates JSON output against schema |
| Regex Matcher | `regex` | Matches output against regex patterns |
| Similarity | `similarity` | Embedding-based semantic similarity |
| Exact Match | `exact_match` | Exact string comparison |
| Contains | `contains` | Check for required/forbidden substrings |
| Python Assertion | `python` | Custom Python assertion code |
| LLM Judge | `llm_judge` | LLM-as-judge evaluation |
| BLEU | `bleu` | BLEU score for translation quality |
| ROUGE | `rouge` | ROUGE score for summarization quality |

## Usage

```yaml
prompts:
  - name: test-json
    prompt: "Return JSON with name and age"
    evaluators:
      - json
```

## Custom Evaluators

Create a class implementing the `Evaluator` interface and register via entry points.
