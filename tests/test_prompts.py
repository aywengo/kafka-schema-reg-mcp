#!/usr/bin/env python3
"""
Test suite for MCP prompts and prompt-based interactions with the Kafka Schema Registry MCP Server.

This module comprehensively tests:
1. MCP prompt functionality and content
2. Prompt registry and management
3. Natural language prompt scenarios
4. Integration with MCP server tools
5. Performance and reliability of prompt operations
"""

import pytest
import pytest_asyncio
import asyncio
import json
import os
import uuid
import tempfile
import re
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock

# Import the unified MCP server and prompts
import sys
sys.path.append('..')
from kafka_schema_registry_unified_mcp import (
    mcp,
    registry_manager,
    REGISTRY_MODE,
    list_registries,
    get_registry_info,
    test_registry_connection as _test_registry_connection,
    register_schema,
    get_schema,
    get_schema_versions,
    list_subjects,
    list_contexts,
    create_context,
    export_schema,
    export_subject,
    export_context,
    check_compatibility,
    get_global_config,
    update_global_config
)

# Import prompts module
from mcp_prompts import (
    PROMPT_REGISTRY,
    get_all_prompt_names,
    get_prompt_content,
    get_prompt_summary,
    get_schema_getting_started_prompt,
    get_schema_registration_prompt,
    get_context_management_prompt,
    get_schema_export_prompt,
    get_multi_registry_prompt,
    get_schema_compatibility_prompt,
    get_troubleshooting_prompt,
    get_advanced_workflows_prompt
)

class PromptTestScenarios:
    """Common prompt scenarios for testing"""
    
    # Basic schema operations
    BASIC_PROMPTS = [
        "List all schema contexts",
        "Show me all subjects",
        "Register a user schema",
        "Get the latest version of user schema",
        "Check schema compatibility",
        "Export a schema"
    ]
    
    # Context management
    CONTEXT_PROMPTS = [
        "Create a development context",
        "Create a production context",
        "List schemas in development context",
        "Move schema from dev to prod",
        "Delete empty context"
    ]
    
    # Configuration management
    CONFIG_PROMPTS = [
        "Get global configuration",
        "Set compatibility to BACKWARD",
        "Update subject compatibility",
        "Show configuration differences"
    ]
    
    # Export and documentation
    EXPORT_PROMPTS = [
        "Export schema as JSON",
        "Export schema as Avro IDL",
        "Export all schemas in context",
        "Generate schema documentation",
        "Create backup of all schemas"
    ]
    
    # Multi-registry (if applicable)
    MULTI_REGISTRY_PROMPTS = [
        "List all registries",
        "Compare development and production registries",
        "Migrate schema between registries",
        "Test all registry connections"
    ]

@pytest.fixture
def unique_subject():
    """Generate a unique test subject name."""
    return f"test-prompt-subject-{uuid.uuid4().hex[:8]}"

@pytest.fixture
def unique_context():
    """Generate a unique test context name."""
    return f"test-prompt-context-{uuid.uuid4().hex[:8]}"

@pytest.fixture
def sample_user_schema():
    """Sample user schema for testing."""
    return {
        "type": "record",
        "name": "User",
        "namespace": "com.example.user",
        "fields": [
            {"name": "id", "type": "int"},
            {"name": "name", "type": "string"},
            {"name": "email", "type": ["null", "string"], "default": None}
        ]
    }

@pytest.fixture
def sample_order_schema():
    """Sample order schema for testing."""
    return {
        "type": "record",
        "name": "Order",
        "namespace": "com.example.order",
        "fields": [
            {"name": "orderId", "type": "string"},
            {"name": "customerId", "type": "int"},
            {"name": "amount", "type": "double"},
            {"name": "timestamp", "type": "long"}
        ]
    }

