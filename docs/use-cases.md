# Kafka Schema Registry MCP Server - Use Cases

This document outlines various real-world use cases and scenarios for the Kafka Schema Registry MCP Server with Context Support.

## 🏢 Enterprise Use Cases

### 1. Multi-Environment Schema Management

#### **Scenario**: Large Enterprise with Multiple Deployment Environments
A technology company with microservices architecture needs to manage schemas across development, staging, and production environments.

**Implementation:**
```bash
# Create environment-specific contexts
curl -X POST http://localhost:38000/contexts/development
curl -X POST http://localhost:38000/contexts/staging  
curl -X POST http://localhost:38000/contexts/production

# Register user schema in development
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "user-events",
    "schema": {
      "type": "record",
      "name": "UserEvent",
      "fields": [
        {"name": "userId", "type": "string"},
        {"name": "eventType", "type": "string"},
        {"name": "timestamp", "type": "long"}
      ]
    },
    "context": "development"
  }'

# Promote to staging after testing
curl -X POST http://localhost:38000/schemas?context=staging \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "user-events", 
    "schema": {...},
    "schemaType": "AVRO"
  }'
```

**Benefits:**
- ✅ Environment isolation prevents accidental production impact
- ✅ Schema evolution testing in safe environments
- ✅ Controlled promotion workflow
- ✅ Independent versioning per environment

---

### 2. Multi-Tenant SaaS Platform

#### **Scenario**: SaaS Platform with Client-Specific Schema Requirements
A platform serving multiple clients where each client may have customized data structures and compliance requirements.

**Implementation:**
```bash
# Create client-specific contexts
curl -X POST http://localhost:38000/contexts/client-acme
curl -X POST http://localhost:38000/contexts/client-globex
curl -X POST http://localhost:38000/contexts/client-initech

# Client-specific user schema with GDPR fields
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "user-profile",
    "schema": {
      "type": "record",
      "name": "UserProfile",
      "fields": [
        {"name": "userId", "type": "string"},
        {"name": "email", "type": "string"},
        {"name": "gdprConsent", "type": "boolean"},
        {"name": "dataRetentionDays", "type": "int", "default": 365}
      ]
    },
    "context": "client-acme"
  }'

# Different schema for another client
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "user-profile", 
    "schema": {
      "type": "record",
      "name": "UserProfile", 
      "fields": [
        {"name": "userId", "type": "string"},
        {"name": "email", "type": "string"},
        {"name": "hipaaCompliant", "type": "boolean"},
        {"name": "encryptionLevel", "type": "string", "default": "AES256"}
      ]
    },
    "context": "client-globex"
  }'
```

**Benefits:**
- ✅ Complete tenant isolation
- ✅ Compliance-specific schema variations
- ✅ Independent evolution per client
- ✅ Scalable multi-tenancy

---

### 3. Microservices Team Boundaries

#### **Scenario**: Large Organization with Multiple Development Teams
Different teams managing different domains (user management, payments, analytics) need schema autonomy while maintaining integration capabilities.

**Implementation:**
```bash
# Team-based contexts
curl -X POST http://localhost:38000/contexts/team-identity
curl -X POST http://localhost:38000/contexts/team-payments
curl -X POST http://localhost:38000/contexts/team-analytics
curl -X POST http://localhost:38000/contexts/shared

# Team Identity manages user schemas
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "user-created",
    "schema": {
      "type": "record",
      "name": "UserCreated",
      "namespace": "com.company.identity",
      "fields": [
        {"name": "userId", "type": "string"},
        {"name": "email", "type": "string"},
        {"name": "createdAt", "type": "long"},
        {"name": "profile", "type": {
          "type": "record",
          "name": "Profile",
          "fields": [
            {"name": "firstName", "type": "string"},
            {"name": "lastName", "type": "string"}
          ]
        }}
      ]
    },
    "context": "team-identity"
  }'

# Shared schema for cross-team events
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "domain-event",
    "schema": {
      "type": "record", 
      "name": "DomainEvent",
      "namespace": "com.company.shared",
      "fields": [
        {"name": "eventId", "type": "string"},
        {"name": "aggregateId", "type": "string"},
        {"name": "eventType", "type": "string"},
        {"name": "timestamp", "type": "long"},
        {"name": "payload", "type": "string"}
      ]
    },
    "context": "shared"
  }'
```

**Benefits:**
- ✅ Team autonomy and ownership
- ✅ Clear domain boundaries
- ✅ Shared schemas for integration
- ✅ Independent development velocity

---

## 🛠️ Development Workflow Use Cases

### 4. Schema Evolution Testing

