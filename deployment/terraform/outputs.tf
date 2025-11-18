# Terraform Outputs for PawConnect AI

output "cloud_run_url" {
  description = "URL of the deployed Cloud Run service"
  value       = google_cloud_run_service.pawconnect_main_agent.status[0].url
}

output "cloud_run_service_name" {
  description = "Name of the Cloud Run service"
  value       = google_cloud_run_service.pawconnect_main_agent.name
}

output "service_account_email" {
  description = "Email of the Cloud Run service account"
  value       = google_service_account.cloud_run_sa.email
}

output "pubsub_search_topic" {
  description = "Pub/Sub topic for search results"
  value       = google_pubsub_topic.search_results.id
}

output "pubsub_recommendations_topic" {
  description = "Pub/Sub topic for recommendations"
  value       = google_pubsub_topic.recommendations.id
}

output "model_artifacts_bucket" {
  description = "Cloud Storage bucket for model artifacts"
  value       = google_storage_bucket.model_artifacts.name
}

output "build_artifacts_bucket" {
  description = "Cloud Storage bucket for build artifacts"
  value       = google_storage_bucket.build_artifacts.name
}

output "project_id" {
  description = "Google Cloud Project ID"
  value       = var.project_id
}

output "region" {
  description = "Google Cloud region"
  value       = var.region
}

output "environment" {
  description = "Environment name"
  value       = var.environment
}
