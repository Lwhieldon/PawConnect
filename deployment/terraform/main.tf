# PawConnect AI - Terraform Infrastructure Configuration
# Provisions Google Cloud resources for the application

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
    "dialogflow.googleapis.com",
    "vision.googleapis.com",
    "aiplatform.googleapis.com",
    "pubsub.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudscheduler.googleapis.com",
    "firestore.googleapis.com",
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
  ])

  service            = each.key
  disable_on_destroy = false
}

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
            cpu    = "2"
            memory = "2Gi"
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
          name = "RESCUEGROUPS_API_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.rescuegroups_api_key.secret_id
              key  = "latest"
            }
          }
        }
      }

      service_account_name = google_service_account.cloud_run_sa.email
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = "1"
        "autoscaling.knative.dev/maxScale" = "10"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [google_project_service.required_apis]
}

# IAM policy for Cloud Run (allow public access)
resource "google_cloud_run_service_iam_member" "public_access" {
  location = google_cloud_run_service.pawconnect_main_agent.location
  service  = google_cloud_run_service.pawconnect_main_agent.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

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
  ])

  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Pub/Sub topics for agent communication
resource "google_pubsub_topic" "search_results" {
  name = "pawconnect-search-results"

  message_retention_duration = "86400s" # 24 hours
}

resource "google_pubsub_topic" "recommendations" {
  name = "pawconnect-recommendations"

  message_retention_duration = "86400s"
}

# Pub/Sub subscriptions
resource "google_pubsub_subscription" "search_results_sub" {
  name  = "pawconnect-search-results-sub"
  topic = google_pubsub_topic.search_results.name

  ack_deadline_seconds = 20

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}

# Firestore database (already created, just reference it)
data "google_firestore_database" "database" {
  name = "(default)"
}

# Secret Manager for API keys
resource "google_secret_manager_secret" "rescuegroups_api_key" {
  secret_id = "rescuegroups-api-key"

  replication {
    auto {}
  }
}

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
  name          = "${var.project_id}-build-artifacts"
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

# Cloud Scheduler job for periodic model retraining
resource "google_cloud_scheduler_job" "model_retrain" {
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
  display_name = "PawConnect Health Check"
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
}
