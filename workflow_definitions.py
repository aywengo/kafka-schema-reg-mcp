#!/usr/bin/env python3
"""
Pre-defined Multi-Step Workflows for Schema Registry Operations

This module contains workflow definitions for complex Schema Registry operations
that require multi-step user guidance.

Workflows:
1. Schema Migration Wizard - Guide users through schema migration
2. Context Reorganization - Help reorganize schemas across contexts
3. Disaster Recovery Setup - Configure DR strategies
4. Schema Evolution Assistant - Guide through schema evolution with breaking change analysis
"""

from typing import Any, Dict, List, Optional

from elicitation import ElicitationField, ElicitationType
from multi_step_elicitation import (
    MultiStepWorkflow,
    WorkflowStep,
)

# Global workflow cache
_cached_workflows = None


def create_schema_migration_workflow() -> MultiStepWorkflow:
    """Create the Schema Migration Wizard workflow."""

    steps = {
        # Step 1: Select migration type
        "migration_type": WorkflowStep(
            id="migration_type",
            title="Schema Migration Wizard - Migration Type",
            description="What type of migration would you like to perform?",
            elicitation_type=ElicitationType.CHOICE,
            fields=[
                ElicitationField(
                    name="migration_type",
                    type="choice",
                    description="Select the type of migration",
                    options=["single_schema", "bulk_migration", "context_migration"],
                    required=True,
                )
            ],
            next_steps={
                "migration_type": {
                    "single_schema": "single_schema_selection",
                    "bulk_migration": "bulk_selection",
                    "context_migration": "context_selection",
                }
            },
        ),
        # Step 2a: Single schema selection
        "single_schema_selection": WorkflowStep(
            id="single_schema_selection",
            title="Select Schema",
            description="Enter the schema details for migration",
            elicitation_type=ElicitationType.FORM,
            fields=[
                ElicitationField(
                    name="source_registry",
                    type="choice",
                    description="Source registry",
                    options=["development", "staging", "production"],
                    required=True,
                ),
                ElicitationField(
                    name="schema_name",
                    type="text",
                    description="Schema name (subject)",
                    placeholder="e.g., com.example.User-value",
                    required=True,
                ),
                ElicitationField(
                    name="version",
                    type="text",
                    description="Version to migrate (leave empty for latest)",
                    placeholder="e.g., 1, 2, latest",
                    required=False,
                    default="latest",
                ),
            ],
            next_steps={"default": "migration_options"},
        ),
        # Step 2b: Bulk selection
        "bulk_selection": WorkflowStep(
            id="bulk_selection",
            title="Bulk Schema Selection",
            description="Select schemas for bulk migration",
            elicitation_type=ElicitationType.FORM,
            fields=[
                ElicitationField(
                    name="source_registry",
                    type="choice",
                    description="Source registry",
                    options=["development", "staging", "production"],
                    required=True,
                ),
                ElicitationField(
                    name="schema_pattern",
                    type="text",
                    description="Schema name pattern (regex supported)",
                    placeholder="e.g., com.example.*, *-value",
                    required=True,
                ),
                ElicitationField(
                    name="include_all_versions",
                    type="confirmation",
                    description="Include all versions of matching schemas?",
                    default="false",
                    required=True,
                ),
                ElicitationField(
                    name="context_filter",
                    type="text",
                    description="Filter by context (optional)",
                    placeholder="e.g., production, staging",
                    required=False,
                ),
            ],
            next_steps={"default": "migration_options"},
        ),
        # Step 2c: Context selection
        "context_selection": WorkflowStep(
            id="context_selection",
            title="Context Selection",
            description="Select context for migration",
            elicitation_type=ElicitationType.FORM,
            fields=[
                ElicitationField(
                    name="source_registry",
                    type="choice",
                    description="Source registry",
                    options=["development", "staging", "production"],
                    required=True,
                ),
                ElicitationField(
                    name="source_context",
                    type="text",
                    description="Source context name",
                    placeholder="e.g., production, staging",
                    required=True,
                ),
                ElicitationField(
                    name="include_dependencies",
                    type="confirmation",
                    description="Include schema dependencies?",
                    default="true",
                    required=True,
                ),
            ],
            next_steps={"default": "migration_options"},
        ),
        # Step 3: Migration options
        "migration_options": WorkflowStep(
            id="migration_options",
            title="Migration Options",
            description="Configure migration options",
            elicitation_type=ElicitationType.FORM,
            fields=[
                ElicitationField(
                    name="target_registry",
                    type="choice",
                    description="Target registry",
                    options=["development", "staging", "production"],
                    required=True,
                ),
                ElicitationField(
                    name="target_context",
                    type="text",
                    description="Target context (leave empty to keep same)",
                    placeholder="e.g., production-backup",
                    required=False,
                ),
                ElicitationField(
                    name="preserve_ids",
                    type="confirmation",
                    description="Preserve schema IDs? (Note: Preserving IDs requires admin access and may cause conflicts)",
                    default="false",
                    required=True,
                ),
                ElicitationField(
                    name="conflict_resolution",
                    type="choice",
                    description="How to handle existing schemas?",
                    options=["skip", "overwrite", "version"],
                    default="skip",
                    required=True,
                ),
                ElicitationField(
                    name="create_backup",
                    type="confirmation",
                    description="Create backup before migration?",
                    default="true",
                    required=True,
                ),
            ],
            next_steps={"default": "review_confirm"},
        ),
        # Step 4: Review and confirm
        "review_confirm": WorkflowStep(
            id="review_confirm",
            title="Review Migration Plan",
            description="Review your migration settings before proceeding",
            elicitation_type=ElicitationType.CONFIRMATION,
            fields=[
                ElicitationField(
                    name="dry_run",
                    type="confirmation",
                    description="Perform dry run first?",
                    default="true",
                    required=True,
                ),
                ElicitationField(
                    name="confirm_migration",
                    type="confirmation",
                    description="Proceed with migration? (Warning: This operation may modify schemas in the target registry)",
                    required=True,
                ),
            ],
            next_steps={"confirm_migration": {"true": "finish", "false": "migration_type"}},  # Start over
        ),
    }

    return MultiStepWorkflow(
        id="schema_migration_wizard",
        name="Schema Migration Wizard",
        description="Guide users through schema migration process",
        steps=steps,
        initial_step_id="migration_type",
        metadata={"estimated_duration": "2-5 minutes", "difficulty": "intermediate", "requires_auth": True},
    )