#### **Scenario**: Safe Schema Evolution with Compatibility Validation
A team needs to evolve schemas while ensuring backward compatibility across all dependent services.

**Workflow:**
```bash
# 1. Check current schema in production
curl http://localhost:38000/schemas/order-events?context=production

# 2. Design evolution in development context
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "order-events",
    "schema": {
      "type": "record",
      "name": "OrderEvent",
      "fields": [
        {"name": "orderId", "type": "string"},
        {"name": "customerId", "type": "string"}, 
        {"name": "amount", "type": "double"},
        {"name": "currency", "type": "string", "default": "USD"},
        {"name": "metadata", "type": ["null", "string"], "default": null}
      ]
    },
    "context": "development"
  }'

# 3. Test compatibility against production
curl -X POST http://localhost:38000/compatibility \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "order-events",
    "schema": {...new_schema...},
    "context": "production"
  }'

# 4. If compatible, promote to staging
curl -X POST http://localhost:38000/schemas?context=staging \
  -H "Content-Type: application/json" \
  -d '{...}'
```

**Benefits:**
- ✅ Risk-free schema evolution
- ✅ Automated compatibility checking  
- ✅ Staged rollout process
- ✅ Rollback capabilities

---

### 5. Feature Branch Schema Development

#### **Scenario**: Feature-Specific Schema Development
Developers working on new features need isolated schema development without affecting main development branch.

**Implementation:**
```bash
# Create feature-specific context
curl -X POST http://localhost:38000/contexts/feature-user-preferences

# Develop feature schema
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "user-preferences-updated",
    "schema": {
      "type": "record",
      "name": "UserPreferencesUpdated", 
      "fields": [
        {"name": "userId", "type": "string"},
        {"name": "preferences", "type": {
          "type": "map",
          "values": "string"
        }},
        {"name": "updatedAt", "type": "long"}
      ]
    },
    "context": "feature-user-preferences"
  }'

# Test integration
curl http://localhost:38000/schemas/user-preferences-updated?context=feature-user-preferences

# When feature is ready, merge to development
curl -X POST http://localhost:38000/schemas?context=development \
  -H "Content-Type: application/json" \
  -d '{...}'

# Clean up feature context
curl -X DELETE http://localhost:38000/contexts/feature-user-preferences
```

**Benefits:**
- ✅ Isolated feature development
- ✅ No conflicts with main development
- ✅ Easy cleanup after merge
- ✅ Parallel feature development

---

## 🔒 Compliance & Governance Use Cases

### 6. Regulatory Compliance Management

#### **Scenario**: Financial Services with Multiple Regulatory Requirements
A financial institution needs different schema variations for different regulatory jurisdictions (GDPR, CCPA, PCI-DSS).

**Implementation:**
```bash
# Regulatory contexts
curl -X POST http://localhost:38000/contexts/gdpr-eu
curl -X POST http://localhost:38000/contexts/ccpa-california  
curl -X POST http://localhost:38000/contexts/pci-payments

# GDPR-compliant transaction schema
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "transaction-event",
    "schema": {
      "type": "record",
      "name": "TransactionEvent",
      "fields": [
        {"name": "transactionId", "type": "string"},
        {"name": "amount", "type": "double"},
        {"name": "currency", "type": "string"},
        {"name": "timestamp", "type": "long"},
        {"name": "gdprConsent", "type": "boolean"},
        {"name": "dataSubjectRights", "type": "string"},
        {"name": "retentionPeriod", "type": "int"}
      ]
    },
    "context": "gdpr-eu"
  }'

# PCI-compliant payment schema (no sensitive data)
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "payment-event",
    "schema": {
      "type": "record", 
      "name": "PaymentEvent",
      "fields": [
        {"name": "paymentId", "type": "string"},
        {"name": "amount", "type": "double"},
        {"name": "currency", "type": "string"},
        {"name": "tokenizedCard", "type": "string"},
        {"name": "merchantId", "type": "string"},
        {"name": "timestamp", "type": "long"}
      ]
    },
    "context": "pci-payments"
  }'
```

**Benefits:**
- ✅ Compliance-specific schema isolation
- ✅ Audit trail per jurisdiction
- ✅ Reduced compliance risk
- ✅ Simplified regulatory reporting

---

### 7. Data Lifecycle Management

#### **Scenario**: Automated Data Retention and Privacy Management
An organization needs to manage data schemas with different retention policies and privacy requirements.

