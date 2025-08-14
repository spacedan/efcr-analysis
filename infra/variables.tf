variable "project_name" { 
    type = string  
    default = "danny-ecfr" 
    description = "Name of the project, used for resource naming"
}

variable "env"          { 
    type = string  
    default = "dev" # e.g., dev|test|prod
}

variable "aws_region"   { 
    type = string  
    default = "us-east-1" 
}

# Simple header-based auth for the API (x-api-key)
variable "api_auth_token" {
  type        = string
  default     = "changeme-local"
  description = "Static token required in 'x-api-key' header for API access"
  sensitive   = true
}

# Optional: names for Lambda zip files (updated later by CI)
variable "api_lambda_zip"    { 
    type = string  
    default = "../artifacts/api_lambda.zip" 
    description = "Path to the API Lambda zip file"
}

variable "ingest_lambda_zip" { 
    type = string  
    default = "../artifacts/ingest_lambda.zip" 
    description = "Path to the Ingest Lambda zip file"
}