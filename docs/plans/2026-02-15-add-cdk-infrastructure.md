# Add CDK Infrastructure to bedrock-core

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the AgentCore Toolkit CLI deployment with a proper AWS CDK stack, modeled after the working `/home/arvindk/devl/aws/strands` reference.

**Architecture:** Restructure the repo into `agent/` (runtime code + Dockerfile) and `cdk/` (infrastructure). CDK stack creates ECR repo, CodeBuild project (ARM64), Lambda build trigger, AgentCore IAM role, and AgentCore Runtime. The agent code (app.py, tools.py, options_scanner.py) moves into `agent/` with a Dockerfile for containerization.

**Tech Stack:** AWS CDK (Python), BedrockAgentCore CfnRuntime, CodeBuild ARM64, ECR, Lambda Custom Resource

**Reference:** Working CDK implementation at `/home/arvindk/devl/aws/strands/cdk/`

---

## Task 1: Create agent/ directory with Dockerfile and requirements.txt

**Files:**
- Create: `agent/Dockerfile`
- Create: `agent/requirements.txt`

**Step 1: Create agent/requirements.txt**

```txt
strands-agents>=1.25.0,<2.0
strands-agents-tools
bedrock-agentcore>=1.3.0,<2.0
python-dotenv
yfinance>=0.2.0
scipy>=1.10.0
pandas>=1.5.0
boto3
```

**Step 2: Create agent/Dockerfile**

```dockerfile
FROM public.ecr.aws/docker/library/python:3.13-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir aws-opentelemetry-distro==0.10.1

ENV AWS_REGION=us-east-1
ENV AWS_DEFAULT_REGION=us-east-1

# Create non-root user
RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

EXPOSE 8080
EXPOSE 8000

COPY . .

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/ping || exit 1

CMD ["opentelemetry-instrument", "python", "-m", "app"]
```

**Step 3: Commit**

```bash
git add agent/Dockerfile agent/requirements.txt
git commit -m "feat: add agent Dockerfile and requirements for CDK deployment"
```

---

## Task 2: Move agent source code into agent/ directory

**Files:**
- Move: `app.py` → `agent/app.py`
- Move: `tools.py` → `agent/tools.py`
- Move: `options_scanner.py` → `agent/options_scanner.py`

The agent code stays exactly as-is. These are just file moves.

**Step 1: Move files**

```bash
cp app.py agent/app.py
cp tools.py agent/tools.py
cp options_scanner.py agent/options_scanner.py
```

Note: Keep originals in place for now (tests reference them). We'll clean up later.

**Step 2: Verify agent/ directory has all needed files**

```bash
ls agent/
# Expected: app.py  Dockerfile  options_scanner.py  requirements.txt  tools.py
```

**Step 3: Commit**

```bash
git add agent/
git commit -m "feat: copy agent source code into agent/ directory for containerization"
```

---

## Task 3: Create CDK infrastructure - cdk.json and requirements.txt

**Files:**
- Create: `cdk/cdk.json`
- Create: `cdk/requirements.txt`

**Step 1: Create cdk/requirements.txt**

```txt
aws-cdk-lib==2.218.0
constructs>=10.0.79
```

**Step 2: Create cdk/cdk.json**

```json
{
  "app": "python3 app.py",
  "watch": {
    "include": ["**"],
    "exclude": [
      "README.md",
      "cdk*.json",
      "requirements*.txt",
      "**/__pycache__",
      "**/*.pyc"
    ]
  },
  "context": {
    "@aws-cdk/aws-lambda:recognizeLayerVersion": true,
    "@aws-cdk/core:checkSecretUsage": true,
    "@aws-cdk/core:target-partitions": ["aws", "aws-cn"],
    "@aws-cdk/aws-iam:minimizePolicies": true,
    "@aws-cdk/core:validateSnapshotRemovalPolicy": true,
    "@aws-cdk/aws-iam:standardizedServicePrincipals": true,
    "@aws-cdk/core:enablePartitionLiterals": true,
    "@aws-cdk/customresources:installLatestAwsSdkDefault": false
  }
}
```

