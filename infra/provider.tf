terraform {
  required_version = ">= 1.5.0"
  
  backend "s3" {
    bucket  = "tf-state-bucket-danny-ecfr"
    key     = "ecfr-analysis/terraform.tfstate"
    region  = "us-east-1"
    encrypt = true
    
    # Optional: Enable state locking with DynamoDB
    dynamodb_table = "terraform-state-lock"
  }
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}