resource "aws_lambda_function" "ingest_lambda" {
  function_name = "${var.project_name}-ingest-${var.env}"
  filename      = var.ingest_lambda_zip
  source_code_hash = filebase64sha256(var.ingest_lambda_zip)
  handler       = "app.handler"
  role          = aws_iam_role.ingest_role.arn
  runtime       = "python3.12"
  timeout       = 60
  memory_size   = 1024
  environment {
    variables = {
      DDB_TABLE      = aws_dynamodb_table.metrics.name
      PROJECT_ENV    = var.env
      ECFR_BASE_URL  = "https://www.ecfr.gov/api"
    }
  }
}