def create_context_reorganization_workflow() -> MultiStepWorkflow:
    """Create the Context Reorganization workflow."""

    steps = {
        # Step 1: Select reorganization strategy
        "reorg_strategy": WorkflowStep(
            id="reorg_strategy",
            title="Context Reorganization - Strategy",
            description="How would you like to reorganize your contexts?",
            elicitation_type=ElicitationType.CHOICE,
            fields=[
                ElicitationField(
                    name="strategy",
                    type="choice",
                    description="Select reorganization strategy",
                    options=["merge", "split", "rename", "restructure"],
                    required=True,
                )
            ],
            next_steps={
                "strategy": {
                    "merge": "merge_contexts",
                    "split": "split_context",
                    "rename": "rename_context",
                    "restructure": "restructure_plan",
                }
            },
        ),
        # Step 2a: Merge contexts
        "merge_contexts": WorkflowStep(
            id="merge_contexts",
            title="Select Contexts to Merge",
            description="Select the contexts you want to merge",
            elicitation_type=ElicitationType.FORM,
            fields=[
                ElicitationField(
                    name="source_contexts",
                    type="text",
                    description="Source contexts (comma-separated)",
                    placeholder="e.g., dev-team-a, dev-team-b",
                    required=True,
                ),
                ElicitationField(
                    name="target_context",
                    type="text",
                    description="Target context name",
                    placeholder="e.g., development",
                    required=True,
                ),
                ElicitationField(
                    name="handle_duplicates",
                    type="choice",
                    description="How to handle duplicate schemas?",
                    options=["keep_newest", "keep_oldest", "prompt"],
                    default="prompt",
                    required=True,
                ),
            ],
            next_steps={"default": "mapping_review"},
        ),
        # Step 2b: Split context
        "split_context": WorkflowStep(
            id="split_context",
            title="Define Context Split",
            description="Define how to split the context",
            elicitation_type=ElicitationType.FORM,
            fields=[
                ElicitationField(name="source_context", type="text", description="Context to split", required=True),
                ElicitationField(
                    name="split_criteria",
                    type="choice",
                    description="Split based on",
                    options=["namespace", "prefix", "custom_rules"],
                    required=True,
                ),
                ElicitationField(
                    name="target_contexts",
                    type="text",
                    description="Target context names (comma-separated)",
                    placeholder="e.g., context-a, context-b, context-c",
                    required=True,
                ),
            ],
            next_steps={"default": "split_rules"},
        ),
        # Step 2c: Rename context
        "rename_context": WorkflowStep(
            id="rename_context",
            title="Rename Context",
            description="Specify context rename mapping",
            elicitation_type=ElicitationType.FORM,
            fields=[
                ElicitationField(
                    name="rename_mappings",
                    type="text",
                    description="Rename mappings (old:new, comma-separated)",
                    placeholder="e.g., dev:development, prod:production",
                    required=True,
                ),
                ElicitationField(
                    name="update_references",
                    type="confirmation",
                    description="Update all schema references?",
                    default="true",
                    required=True,
                ),
            ],
            next_steps={"default": "review_changes"},
        ),
        # Step 3: Split rules (conditional)
        "split_rules": WorkflowStep(
            id="split_rules",
            title="Define Split Rules",
            description="Define rules for splitting schemas",
            elicitation_type=ElicitationType.FORM,
            fields=[
                ElicitationField(
                    name="split_rules",
                    type="text",
                    description="Split rules (pattern:context, one per line)",
                    placeholder="com.example.user.*:user-context\ncom.example.order.*:order-context",
                    required=True,
                ),
                ElicitationField(
                    name="default_context",
                    type="text",
                    description="Default context for unmatched schemas",
                    required=True,
                ),
            ],
            next_steps={"default": "mapping_review"},
        ),
        # Step 4: Mapping review
        "mapping_review": WorkflowStep(
            id="mapping_review",
            title="Review Schema Mappings",
            description="Review how schemas will be reorganized",
            elicitation_type=ElicitationType.FORM,
            fields=[
                ElicitationField(
                    name="generate_report",
                    type="confirmation",
                    description="Generate detailed mapping report?",
                    default="true",
                    required=True,
                ),
                ElicitationField(
                    name="test_mode",
                    type="confirmation",
                    description="Run in test mode first?",
                    default="true",
                    required=True,
                ),
            ],
            next_steps={"default": "execute_reorg"},
        ),
        # Step 5: Execute reorganization
        "execute_reorg": WorkflowStep(
            id="execute_reorg",
            title="Execute Reorganization",
            description="Final confirmation before reorganization",
            elicitation_type=ElicitationType.CONFIRMATION,
            fields=[
                ElicitationField(
                    name="backup_first",
                    type="confirmation",
                    description="Create full backup before reorganization?",
                    default="true",
                    required=True,
                ),
                ElicitationField(
                    name="proceed",
                    type="confirmation",
                    description=(
                        "Proceed with context reorganization? (Warning: This will modify "
                        "context structure across registries)"
                    ),
                    required=True,
                ),
            ],
            next_steps={"proceed": {"true": "finish", "false": "reorg_strategy"}},
        ),
        # Alternative path: Complete restructure
        "restructure_plan": WorkflowStep(
            id="restructure_plan",
            title="Define New Structure",
            description="Define your new context structure",
            elicitation_type=ElicitationType.FORM,
            fields=[
                ElicitationField(
                    name="structure_definition",
                    type="text",
                    description="New context structure (YAML or JSON)",
                    placeholder=(
                        "contexts:\n  - name: production\n    patterns: ['*.prod', 'prod.*']\n"
                        "  - name: development\n    patterns: ['*.dev', 'dev.*']"
                    ),
                    required=True,
                ),
                ElicitationField(
                    name="migration_strategy",
                    type="choice",
                    description="Migration approach",
                    options=["gradual", "immediate", "parallel"],
                    default="gradual",
                    required=True,
                ),
            ],
            next_steps={"default": "mapping_review"},
        ),
        # Alternative review path
        "review_changes": WorkflowStep(
            id="review_changes",
            title="Review Changes",
            description="Review the planned changes",
            elicitation_type=ElicitationType.CONFIRMATION,
            fields=[
                ElicitationField(
                    name="confirm_changes", type="confirmation", description="Apply these changes?", required=True
                )
            ],
            next_steps={"confirm_changes": {"true": "finish", "false": "reorg_strategy"}},
        ),
    }

    return MultiStepWorkflow(
        id="context_reorganization",
        name="Context Reorganization",
        description="Reorganize schemas across contexts",
        steps=steps,
        initial_step_id="reorg_strategy",
        metadata={
            "estimated_duration": "5-10 minutes",
            "difficulty": "advanced",
            "requires_auth": True,
            "requires_admin": True,
        },
    )


