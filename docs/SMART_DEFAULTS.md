# Smart Defaults for Elicitation Forms

The Smart Defaults system learns from user patterns and organizational conventions to pre-populate elicitation forms, significantly improving user experience by reducing repetitive input.

## Overview

Smart Defaults uses three layers of intelligence to suggest values:

1. **Template-based defaults** - Pre-configured best practices for common operations
2. **Pattern-based defaults** - Learned from analyzing existing schemas and naming conventions
3. **History-based defaults** - Learned from user choices and feedback

## Features

### Pattern Recognition
- Detects naming conventions (camelCase, snake_case, hyphenated, etc.)
- Identifies common prefixes and suffixes
- Analyzes field patterns across schemas
- Learns organizational conventions

### Context-Aware Suggestions
- Different defaults for dev/staging/production environments
- Team and project-specific preferences
- Compatibility mode suggestions based on context
- Smart field type detection

### Learning Engine
- Tracks user choices and acceptance rates
- Adjusts confidence scores based on feedback
- Persists learning data locally
- Privacy-aware with configurable exclusions

### Seamless Integration
- Works transparently with existing elicitation forms
- Shows confidence scores and reasoning
- Allows users to accept or override suggestions
- No changes required to existing workflows

## How It Works

When an elicitation form is created, the Smart Defaults system:

1. **Analyzes the context** - Determines the operation type and environment
2. **Gathers suggestions** - Combines template, pattern, and history-based defaults
3. **Enhances the form** - Adds suggested values with confidence scores
4. **Presents to user** - Shows suggestions in the elicitation form
5. **Learns from feedback** - Records whether suggestions were accepted

## Configuration

Smart Defaults can be configured via environment variables or a JSON configuration file.

### Environment Variables

```bash
# Enable/disable smart defaults
export SMART_DEFAULTS_ENABLED=true

# Enable specific features
export SMART_DEFAULTS_PATTERN_RECOGNITION=true
export SMART_DEFAULTS_LEARNING=true

# Set confidence thresholds
export SMART_DEFAULTS_MIN_CONFIDENCE=0.3
export SMART_DEFAULTS_AUTO_FILL_CONFIDENCE=0.7

# Privacy settings
export SMART_DEFAULTS_ANONYMIZE=false
export SMART_DEFAULTS_EXCLUDED_FIELDS=password,secret,token
export SMART_DEFAULTS_EXCLUDED_CONTEXTS=sensitive-data

# UI settings
export SMART_DEFAULTS_SHOW_CONFIDENCE=true
```

### Configuration File

Create `~/.kafka-schema-mcp/smart_defaults_config.json`:

```json
{
  "enabled": true,
  "enable_pattern_recognition": true,
  "enable_learning": true,
  "min_confidence_for_suggestion": 0.3,
  "min_confidence_for_auto_fill": 0.7,
  "show_confidence_scores": true,
  "excluded_fields": ["password", "secret", "token"],
  "environment_defaults": {
    "production": {
      "compatibility": "FULL",
      "dry_run": true
    },
    "development": {
      "compatibility": "NONE",
      "dry_run": false
    }
  }
}
```

## Usage Examples

### Schema Registration with Smart Defaults

When registering a schema, the system will suggest:
- Subject naming based on detected patterns
- Compatibility mode based on context
- Common fields based on schema type

```python
# The elicitation form will show:
# Subject: [order-events-created] (suggested - 85% confidence)
# Compatibility: [BACKWARD] (suggested - 70% confidence)
# Schema Type: [AVRO] (default - 80% confidence)
```

### Migration with Learned Preferences

For migrations, the system remembers your preferences:
- Preserve IDs setting from previous migrations
- Dry run preferences
- Version migration patterns

### Context Creation with Metadata

When creating contexts, get suggestions for:
- Environment detection from context name
- Owner based on similar contexts
- Tags from organizational patterns

## Privacy and Security

Smart Defaults is designed with privacy in mind:

- **Local storage only** - All learning data is stored locally
- **Configurable exclusions** - Exclude sensitive fields from learning
- **No external data sharing** - Patterns stay within your organization
- **Anonymization option** - Can anonymize stored values
- **Retention controls** - Automatic cleanup of old data

### Excluded Fields

By default, the following field patterns are excluded from learning:
- password
- secret
- key
- token
- credential

### Data Retention

Learning data is retained for 90 days by default. This can be configured via:
```bash
export SMART_DEFAULTS_RETENTION_DAYS=30
```

## Implementation Details

### Pattern Detection

The system uses regular expressions and statistical analysis to detect:
- Naming conventions (75%+ occurrence rate)
- Common prefixes/suffixes (40%+ occurrence rate)
- Field type patterns (appears in 2+ schemas)

### Confidence Scoring

Confidence scores are calculated based on:
- **Pattern strength** - How consistently a pattern appears
- **Historical acceptance** - How often users accept suggestions
- **Recency** - Recent choices are weighted higher
- **Context match** - Higher confidence for exact context matches

### Learning Algorithm

The learning engine uses:
- **Incremental updates** - Learns from each user interaction
- **Decay factor** - Old patterns gradually lose weight
- **Feedback loops** - Acceptance/rejection affects future confidence

## Troubleshooting

### Suggestions Not Appearing

1. Check if smart defaults are enabled:
   ```bash
   export SMART_DEFAULTS_ENABLED=true
   ```

2. Verify minimum occurrences are met:
   - Patterns need 2+ occurrences by default
   - Adjust via `minimum_occurrences_for_pattern`

3. Check confidence thresholds:
   - Suggestions below `min_confidence_for_suggestion` are hidden

### Incorrect Suggestions

1. Clear learning history:
   ```bash
   rm -rf ~/.kafka-schema-mcp/smart_defaults/learning_history.json
   ```

2. Exclude problematic fields:
   ```bash
   export SMART_DEFAULTS_EXCLUDED_FIELDS=field1,field2
   ```

3. Adjust confidence thresholds for better accuracy

### Performance Issues

1. Disable caching if needed:
   ```json
   {"enable_caching": false}
   ```

2. Reduce pattern tracking:
   ```json
   {"max_patterns_to_track": 20}
   ```

3. Use async learning:
   ```json
   {"async_learning": true}
   ```

## Future Enhancements

- Machine learning models for better predictions
- Cross-registry pattern sharing (opt-in)
- A/B testing for suggestion effectiveness
- Integration with schema documentation
- Custom pattern definitions
- Team-specific learning profiles

## Contributing

To contribute to Smart Defaults development:

1. Check the implementation in `smart_defaults.py`
2. Review integration in `smart_defaults_integration.py`
3. Add tests to `tests/test_smart_defaults.py`
4. Update configuration in `smart_defaults_config.py`

## License

This feature is part of the Kafka Schema Registry MCP server and follows the same license terms.
