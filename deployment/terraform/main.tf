# PawConnect AI - Terraform Infrastructure Configuration
# Production deployment with all required GCP resources

terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # Store state in Google Cloud Storage
  backend "gcs" {
    bucket = "pawconnect-terraform-state"
    prefix = "terraform/state"
  }
}

# Provider configuration
provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "containerregistry.googleapis.com",
    "artifactregistry.googleapis.com",
    "dialogflow.googleapis.com",
    "vision.googleapis.com",
    "aiplatform.googleapis.com",
    "pubsub.googleapis.com",
    "firestore.googleapis.com",
    "redis.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudscheduler.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "compute.googleapis.com",
    "vpcaccess.googleapis.com",
  ])

  service            = each.key
  disable_on_destroy = false
}

# =============================================================================
# VPC NETWORK
# =============================================================================

# VPC Network for production
resource "google_compute_network" "pawconnect_vpc" {
  name                    = "pawconnect-vpc"
  auto_create_subnetworks = false
  depends_on              = [google_project_service.required_apis]
}

# Subnet for the VPC
resource "google_compute_subnetwork" "pawconnect_subnet" {
  name          = "pawconnect-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.pawconnect_vpc.id
}

# VPC Access Connector for Cloud Run
resource "google_vpc_access_connector" "pawconnect_connector" {
  name          = "pawconnect-connector"
  region        = var.region
  network       = google_compute_network.pawconnect_vpc.name
  ip_cidr_range = "10.8.0.0/28"
  min_instances = 2
  max_instances = 3

  depends_on = [google_project_service.required_apis]
}

# =============================================================================
# MEMORYSTORE (REDIS)
# =============================================================================

# Redis instance for caching
resource "google_redis_instance" "pawconnect_redis" {
  name               = "pawconnect-redis"
  tier               = var.redis_tier
  memory_size_gb     = var.redis_memory_size
  region             = var.region
  redis_version      = "REDIS_7_0"
  authorized_network = google_compute_network.pawconnect_vpc.id
  auth_enabled       = true
  connect_mode       = "DIRECT_PEERING"

  depends_on = [google_project_service.required_apis]
}

# =============================================================================
# SECRET MANAGER
# =============================================================================

