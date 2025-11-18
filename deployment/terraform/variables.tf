# Terraform Variables for PawConnect AI

variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "Google Cloud region for resources"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production."
  }
}

variable "alert_email" {
  description = "Email address for monitoring alerts"
  type        = string
}

variable "dialogflow_agent_id" {
  description = "Dialogflow CX Agent ID"
  type        = string
  sensitive   = true
}

variable "rescuegroups_api_key" {
  description = "RescueGroups API Key"
  type        = string
  sensitive   = true
}

variable "vertex_ai_endpoint" {
  description = "Vertex AI model endpoint (optional)"
  type        = string
  default     = ""
}

variable "min_instances" {
  description = "Minimum number of Cloud Run instances"
  type        = number
  default     = 1
}

variable "max_instances" {
  description = "Maximum number of Cloud Run instances"
  type        = number
  default     = 10
}

variable "container_memory" {
  description = "Memory limit for Cloud Run container"
  type        = string
  default     = "2Gi"
}

variable "container_cpu" {
  description = "CPU limit for Cloud Run container"
  type        = string
  default     = "2"
}

variable "enable_vpc_connector" {
  description = "Enable VPC connector for Cloud Run"
  type        = bool
  default     = false
}

variable "vpc_connector_name" {
  description = "VPC connector name (if enabled)"
  type        = string
  default     = ""
}
