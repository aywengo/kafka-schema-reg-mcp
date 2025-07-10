"""
Patch for interactive_tools.py to integrate Smart Defaults

This file shows the necessary changes to integrate smart defaults into
the existing interactive tools. Apply these changes to interactive_tools.py.
"""

# Add these imports at the top of interactive_tools.py
from smart_defaults_integration import (
    get_smart_defaults_enhancer,
    create_enhanced_schema_field_elicitation,
    create_enhanced_migration_elicitation,
    create_enhanced_context_metadata_elicitation,
    create_enhanced_export_elicitation,
)

# Replace the existing elicitation request creation calls with enhanced versions

# Example 1: In register_schema_interactive(), replace:
# OLD:
# elicitation_request = create_schema_field_elicitation(context=context, existing_fields=existing_fields)
# NEW:
enhancer = get_smart_defaults_enhancer(registry_manager)
elicitation_request = await create_enhanced_schema_field_elicitation(
    enhancer=enhancer,
    context=context,
    existing_fields=existing_fields,
    record_type=schema_definition.get("name") if schema_definition else None
)

# Example 2: In migrate_context_interactive(), replace:
# OLD:
# elicitation_request = create_migration_preferences_elicitation(
#     source_registry=source_registry,
#     target_registry=target_registry,
#     context=context,
# )
# NEW:
enhancer = get_smart_defaults_enhancer(registry_manager)
elicitation_request = await create_enhanced_migration_elicitation(
    enhancer=enhancer,
    source_registry=source_registry,
    target_registry=target_registry,
    context=context,
    previous_migrations=None  # Could be loaded from history
)

# Example 3: In create_context_interactive(), replace:
# OLD:
# elicitation_request = create_context_metadata_elicitation(context_name=context)
# NEW:
enhancer = get_smart_defaults_enhancer(registry_manager)
elicitation_request = await create_enhanced_context_metadata_elicitation(
    enhancer=enhancer,
    context_name=context,
    similar_contexts=None  # Could be loaded from registry
)

# Example 4: In export_global_interactive(), replace:
# OLD:
# elicitation_request = create_export_preferences_elicitation(operation_type="global_export")
# NEW:
enhancer = get_smart_defaults_enhancer(registry_manager)
elicitation_request = await create_enhanced_export_elicitation(
    enhancer=enhancer,
    operation_type="global_export",
    context=context,
    previous_exports=None  # Could be loaded from history
)

# Add feedback processing after receiving elicitation responses
# After each successful elicitation response, add:
if response and response.complete:
    # Process feedback for learning
    await enhancer.process_response_feedback(
        response=response,
        request=elicitation_request,
        operation="<operation_name>",  # e.g., "create_schema", "migrate_context", etc.
        context=context
    )
    
    # ... rest of the existing response processing code

# Enable smart defaults globally at server startup
# Add this to the main server initialization:
from smart_defaults_integration import enable_smart_defaults_globally
enable_smart_defaults_globally(registry_manager)