# Secret Manager for API keys
resource "google_secret_manager_secret" "rescuegroups_api_key" {
  secret_id = "rescuegroups-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret" "redis_password" {
  secret_id = "redis-password"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret" "dialogflow_agent_id" {
  secret_id = "dialogflow-agent-id"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

# =============================================================================
# SERVICE ACCOUNT
# =============================================================================

# Service account for Cloud Run
resource "google_service_account" "cloud_run_sa" {
  account_id   = "pawconnect-cloud-run"
  display_name = "PawConnect Cloud Run Service Account"
}

# IAM roles for service account
resource "google_project_iam_member" "cloud_run_roles" {
  for_each = toset([
    "roles/dialogflow.client",
    "roles/vision.user",
    "roles/aiplatform.user",
    "roles/pubsub.publisher",
    "roles/pubsub.subscriber",
    "roles/datastore.user",
    "roles/secretmanager.secretAccessor",
    "roles/cloudvision.user",
  ])

  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# =============================================================================
# PUB/SUB TOPICS & SUBSCRIPTIONS
# =============================================================================

# Pub/Sub topics for agent communication
resource "google_pubsub_topic" "search_results" {
  name = "pawconnect-prod-search-results"

  message_retention_duration = "604800s" # 7 days
}

resource "google_pubsub_topic" "recommendations" {
  name = "pawconnect-prod-recommendations"

  message_retention_duration = "604800s"
}

resource "google_pubsub_topic" "vision_analysis" {
  name = "pawconnect-prod-vision-analysis"

  message_retention_duration = "604800s"
}

resource "google_pubsub_topic" "workflow_events" {
  name = "pawconnect-prod-workflow-events"

  message_retention_duration = "604800s"
}

# Pub/Sub subscriptions
resource "google_pubsub_subscription" "search_results_sub" {
  name  = "pawconnect-prod-search-sub"
  topic = google_pubsub_topic.search_results.name

  ack_deadline_seconds       = 60
  message_retention_duration = "604800s"

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}

resource "google_pubsub_subscription" "recommendations_sub" {
  name  = "pawconnect-prod-recommendation-sub"
  topic = google_pubsub_topic.recommendations.name

  ack_deadline_seconds       = 60
  message_retention_duration = "604800s"

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}

resource "google_pubsub_subscription" "vision_analysis_sub" {
  name  = "pawconnect-prod-vision-sub"
  topic = google_pubsub_topic.vision_analysis.name

  ack_deadline_seconds       = 60
  message_retention_duration = "604800s"

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}

resource "google_pubsub_subscription" "workflow_events_sub" {
  name  = "pawconnect-prod-workflow-sub"
  topic = google_pubsub_topic.workflow_events.name

  ack_deadline_seconds       = 60
  message_retention_duration = "604800s"

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}

# =============================================================================
# CLOUD RUN SERVICES
# =============================================================================

# Cloud Run service for main agent
resource "google_cloud_run_service" "pawconnect_main_agent" {
  name     = "pawconnect-main-agent"
  location = var.region

  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/pawconnect-ai:latest"

        resources {
          limits = {
            cpu    = var.container_cpu
            memory = var.container_memory
          }
        }

        # Environment variables
        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }

        env {
          name  = "GCP_REGION"
          value = var.region
        }

        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }

        env {
          name  = "TESTING_MODE"
          value = "False"
        }

        env {
          name  = "MOCK_APIS"
          value = "False"
        }

        env {
          name  = "LOG_LEVEL"
          value = "INFO"
        }

        env {
          name  = "REDIS_HOST"
          value = google_redis_instance.pawconnect_redis.host
        }

        env {
          name  = "REDIS_PORT"
          value = "6379"
        }

        env {
          name  = "USE_GEMINI_FOR_CONVERSATION"
          value = "True"
        }

        env {
          name  = "GEMINI_MODEL_NAME"
          value = "gemini-2.0-flash-001"
        }

        env {
          name  = "VISION_API_ENABLED"
          value = "True"
        }

        env {
          name  = "PUBSUB_TOPIC_PREFIX"
          value = "pawconnect-prod"
        }

        env {
          name  = "FIRESTORE_COLLECTION_USERS"
          value = "users"
        }

        env {
          name  = "FIRESTORE_COLLECTION_APPLICATIONS"
          value = "applications"
        }

        # Secrets from Secret Manager
        env {
          name = "RESCUEGROUPS_API_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.rescuegroups_api_key.secret_id
              key  = "latest"
            }
          }
        }

        env {
          name = "REDIS_PASSWORD"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.redis_password.secret_id
              key  = "latest"
            }
          }
        }

        env {
          name = "DIALOGFLOW_AGENT_ID"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.dialogflow_agent_id.secret_id
              key  = "latest"
            }
          }
        }
      }

      service_account_name = google_service_account.cloud_run_sa.email
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale"                = var.min_instances
        "autoscaling.knative.dev/maxScale"                = var.max_instances
        "run.googleapis.com/vpc-access-connector"         = google_vpc_access_connector.pawconnect_connector.id
        "run.googleapis.com/vpc-access-egress"            = "private-ranges-only"
        "run.googleapis.com/execution-environment"        = "gen2"
        "run.googleapis.com/cpu-throttling"               = "true"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_project_service.required_apis,
    google_vpc_access_connector.pawconnect_connector,
    google_redis_instance.pawconnect_redis
  ]
}