**Implementation:**
```bash
# Lifecycle-based contexts
curl -X POST http://localhost:38000/contexts/short-retention
curl -X POST http://localhost:38000/contexts/long-retention
curl -X POST http://localhost:38000/contexts/archived

# Short retention schema (30 days)
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "user-activity",
    "schema": {
      "type": "record",
      "name": "UserActivity",
      "fields": [
        {"name": "userId", "type": "string"},
        {"name": "activity", "type": "string"},
        {"name": "timestamp", "type": "long"},
        {"name": "ttl", "type": "long", "default": 2592000},
        {"name": "piiLevel", "type": "string", "default": "HIGH"}
      ]
    },
    "context": "short-retention"
  }'

# Long retention schema (7 years)
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "financial-record",
    "schema": {
      "type": "record",
      "name": "FinancialRecord", 
      "fields": [
        {"name": "recordId", "type": "string"},
        {"name": "amount", "type": "double"},
        {"name": "timestamp", "type": "long"},
        {"name": "ttl", "type": "long", "default": 220752000},
        {"name": "auditRequired", "type": "boolean", "default": true}
      ]
    },
    "context": "long-retention"
  }'
```

**Benefits:**
- ✅ Automated retention policy enforcement
- ✅ Privacy-aware schema design
- ✅ Compliance with data protection laws
- ✅ Simplified data governance

---

## 🧪 Testing & Quality Assurance Use Cases

### 8. A/B Testing Schema Management

#### **Scenario**: Running Multiple Schema Versions for A/B Testing
A data science team needs to run experiments with different event schemas to optimize data collection.

**Implementation:**
```bash
# A/B test contexts
curl -X POST http://localhost:38000/contexts/experiment-control
curl -X POST http://localhost:38000/contexts/experiment-variant-a
curl -X POST http://localhost:38000/contexts/experiment-variant-b

# Control group schema (baseline)
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "user-interaction",
    "schema": {
      "type": "record",
      "name": "UserInteraction",
      "fields": [
        {"name": "userId", "type": "string"},
        {"name": "pageUrl", "type": "string"}, 
        {"name": "timestamp", "type": "long"}
      ]
    },
    "context": "experiment-control"
  }'

# Variant A: Additional engagement metrics
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "user-interaction",
    "schema": {
      "type": "record",
      "name": "UserInteraction",
      "fields": [
        {"name": "userId", "type": "string"},
        {"name": "pageUrl", "type": "string"},
        {"name": "timestamp", "type": "long"},
        {"name": "scrollDepth", "type": "double"},
        {"name": "timeOnPage", "type": "long"}
      ]
    },
    "context": "experiment-variant-a"
  }'
```

**Benefits:**
- ✅ Parallel experiment execution
- ✅ Schema isolation per variant
- ✅ Easy comparison and analysis
- ✅ Quick rollback capabilities

---

### 9. Chaos Engineering & Resilience Testing

#### **Scenario**: Testing System Resilience to Schema Changes
A platform engineering team needs to test how services handle schema evolution and compatibility issues.

**Implementation:**
```bash
# Create chaos testing context
curl -X POST http://localhost:38000/contexts/chaos-testing

# Introduce intentionally breaking schema
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "order-event",
    "schema": {
      "type": "record",
      "name": "OrderEvent",
      "fields": [
        {"name": "orderId", "type": "int"},
        {"name": "customerId", "type": "int"},
        {"name": "total", "type": "string"}
      ]
    },
    "context": "chaos-testing"  
  }'

# Test compatibility (should fail)
curl -X POST http://localhost:38000/compatibility \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "order-event",
    "schema": {...breaking_schema...},
    "context": "production"
  }'

# Monitor service behavior and recovery
```

**Benefits:**
- ✅ Controlled failure injection
- ✅ Resilience validation
- ✅ Monitoring effectiveness testing
- ✅ Disaster recovery validation

---

## 📊 Analytics & Monitoring Use Cases

### 10. Schema Analytics and Governance

#### **Scenario**: Understanding Schema Usage and Evolution Patterns
A data governance team needs insights into schema usage, evolution patterns, and potential optimization opportunities.

**Monitoring Queries:**
```bash
# Analyze schema evolution across contexts
for context in development staging production; do
  echo "=== Context: $context ==="
  curl -s "http://localhost:38000/subjects?context=$context" | jq .
  echo ""
done

# Version analysis per subject
curl -s "http://localhost:38000/schemas/user-events/versions?context=production" | jq .

# Schema size and complexity analysis
curl -s "http://localhost:38000/schemas/user-events?context=production" | \
  jq '.schema | fromjson | .fields | length'
```

