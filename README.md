The client's specific wishes: 

- [ ] download the current eCFR data,  
- [ ] store the data server-side,  
- [ ] create APIs that can retrieve the server-side stored data,  
- [ ] provide a UI to analyze it for items such as  
    - [ ] word count per agency,  
    - [ ] historical changes over time, and  
    - [ ] a checksum for each agency  
    - [ ] my own custom metric to help inform decision making 

How I will approach this:  
   1. I will start with a solid cloud deployment framework to build out hosting infrastructure in AWS
   2. Build an AWS infrastructure and application deployment framework for the back-end and front-end of the application 
   3. Implement syntax checking, security checking, code coverage for appropriate parts

Github Automation:  
Github Actions run in 3 phases that can be run sequentially or, for 2 and 3, ad-hoc as needed.  
   1. Deploy application infrastructure. 
   2. Download data and upload to dynamo DB
   3. Deploy updated lambda / api / frontend (DEV deployment)

AWS Infrastructure (Terraform? Python CDK?).  
The AWS infrastructure will consist of the following components.  
   1. AWS VPC, SGs, IAM elements.  
   2. Lambda to pull data and write to Dynamo.  
   3. Lambda to compute analytics.  
   4. API gateway to dynamo.  
   5. Frontend in s3/cloudfront to view data.  



API Documentation:

https://www.ecfr.gov/developers/documentation/api/v1

Potential extensions:  



Security:  
~~Add Provider to authenticate to AWS from github pipeline with OIDC:~~  
- ~~https://registry.terraform.io/modules/terraform-aws-modules/iam/aws/latest/examples/iam-github-oidc~~  
- ~~https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-idp_oidc.html#idp_oidc_Create_GitHub~~  
  
Additional Dependency scanning / hygine added to pipeline:
  - trivy: https://github.com/aquasecurity/trivy  
  - Bandit: https://github.com/PyCQA/bandit  


Test/QA: 
  - more test coverage  
  - OPA or Flake8 enforcement  

Infra enhancements:  
  - deeper aws cost insights with budgeting / costexplorer dashboards  
  - make multi-cloud compatible using k8s or other multicloud framework:
    - https://github.com/serverless/multicloud