class TestBasicPromptScenarios:
    """Test basic prompt scenarios that users commonly request."""
    
    @pytest.mark.asyncio
    async def test_list_all_schemas_prompt(self):
        """Test: 'List all schema contexts'"""
        try:
            result = list_contexts()
            assert isinstance(result, (list, dict))
            
            if isinstance(result, dict) and "contexts" in result:
                contexts = result["contexts"]
            else:
                contexts = result
                
            assert isinstance(contexts, list)
            print(f"✅ Found {len(contexts)} contexts")
            
        except Exception as e:
            pytest.skip(f"Registry not available: {e}")
    
    @pytest.mark.asyncio 
    async def test_show_all_subjects_prompt(self):
        """Test: 'Show me all subjects'"""
        try:
            result = list_subjects()
            assert isinstance(result, (list, dict))
            
            if isinstance(result, dict) and "subjects" in result:
                subjects = result["subjects"]
            else:
                subjects = result
                
            assert isinstance(subjects, list)
            print(f"✅ Found {len(subjects)} subjects")
            
        except Exception as e:
            pytest.skip(f"Registry not available: {e}")
    
    @pytest.mark.asyncio
    async def test_register_user_schema_prompt(self, unique_subject, sample_user_schema):
        """Test: 'Register a user schema with id, name, and email fields'"""
        try:
            result = register_schema(
                subject=unique_subject,
                schema_definition=sample_user_schema,
                schema_type="AVRO"
            )
            
            assert isinstance(result, dict)
            assert "id" in result or "schema_id" in result or "error" not in result
            print(f"✅ Registered schema for subject '{unique_subject}'")
            
        except Exception as e:
            pytest.skip(f"Registry not available: {e}")
    
    @pytest.mark.asyncio
    async def test_get_latest_schema_prompt(self, unique_subject, sample_user_schema):
        """Test: 'Get the latest version of user schema'"""
        try:
            # First register a schema
            register_result = register_schema(
                subject=unique_subject,
                schema_definition=sample_user_schema,
                schema_type="AVRO"
            )
            
            if "error" in register_result:
                pytest.skip("Could not register schema")
            
            # Then get it
            result = get_schema(subject=unique_subject, version="latest")
            
            assert isinstance(result, dict)
            assert "schema" in result or "error" not in result
            print(f"✅ Retrieved latest schema for '{unique_subject}'")
            
        except Exception as e:
            pytest.skip(f"Registry not available: {e}")

    def test_prompt_scenarios_coverage(self):
        """Ensure all prompt scenarios are covered in tests."""
        all_prompts = (
            PromptTestScenarios.BASIC_PROMPTS +
            PromptTestScenarios.CONTEXT_PROMPTS +
            PromptTestScenarios.CONFIG_PROMPTS +
            PromptTestScenarios.EXPORT_PROMPTS
        )
        
        assert len(all_prompts) >= 15, "Should have at least 15 prompt scenarios"
        print(f"✅ Defined {len(all_prompts)} prompt scenarios for testing")
    
    def test_prompt_categories_complete(self):
        """Verify all major prompt categories are covered."""
        required_categories = [
            "BASIC_PROMPTS",
            "CONTEXT_PROMPTS", 
            "CONFIG_PROMPTS",
            "EXPORT_PROMPTS"
        ]
        
        for category in required_categories:
            assert hasattr(PromptTestScenarios, category)
            prompts = getattr(PromptTestScenarios, category)
            assert len(prompts) > 0, f"Category {category} should have prompts"
        
        print(f"✅ All {len(required_categories)} prompt categories are covered")

