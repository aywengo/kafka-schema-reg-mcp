{{/*
Expand the name of the chart.
*/}}
{{- define "kafka-schema-registry-mcp.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "kafka-schema-registry-mcp.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "kafka-schema-registry-mcp.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "kafka-schema-registry-mcp.labels" -}}
helm.sh/chart: {{ include "kafka-schema-registry-mcp.chart" . }}
{{ include "kafka-schema-registry-mcp.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.commonLabels }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "kafka-schema-registry-mcp.selectorLabels" -}}
app.kubernetes.io/name: {{ include "kafka-schema-registry-mcp.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "kafka-schema-registry-mcp.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "kafka-schema-registry-mcp.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Generate OAuth2 secret name
*/}}
{{- define "kafka-schema-registry-mcp.oauth2SecretName" -}}
{{- if .Values.auth.existingSecret.enabled }}
{{- .Values.auth.existingSecret.name }}
{{- else }}
{{- printf "%s-oauth2" (include "kafka-schema-registry-mcp.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Generate Schema Registry secret name
*/}}
{{- define "kafka-schema-registry-mcp.schemaRegistrySecretName" -}}
{{- if .Values.schemaRegistry.existingSecret.enabled }}
{{- .Values.schemaRegistry.existingSecret.name }}
{{- else }}
{{- printf "%s-schema-registry" (include "kafka-schema-registry-mcp.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Generate ConfigMap name
*/}}
{{- define "kafka-schema-registry-mcp.configMapName" -}}
{{- printf "%s-config" (include "kafka-schema-registry-mcp.fullname" .) }}
{{- end }}

{{/*
Common annotations
*/}}
{{- define "kafka-schema-registry-mcp.annotations" -}}
{{- with .Values.commonAnnotations }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{/*
Generate multi-registry environment variables
*/}}
{{- define "kafka-schema-registry-mcp.multiRegistryEnvVars" -}}
{{- if .Values.schemaRegistry.multiRegistry.enabled }}
{{- range $index, $registry := .Values.schemaRegistry.multiRegistry.registries }}
{{- $registryIndex := add $index 1 }}
- name: SCHEMA_REGISTRY_NAME_{{ $registryIndex }}
  value: {{ $registry.name | quote }}
- name: SCHEMA_REGISTRY_URL_{{ $registryIndex }}
  value: {{ $registry.url | quote }}
- name: READONLY_{{ $registryIndex }}
  value: {{ $registry.readonly | quote }}
{{- if $registry.user }}
- name: SCHEMA_REGISTRY_USER_{{ $registryIndex }}
  value: {{ $registry.user | quote }}
{{- end }}
{{- if $registry.password }}
- name: SCHEMA_REGISTRY_PASSWORD_{{ $registryIndex }}
  value: {{ $registry.password | quote }}
{{- end }}
{{- end }}
{{- end }}
{{- end }} 