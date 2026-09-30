{{/* Common labels, applied everywhere - what Kyverno's namespaceSelector-scoped policies (ADR 0013) and both NetworkPolicies (ADR 0014) match against. */}}
{{- define "palisade.labels" -}}
app.kubernetes.io/part-of: palisade
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}