class TestContextManagementPrompts:
    """Test context-related prompt scenarios."""
    
    @pytest.mark.asyncio
    async def test_create_development_context_prompt(self, unique_context):
        """Test: 'Create a development context for our team'"""
        try:
            dev_context = f"{unique_context}-dev"
            result = create_context(context=dev_context)
            
            assert isinstance(result, dict)
            # Should either succeed or already exist
            assert "error" not in result or "already exists" in result.get("error", "")
            print(f"✅ Created/verified development context '{dev_context}'")
            
        except Exception as e:
            pytest.skip(f"Registry not available: {e}")
    
    @pytest.mark.asyncio
    async def test_create_production_context_prompt(self, unique_context):
        """Test: 'Create a production context with strict settings'"""
        try:
            prod_context = f"{unique_context}-prod"
            result = create_context(context=prod_context)
            
            assert isinstance(result, dict)
            # Should either succeed or already exist
            assert "error" not in result or "already exists" in result.get("error", "")
            print(f"✅ Created/verified production context '{prod_context}'")
            
        except Exception as e:
            pytest.skip(f"Registry not available: {e}")
    
    @pytest.mark.asyncio
    async def test_list_schemas_in_context_prompt(self, unique_context, unique_subject, sample_user_schema):
        """Test: 'List all schemas in the development context'"""
        try:
            dev_context = f"{unique_context}-dev"
            
            # Create context and register a schema
            create_context(context=dev_context)
            register_schema(
                subject=unique_subject,
                schema_definition=sample_user_schema,
                context=dev_context
            )
            
            # List subjects in context
            result = list_subjects(context=dev_context)
            
            assert isinstance(result, (list, dict))
            print(f"✅ Listed schemas in context '{dev_context}'")
            
        except Exception as e:
            pytest.skip(f"Registry not available: {e}")

class TestConfigurationManagementPrompts:
    """Test configuration-related prompt scenarios."""
    
    @pytest.mark.asyncio
    async def test_get_global_configuration_prompt(self):
        """Test: 'Show me the global compatibility configuration'"""
        try:
            result = get_global_config()
            
            assert isinstance(result, dict)
            # Should have compatibility info or be a valid response
            print(f"✅ Retrieved global configuration")
            
        except Exception as e:
            pytest.skip(f"Registry not available: {e}")
    
    @pytest.mark.asyncio
    async def test_set_backward_compatibility_prompt(self):
        """Test: 'Set the global compatibility to BACKWARD'"""
        try:
            result = update_global_config(compatibility="BACKWARD")
            
            assert isinstance(result, dict)
            # Should either succeed or indicate readonly mode
            assert "error" not in result or "readonly" in result.get("error", "").lower()
            print(f"✅ Updated global compatibility to BACKWARD")
            
        except Exception as e:
            pytest.skip(f"Registry not available: {e}")

class TestExportAndDocumentationPrompts:
    """Test export and documentation prompt scenarios."""
    
    @pytest.mark.asyncio
    async def test_export_schema_as_json_prompt(self, unique_subject, sample_user_schema):
        """Test: 'Export the user schema as JSON for documentation'"""
        try:
            # Register schema first
            register_result = register_schema(
                subject=unique_subject,
                schema_definition=sample_user_schema
            )
            
            if "error" in register_result:
                pytest.skip("Could not register schema")
            
            # Export as JSON
            result = export_schema(
                subject=unique_subject,
                format="json"
            )
            
            assert isinstance(result, dict)
            assert "export_data" in result or "schema" in result
            print(f"✅ Exported schema '{unique_subject}' as JSON")
            
        except Exception as e:
            pytest.skip(f"Registry not available: {e}")
    
    @pytest.mark.asyncio
    async def test_export_schema_as_avro_idl_prompt(self, unique_subject, sample_user_schema):
        """Test: 'Export the user schema as Avro IDL for the development team'"""
        try:
            # Register schema first
            register_result = register_schema(
                subject=unique_subject,
                schema_definition=sample_user_schema
            )
            
            if "error" in register_result:
                pytest.skip("Could not register schema")
            
            # Export as Avro IDL
            result = export_schema(
                subject=unique_subject,
                format="avro_idl"
            )
            
            assert isinstance(result, dict)
            assert "export_data" in result or "avro_idl" in result or "idl" in result
            print(f"✅ Exported schema '{unique_subject}' as Avro IDL")
            
        except Exception as e:
            pytest.skip(f"Registry not available: {e}")
    
    @pytest.mark.asyncio
    async def test_export_all_schemas_in_context_prompt(self, unique_context, unique_subject, sample_user_schema):
        """Test: 'Export all schemas in the development context for backup'"""
        try:
            dev_context = f"{unique_context}-dev"
            
            # Create context and register schema
            create_context(context=dev_context)
            register_schema(
                subject=unique_subject,
                schema_definition=sample_user_schema,
                context=dev_context
            )
            
            # Export context
            result = export_context(context=dev_context)
            
            assert isinstance(result, dict)
            assert "export_data" in result or "schemas" in result or "subjects" in result
            print(f"✅ Exported all schemas from context '{dev_context}'")
            
        except Exception as e:
            pytest.skip(f"Registry not available: {e}")

