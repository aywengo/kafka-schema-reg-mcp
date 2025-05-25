import os
import json
from typing import Dict, List, Optional, Union
from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import base64

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Kafka Schema Registry MCP",
    description="Message Control Protocol server for Kafka Schema Registry with Context Support, Configuration Management, and Mode Control",
    version="1.2.0"
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

def build_context_url(base_url: str, context: Optional[str] = None) -> str:
    """Build URL with optional context support."""
    if context:
        return f"{SCHEMA_REGISTRY_URL}/contexts/{context}{base_url}"
    return f"{SCHEMA_REGISTRY_URL}{base_url}"

@app.get("/")
async def root():
    return {"message": "Kafka Schema Registry MCP Server with Context Support, Configuration Management, and Mode Control"}

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)