**Custom Analytics Script:**
```python
import requests
import json
from datetime import datetime

class SchemaAnalytics:
    def __init__(self, mcp_url):
        self.mcp_url = mcp_url
    
    def analyze_schema_evolution(self):
        """Analyze schema evolution patterns across contexts"""
        contexts = self.get_contexts()
        
        for context in contexts:
            subjects = self.get_subjects(context)
            for subject in subjects:
                versions = self.get_versions(subject, context)
                print(f"Subject {subject} in {context}: {len(versions)} versions")
    
    def detect_breaking_changes(self):
        """Detect potential breaking changes"""
        # Implementation for breaking change detection
        pass
    
    def generate_governance_report(self):
        """Generate comprehensive governance report"""
        # Implementation for governance reporting
        pass
```

**Benefits:**
- ✅ Data-driven schema governance
- ✅ Evolution pattern insights
- ✅ Breaking change prevention
- ✅ Optimization opportunities identification

---

## 🚀 Performance & Scalability Use Cases

### 11. High-Volume Event Processing

#### **Scenario**: E-commerce Platform with Millions of Events
A large e-commerce platform processes millions of events daily and needs efficient schema management for different event types.

**Schema Strategy:**
```bash
# Event-type contexts for performance isolation
curl -X POST http://localhost:38000/contexts/events-high-volume
curl -X POST http://localhost:38000/contexts/events-critical
curl -X POST http://localhost:38000/contexts/events-analytics

# High-volume, lightweight schema
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "page-view",
    "schema": {
      "type": "record",
      "name": "PageView",
      "fields": [
        {"name": "sessionId", "type": "string"},
        {"name": "pageId", "type": "string"},
        {"name": "timestamp", "type": "long"}
      ]
    },
    "context": "events-high-volume"
  }'

# Critical business events with full detail
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "order-completed",
    "schema": {
      "type": "record",
      "name": "OrderCompleted",
      "fields": [
        {"name": "orderId", "type": "string"},
        {"name": "customerId", "type": "string"},
        {"name": "items", "type": {
          "type": "array",
          "items": {
            "type": "record",
            "name": "OrderItem",
            "fields": [
              {"name": "productId", "type": "string"},
              {"name": "quantity", "type": "int"},
              {"name": "price", "type": "double"}
            ]
          }
        }},
        {"name": "total", "type": "double"},
        {"name": "timestamp", "type": "long"}
      ]
    },
    "context": "events-critical"
  }'
```

**Benefits:**
- ✅ Performance optimization by event type
- ✅ Resource allocation efficiency
- ✅ Scalable schema organization
- ✅ Reduced serialization overhead

---

## 🎯 Integration Patterns

### 12. Event-Driven Architecture Integration

#### **Scenario**: Microservices with Complex Event Choreography
A system with multiple microservices using event-driven architecture needs coordinated schema management for event choreography.

**Event Flow Schema Management:**
```bash
# Service-specific contexts
curl -X POST http://localhost:38000/contexts/user-service
curl -X POST http://localhost:38000/contexts/order-service  
curl -X POST http://localhost:38000/contexts/payment-service
curl -X POST http://localhost:38000/contexts/notification-service

# User service publishes user events
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "user-registered",
    "schema": {
      "type": "record",
      "name": "UserRegistered",
      "fields": [
        {"name": "userId", "type": "string"},
        {"name": "email", "type": "string"},
        {"name": "registeredAt", "type": "long"},
        {"name": "correlationId", "type": "string"}
      ]
    },
    "context": "user-service"
  }'

# Order service consumes user events and publishes order events  
curl -X POST http://localhost:38000/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "order-created",
    "schema": {
      "type": "record",
      "name": "OrderCreated", 
      "fields": [
        {"name": "orderId", "type": "string"},
        {"name": "userId", "type": "string"},
        {"name": "items", "type": {"type": "array", "items": "string"}},
        {"name": "total", "type": "double"},
        {"name": "createdAt", "type": "long"},
        {"name": "correlationId", "type": "string"}
      ]
    },
    "context": "order-service"
  }'
```

**Cross-Service Schema Validation:**
```bash
# Validate cross-service event compatibility
curl -X POST http://localhost:38000/compatibility \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "user-registered",
    "schema": {...updated_schema...},
    "context": "user-service"
  }'
```

**Benefits:**
- ✅ Service autonomy with schema ownership
- ✅ Event contract validation
- ✅ Choreography pattern support
- ✅ Reduced coupling between services

---

This comprehensive use case documentation demonstrates the versatility and power of the Kafka Schema Registry MCP server across various domains, team structures, and technical requirements. Each use case provides practical implementation examples and clear benefits for specific scenarios. 