**Step 3: Commit**

```bash
git add cdk/cdk.json cdk/requirements.txt
git commit -m "feat: add CDK configuration and dependencies"
```

---

## Task 4: Create CDK build_trigger.py Lambda handler

**Files:**
- Create: `cdk/build_trigger.py`

**Step 1: Create the Lambda handler**

This is the CloudFormation Custom Resource handler that triggers CodeBuild during `cdk deploy` and waits for completion. Copy directly from the working strands reference (`/home/arvindk/devl/aws/strands/cdk/build_trigger.py`) — it's generic and works as-is.

```python
"""Lambda handler for triggering CodeBuild and waiting for completion.

Deployed as a Custom Resource handler during CDK deploy.
"""

import boto3
import json
import logging
import time
import urllib3

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def send_cfn_response(event, context, status, data, reason=None):
    """Send response back to CloudFormation."""
    body = json.dumps({
        "Status": status,
        "Reason": reason or f"See CloudWatch Log Stream: {context.log_stream_name}",
        "PhysicalResourceId": context.log_stream_name,
        "StackId": event["StackId"],
        "RequestId": event["RequestId"],
        "LogicalResourceId": event["LogicalResourceId"],
        "NoEcho": False,
        "Data": data,
    })

    http = urllib3.PoolManager()
    try:
        http.request(
            "PUT", event["ResponseURL"],
            headers={"content-type": "", "content-length": str(len(body))},
            body=body,
        )
    except Exception as e:
        logger.error("Failed to send CFN response: %s", e)


def handler(event, context):
    logger.info("Received event: %s", json.dumps(event))

    try:
        if event["RequestType"] == "Delete":
            send_cfn_response(event, context, "SUCCESS", {})
            return

        project_name = event["ResourceProperties"]["ProjectName"]
        codebuild_client = boto3.client("codebuild")

        # Start build
        response = codebuild_client.start_build(projectName=project_name)
        build_id = response["build"]["id"]
        logger.info("Started build: %s", build_id)

        # Wait for completion (leave 30s buffer for response)
        max_wait = context.get_remaining_time_in_millis() / 1000 - 30
        start_time = time.time()

        while True:
            if time.time() - start_time > max_wait:
                send_cfn_response(event, context, "FAILED", {"Error": "Build timeout"})
                return

            builds = codebuild_client.batch_get_builds(ids=[build_id])
            status = builds["builds"][0]["buildStatus"]

            if status == "SUCCEEDED":
                logger.info("Build %s succeeded", build_id)
                send_cfn_response(event, context, "SUCCESS", {"BuildId": build_id})
                return
            elif status in ("FAILED", "FAULT", "STOPPED", "TIMED_OUT"):
                logger.error("Build %s failed: %s", build_id, status)
                send_cfn_response(event, context, "FAILED", {"Error": f"Build failed: {status}"})
                return

            logger.info("Build %s status: %s, waiting...", build_id, status)
            time.sleep(30)

    except Exception as e:
        logger.error("Error: %s", e)
        send_cfn_response(event, context, "FAILED", {"Error": str(e)})
```

**Step 2: Commit**

```bash
git add cdk/build_trigger.py
git commit -m "feat: add CodeBuild trigger Lambda for CDK custom resource"
```

---

## Task 5: Create CDK stack.py

**Files:**
- Create: `cdk/stack.py`

**Step 1: Create the CDK stack**

Adapted from strands reference. Key differences from strands:
- Stack name: `BedrockCore` (not `StrandsHelloWorld`)
- Agent runtime name: `BedrockCore_OptionsAgent`
- Description reflects options scanner agent
- Environment variables include `BEDROCK_MODEL_ID`