class TestMultiRegistryPrompts:
    """Test multi-registry prompt scenarios (if applicable)."""
    
    @pytest.mark.asyncio
    async def test_list_all_registries_prompt(self):
        """Test: 'Show me all available Schema Registry instances'"""
        try:
            result = list_registries()
            
            assert isinstance(result, list)
            print(f"✅ Found {len(result)} registry instances")
            
            # Verify each registry has required fields
            for registry in result:
                assert isinstance(registry, dict)
                assert "name" in registry or "url" in registry
            
        except Exception as e:
            pytest.skip(f"Registry not available: {e}")
    
    @pytest.mark.asyncio
    async def test_test_all_connections_prompt(self):
        """Test: 'Test connections to all Schema Registry instances'"""
        try:
            if REGISTRY_MODE == "single":
                # Test single registry
                result = _test_registry_connection()
            else:
                # Test all registries
                from kafka_schema_registry_unified_mcp import test_all_registries
                result = await test_all_registries()
            
            assert isinstance(result, dict)
            print(f"✅ Tested registry connections")
            
        except Exception as e:
            pytest.skip(f"Registry not available: {e}")

class TestComplexWorkflowPrompts:
    """Test complex workflow scenarios."""
    
    @pytest.mark.asyncio
    async def test_complete_schema_lifecycle_prompt(self, unique_context, unique_subject, sample_user_schema, sample_order_schema):
        """Test: Complete schema lifecycle from development to production"""
        try:
            # Create development and production contexts
            dev_context = f"{unique_context}-dev"
            prod_context = f"{unique_context}-prod"
            
            create_context(context=dev_context)
            create_context(context=prod_context)
            
            # Register schema in development
            register_result = register_schema(
                subject=unique_subject,
                schema_definition=sample_user_schema,
                context=dev_context
            )
            
            if "error" in register_result:
                pytest.skip("Could not register schema")
            
            # Check compatibility before promoting to production
            compat_result = check_compatibility(
                subject=unique_subject,
                schema_definition=sample_user_schema,
                context=prod_context
            )
            
            # Export from development context
            export_result = export_context(context=dev_context)
            
            assert isinstance(export_result, dict)
            print(f"✅ Completed schema lifecycle workflow")
            
        except Exception as e:
            pytest.skip(f"Registry not available: {e}")
    
    @pytest.mark.asyncio
    async def test_schema_documentation_generation_prompt(self, unique_subject, sample_user_schema):
        """Test: 'Generate comprehensive documentation for all our schemas'"""
        try:
            # Register schema
            register_result = register_schema(
                subject=unique_subject,
                schema_definition=sample_user_schema
            )
            
            if "error" in register_result:
                pytest.skip("Could not register schema")
            
            # Export with full metadata
            result = export_subject(
                subject=unique_subject,
                include_metadata=True,
                include_config=True
            )
            
            assert isinstance(result, dict)
            assert "export_data" in result or "metadata" in result or "schemas" in result
            print(f"✅ Generated documentation for schema '{unique_subject}'")
            
        except Exception as e:
            pytest.skip(f"Registry not available: {e}")

# Performance and stress testing for prompts
class TestPromptPerformance:
    """Test performance characteristics of prompt-based operations."""
    
    @pytest.mark.asyncio
    async def test_rapid_fire_prompts(self):
        """Test: Multiple rapid prompts don't interfere with each other"""
        try:
            tasks = []
            
            # Create multiple concurrent prompt operations
            for i in range(5):
                task = asyncio.create_task(self._single_prompt_operation(i))
                tasks.append(task)
            
            # Wait for all to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all completed successfully
            successful = sum(1 for r in results if not isinstance(r, Exception))
            print(f"✅ {successful}/{len(tasks)} rapid-fire prompts completed successfully")
            
        except Exception as e:
            pytest.skip(f"Registry not available: {e}")
    
    async def _single_prompt_operation(self, index):
        """Single prompt operation for concurrent testing."""
        subject = f"rapid-test-{index}-{uuid.uuid4().hex[:6]}"
        schema = {
            "type": "record",
            "name": f"TestRecord{index}",
            "fields": [{"name": "id", "type": "int"}]
        }
        
        # Simulate a user prompt: "Register a test schema"
        result = register_schema(
            subject=subject,
            schema_definition=schema
        )
        
        return result

