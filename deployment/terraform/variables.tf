# Terraform Variables for PawConnect AI - Production Configuration

# =============================================================================
# PROJECT CONFIGURATION
# =============================================================================

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

# =============================================================================
# ALERTING & MONITORING
# =============================================================================

variable "alert_email" {
  description = "Email address for monitoring alerts"
  type        = string
}

# =============================================================================
# SECRETS (Provided via Secret Manager)
# =============================================================================

variable "dialogflow_agent_id" {
  description = "Dialogflow CX Agent ID (stored in Secret Manager)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "rescuegroups_api_key" {
  description = "RescueGroups API Key (stored in Secret Manager)"
  type        = string
  sensitive   = true
  default     = ""
}

# =============================================================================
# VERTEX AI (OPTIONAL)
# =============================================================================

variable "vertex_ai_endpoint" {
  description = "Vertex AI model endpoint (optional)"
  type        = string
  default     = ""
}

# =============================================================================
# CLOUD RUN CONFIGURATION
# =============================================================================

variable "min_instances" {
  description = "Minimum number of Cloud Run instances"
  type        = number
  default     = 1

  validation {
    condition     = var.min_instances >= 0 && var.min_instances <= 100
    error_message = "min_instances must be between 0 and 100."
  }
}

variable "max_instances" {
  description = "Maximum number of Cloud Run instances"
  type        = number
  default     = 20

  validation {
    condition     = var.max_instances >= 1 && var.max_instances <= 1000
    error_message = "max_instances must be between 1 and 1000."
  }
}

variable "container_memory" {
  description = "Memory limit for Cloud Run container"
  type        = string
  default     = "2Gi"

  validation {
    condition     = can(regex("^[0-9]+(Mi|Gi)$", var.container_memory))
    error_message = "container_memory must be a valid memory size (e.g., 512Mi, 2Gi)."
  }
}

variable "container_cpu" {
  description = "CPU limit for Cloud Run container"
  type        = string
  default     = "2"

  validation {
    condition     = contains(["1", "2", "4", "6", "8"], var.container_cpu)
    error_message = "container_cpu must be one of: 1, 2, 4, 6, 8."
  }
}

# =============================================================================
# REDIS (MEMORYSTORE) CONFIGURATION
# =============================================================================

variable "redis_tier" {
  description = "Redis instance tier (BASIC or STANDARD_HA)"
  type        = string
  default     = "BASIC"

  validation {
    condition     = contains(["BASIC", "STANDARD_HA"], var.redis_tier)
    error_message = "redis_tier must be either BASIC or STANDARD_HA."
  }
}

variable "redis_memory_size" {
  description = "Redis memory size in GB"
  type        = number
  default     = 1

  validation {
    condition     = var.redis_memory_size >= 1 && var.redis_memory_size <= 300
    error_message = "redis_memory_size must be between 1 and 300 GB."
  }
}

# =============================================================================
# VPC CONFIGURATION
# =============================================================================

variable "enable_vpc_connector" {
  description = "Enable VPC connector for Cloud Run (always true for production)"
  type        = bool
  default     = true
}

variable "vpc_connector_name" {
  description = "VPC connector name"
  type        = string
  default     = "pawconnect-connector"
}

# =============================================================================
# FEATURE FLAGS
# =============================================================================

variable "enable_model_retraining" {
  description = "Enable automated model retraining via Cloud Scheduler"
  type        = bool
  default     = false
}

# =============================================================================
# ADDITIONAL CONFIGURATION
# =============================================================================

variable "labels" {
  description = "Labels to apply to all resources"
  type        = map(string)
  default = {
    application = "pawconnect"
    managed_by  = "terraform"
  }
}