```python
"""CDK Stack for Bedrock Core Options Agent on Bedrock AgentCore.

Creates: ECR repo, CodeBuild project (ARM64), build trigger Lambda,
AgentCore IAM role, and AgentCore Runtime.
"""

from aws_cdk import (
    Stack,
    aws_ecr as ecr,
    aws_codebuild as codebuild,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_s3_assets as s3_assets,
    aws_bedrockagentcore as bedrockagentcore,
    CustomResource,
    CfnOutput,
    Duration,
    RemovalPolicy,
)
from constructs import Construct
import os


class AgentCoreStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        image_tag = "latest"
        agent_dir = os.path.join(os.path.dirname(__file__), "..", "agent")

        # --- ECR Repository ---
        ecr_repo = ecr.Repository(
            self,
            "ECRRepository",
            repository_name=f"{self.stack_name.lower()}-agent",
            image_tag_mutability=ecr.TagMutability.MUTABLE,
            removal_policy=RemovalPolicy.DESTROY,
            empty_on_delete=True,
            image_scan_on_push=True,
        )

        # --- S3 Asset: upload agent/ source for CodeBuild ---
        source_asset = s3_assets.Asset(self, "AgentSource", path=agent_dir)

        # --- CodeBuild Role ---
        codebuild_role = iam.Role(
            self,
            "CodeBuildRole",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            inline_policies={
                "CodeBuildPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            sid="CloudWatchLogs",
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents",
                            ],
                            resources=[
                                f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/codebuild/*"
                            ],
                        ),
                        iam.PolicyStatement(
                            sid="ECRAccess",
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "ecr:BatchCheckLayerAvailability",
                                "ecr:GetDownloadUrlForLayer",
                                "ecr:BatchGetImage",
                                "ecr:GetAuthorizationToken",
                                "ecr:PutImage",
                                "ecr:InitiateLayerUpload",
                                "ecr:UploadLayerPart",
                                "ecr:CompleteLayerUpload",
                            ],
                            resources=[ecr_repo.repository_arn, "*"],
                        ),
                        iam.PolicyStatement(
                            sid="S3SourceAccess",
                            effect=iam.Effect.ALLOW,
                            actions=["s3:GetObject"],
                            resources=[f"{source_asset.bucket.bucket_arn}/*"],
                        ),
                    ]
                )
            },
        )

        # --- CodeBuild Project (ARM64) ---
        build_project = codebuild.Project(
            self,
            "AgentImageBuild",
            project_name=f"{self.stack_name}-agent-build",
            description="Build Bedrock Core agent Docker image (ARM64)",
            role=codebuild_role,
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxArmBuildImage.AMAZON_LINUX_2_STANDARD_3_0,
                compute_type=codebuild.ComputeType.LARGE,
                privileged=True,
            ),
            source=codebuild.Source.s3(
                bucket=source_asset.bucket,
                path=source_asset.s3_object_key,
            ),
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "pre_build": {
                        "commands": [
                            "echo Logging in to Amazon ECR...",
                            "aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com",
                        ]
                    },
                    "build": {
                        "commands": [
                            "echo Building Docker image...",
                            "docker build -t $IMAGE_REPO_NAME:$IMAGE_TAG .",
                            "docker tag $IMAGE_REPO_NAME:$IMAGE_TAG $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$IMAGE_TAG",
                        ]
                    },
                    "post_build": {
                        "commands": [
                            "echo Pushing Docker image...",
                            "docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$IMAGE_TAG",
                            "echo Done.",
                        ]
                    },
                },
            }),
            environment_variables={
                "AWS_DEFAULT_REGION": codebuild.BuildEnvironmentVariable(value=self.region),
                "AWS_ACCOUNT_ID": codebuild.BuildEnvironmentVariable(value=self.account),
                "IMAGE_REPO_NAME": codebuild.BuildEnvironmentVariable(value=ecr_repo.repository_name),
                "IMAGE_TAG": codebuild.BuildEnvironmentVariable(value=image_tag),
            },
        )

        # --- Lambda: trigger CodeBuild and wait for completion ---
        build_trigger_fn = lambda_.Function(
            self,
            "BuildTriggerFunction",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="build_trigger.handler",
            timeout=Duration.minutes(15),
            code=lambda_.Code.from_asset(
                os.path.dirname(__file__),
                exclude=["*.pyc", "__pycache__", "cdk.out", "cdk.json", "*.txt"],
            ),
            initial_policy=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["codebuild:StartBuild", "codebuild:BatchGetBuilds"],
                    resources=[build_project.project_arn],
                )
            ],
        )

        # Custom Resource to trigger the build during cdk deploy
        trigger_build = CustomResource(
            self,
            "TriggerImageBuild",
            service_token=build_trigger_fn.function_arn,
            properties={"ProjectName": build_project.project_name},
        )

        # --- AgentCore Execution Role ---
        agent_role = iam.Role(
            self,
            "AgentCoreRole",
            assumed_by=iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
            inline_policies={
                "AgentCorePolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            sid="ECRImageAccess",
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "ecr:BatchGetImage",
                                "ecr:GetDownloadUrlForLayer",
                                "ecr:BatchCheckLayerAvailability",
                            ],
                            resources=[f"arn:aws:ecr:{self.region}:{self.account}:repository/*"],
                        ),
                        iam.PolicyStatement(
                            sid="ECRTokenAccess",
                            effect=iam.Effect.ALLOW,
                            actions=["ecr:GetAuthorizationToken"],
                            resources=["*"],
                        ),
                        iam.PolicyStatement(
                            sid="CloudWatchLogs",
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "logs:DescribeLogStreams",
                                "logs:CreateLogGroup",
                                "logs:DescribeLogGroups",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents",
                            ],
                            resources=[
                                f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/bedrock-agentcore/runtimes/*"
                            ],
                        ),
                        iam.PolicyStatement(
                            sid="XRayTracing",
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "xray:PutTraceSegments",
                                "xray:PutTelemetryRecords",
                                "xray:GetSamplingRules",
                                "xray:GetSamplingTargets",
                            ],
                            resources=["*"],
                        ),
                        iam.PolicyStatement(
                            sid="CloudWatchMetrics",
                            effect=iam.Effect.ALLOW,
                            actions=["cloudwatch:PutMetricData"],
                            resources=["*"],
                            conditions={
                                "StringEquals": {"cloudwatch:namespace": "bedrock-agentcore"}
                            },
                        ),
                        iam.PolicyStatement(
                            sid="GetAgentAccessToken",
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "bedrock-agentcore:GetWorkloadAccessToken",
                                "bedrock-agentcore:GetWorkloadAccessTokenForJWT",
                                "bedrock-agentcore:GetWorkloadAccessTokenForUserId",
                            ],
                            resources=[
                                f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:workload-identity-directory/default",
                                f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:workload-identity-directory/default/workload-identity/*",
                            ],
                        ),
                        iam.PolicyStatement(
                            sid="BedrockModelInvocation",
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "bedrock:InvokeModel",
                                "bedrock:InvokeModelWithResponseStream",
                            ],
                            resources=[
                                "arn:aws:bedrock:*::foundation-model/*",
                                f"arn:aws:bedrock:{self.region}:{self.account}:*",
                            ],
                        ),
                    ]
                )
            },
        )

        # --- AgentCore Runtime ---
        agent_runtime = bedrockagentcore.CfnRuntime(
            self,
            "AgentRuntime",
            agent_runtime_name=f"{self.stack_name.replace('-', '_')}_OptionsAgent",
            agent_runtime_artifact=bedrockagentcore.CfnRuntime.AgentRuntimeArtifactProperty(
                container_configuration=bedrockagentcore.CfnRuntime.ContainerConfigurationProperty(
                    container_uri=f"{ecr_repo.repository_uri}:{image_tag}"
                )
            ),
            network_configuration=bedrockagentcore.CfnRuntime.NetworkConfigurationProperty(
                network_mode="PUBLIC"
            ),
            protocol_configuration="HTTP",
            role_arn=agent_role.role_arn,
            description="Bedrock Core Options Scanner agent on AgentCore",
            environment_variables={
                "AWS_DEFAULT_REGION": self.region,
                "BEDROCK_MODEL_ID": "us.amazon.nova-lite-v1:0",
            },
        )

        # Runtime depends on image being built first
        agent_runtime.node.add_dependency(trigger_build)

        # --- Outputs ---
        CfnOutput(self, "AgentRuntimeId",
                  description="Agent Runtime ID",
                  value=agent_runtime.attr_agent_runtime_id)

        CfnOutput(self, "AgentRuntimeArn",
                  description="Agent Runtime ARN",
                  value=agent_runtime.attr_agent_runtime_arn)

        CfnOutput(self, "AgentRoleArn",
                  description="Agent execution role ARN",
                  value=agent_role.role_arn)
```

