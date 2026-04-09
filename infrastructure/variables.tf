variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "eastus"
}

variable "prefix" {
  description = "Naming prefix for all resources"
  type        = string
  default     = "monitor"
}

variable "mysql_admin_password" {
  description = "Administrator password for MySQL Flexible Server"
  type        = string
  sensitive   = true
}
