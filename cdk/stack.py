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
                exclude=["*.pyc", "__pycache__", "cdk.out", ".venv", "cdk.json", "*.txt", "app.py", "stack.py"],
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
                # "BEDROCK_MODEL_ID": "us.amazon.nova-lite-v1:0",
                "BEDROCK_MODEL_ID": "deepseek.v3.2",
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
