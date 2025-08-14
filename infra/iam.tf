# Common policy documents
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals { 
        type = "Service" 
        identifiers = ["lambda.amazonaws.com"] 
    }
  }
}

data "aws_iam_policy_document" "lambda_logs" {
  statement {
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "dynamodb_rw" {
  statement {
    actions = [
      "dynamodb:PutItem", "dynamodb:BatchWriteItem", "dynamodb:UpdateItem",
      "dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"
    ]
    resources = [aws_dynamodb_table.metrics.arn]
  }
}

resource "aws_iam_role" "api_role" {
  name               = "${var.project_name}-api-${var.env}"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy" "api_logs" {
  name   = "${var.project_name}-api-logs-${var.env}"
  role   = aws_iam_role.api_role.id
  policy = data.aws_iam_policy_document.lambda_logs.json
}

resource "aws_iam_role_policy" "api_dynamodb" {
  name   = "${var.project_name}-api-dynamodb-${var.env}"
  role   = aws_iam_role.api_role.id
  policy = data.aws_iam_policy_document.dynamodb_rw.json
}

data "aws_iam_policy_document" "lambda_invoke" {
  statement {
    actions   = ["lambda:InvokeFunction"]
    resources = [aws_lambda_function.ingest_lambda.arn]
  }
}

resource "aws_iam_role_policy" "api_lambda_invoke" {
  name   = "${var.project_name}-api-lambda-invoke-${var.env}"
  role   = aws_iam_role.api_role.id
  policy = data.aws_iam_policy_document.lambda_invoke.json
}

resource "aws_iam_role" "ingest_role" {
  name               = "${var.project_name}-ingest-${var.env}"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy" "ingest_logs" {
  name   = "${var.project_name}-ingest-logs-${var.env}"
  role   = aws_iam_role.ingest_role.id
  policy = data.aws_iam_policy_document.lambda_logs.json
}

resource "aws_iam_role_policy" "ingest_dynamodb" {
  name   = "${var.project_name}-ingest-dynamodb-${var.env}"
  role   = aws_iam_role.ingest_role.id
  policy = data.aws_iam_policy_document.dynamodb_rw.json
}