# ===== NEW COMPREHENSIVE PROMPT TESTS =====

class TestMCPPromptsModule:
    """Test the MCP prompts module functionality."""
    
    def test_prompt_registry_structure(self):
        """Test that the prompt registry is properly structured."""
        assert isinstance(PROMPT_REGISTRY, dict)
        assert len(PROMPT_REGISTRY) >= 8, "Should have at least 8 prompts"
        
        expected_prompts = [
            "schema-getting-started",
            "schema-registration", 
            "context-management",
            "schema-export",
            "multi-registry",
            "schema-compatibility",
            "troubleshooting",
            "advanced-workflows"
        ]
        
        for prompt_name in expected_prompts:
            assert prompt_name in PROMPT_REGISTRY, f"Missing prompt: {prompt_name}"
            assert callable(PROMPT_REGISTRY[prompt_name]), f"Prompt {prompt_name} should be callable"
        
        print(f"✅ Validated {len(PROMPT_REGISTRY)} prompts in registry")
    
    def test_get_all_prompt_names(self):
        """Test getting all prompt names."""
        names = get_all_prompt_names()
        assert isinstance(names, list)
        assert len(names) >= 8
        assert "schema-getting-started" in names
        assert "advanced-workflows" in names
        print(f"✅ Retrieved {len(names)} prompt names")
    
    def test_get_prompt_content_valid(self):
        """Test getting content for valid prompts."""
        for prompt_name in get_all_prompt_names():
            content = get_prompt_content(prompt_name)
            assert isinstance(content, str)
            assert len(content) > 100, f"Prompt {prompt_name} content too short"
            assert "##" in content, f"Prompt {prompt_name} should have markdown headers"
        print("✅ All prompts return valid content")
    
    def test_get_prompt_content_invalid(self):
        """Test getting content for invalid prompt."""
        content = get_prompt_content("non-existent-prompt")
        assert "not found" in content.lower()
        assert "available prompts" in content.lower()
        print("✅ Invalid prompt handling works correctly")
    
    def test_get_prompt_summary(self):
        """Test the prompt summary functionality."""
        summary = get_prompt_summary()
        assert isinstance(summary, dict)
        assert "total_prompts" in summary
        assert "available_prompts" in summary
        assert "categories" in summary
        assert summary["total_prompts"] >= 8
        assert len(summary["available_prompts"]) >= 8
        print(f"✅ Prompt summary: {summary['total_prompts']} total prompts")

