import os
import json
import io
import zipfile
from datetime import datetime
from typing import Dict, List, Optional, Union
from fastapi import FastAPI, HTTPException, Depends, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import base64

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Kafka Schema Registry MCP",
    description="Message Control Protocol server for Kafka Schema Registry with Context Support, Configuration Management, Mode Control, and Schema Export",
    version="1.3.0"
)

# Configuration
SCHEMA_REGISTRY_URL = os.getenv("SCHEMA_REGISTRY_URL", "http://localhost:8081")
SCHEMA_REGISTRY_USER = os.getenv("SCHEMA_REGISTRY_USER", "")
SCHEMA_REGISTRY_PASSWORD = os.getenv("SCHEMA_REGISTRY_PASSWORD", "")
API_VERSION = "v1"

# Setup authentication
auth = None
headers = {"Content-Type": "application/vnd.schemaregistry.v1+json"}
standard_headers = {"Content-Type": "application/json"}
if SCHEMA_REGISTRY_USER and SCHEMA_REGISTRY_PASSWORD:
    auth = HTTPBasicAuth(SCHEMA_REGISTRY_USER, SCHEMA_REGISTRY_PASSWORD)
    # Also prepare headers for compatibility
    credentials = base64.b64encode(f"{SCHEMA_REGISTRY_USER}:{SCHEMA_REGISTRY_PASSWORD}".encode()).decode()
    headers["Authorization"] = f"Basic {credentials}"
    standard_headers["Authorization"] = f"Basic {credentials}"

class SchemaRequest(BaseModel):
    subject: str
    schema: Dict
    schemaType: Optional[str] = "AVRO"
    context: Optional[str] = None

class CompatibilityRequest(BaseModel):
    subject: str
    schema: Dict
    schemaType: Optional[str] = "AVRO"
    context: Optional[str] = None

class ContextRequest(BaseModel):
    context: str

class ConfigRequest(BaseModel):
    compatibility: Optional[str] = None  # BACKWARD, FORWARD, FULL, NONE, BACKWARD_TRANSITIVE, FORWARD_TRANSITIVE, FULL_TRANSITIVE

class ModeRequest(BaseModel):
    mode: str  # IMPORT, READONLY, READWRITE

class ExportRequest(BaseModel):
    format: Optional[str] = "json"  # json, avro_idl, bundle
    include_metadata: Optional[bool] = True
    include_config: Optional[bool] = True
    include_versions: Optional[str] = "all"  # all, latest, specific version number

class SchemaRegistrationResponse(BaseModel):
    id: int

class SchemaResponse(BaseModel):
    subject: str
    version: int
    id: int
    schema: str  # Schema Registry returns this as a JSON string, not Dict

class ContextResponse(BaseModel):
    contexts: List[str]

class ConfigResponse(BaseModel):
    compatibilityLevel: str

class ModeResponse(BaseModel):
    mode: str

class ExportedSchema(BaseModel):
    subject: str
    version: int
    id: int
    schema: str
    schemaType: str
    metadata: Optional[Dict] = None

class SubjectExport(BaseModel):
    subject: str
    versions: List[ExportedSchema]
    config: Optional[Dict] = None
    mode: Optional[Dict] = None
    
class ContextExport(BaseModel):
    context: str
    exported_at: str
    subjects: List[SubjectExport]
    global_config: Optional[Dict] = None
    global_mode: Optional[Dict] = None

class GlobalExport(BaseModel):
    exported_at: str
    contexts: List[ContextExport]
    default_context: ContextExport
    global_config: Optional[Dict] = None
    global_mode: Optional[Dict] = None

def build_context_url(base_url: str, context: Optional[str] = None) -> str:
    """Build URL with optional context support."""
    if context:
        return f"{SCHEMA_REGISTRY_URL}/contexts/{context}{base_url}"
    return f"{SCHEMA_REGISTRY_URL}{base_url}"

