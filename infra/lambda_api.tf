resource "aws_lambda_function" "api_lambda" {
  function_name = "${var.project_name}-api-${var.env}"
  filename      = var.api_lambda_zip
  source_code_hash = filebase64sha256(var.api_lambda_zip)
  handler       = "simple_app.handler"
  role          = aws_iam_role.api_role.arn
  runtime       = "python3.12"
  timeout       = 15
  memory_size   = 512
  environment {
    variables = {
      DDB_TABLE      = aws_dynamodb_table.metrics.name
      API_AUTH_TOKEN = var.api_auth_token
      PROJECT_ENV    = var.env
    }
  }
}