def create_disaster_recovery_workflow() -> MultiStepWorkflow:
    """Create the Disaster Recovery Setup workflow."""

    steps = {
        # Step 1: Choose DR strategy
        "dr_strategy": WorkflowStep(
            id="dr_strategy",
            title="Disaster Recovery Setup - Strategy",
            description="Choose your disaster recovery strategy",
            elicitation_type=ElicitationType.CHOICE,
            fields=[
                ElicitationField(
                    name="dr_strategy",
                    type="choice",
                    description="Select DR strategy",
                    options=["active_passive", "active_active", "backup_restore", "multi_region"],
                    required=True,
                )
            ],
            next_steps={
                "dr_strategy": {
                    "active_passive": "active_passive_config",
                    "active_active": "active_active_config",
                    "backup_restore": "backup_config",
                    "multi_region": "multi_region_config",
                }
            },
        ),
        # Step 2a: Active-Passive configuration
        "active_passive_config": WorkflowStep(
            id="active_passive_config",
            title="Active-Passive Configuration",
            description="Configure active-passive disaster recovery",
            elicitation_type=ElicitationType.FORM,
            fields=[
                ElicitationField(
                    name="primary_registry",
                    type="choice",
                    description="Primary registry",
                    options=["production", "us-east-1", "eu-west-1"],
                    required=True,
                ),
                ElicitationField(
                    name="standby_registry",
                    type="choice",
                    description="Standby registry",
                    options=["dr-production", "us-west-2", "eu-central-1"],
                    required=True,
                ),
                ElicitationField(
                    name="replication_interval",
                    type="choice",
                    description="Replication interval",
                    options=["realtime", "1min", "5min", "15min", "hourly"],
                    default="5min",
                    required=True,
                ),
                ElicitationField(
                    name="failover_mode",
                    type="choice",
                    description="Failover mode",
                    options=["manual", "automatic"],
                    default="manual",
                    required=True,
                ),
            ],
            next_steps={"default": "sync_options"},
        ),
        # Step 2b: Active-Active configuration
        "active_active_config": WorkflowStep(
            id="active_active_config",
            title="Active-Active Configuration",
            description="Configure active-active disaster recovery",
            elicitation_type=ElicitationType.FORM,
            fields=[
                ElicitationField(
                    name="active_registries",
                    type="text",
                    description="Active registries (comma-separated)",
                    placeholder="e.g., us-east-1, us-west-2, eu-west-1",
                    required=True,
                ),
                ElicitationField(
                    name="conflict_resolution",
                    type="choice",
                    description="Conflict resolution strategy",
                    options=["last_write_wins", "version_vector", "manual"],
                    default="last_write_wins",
                    required=True,
                ),
                ElicitationField(
                    name="sync_topology",
                    type="choice",
                    description="Synchronization topology",
                    options=["mesh", "hub_spoke", "ring"],
                    default="mesh",
                    required=True,
                ),
            ],
            next_steps={"default": "sync_options"},
        ),
        # Step 2c: Backup configuration
        "backup_config": WorkflowStep(
            id="backup_config",
            title="Backup Configuration",
            description="Configure backup and restore settings",
            elicitation_type=ElicitationType.FORM,
            fields=[
                ElicitationField(
                    name="backup_schedule",
                    type="choice",
                    description="Backup schedule",
                    options=["hourly", "daily", "weekly", "custom"],
                    default="daily",
                    required=True,
                ),
                ElicitationField(
                    name="backup_location",
                    type="text",
                    description="Backup storage location",
                    placeholder="e.g., s3://my-bucket/schema-backups",
                    required=True,
                ),
                ElicitationField(
                    name="retention_policy",
                    type="choice",
                    description="Backup retention",
                    options=["7days", "30days", "90days", "1year", "indefinite"],
                    default="30days",
                    required=True,
                ),
                ElicitationField(
                    name="encryption",
                    type="confirmation",
                    description="Encrypt backups?",
                    default="true",
                    required=True,
                ),
            ],
            next_steps={"default": "restore_testing"},
        ),
        # Step 2d: Multi-region configuration
        "multi_region_config": WorkflowStep(
            id="multi_region_config",
            title="Multi-Region Configuration",
            description="Configure multi-region disaster recovery",
            elicitation_type=ElicitationType.FORM,
            fields=[
                ElicitationField(
                    name="regions",
                    type="text",
                    description="Regions (comma-separated)",
                    placeholder="e.g., us-east-1, us-west-2, eu-west-1, ap-southeast-1",
                    required=True,
                ),
                ElicitationField(
                    name="primary_region",
                    type="text",
                    description="Primary region",
                    placeholder="e.g., us-east-1",
                    required=True,
                ),
                ElicitationField(
                    name="data_residency",
                    type="confirmation",
                    description="Enforce data residency rules?",
                    default="false",
                    required=True,
                ),
                ElicitationField(
                    name="cross_region_replication",
                    type="choice",
                    description="Cross-region replication",
                    options=["all_regions", "adjacent_only", "custom"],
                    default="all_regions",
                    required=True,
                ),
            ],
            next_steps={"default": "sync_options"},
        ),
        # Step 3: Sync options (for replication strategies)
        "sync_options": WorkflowStep(
            id="sync_options",
            title="Synchronization Options",
            description="Configure synchronization settings",
            elicitation_type=ElicitationType.FORM,
            fields=[
                ElicitationField(
                    name="sync_scope",
                    type="choice",
                    description="What to synchronize?",
                    options=["schemas_only", "schemas_and_metadata", "full_mirror"],
                    default="schemas_and_metadata",
                    required=True,
                ),
                ElicitationField(
                    name="initial_sync",
                    type="confirmation",
                    description="Perform initial full sync?",
                    default="true",
                    required=True,
                ),
                ElicitationField(
                    name="monitor_lag",
                    type="confirmation",
                    description="Enable replication lag monitoring?",
                    default="true",
                    required=True,
                ),
                ElicitationField(
                    name="alert_threshold",
                    type="text",
                    description="Alert threshold (seconds)",
                    placeholder="e.g., 300",
                    default="300",
                    required=False,
                ),
            ],
            next_steps={"default": "test_validate"},
        ),
        # Step 3b: Restore testing (for backup strategy)
        "restore_testing": WorkflowStep(
            id="restore_testing",
            title="Restore Testing",
            description="Configure restore testing",
            elicitation_type=ElicitationType.FORM,
            fields=[
                ElicitationField(
                    name="test_restore_schedule",
                    type="choice",
                    description="Test restore frequency",
                    options=["weekly", "monthly", "quarterly"],
                    default="monthly",
                    required=True,
                ),
                ElicitationField(
                    name="test_environment",
                    type="text",
                    description="Test restore environment",
                    placeholder="e.g., dr-test",
                    required=True,
                ),
                ElicitationField(
                    name="auto_validate",
                    type="confirmation",
                    description="Automatically validate restored schemas?",
                    default="true",
                    required=True,
                ),
            ],
            next_steps={"default": "test_validate"},
        ),
        # Step 4: Test and validate
        "test_validate": WorkflowStep(
            id="test_validate",
            title="Test and Validate",
            description="Test your disaster recovery configuration",
            elicitation_type=ElicitationType.FORM,
            fields=[
                ElicitationField(
                    name="run_dr_drill",
                    type="confirmation",
                    description="Run disaster recovery drill?",
                    default="true",
                    required=True,
                ),
                ElicitationField(
                    name="validation_scope",
                    type="choice",
                    description="Validation scope",
                    options=["connectivity", "replication", "failover", "full"],
                    default="full",
                    required=True,
                ),
                ElicitationField(
                    name="generate_runbook",
                    type="confirmation",
                    description="Generate DR runbook?",
                    default="true",
                    required=True,
                ),
            ],
            next_steps={"default": "finalize_dr"},
        ),
        # Step 5: Finalize DR setup
        "finalize_dr": WorkflowStep(
            id="finalize_dr",
            title="Finalize DR Setup",
            description="Review and activate your disaster recovery configuration",
            elicitation_type=ElicitationType.CONFIRMATION,
            fields=[
                ElicitationField(
                    name="enable_monitoring",
                    type="confirmation",
                    description="Enable DR monitoring and alerts?",
                    default="true",
                    required=True,
                ),
                ElicitationField(
                    name="activate_dr",
                    type="confirmation",
                    description=(
                        "Activate disaster recovery configuration? (Warning: This will enable "
                        "the DR configuration across your registries)"
                    ),
                    required=True,
                ),
            ],
            next_steps={"activate_dr": {"true": "finish", "false": "dr_strategy"}},
        ),
    }

    return MultiStepWorkflow(
        id="disaster_recovery_setup",
        name="Disaster Recovery Setup",
        description="Configure disaster recovery for Schema Registry",
        steps=steps,
        initial_step_id="dr_strategy",
        metadata={
            "estimated_duration": "10-15 minutes",
            "difficulty": "expert",
            "requires_auth": True,
            "requires_admin": True,
            "compliance_relevant": True,
        },
    )