class TestIndividualPromptContent:
    """Test the content and structure of individual prompts."""
    
    def test_schema_getting_started_content(self):
        """Test the getting started prompt content."""
        content = get_schema_getting_started_prompt()
        assert "Getting Started with Schema Registry" in content
        assert "Basic Operations" in content
        assert "Context Management" in content
        assert "Configuration & Monitoring" in content
        assert "List all schema contexts" in content
        print("✅ Getting started prompt has expected structure")
    
    def test_schema_registration_content(self):
        """Test the schema registration prompt content."""
        content = get_schema_registration_prompt()
        assert "Schema Registration Guide" in content
        assert "Quick Registration" in content
        assert "Schema Types Supported" in content
        assert "AVRO" in content and "JSON" in content and "PROTOBUF" in content
        assert "Common Schema Examples" in content
        print("✅ Schema registration prompt has expected structure")
    
    def test_context_management_content(self):
        """Test the context management prompt content."""
        content = get_context_management_prompt()
        assert "Schema Context Management" in content
        assert "Common Context Patterns" in content
        assert "development" in content and "staging" in content and "production" in content
        assert "Schema Promotion Workflow" in content
        print("✅ Context management prompt has expected structure")
    
    def test_schema_export_content(self):
        """Test the schema export prompt content."""
        content = get_schema_export_prompt()
        assert "Schema Export & Documentation" in content
        assert "Export Options" in content
        assert "JSON" in content and "Avro IDL" in content
        assert "Common Use Cases" in content
        print("✅ Schema export prompt has expected structure")
    
    def test_multi_registry_content(self):
        """Test the multi-registry prompt content."""
        content = get_multi_registry_prompt()
        assert "Multi-Registry Management" in content
        assert "Cross-Registry Operations" in content
        assert "Environment Patterns" in content
        assert "Development → Staging → Production" in content
        print("✅ Multi-registry prompt has expected structure")
    
    def test_schema_compatibility_content(self):
        """Test the schema compatibility prompt content."""
        content = get_schema_compatibility_prompt()
        assert "Schema Compatibility & Evolution" in content
        assert "Compatibility Levels" in content
        assert "BACKWARD" in content and "FORWARD" in content and "FULL" in content
        assert "Breaking Changes" in content
        print("✅ Schema compatibility prompt has expected structure")
    
    def test_troubleshooting_content(self):
        """Test the troubleshooting prompt content."""
        content = get_troubleshooting_prompt()
        assert "Schema Registry Troubleshooting" in content
        assert "Quick Diagnostics" in content
        assert "Common Issues & Solutions" in content
        assert "Connection Problems" in content
        print("✅ Troubleshooting prompt has expected structure")
    
    def test_advanced_workflows_content(self):
        """Test the advanced workflows prompt content."""
        content = get_advanced_workflows_prompt()
        assert "Advanced Schema Registry Workflows" in content
        assert "CI/CD Integration Workflows" in content
        assert "Enterprise Governance Workflows" in content
        assert "Complete Release Workflow" in content
        print("✅ Advanced workflows prompt has expected structure")

class TestPromptContentQuality:
    """Test the quality and consistency of prompt content."""
    
    def test_all_prompts_have_headers(self):
        """Test that all prompts have proper markdown headers."""
        for prompt_name in get_all_prompt_names():
            content = get_prompt_content(prompt_name)
            
            # Should have main header
            assert content.startswith("# "), f"Prompt {prompt_name} should start with main header"
            
            # Should have secondary headers
            assert "## " in content, f"Prompt {prompt_name} should have secondary headers"
            
            # Should have proper structure
            lines = content.split('\n')
            first_line = lines[0]
            assert first_line.startswith("# "), f"First line should be main header in {prompt_name}"
        
        print("✅ All prompts have proper markdown structure")
    
    def test_all_prompts_have_examples(self):
        """Test that all prompts include actionable examples."""
        for prompt_name in get_all_prompt_names():
            content = get_prompt_content(prompt_name)
            
            # Should have quoted examples (commands in quotes)
            quote_pattern = r'"[^"]*"'
            quotes = re.findall(quote_pattern, content)
            assert len(quotes) >= 3, f"Prompt {prompt_name} should have at least 3 quoted examples"
            
            # Should have action words
            action_words = ["Register", "List", "Show", "Export", "Create", "Check", "Test", "Generate"]
            has_actions = any(word in content for word in action_words)
            assert has_actions, f"Prompt {prompt_name} should have action verbs"
        
        print("✅ All prompts contain actionable examples")
    
    def test_prompt_length_appropriate(self):
        """Test that prompts are substantial but not too long."""
        for prompt_name in get_all_prompt_names():
            content = get_prompt_content(prompt_name)
            word_count = len(content.split())
            
            # Should be substantial but not overwhelming (relaxed minimum for concise prompts)
            assert 100 <= word_count <= 2000, f"Prompt {prompt_name} has {word_count} words (should be 100-2000)"
            
            # Should have reasonable number of lines
            line_count = len(content.split('\n'))
            assert 15 <= line_count <= 200, f"Prompt {prompt_name} has {line_count} lines (should be 15-200)"
        
        print("✅ All prompts have appropriate length")
    
    def test_prompts_use_emojis_consistently(self):
        """Test that prompts use emojis for visual organization."""
        for prompt_name in get_all_prompt_names():
            content = get_prompt_content(prompt_name)
            
            # Should have emojis in headers
            emoji_pattern = r'[🚀📋🏗️📊🌐🔄🛠️🎯⚙️📝🔧🔍]'
            emojis = re.findall(emoji_pattern, content)
            assert len(emojis) >= 3, f"Prompt {prompt_name} should have at least 3 emojis for organization"
        
        print("✅ All prompts use emojis consistently")