# IAM policy for Cloud Run (allow public access)
resource "google_cloud_run_service_iam_member" "public_access" {
  location = google_cloud_run_service.pawconnect_main_agent.location
  service  = google_cloud_run_service.pawconnect_main_agent.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Cloud Run service for Dialogflow webhook
resource "google_cloud_run_service" "pawconnect_webhook" {
  name     = "pawconnect-dialogflow-webhook"
  location = var.region

  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/pawconnect-ai:latest"

        resources {
          limits = {
            cpu    = "1"
            memory = "1Gi"
          }
        }

        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }

        env {
          name  = "GCP_REGION"
          value = var.region
        }

        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }

        env {
          name  = "TESTING_MODE"
          value = "False"
        }

        env {
          name  = "MOCK_APIS"
          value = "False"
        }

        env {
          name  = "REDIS_HOST"
          value = google_redis_instance.pawconnect_redis.host
        }

        env {
          name = "RESCUEGROUPS_API_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.rescuegroups_api_key.secret_id
              key  = "latest"
            }
          }
        }

        env {
          name = "REDIS_PASSWORD"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.redis_password.secret_id
              key  = "latest"
            }
          }
        }
      }

      service_account_name = google_service_account.cloud_run_sa.email
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale"                = "0"
        "autoscaling.knative.dev/maxScale"                = "10"
        "run.googleapis.com/vpc-access-connector"         = google_vpc_access_connector.pawconnect_connector.id
        "run.googleapis.com/vpc-access-egress"            = "private-ranges-only"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_project_service.required_apis,
    google_vpc_access_connector.pawconnect_connector,
    google_redis_instance.pawconnect_redis
  ]
}

# IAM policy for webhook (allow public access)
resource "google_cloud_run_service_iam_member" "webhook_public_access" {
  location = google_cloud_run_service.pawconnect_webhook.location
  service  = google_cloud_run_service.pawconnect_webhook.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# =============================================================================
# CLOUD STORAGE
# =============================================================================

# Cloud Storage bucket for model artifacts
resource "google_storage_bucket" "model_artifacts" {
  name          = "${var.project_id}-model-artifacts"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
}

# Cloud Storage bucket for build artifacts
resource "google_storage_bucket" "build_artifacts" {
  name          = "${var.project_id}-artifacts"
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
}

# Cloud Storage bucket for pet images
resource "google_storage_bucket" "pet_images" {
  name          = "${var.project_id}-pet-images"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
}

# =============================================================================
# MONITORING & ALERTING
# =============================================================================

# Monitoring notification channel (email)
resource "google_monitoring_notification_channel" "email" {
  display_name = "PawConnect Alerts"
  type         = "email"

  labels = {
    email_address = var.alert_email
  }
}

# Uptime check for Cloud Run service
resource "google_monitoring_uptime_check_config" "health_check" {
  display_name = "PawConnect Main Agent Health Check"
  timeout      = "10s"
  period       = "60s"

  http_check {
    path         = "/health"
    port         = "443"
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = replace(google_cloud_run_service.pawconnect_main_agent.status[0].url, "https://", "")
    }
  }

  depends_on = [google_cloud_run_service.pawconnect_main_agent]
}

# Uptime check for webhook
resource "google_monitoring_uptime_check_config" "webhook_health_check" {
  display_name = "PawConnect Webhook Health Check"
  timeout      = "10s"
  period       = "60s"

  http_check {
    path         = "/health"
    port         = "443"
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = replace(google_cloud_run_service.pawconnect_webhook.status[0].url, "https://", "")
    }
  }

  depends_on = [google_cloud_run_service.pawconnect_webhook]
}

# =============================================================================
# CLOUD SCHEDULER
# =============================================================================

# Cloud Scheduler job for periodic model retraining (optional)
resource "google_cloud_scheduler_job" "model_retrain" {
  count = var.enable_model_retraining ? 1 : 0

  name        = "pawconnect-model-retrain"
  description = "Trigger model retraining weekly"
  schedule    = "0 2 * * 0" # Every Sunday at 2 AM
  time_zone   = "America/Los_Angeles"

  http_target {
    uri         = "${google_cloud_run_service.pawconnect_main_agent.status[0].url}/api/retrain"
    http_method = "POST"

    oidc_token {
      service_account_email = google_service_account.cloud_run_sa.email
    }
  }

  depends_on = [google_project_service.required_apis]
}
