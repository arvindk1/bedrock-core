#!/usr/bin/env python3
import aws_cdk as cdk
from stack import AgentCoreStack

app = cdk.App()
AgentCoreStack(app, "BedrockCore")

app.synth()