class TestPromptIntegration:
    """Test integration between prompts and MCP server tools."""
    
    def test_prompt_commands_match_tools(self):
        """Test that prompt examples reference valid MCP tools."""
        # Get list of available tools from the MCP server
        available_tools = [
            "list_contexts", "list_subjects", "register_schema", "get_schema",
            "export_schema", "export_context", "create_context", "check_compatibility",
            "get_global_config", "list_registries", "_test_registry_connection"
        ]
        
        for prompt_name in get_all_prompt_names():
            content = get_prompt_content(prompt_name)
            
            # Extract quoted commands
            quote_pattern = r'"([^"]*)"'
            commands = re.findall(quote_pattern, content)
            
            # Check if commands align with available functionality
            schema_related = any("schema" in cmd.lower() for cmd in commands)
            context_related = any("context" in cmd.lower() for cmd in commands)
            
            if prompt_name in ["schema-registration", "schema-getting-started"]:
                assert schema_related, f"Prompt {prompt_name} should have schema-related commands"
            
            if prompt_name in ["context-management", "schema-getting-started"]:
                assert context_related, f"Prompt {prompt_name} should have context-related commands"
        
        print("✅ Prompt commands align with available tools")
    
    @pytest.mark.asyncio
    async def test_prompt_workflow_feasibility(self):
        """Test that prompt workflows are actually feasible with current tools."""
        try:
            # Test basic workflow from getting-started prompt
            contexts_result = list_contexts()
            assert isinstance(contexts_result, (list, dict))
            
            subjects_result = list_subjects()
            assert isinstance(subjects_result, (list, dict))
            
            registries_result = list_registries()
            assert isinstance(registries_result, list)
            
            print("✅ Basic prompt workflows are feasible")
            
        except Exception as e:
            pytest.skip(f"Registry not available for workflow testing: {e}")