**Step 2: Commit**

```bash
git add cdk/stack.py
git commit -m "feat: add CDK stack for AgentCore deployment"
```

---

## Task 6: Create CDK app.py entry point

**Files:**
- Create: `cdk/app.py`

**Step 1: Create the CDK app entry point**

```python
#!/usr/bin/env python3
import aws_cdk as cdk
from stack import AgentCoreStack

app = cdk.App()
AgentCoreStack(app, "BedrockCore")

app.synth()
```

**Step 2: Commit**

```bash
git add cdk/app.py
git commit -m "feat: add CDK app entry point"
```

---

## Task 7: Set up CDK virtual environment and verify synth

**Step 1: Create CDK venv and install dependencies**

```bash
cd cdk
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Step 2: Run cdk synth to verify the stack compiles**

```bash
cd /home/arvindk/devl/aws/bedrock-core/cdk
cdk synth
```

Expected: CloudFormation template output (JSON/YAML) with no errors.

**Step 3: Fix any issues**

If synth fails, read the error, fix, re-run until it passes.

**Step 4: Add .gitignore for CDK artifacts**

Add to `.gitignore` (or create one):
```
cdk/cdk.out/
cdk/.venv/
```

**Step 5: Commit**

```bash
git add .gitignore cdk/
git commit -m "feat: CDK synth verified, add gitignore for CDK artifacts"
```

---

## Task 8: Update tests for agent/ directory structure

**Files:**
- Modify: `tests/test_entrypoint.py` — update imports if needed
- Modify: `tests/test_tools.py` — update imports if needed

**Step 1: Check if existing tests still pass with original files in place**

```bash
cd /home/arvindk/devl/aws/bedrock-core
source .venv/bin/activate
pytest tests/ -v
```

**Step 2: If tests pass, no changes needed for now**

The original files at root level still exist. Tests reference `app`, `tools`, `options_scanner` which resolve to root-level files.

**Step 3: Commit if any changes were needed**

---

## Task 9: Clean up root-level agent files (optional, after CDK deploy works)

**Files:**
- Keep: `app.py`, `tools.py`, `options_scanner.py` at root (for `agentcore` CLI backward compat)
- OR remove them if fully switching to CDK

**Decision point:** Only do this after `cdk deploy` succeeds. The root files serve as fallback for `agentcore deploy`. Remove them only when CDK is the confirmed deployment path.

---

## Deployment

Once all tasks are complete, deploy with:

```bash
cd /home/arvindk/devl/aws/bedrock-core/cdk
source .venv/bin/activate
cdk bootstrap   # one-time, if not already done for this account/region
cdk deploy
```

This will:
1. Create ECR repository
2. Upload agent source to S3
3. Create CodeBuild project
4. Trigger Lambda to build Docker image via CodeBuild
5. Create AgentCore Runtime pointing to the built image
