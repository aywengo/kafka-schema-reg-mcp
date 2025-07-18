# Configuration Guide - Smart Defaults

This document provides configuration details for the Smart Defaults feature of the Kafka Schema Registry MCP Server.

## Overview

Smart Defaults learns from user patterns and organizational conventions to pre-populate elicitation forms. This feature can be configured via environment variables or JSON configuration files.

## Quick Start

### Enable Smart Defaults

```bash
export SMART_DEFAULTS_ENABLED=true
```

That's it! Smart Defaults will now learn from your usage patterns and provide intelligent suggestions.

## Environment Variables

All configuration options can be set via environment variables:

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SMART_DEFAULTS_ENABLED` | `true` | Enable/disable the entire Smart Defaults system |
| `SMART_DEFAULTS_PATTERN_RECOGNITION` | `true` | Enable pattern recognition for naming conventions |
| `SMART_DEFAULTS_LEARNING` | `true` | Enable learning from user choices |
| `SMART_DEFAULTS_STORAGE_PATH` | `~/.kafka-schema-mcp/smart_defaults` | Path for storing learned patterns |

### Confidence Thresholds

| Variable | Default | Description |
|----------|---------|-------------|
| `SMART_DEFAULTS_MIN_CONFIDENCE` | `0.3` | Minimum confidence to show a suggestion |
| `SMART_DEFAULTS_AUTO_FILL_CONFIDENCE` | `0.7` | Minimum confidence to auto-fill a field |

### Privacy Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SMART_DEFAULTS_ANONYMIZE` | `false` | Anonymize stored values |
| `SMART_DEFAULTS_EXCLUDED_FIELDS` | `password,secret,token` | Comma-separated list of fields to exclude from learning |
| `SMART_DEFAULTS_EXCLUDED_CONTEXTS` | `""` | Comma-separated list of contexts to exclude |

### UI Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SMART_DEFAULTS_SHOW_CONFIDENCE` | `true` | Show confidence scores in suggestions |

## JSON Configuration File

For more complex configurations, create a file at `~/.kafka-schema-mcp/smart_defaults_config.json`:

```json
{
  "enabled": true,
  "enable_pattern_recognition": true,
  "enable_learning": true,
  "enable_field_suggestions": true,
  
  "learning_storage_path": "/path/to/storage",
  "learning_retention_days": 90,
  "minimum_occurrences_for_pattern": 2,
  
  "min_confidence_for_suggestion": 0.3,
  "min_confidence_for_auto_fill": 0.7,
  "high_confidence_threshold": 0.8,
  
  "pattern_detection_threshold": 0.4,
  "max_patterns_to_track": 50,
  "pattern_cache_ttl_seconds": 300,
  
  "anonymize_values": false,
  "excluded_fields": ["password", "secret", "key", "token", "credential"],
  "excluded_contexts": [],
  
  "show_confidence_scores": true,
  "show_suggestion_source": true,
  "show_reasoning": true,
  "max_field_suggestions": 10,
  
  "enable_caching": true,
  "cache_size": 100,
  "async_learning": true,
  
  "environment_defaults": {
    "production": {
      "compatibility": "FULL",
      "dry_run": true,
      "preserve_ids": true
    },
    "staging": {
      "compatibility": "BACKWARD",
      "dry_run": true,
      "preserve_ids": true
    },
    "development": {
      "compatibility": "NONE",
      "dry_run": false,
      "preserve_ids": false
    }
  },
  
  "enable_multi_step_learning": true,
  "suggestion_decay_factor": 0.95,
  "enable_cross_context_learning": false
}
```

## Configuration Precedence

1. Environment variables (highest priority)
2. JSON configuration file
3. Default values (lowest priority)

## Environment-Specific Defaults

Smart Defaults can apply different suggestions based on the detected environment:

- **Production**: Conservative settings (FULL compatibility, dry_run enabled)
- **Staging**: Balanced settings (BACKWARD compatibility)
- **Development**: Flexible settings (NONE compatibility, dry_run disabled)

Environment detection is based on context names containing keywords like "prod", "staging", "dev".

## Privacy Considerations

### Excluded Fields

By default, the following field patterns are excluded from learning:
- password
- secret
- key
- token
- credential

Add more exclusions via `SMART_DEFAULTS_EXCLUDED_FIELDS`.

### Data Retention

Learning data is retained for 90 days by default. Adjust with:
```bash
export SMART_DEFAULTS_RETENTION_DAYS=30
```

### Local Storage Only

All learning data is stored locally. No data is sent to external services.

## Performance Tuning

### Caching

Control caching behavior:
```json
{
  "enable_caching": true,
  "cache_size": 100,
  "pattern_cache_ttl_seconds": 300
}
```

### Pattern Limits

Limit pattern tracking for performance:
```json
{
  "max_patterns_to_track": 50,
  "minimum_occurrences_for_pattern": 2
}
```

### Async Learning

Enable asynchronous learning to avoid blocking operations:
```json
{
  "async_learning": true
}
```

## Monitoring

Check Smart Defaults status:

```python
# In the MCP server logs, you'll see:
# Smart Defaults initialized with settings:
#   - Pattern Recognition: enabled
#   - Learning Engine: enabled
#   - Field Suggestions: enabled
#   - Storage Path: /home/user/.kafka-schema-mcp/smart_defaults
#   - Confidence Thresholds: suggestion=0.3, auto-fill=0.7
#   - Privacy: anonymize=no, excluded_fields=5
```

## Troubleshooting

### Suggestions Not Appearing

1. Ensure Smart Defaults is enabled
2. Check minimum confidence thresholds
3. Verify pattern has occurred at least 2 times
4. Check logs for initialization errors

### Clearing Learning Data

Remove all learned patterns:
```bash
rm -rf ~/.kafka-schema-mcp/smart_defaults/learning_history.json
```

### Disabling for Specific Operations

Disable learning for sensitive contexts:
```bash
export SMART_DEFAULTS_EXCLUDED_CONTEXTS=sensitive-data,private-schemas
```

## Examples

### Basic Setup

```bash
# Enable with default settings
export SMART_DEFAULTS_ENABLED=true

# Start the server
python kafka_schema_registry_unified_mcp.py
```

### Production Setup

```bash
# Conservative settings for production
export SMART_DEFAULTS_ENABLED=true
export SMART_DEFAULTS_AUTO_FILL_CONFIDENCE=0.9
export SMART_DEFAULTS_ANONYMIZE=true
export SMART_DEFAULTS_EXCLUDED_CONTEXTS=pii,sensitive
```

### Development Setup

```bash
# Aggressive learning for development
export SMART_DEFAULTS_ENABLED=true
export SMART_DEFAULTS_MIN_CONFIDENCE=0.1
export SMART_DEFAULTS_AUTO_FILL_CONFIDENCE=0.5
export SMART_DEFAULTS_RETENTION_DAYS=180
```

## Integration with Docker

When using Docker, pass environment variables:

```bash
docker run -e SMART_DEFAULTS_ENABLED=true \
           -e SMART_DEFAULTS_SHOW_CONFIDENCE=true \
           -v ~/.kafka-schema-mcp:/app/.kafka-schema-mcp \
           aywengo/kafka-schema-reg-mcp:latest
```

Or use Docker Compose:

```yaml
services:
  mcp-server:
    image: aywengo/kafka-schema-reg-mcp:latest
    environment:
      - SMART_DEFAULTS_ENABLED=true
      - SMART_DEFAULTS_MIN_CONFIDENCE=0.3
      - SMART_DEFAULTS_AUTO_FILL_CONFIDENCE=0.7
    volumes:
      - ~/.kafka-schema-mcp:/app/.kafka-schema-mcp
```