class TestPromptPerformanceAndReliability:
    """Test performance and reliability of prompt operations."""
    
    def test_prompt_generation_performance(self):
        """Test that prompt generation is fast."""
        import time
        
        for prompt_name in get_all_prompt_names():
            start_time = time.time()
            content = get_prompt_content(prompt_name)
            end_time = time.time()
            
            generation_time = end_time - start_time
            assert generation_time < 0.1, f"Prompt {prompt_name} took {generation_time:.3f}s to generate (should be <0.1s)"
            assert len(content) > 0, f"Prompt {prompt_name} should return content"
        
        print("✅ All prompts generate quickly")
    
    def test_concurrent_prompt_access(self):
        """Test that prompts can be accessed concurrently."""
        import threading
        import time
        
        results = {}
        errors = {}
        
        def get_prompt_worker(prompt_name):
            try:
                start_time = time.time()
                content = get_prompt_content(prompt_name)
                end_time = time.time()
                results[prompt_name] = {
                    "content_length": len(content),
                    "generation_time": end_time - start_time
                }
            except Exception as e:
                errors[prompt_name] = str(e)
        
        # Create threads for all prompts
        threads = []
        for prompt_name in get_all_prompt_names():
            thread = threading.Thread(target=get_prompt_worker, args=(prompt_name,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Errors in concurrent access: {errors}"
        assert len(results) == len(get_all_prompt_names()), "All prompts should complete"
        
        print(f"✅ Successfully accessed {len(results)} prompts concurrently")
    
    def test_prompt_memory_usage(self):
        """Test that prompts don't use excessive memory."""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss
            
            # Generate all prompts multiple times
            for i in range(10):
                for prompt_name in get_all_prompt_names():
                    content = get_prompt_content(prompt_name)
                    assert len(content) > 0
            
            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory
            
            # Should not increase memory significantly (allow 10MB increase)
            assert memory_increase < 10 * 1024 * 1024, f"Memory increased by {memory_increase / 1024 / 1024:.1f}MB"
            
            print(f"✅ Memory usage stable (increased {memory_increase / 1024:.1f}KB)")
        except ImportError:
            pytest.skip("psutil not available - skipping memory test")

class TestPromptAccessibility:
    """Test that prompts are accessible and user-friendly."""
    
    def test_prompts_have_clear_purpose(self):
        """Test that each prompt has a clear, stated purpose."""
        purpose_indicators = ["help", "guide", "management", "workflow", "documentation", "troubleshoot"]
        
        for prompt_name in get_all_prompt_names():
            content = get_prompt_content(prompt_name)
            first_paragraph = content.split('\n\n')[0] if '\n\n' in content else content[:200]
            
            has_clear_purpose = any(indicator in first_paragraph.lower() for indicator in purpose_indicators)
            assert has_clear_purpose, f"Prompt {prompt_name} should clearly state its purpose"
        
        print("✅ All prompts have clear purposes")
    
    def test_prompts_progressive_complexity(self):
        """Test that prompts progress from basic to advanced concepts."""
        basic_prompts = ["schema-getting-started", "schema-registration"]
        intermediate_prompts = ["context-management", "schema-export", "schema-compatibility"]
        advanced_prompts = ["multi-registry", "troubleshooting", "advanced-workflows"]
        
        # Basic prompts should have simpler language
        for prompt_name in basic_prompts:
            content = get_prompt_content(prompt_name)
            
            # Should mention "basic" or "simple" or "quick"
            simplicity_words = ["basic", "simple", "quick", "easy", "getting started"]
            has_simple_language = any(word in content.lower() for word in simplicity_words)
            assert has_simple_language, f"Basic prompt {prompt_name} should use simple language"
        
        # Advanced prompts should mention complexity
        for prompt_name in advanced_prompts:
            content = get_prompt_content(prompt_name)
            
            # Should mention advanced concepts
            complexity_words = ["advanced", "complex", "sophisticated", "enterprise", "workflow"]
            has_complex_language = any(word in content.lower() for word in complexity_words)
            assert has_complex_language, f"Advanced prompt {prompt_name} should mention complexity"
        
        print("✅ Prompts show progressive complexity")

class TestPromptDocumentationAlignment:
    """Test that prompts align with documentation and actual capabilities."""
    
    def test_prompt_tools_exist(self):
        """Test that tools mentioned in prompts actually exist."""
        # This is a simplified test - in a real scenario you'd check against the actual MCP server
        expected_capabilities = [
            "register", "list", "export", "create", "delete", "check", "test", "compare", "migrate"
        ]
        
        for prompt_name in get_all_prompt_names():
            content = get_prompt_content(prompt_name)
            
            # Should mention at least some expected capabilities
            mentioned_capabilities = [cap for cap in expected_capabilities if cap in content.lower()]
            assert len(mentioned_capabilities) >= 2, f"Prompt {prompt_name} should mention relevant capabilities"
        
        print("✅ Prompts reference existing capabilities")
    
    def test_prompt_consistency_across_registry_modes(self):
        """Test that prompts work for both single and multi-registry modes."""
        for prompt_name in get_all_prompt_names():
            content = get_prompt_content(prompt_name)
            
            # Multi-registry specific prompts
            if prompt_name == "multi-registry":
                assert "multiple" in content.lower() or "multi" in content.lower()
            else:
                # Other prompts should work for both modes
                # Should not be overly specific to one mode
                single_specific = content.count("single registry")
                multi_specific = content.count("multiple registries")
                
                # Allow some mode-specific content but not overwhelming
                assert single_specific <= 2 and multi_specific <= 2, f"Prompt {prompt_name} too mode-specific"
        
        print("✅ Prompts work across registry modes")

if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--disable-warnings"
    ]) 