@app.get("/")
async def root():
    return {"message": "Kafka Schema Registry MCP Server with Context Support, Configuration Management, Mode Control, and Schema Export"}

# Context Management Endpoints
@app.get("/contexts", response_model=ContextResponse)
async def list_contexts():
    """List all available schema contexts."""
    try:
        response = requests.get(
            f"{SCHEMA_REGISTRY_URL}/contexts",
            auth=auth,
            headers=headers
        )
        response.raise_for_status()
        return {"contexts": response.json()}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/contexts/{context}")
async def create_context(context: str):
    """Create a new schema context."""
    try:
        response = requests.post(
            f"{SCHEMA_REGISTRY_URL}/contexts/{context}",
            auth=auth,
            headers=headers
        )
        response.raise_for_status()
        return {"message": f"Context '{context}' created successfully"}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/contexts/{context}")
async def delete_context(context: str):
    """Delete a schema context."""
    try:
        response = requests.delete(
            f"{SCHEMA_REGISTRY_URL}/contexts/{context}",
            auth=auth,
            headers=headers
        )
        response.raise_for_status()
        return {"message": f"Context '{context}' deleted successfully"}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

# Schema Management Endpoints with Context Support
@app.post("/schemas", response_model=SchemaRegistrationResponse)
async def register_schema(schema_request: SchemaRequest, context: Optional[str] = Query(None, description="Schema context")):
    """Register a new schema version under the specified subject, optionally in a specific context."""
    try:
        # Use context from request body or query parameter
        target_context = schema_request.context or context
        
        payload = {
            "schema": json.dumps(schema_request.schema),
            "schemaType": schema_request.schemaType
        }
        
        url = build_context_url(f"/subjects/{schema_request.subject}/versions", target_context)
        
        response = requests.post(
            url,
            data=json.dumps(payload),
            auth=auth,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/schemas/{subject}", response_model=SchemaResponse)
async def get_schema(subject: str, version: Optional[str] = "latest", context: Optional[str] = Query(None, description="Schema context")):
    """Get a specific version of a schema, optionally from a specific context."""
    try:
        url = build_context_url(f"/subjects/{subject}/versions/{version}", context)
        
        response = requests.get(
            url,
            auth=auth,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=404, detail=f"Schema not found: {str(e)}")

@app.get("/schemas/{subject}/versions", response_model=List[int])
async def get_schema_versions(subject: str, context: Optional[str] = Query(None, description="Schema context")):
    """Get all versions of a schema, optionally from a specific context."""
    try:
        url = build_context_url(f"/subjects/{subject}/versions", context)
        
        response = requests.get(
            url,
            auth=auth,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=404, detail=f"Schema versions not found: {str(e)}")

@app.post("/compatibility")
async def check_compatibility(compatibility_request: CompatibilityRequest, context: Optional[str] = Query(None, description="Schema context")):
    """Check if a schema is compatible with the specified subject, optionally in a specific context."""
    try:
        # Use context from request body or query parameter
        target_context = compatibility_request.context or context
        
        payload = {
            "schema": json.dumps(compatibility_request.schema),
            "schemaType": compatibility_request.schemaType
        }
        
        url = build_context_url(f"/compatibility/subjects/{compatibility_request.subject}/versions/latest", target_context)
        
        response = requests.post(
            url,
            data=json.dumps(payload),
            auth=auth,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

# Context-aware Subject Management
@app.get("/subjects")
async def list_subjects(context: Optional[str] = Query(None, description="Schema context")):
    """List all subjects, optionally filtered by context."""
    try:
        url = build_context_url("/subjects", context)
        
        response = requests.get(
            url,
            auth=auth,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/subjects/{subject}")
async def delete_subject(subject: str, context: Optional[str] = Query(None, description="Schema context")):
    """Delete a subject and all its versions, optionally from a specific context."""
    try:
        url = build_context_url(f"/subjects/{subject}", context)
        
        response = requests.delete(
            url,
            auth=auth,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

# Configuration Management Endpoints
@app.get("/config", response_model=ConfigResponse)
async def get_global_config(context: Optional[str] = Query(None, description="Schema context")):
    """Get global configuration settings, optionally for a specific context."""
    try:
        url = build_context_url("/config", context)
        
        response = requests.get(
            url,
            auth=auth,
            headers=standard_headers
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/config")
async def update_global_config(config_request: ConfigRequest, context: Optional[str] = Query(None, description="Schema context")):
    """Update global configuration settings, optionally for a specific context."""
    try:
        url = build_context_url("/config", context)
        
        payload = {}
        if config_request.compatibility:
            payload["compatibility"] = config_request.compatibility
        
        response = requests.put(
            url,
            data=json.dumps(payload),
            auth=auth,
            headers=standard_headers
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/config/{subject}", response_model=ConfigResponse)
async def get_subject_config(subject: str, context: Optional[str] = Query(None, description="Schema context")):
    """Get configuration settings for a specific subject, optionally in a specific context."""
    try:
        url = build_context_url(f"/config/{subject}", context)
        
        response = requests.get(
            url,
            auth=auth,
            headers=standard_headers
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=404, detail=f"Subject config not found: {str(e)}")

@app.put("/config/{subject}")
async def update_subject_config(subject: str, config_request: ConfigRequest, context: Optional[str] = Query(None, description="Schema context")):
    """Update configuration settings for a specific subject, optionally in a specific context."""
    try:
        url = build_context_url(f"/config/{subject}", context)
        
        payload = {}
        if config_request.compatibility:
            payload["compatibility"] = config_request.compatibility
        
        response = requests.put(
            url,
            data=json.dumps(payload),
            auth=auth,
            headers=standard_headers
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/config/{subject}")
async def delete_subject_config(subject: str, context: Optional[str] = Query(None, description="Schema context")):
    """Delete configuration settings for a specific subject, reverting to global config."""
    try:
        url = build_context_url(f"/config/{subject}", context)
        
        response = requests.delete(
            url,
            auth=auth,
            headers=standard_headers
        )
        response.raise_for_status()
        return {"message": f"Configuration for subject '{subject}' deleted successfully"}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mode Management Endpoints
@app.get("/mode", response_model=ModeResponse)
async def get_mode(context: Optional[str] = Query(None, description="Schema context")):
    """Get the current mode of the Schema Registry, optionally for a specific context."""
    try:
        url = build_context_url("/mode", context)
        
        response = requests.get(
            url,
            auth=auth,
            headers=standard_headers
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/mode")
async def update_mode(mode_request: ModeRequest, context: Optional[str] = Query(None, description="Schema context")):
    """Update the mode of the Schema Registry, optionally for a specific context."""
    try:
        url = build_context_url("/mode", context)
        
        payload = {"mode": mode_request.mode}
        
        response = requests.put(
            url,
            data=json.dumps(payload),
            auth=auth,
            headers=standard_headers
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/mode/{subject}", response_model=ModeResponse)
async def get_subject_mode(subject: str, context: Optional[str] = Query(None, description="Schema context")):
    """Get the mode for a specific subject, optionally in a specific context."""
    try:
        url = build_context_url(f"/mode/{subject}", context)
        
        response = requests.get(
            url,
            auth=auth,
            headers=standard_headers
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=404, detail=f"Subject mode not found: {str(e)}")

@app.put("/mode/{subject}")
async def update_subject_mode(subject: str, mode_request: ModeRequest, context: Optional[str] = Query(None, description="Schema context")):
    """Update the mode for a specific subject, optionally in a specific context."""
    try:
        url = build_context_url(f"/mode/{subject}", context)
        
        payload = {"mode": mode_request.mode}
        
        response = requests.put(
            url,
            data=json.dumps(payload),
            auth=auth,
            headers=standard_headers
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/mode/{subject}")
async def delete_subject_mode(subject: str, context: Optional[str] = Query(None, description="Schema context")):
    """Delete the mode setting for a specific subject, reverting to global mode."""
    try:
        url = build_context_url(f"/mode/{subject}", context)
        
        response = requests.delete(
            url,
            auth=auth,
            headers=standard_headers
        )
        response.raise_for_status()
        return {"message": f"Mode setting for subject '{subject}' deleted successfully"}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

# Schema Export Functionality

def format_schema_as_avro_idl(schema_str: str, subject: str) -> str:
    """Convert Avro JSON schema to Avro IDL format."""
    try:
        schema_obj = json.loads(schema_str)
        
        def format_field(field):
            field_type = field["type"]
            field_name = field["name"]
            default = field.get("default", None)
            doc = field.get("doc", "")
            
            if isinstance(field_type, list) and "null" in field_type:
                # Union type with null (optional field)
                non_null_types = [t for t in field_type if t != "null"]
                if len(non_null_types) == 1:
                    field_type_str = f"{non_null_types[0]}?"
                else:
                    field_type_str = f"union {{ {', '.join(field_type)} }}"
            elif isinstance(field_type, dict):
                # Complex type
                if field_type.get("type") == "array":
                    field_type_str = f"array<{field_type['items']}>"
                elif field_type.get("type") == "map":
                    field_type_str = f"map<{field_type['values']}>"
                else:
                    field_type_str = str(field_type)
            else:
                field_type_str = str(field_type)
            
            field_line = f"  {field_type_str} {field_name}"
            if default is not None:
                field_line += f" = {json.dumps(default)}"
            field_line += ";"
            
            if doc:
                field_line = f"  /** {doc} */\n{field_line}"
            
            return field_line
        
        namespace = schema_obj.get("namespace", "")
        record_name = schema_obj.get("name", subject)
        doc = schema_obj.get("doc", f"Schema for {subject}")
        
        idl = f"""/**
 * {doc}
 * Generated from Schema Registry subject: {subject}
 */
"""
        
        if namespace:
            idl += f"@namespace(\"{namespace}\")\n"
        
        idl += f"protocol {record_name}Protocol {{\n\n"
        idl += f"record {record_name} {{\n"
        
        for field in schema_obj.get("fields", []):
            idl += format_field(field) + "\n"
        
        idl += "}\n\n}"
        
        return idl
    except Exception as e:
        # Fallback to JSON if IDL conversion fails
        return schema_str

async def get_schema_with_metadata(subject: str, version: str, context: Optional[str] = None) -> ExportedSchema:
    """Get schema with metadata for export."""
    try:
        # Get schema details
        url = build_context_url(f"/subjects/{subject}/versions/{version}", context)
        response = requests.get(url, auth=auth, headers=headers)
        response.raise_for_status()
        schema_data = response.json()
        
        # Get schema type (default to AVRO if not available)
        schema_type = "AVRO"
        try:
            # Try to determine schema type from schema registry response
            if "schemaType" in schema_data:
                schema_type = schema_data["schemaType"]
        except:
            pass
        
        # Build metadata
        # Use external URL for tests, internal URL for container communication
        external_registry_url = SCHEMA_REGISTRY_URL
        if SCHEMA_REGISTRY_URL.startswith("http://schema-registry-mcp:"):
            external_registry_url = "http://localhost:38081"
        
        metadata = {
            "exported_at": datetime.now().isoformat(),
            "registry_url": external_registry_url,
            "context": context
        }
        
        return ExportedSchema(
            subject=schema_data["subject"],
            version=schema_data["version"],
            id=schema_data["id"],
            schema=schema_data["schema"],
            schemaType=schema_type,
            metadata=metadata
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get schema {subject}:{version}: {str(e)}")

async def get_subject_config_safe(subject: str, context: Optional[str] = None) -> Optional[Dict]:
    """Get subject configuration, return None if not found."""
    try:
        url = build_context_url(f"/config/{subject}", context)
        response = requests.get(url, auth=auth, headers=standard_headers)
        response.raise_for_status()
        return response.json()
    except:
        return None

async def get_subject_mode_safe(subject: str, context: Optional[str] = None) -> Optional[Dict]:
    """Get subject mode, return None if not found."""
    try:
        url = build_context_url(f"/mode/{subject}", context)
        response = requests.get(url, auth=auth, headers=standard_headers)
        response.raise_for_status()
        return response.json()
    except:
        return None

async def export_subject_data(subject: str, export_request: ExportRequest, context: Optional[str] = None) -> SubjectExport:
    """Export all data for a specific subject."""
    try:
        # Get all versions for the subject
        url = build_context_url(f"/subjects/{subject}/versions", context)
        response = requests.get(url, auth=auth, headers=headers)
        response.raise_for_status()
        versions = response.json()
        
        # Determine which versions to export
        versions_to_export = []
        if export_request.include_versions == "latest":
            versions_to_export = [max(versions)]
        elif export_request.include_versions == "all":
            versions_to_export = versions
        elif export_request.include_versions.isdigit():
            version_num = int(export_request.include_versions)
            if version_num in versions:
                versions_to_export = [version_num]
        else:
            versions_to_export = versions
        
        # Export each version
        exported_schemas = []
        for version in versions_to_export:
            schema = await get_schema_with_metadata(subject, str(version), context)
            exported_schemas.append(schema)
        
        # Get config and mode if requested
        config = None
        mode = None
        if export_request.include_config:
            config = await get_subject_config_safe(subject, context)
        if export_request.include_metadata:
            mode = await get_subject_mode_safe(subject, context)
        
        return SubjectExport(
            subject=subject,
            versions=exported_schemas,
            config=config,
            mode=mode
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export subject {subject}: {str(e)}")

async def export_context_data(context: str, export_request: ExportRequest) -> ContextExport:
    """Export all data for a specific context."""
    try:
        # Get all subjects in the context
        url = build_context_url("/subjects", context)
        response = requests.get(url, auth=auth, headers=headers)
        
        # Handle case where context has no subjects or doesn't exist
        if response.status_code == 404:
            subjects = []
        else:
            response.raise_for_status()
            subjects = response.json()
        
        # Export each subject
        exported_subjects = []
        for subject in subjects:
            # Remove context prefix if present (:.context:subject -> subject)
            clean_subject = subject
            if subject.startswith(f":.{context}:"):
                clean_subject = subject[len(f":.{context}:"):]
            
            subject_export = await export_subject_data(clean_subject, export_request, context)
            exported_subjects.append(subject_export)
        
        # Get global config and mode for context if requested
        global_config = None
        global_mode = None
        if export_request.include_config:
            try:
                url = build_context_url("/config", context)
                response = requests.get(url, auth=auth, headers=standard_headers)
                response.raise_for_status()
                global_config = response.json()
            except:
                pass
        
        if export_request.include_metadata:
            try:
                url = build_context_url("/mode", context)
                response = requests.get(url, auth=auth, headers=standard_headers)
                response.raise_for_status()
                global_mode = response.json()
            except:
                pass
        
        return ContextExport(
            context=context,
            exported_at=datetime.now().isoformat(),
            subjects=exported_subjects,
            global_config=global_config,
            global_mode=global_mode
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export context {context}: {str(e)}")

# Export Endpoints

@app.get("/export/schemas/{subject}")
async def export_schema(
    subject: str, 
    version: Optional[str] = "latest",
    context: Optional[str] = Query(None, description="Schema context"),
    format: Optional[str] = Query("json", description="Export format: json, avro_idl"),
    include_metadata: Optional[bool] = Query(True, description="Include export metadata")
):
    """Export a single schema version."""
    try:
        export_request = ExportRequest(
            format=format,
            include_metadata=include_metadata,
            include_versions=version
        )
        
        schema = await get_schema_with_metadata(subject, version, context)
        
        if format == "avro_idl":
            idl_content = format_schema_as_avro_idl(schema.schema, subject)
            return Response(
                content=idl_content,
                media_type="text/plain",
                headers={"Content-Disposition": f"attachment; filename={subject}_v{schema.version}.avdl"}
            )
        else:
            return schema
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/export/subjects/{subject}")
async def export_subject(
    subject: str,
    export_request: ExportRequest,
    context: Optional[str] = Query(None, description="Schema context")
):
    """Export all versions and metadata for a specific subject."""
    try:
        return await export_subject_data(subject, export_request, context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/export/contexts/{context}")
async def export_context(
    context: str,
    export_request: ExportRequest
):
    """Export all schemas, config, and mode for a specific context."""
    try:
        context_export = await export_context_data(context, export_request)
        
        if export_request.format == "bundle":
            # Create a ZIP bundle
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add context metadata
                zip_file.writestr(f"{context}/metadata.json", json.dumps({
                    "context": context,
                    "exported_at": context_export.exported_at,
                    "global_config": context_export.global_config,
                    "global_mode": context_export.global_mode
                }, indent=2))
                
                # Add each subject's schemas
                for subject_export in context_export.subjects:
                    subject_dir = f"{context}/subjects/{subject_export.subject}"
                    
                    # Subject metadata
                    zip_file.writestr(f"{subject_dir}/metadata.json", json.dumps({
                        "subject": subject_export.subject,
                        "config": subject_export.config,
                        "mode": subject_export.mode
                    }, indent=2))
                    
                    # Schema versions
                    for schema in subject_export.versions:
                        schema_file = f"{subject_dir}/v{schema.version}.json"
                        zip_file.writestr(schema_file, json.dumps({
                            "subject": schema.subject,
                            "version": schema.version,
                            "id": schema.id,
                            "schema": json.loads(schema.schema),
                            "schemaType": schema.schemaType,
                            "metadata": schema.metadata
                        }, indent=2))
                        
                        # Also create IDL version
                        if schema.schemaType == "AVRO":
                            idl_content = format_schema_as_avro_idl(schema.schema, schema.subject)
                            idl_file = f"{subject_dir}/v{schema.version}.avdl"
                            zip_file.writestr(idl_file, idl_content)
            
            zip_buffer.seek(0)
            return StreamingResponse(
                io.BytesIO(zip_buffer.read()),
                media_type="application/zip",
                headers={"Content-Disposition": f"attachment; filename={context}_export.zip"}
            )
        else:
            return context_export
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/export/global")
async def export_global(export_request: ExportRequest):
    """Export all schemas from all contexts."""
    try:
        # Get all contexts
        response = requests.get(f"{SCHEMA_REGISTRY_URL}/contexts", auth=auth, headers=headers)
        response.raise_for_status()
        contexts = response.json()
        
        # Export each context
        exported_contexts = []
        for context in contexts:
            # Clean context name (remove leading dot if present)
            clean_context = context.lstrip('.')
            context_export = await export_context_data(clean_context, export_request)
            # Use the clean context name in the export
            context_export.context = clean_context
            exported_contexts.append(context_export)
        
        # Export default context (no context specified)
        default_export = await export_context_data("", export_request)
        # Ensure default context has empty string as context name
        default_export.context = ""
        
        # Get global config and mode
        global_config = None
        global_mode = None
        if export_request.include_config:
            try:
                response = requests.get(f"{SCHEMA_REGISTRY_URL}/config", auth=auth, headers=standard_headers)
                response.raise_for_status()
                global_config = response.json()
            except:
                pass
        
        if export_request.include_metadata:
            try:
                response = requests.get(f"{SCHEMA_REGISTRY_URL}/mode", auth=auth, headers=standard_headers)
                response.raise_for_status()
                global_mode = response.json()
            except:
                pass
        
        global_export = GlobalExport(
            exported_at=datetime.now().isoformat(),
            contexts=exported_contexts,
            default_context=default_export,
            global_config=global_config,
            global_mode=global_mode
        )
        
        if export_request.format == "bundle":
            # Create a comprehensive ZIP bundle
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Global metadata
                zip_file.writestr("global_metadata.json", json.dumps({
                    "exported_at": global_export.exported_at,
                    "global_config": global_config,
                    "global_mode": global_mode,
                    "contexts": [ctx.context for ctx in exported_contexts]
                }, indent=2))
                
                # Export each context
                all_contexts = exported_contexts + [default_export]
                for context_export in all_contexts:
                    context_name = context_export.context or "default"
                    context_dir = f"contexts/{context_name}"
                    
                    # Context metadata
                    zip_file.writestr(f"{context_dir}/metadata.json", json.dumps({
                        "context": context_export.context,
                        "exported_at": context_export.exported_at,
                        "global_config": context_export.global_config,
                        "global_mode": context_export.global_mode
                    }, indent=2))
                    
                    # Export subjects in this context
                    for subject_export in context_export.subjects:
                        subject_dir = f"{context_dir}/subjects/{subject_export.subject}"
                        
                        # Subject metadata
                        zip_file.writestr(f"{subject_dir}/metadata.json", json.dumps({
                            "subject": subject_export.subject,
                            "config": subject_export.config,
                            "mode": subject_export.mode
                        }, indent=2))
                        
                        # Schema versions
                        for schema in subject_export.versions:
                            schema_file = f"{subject_dir}/v{schema.version}.json"
                            zip_file.writestr(schema_file, json.dumps({
                                "subject": schema.subject,
                                "version": schema.version,
                                "id": schema.id,
                                "schema": json.loads(schema.schema),
                                "schemaType": schema.schemaType,
                                "metadata": schema.metadata
                            }, indent=2))
                            
                            # IDL version for Avro schemas
                            if schema.schemaType == "AVRO":
                                idl_content = format_schema_as_avro_idl(schema.schema, schema.subject)
                                idl_file = f"{subject_dir}/v{schema.version}.avdl"
                                zip_file.writestr(idl_file, idl_content)
            
            zip_buffer.seek(0)
            return StreamingResponse(
                io.BytesIO(zip_buffer.read()),
                media_type="application/zip",
                headers={"Content-Disposition": f"attachment; filename=schema_registry_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"}
            )
        else:
            return global_export
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/export/subjects")
async def list_exportable_subjects(
    context: Optional[str] = Query(None, description="Schema context")
):
    """List all subjects available for export."""
    try:
        url = build_context_url("/subjects", context)
        response = requests.get(url, auth=auth, headers=headers)
        response.raise_for_status()
        subjects = response.json()
        
        # Get version counts for each subject
        subject_info = []
        for subject in subjects:
            try:
                versions_url = build_context_url(f"/subjects/{subject}/versions", context)
                versions_response = requests.get(versions_url, auth=auth, headers=headers)
                versions_response.raise_for_status()
                versions = versions_response.json()
                
                # Clean subject name if it has context prefix
                clean_subject = subject
                if context and subject.startswith(f":.{context}:"):
                    clean_subject = subject[len(f":.{context}:"):]
                
                subject_info.append({
                    "subject": clean_subject,
                    "full_subject": subject,
                    "version_count": len(versions),
                    "latest_version": max(versions) if versions else 0,
                    "context": context
                })
            except:
                # If we can't get versions, just include the subject
                subject_info.append({
                    "subject": subject,
                    "full_subject": subject,
                    "version_count": 0,
                    "latest_version": 0,
                    "context": context
                })
        
        return {
            "context": context,
            "subjects": subject_info,
            "total_subjects": len(subject_info)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)