def create_schema_evolution_workflow() -> MultiStepWorkflow:
    """Create the Schema Evolution Assistant workflow."""

    def should_show_compatibility_options(state: Dict[str, Any]) -> Optional[str]:
        """Conditional logic to show compatibility options based on breaking changes."""
        if state.get("has_breaking_changes") == "true":
            return "compatibility_resolution"
        return "evolution_strategy"

    def determine_strategy_path(state: Dict[str, Any]) -> Optional[str]:
        """Determine next step based on evolution strategy."""
        strategy = state.get("evolution_strategy")
        if strategy == "multi_version_migration":
            return "version_planning"
        elif strategy == "dual_support":
            return "dual_support_config"
        elif strategy == "gradual_migration":
            return "migration_phases"
        else:
            return "implementation_details"

    steps = {
        # Step 1: Schema Change Analysis
        "change_analysis": WorkflowStep(
            id="change_analysis",
            title="Schema Evolution Assistant - Change Analysis",
            description="Let's analyze your schema changes to understand their impact",
            elicitation_type=ElicitationType.FORM,
            fields=[
                ElicitationField(
                    name="subject",
                    type="text",
                    description="Schema subject name",
                    placeholder="e.g., com.example.User-value",
                    required=True,
                ),
                ElicitationField(
                    name="change_type",
                    type="choice",
                    description="What type of change are you making?",
                    options=[
                        "add_fields",
                        "remove_fields",
                        "modify_fields",
                        "restructure_schema",
                        "multiple_changes",
                    ],
                    required=True,
                ),
                ElicitationField(
                    name="change_description",
                    type="text",
                    description="Describe your changes",
                    placeholder="e.g., Adding email field, changing userId from int to string",
                    required=True,
                ),
                ElicitationField(
                    name="current_consumers",
                    type="text",
                    description="Number of active consumers (approximate)",
                    placeholder="e.g., 10-50",
                    required=True,
                ),
                ElicitationField(
                    name="production_impact",
                    type="choice",
                    description="Is this a production system?",
                    options=["yes_critical", "yes_non_critical", "no_staging", "no_development"],
                    required=True,
                ),
            ],
            next_steps={"default": "breaking_changes_check"},
        ),
        # Step 2: Breaking Changes Check
        "breaking_changes_check": WorkflowStep(
            id="breaking_changes_check",
            title="Breaking Changes Detection",
            description="Analyzing your changes for compatibility issues...",
            elicitation_type=ElicitationType.FORM,
            fields=[
                ElicitationField(
                    name="has_breaking_changes",
                    type="choice",
                    description="Based on your changes, we've detected potential breaking changes. How should we proceed?",
                    options=["true", "false", "unsure"],
                    required=True,
                ),
                ElicitationField(
                    name="current_compatibility",
                    type="choice",
                    description="Current compatibility mode",
                    options=["BACKWARD", "FORWARD", "FULL", "NONE"],
                    default="BACKWARD",
                    required=True,
                ),
                ElicitationField(
                    name="risk_tolerance",
                    type="choice",
                    description="Risk tolerance for this change",
                    options=["very_low", "low", "medium", "high"],
                    default="low",
                    required=True,
                ),
            ],
            conditions={"check_breaking": should_show_compatibility_options},
        ),
        # Step 3a: Compatibility Resolution (if breaking changes)
        "compatibility_resolution": WorkflowStep(
            id="compatibility_resolution",
            title="Compatibility Resolution",
            description="Your changes have breaking compatibility. Let's resolve this safely.",
            elicitation_type=ElicitationType.FORM,
            fields=[
                ElicitationField(
                    name="resolution_approach",
                    type="choice",
                    description="How would you like to handle the breaking changes?",
                    options=[
                        "make_backward_compatible",
                        "use_union_types",
                        "add_defaults",
                        "create_new_subject",
                        "force_with_coordination",
                    ],
                    required=True,
                ),
                ElicitationField(
                    name="compatibility_override",
                    type="confirmation",
                    description="Temporarily change compatibility mode for this operation?",
                    default="false",
                    required=True,
                ),
                ElicitationField(
                    name="compatibility_notes",
                    type="text",
                    description="Notes about compatibility decisions",
                    placeholder="e.g., All consumers will be updated by DATE",
                    required=False,
                ),
            ],
            next_steps={"default": "evolution_strategy"},
        ),
        # Step 3b: Evolution Strategy Selection
        "evolution_strategy": WorkflowStep(
            id="evolution_strategy",
            title="Evolution Strategy",
            description="Choose your schema evolution strategy",
            elicitation_type=ElicitationType.CHOICE,
            fields=[
                ElicitationField(
                    name="evolution_strategy",
                    type="choice",
                    description="Select the evolution approach that best fits your needs",
                    options=[
                        "direct_update",
                        "multi_version_migration",
                        "dual_support",
                        "gradual_migration",
                        "blue_green_deployment",
                    ],
                    required=True,
                ),
            ],
            conditions={"strategy_routing": determine_strategy_path},
        ),
        # Step 4a: Multi-Version Migration Planning
        "version_planning": WorkflowStep(
            id="version_planning",
            title="Multi-Version Migration Plan",
            description="Plan your multi-version migration path",
            elicitation_type=ElicitationType.FORM,
            fields=[
                ElicitationField(
                    name="intermediate_versions",
                    type="text",
                    description="Number of intermediate versions needed",
                    placeholder="e.g., 2",
                    default="1",
                    required=True,
                ),
                ElicitationField(
                    name="version_timeline",
                    type="text",
                    description="Timeline for each version (days)",
                    placeholder="e.g., 7,14,30",
                    required=True,
                ),
                ElicitationField(
                    name="deprecation_strategy",
                    type="choice",
                    description="How to handle deprecated fields?",
                    options=["mark_deprecated", "log_warnings", "dual_write", "ignore"],
                    default="mark_deprecated",
                    required=True,
                ),
            ],
            next_steps={"default": "consumer_coordination"},
        ),
        # Step 4b: Dual Support Configuration
        "dual_support_config": WorkflowStep(
            id="dual_support_config",
            title="Dual Support Configuration",
            description="Configure dual schema support",
            elicitation_type=ElicitationType.FORM,
            fields=[
                ElicitationField(
                    name="support_duration",
                    type="choice",
                    description="How long to support both schemas?",
                    options=["1_week", "2_weeks", "1_month", "3_months", "custom"],
                    default="1_month",
                    required=True,
                ),
                ElicitationField(
                    name="field_mapping",
                    type="text",
                    description="Field mapping rules (old:new)",
                    placeholder="e.g., userId:user_id, userName:user_name",
                    required=True,
                ),
                ElicitationField(
                    name="conversion_logic",
                    type="choice",
                    description="Conversion handling",
                    options=["automatic", "custom_code", "consumer_side"],
                    default="automatic",
                    required=True,
                ),
            ],
            next_steps={"default": "consumer_coordination"},
        ),
        # Step 4c: Gradual Migration Phases
        "migration_phases": WorkflowStep(
            id="migration_phases",
            title="Gradual Migration Phases",
            description="Define migration phases",
            elicitation_type=ElicitationType.FORM,
            fields=[
                ElicitationField(
                    name="phase_count",
                    type="choice",
                    description="Number of migration phases",
                    options=["2", "3", "4", "5+"],
                    default="3",
                    required=True,
                ),
                ElicitationField(
                    name="phase_criteria",
                    type="choice",
                    description="Phase progression criteria",
                    options=["percentage_based", "time_based", "manual_approval", "metric_based"],
                    default="percentage_based",
                    required=True,
                ),
                ElicitationField(
                    name="rollback_checkpoints",
                    type="confirmation",
                    description="Create rollback checkpoints at each phase?",
                    default="true",
                    required=True,
                ),
            ],
            next_steps={"default": "consumer_coordination"},
        ),
        # Step 4d: Direct Implementation Details
        "implementation_details": WorkflowStep(
            id="implementation_details",
            title="Implementation Details",
            description="Configure implementation specifics",
            elicitation_type=ElicitationType.FORM,
            fields=[
                ElicitationField(
                    name="deployment_window",
                    type="text",
                    description="Preferred deployment window",
                    placeholder="e.g., 2024-01-15 02:00 UTC",
                    required=True,
                ),
                ElicitationField(
                    name="validation_approach",
                    type="choice",
                    description="Schema validation approach",
                    options=["strict_validation", "lenient_validation", "custom_validators"],
                    default="strict_validation",
                    required=True,
                ),
            ],
            next_steps={"default": "consumer_coordination"},
        ),
        # Step 5: Consumer Coordination
        "consumer_coordination": WorkflowStep(
            id="consumer_coordination",
            title="Consumer Coordination",
            description="Plan consumer coordination and communication",
            elicitation_type=ElicitationType.FORM,
            fields=[
                ElicitationField(
                    name="notification_method",
                    type="choice",
                    description="How to notify consumers?",
                    options=[
                        "automatic_alerts",
                        "email_notification",
                        "api_deprecation_headers",
                        "documentation_only",
                        "multi_channel",
                    ],
                    default="multi_channel",
                    required=True,
                ),
                ElicitationField(
                    name="consumer_testing",
                    type="choice",
                    description="Consumer testing approach",
                    options=["sandbox_environment", "canary_consumers", "parallel_testing", "consumer_managed"],
                    default="sandbox_environment",
                    required=True,
                ),
                ElicitationField(
                    name="support_period",
                    type="choice",
                    description="Support period for old schema",
                    options=["1_week", "2_weeks", "1_month", "3_months", "6_months"],
                    default="1_month",
                    required=True,
                ),
            ],
            next_steps={"default": "rollback_planning"},
        ),
        # Step 6: Rollback Planning
        "rollback_planning": WorkflowStep(
            id="rollback_planning",
            title="Rollback Strategy",
            description="Plan your rollback strategy in case issues arise",
            elicitation_type=ElicitationType.FORM,
            fields=[
                ElicitationField(
                    name="rollback_trigger",
                    type="choice",
                    description="When to trigger rollback?",
                    options=["error_rate_threshold", "consumer_reports", "manual_decision", "automated_monitoring"],
                    default="automated_monitoring",
                    required=True,
                ),
                ElicitationField(
                    name="rollback_time",
                    type="choice",
                    description="Maximum rollback time",
                    options=["5_minutes", "15_minutes", "1_hour", "4_hours"],
                    default="15_minutes",
                    required=True,
                ),
                ElicitationField(
                    name="data_handling",
                    type="choice",
                    description="How to handle data during rollback?",
                    options=["preserve_all", "transform_backward", "quarantine_incompatible", "custom_handler"],
                    default="preserve_all",
                    required=True,
                ),
                ElicitationField(
                    name="rollback_testing",
                    type="confirmation",
                    description="Test rollback procedure before deployment?",
                    default="true",
                    required=True,
                ),
            ],
            next_steps={"default": "final_review"},
        ),
        # Step 7: Final Review and Documentation
        "final_review": WorkflowStep(
            id="final_review",
            title="Final Review",
            description="Review your schema evolution plan",
            elicitation_type=ElicitationType.FORM,
            fields=[
                ElicitationField(
                    name="generate_migration_guide",
                    type="confirmation",
                    description="Generate migration guide for consumers?",
                    default="true",
                    required=True,
                ),
                ElicitationField(
                    name="create_runbook",
                    type="confirmation",
                    description="Create operational runbook?",
                    default="true",
                    required=True,
                ),
                ElicitationField(
                    name="schedule_dry_run",
                    type="confirmation",
                    description="Schedule a dry run first?",
                    default="true",
                    required=True,
                ),
                ElicitationField(
                    name="evolution_notes",
                    type="text",
                    description="Additional notes for the evolution",
                    placeholder="Any special considerations or requirements",
                    required=False,
                ),
            ],
            next_steps={"default": "execute_evolution"},
        ),
        # Step 8: Execute Evolution
        "execute_evolution": WorkflowStep(
            id="execute_evolution",
            title="Execute Schema Evolution",
            description="Ready to execute your schema evolution plan",
            elicitation_type=ElicitationType.CONFIRMATION,
            fields=[
                ElicitationField(
                    name="final_confirmation",
                    type="confirmation",
                    description=(
                        "Execute schema evolution? This will implement your planned changes "
                        "according to the strategy you've selected."
                    ),
                    required=True,
                ),
                ElicitationField(
                    name="monitor_execution",
                    type="confirmation",
                    description="Enable real-time monitoring during execution?",
                    default="true",
                    required=True,
                ),
            ],
            next_steps={"final_confirmation": {"true": "finish", "false": "change_analysis"}},  # Start over
        ),
    }

    return MultiStepWorkflow(
        id="schema_evolution_assistant",
        name="Schema Evolution Assistant",
        description="Comprehensive guide for safe schema evolution with breaking change analysis and migration strategies",
        steps=steps,
        initial_step_id="change_analysis",
        metadata={
            "estimated_duration": "10-20 minutes",
            "difficulty": "intermediate",
            "requires_auth": True,
            "compliance_relevant": True,
            "supports_rollback": True,
        },
    )


def get_all_workflows() -> List[MultiStepWorkflow]:
    """Get all pre-defined workflows."""
    global _cached_workflows
    if _cached_workflows is None:
        _cached_workflows = [
            create_schema_migration_workflow(),
            create_context_reorganization_workflow(),
            create_disaster_recovery_workflow(),
            create_schema_evolution_workflow(),
        ]
    return _cached_workflows


def get_workflow_by_id(workflow_id: str) -> MultiStepWorkflow:
    """Get a specific workflow by ID."""
    workflows = {workflow.id: workflow for workflow in get_all_workflows()}
    return workflows.get(workflow_id)
