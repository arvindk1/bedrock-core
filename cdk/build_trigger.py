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
    body = json.dumps(
        {
            "Status": status,
            "Reason": reason or f"See CloudWatch Log Stream: {context.log_stream_name}",
            "PhysicalResourceId": context.log_stream_name,
            "StackId": event["StackId"],
            "RequestId": event["RequestId"],
            "LogicalResourceId": event["LogicalResourceId"],
            "NoEcho": False,
            "Data": data,
        }
    )

    http = urllib3.PoolManager()
    try:
        http.request(
            "PUT",
            event["ResponseURL"],
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
                send_cfn_response(
                    event, context, "FAILED", {"Error": f"Build failed: {status}"}
                )
                return

            logger.info("Build %s status: %s, waiting...", build_id, status)
            time.sleep(30)

    except Exception as e:
        logger.error("Error: %s", e)
        send_cfn_response(event, context, "FAILED", {"Error": str(e)})
