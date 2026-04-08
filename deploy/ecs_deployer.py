import os
import json
import time
import boto3
from core.utils import get_logger

logger = get_logger("ecs_deployer")

AWS_REGION      = os.getenv("AWS_REGION", "us-west-2")
AWS_ACCOUNT_ID  = os.getenv("AWS_ACCOUNT_ID")
ECS_CLUSTER     = os.getenv("ECS_CLUSTER_NAME", "app-builder-cluster")
EXECUTION_ROLE  = os.getenv("ECS_EXECUTION_ROLE_ARN")


def get_default_vpc_and_subnets() -> tuple[str, list[str]]:
    """Get the default VPC and public subnets."""
    ec2 = boto3.client("ec2", region_name=AWS_REGION)

    vpcs = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])
    vpc_id = vpcs["Vpcs"][0]["VpcId"]

    subnets = ec2.describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )
    subnet_ids = [s["SubnetId"] for s in subnets["Subnets"]][:2]

    return vpc_id, subnet_ids


def create_security_group(project_id: str, vpc_id: str) -> str:
    """Create or reuse a security group for the app."""
    ec2 = boto3.client("ec2", region_name=AWS_REGION)
    sg_name = f"app-builder-{project_id}"

    # Check if it already exists
    existing = ec2.describe_security_groups(
        Filters=[
            {"Name": "group-name", "Values": [sg_name]},
            {"Name": "vpc-id", "Values": [vpc_id]}
        ]
    )
    if existing["SecurityGroups"]:
        sg_id = existing["SecurityGroups"][0]["GroupId"]
        logger.info(f"Reusing existing security group: {sg_id}")
        return sg_id

    # Create new
    sg = ec2.create_security_group(
        GroupName=sg_name,
        Description=f"Security group for app {project_id}",
        VpcId=vpc_id
    )
    sg_id = sg["GroupId"]

    ec2.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {
                "IpProtocol": "tcp",
                "FromPort": 80,
                "ToPort": 80,
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}]
            },
            {
                "IpProtocol": "tcp",
                "FromPort": 5000,
                "ToPort": 5000,
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}]
            }
        ]
    )

    return sg_id


def register_task_definition(
    project_id: str,
    service: str,
    image: str,
    port: int,
    env_vars: dict
) -> str:
    """Register an ECS task definition."""
    ecs = boto3.client("ecs", region_name=AWS_REGION)

    environment = [
        {"name": k, "value": str(v)}
        for k, v in env_vars.items()
    ]

    response = ecs.register_task_definition(
        family=f"app-builder-{project_id}-{service}",
        networkMode="awsvpc",
        requiresCompatibilities=["FARGATE"],
        cpu="256",
        memory="512",
        executionRoleArn=EXECUTION_ROLE,
        containerDefinitions=[
            {
                "name": service,
                "image": image,
                "portMappings": [
                    {"containerPort": port, "protocol": "tcp"}
                ],
                "environment": environment,
                "essential": True,
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": f"/ecs/app-builder-{project_id}",
                        "awslogs-region": AWS_REGION,
                        "awslogs-stream-prefix": service,
                        "awslogs-create-group": "true"
                    }
                }
            }
        ]
    )

    return response["taskDefinition"]["taskDefinitionArn"]


def create_alb(project_id: str, vpc_id: str, subnet_ids: list, sg_id: str) -> tuple[str, str, str]:
    """Create an Application Load Balancer."""
    elb = boto3.client("elbv2", region_name=AWS_REGION)

    # Create ALB
    alb = elb.create_load_balancer(
        Name=f"ab-{project_id}",
        Subnets=subnet_ids,
        SecurityGroups=[sg_id],
        Scheme="internet-facing",
        Type="application",
        IpAddressType="ipv4"
    )
    alb_arn = alb["LoadBalancers"][0]["LoadBalancerArn"]
    alb_dns = alb["LoadBalancers"][0]["DNSName"]

    # Create target groups
    frontend_tg = elb.create_target_group(
        Name=f"ab-{project_id}-fe",
        Protocol="HTTP",
        Port=80,
        VpcId=vpc_id,
        TargetType="ip",
        HealthCheckPath="/",
        HealthCheckIntervalSeconds=30
    )
    frontend_tg_arn = frontend_tg["TargetGroups"][0]["TargetGroupArn"]

    backend_tg = elb.create_target_group(
        Name=f"ab-{project_id}-be",
        Protocol="HTTP",
        Port=5000,
        VpcId=vpc_id,
        TargetType="ip",
        HealthCheckPath="/api/health",
        HealthCheckIntervalSeconds=30
    )
    backend_tg_arn = backend_tg["TargetGroups"][0]["TargetGroupArn"]

    # Create listener — route /api/* to backend, everything else to frontend
    elb.create_listener(
        LoadBalancerArn=alb_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[
            {"Type": "forward", "TargetGroupArn": frontend_tg_arn}
        ]
    )

    # Add rule to route /api/* to backend
    listeners = elb.describe_listeners(LoadBalancerArn=alb_arn)
    listener_arn = listeners["Listeners"][0]["ListenerArn"]

    elb.create_rule(
        ListenerArn=listener_arn,
        Priority=1,
        Conditions=[
            {
                "Field": "path-pattern",
                "Values": ["/api/*"]
            }
        ],
        Actions=[
            {"Type": "forward", "TargetGroupArn": backend_tg_arn}
        ]
    )

    return alb_arn, alb_dns, frontend_tg_arn, backend_tg_arn


def create_ecs_service(
    project_id: str,
    service_name: str,
    task_definition_arn: str,
    subnet_ids: list,
    sg_id: str,
    target_group_arn: str,
    container_port: int
):
    """Create an ECS Fargate service."""
    ecs = boto3.client("ecs", region_name=AWS_REGION)

    ecs.create_service(
        cluster=ECS_CLUSTER,
        serviceName=f"app-builder-{project_id}-{service_name}",
        taskDefinition=task_definition_arn,
        desiredCount=1,
        launchType="FARGATE",
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": subnet_ids,
                "securityGroups": [sg_id],
                "assignPublicIp": "ENABLED"
            }
        },
        loadBalancers=[
            {
                "targetGroupArn": target_group_arn,
                "containerName": service_name,
                "containerPort": container_port
            }
        ]
    )

    logger.info(f"ECS service created: app-builder-{project_id}-{service_name}")


def deploy_app(
    project_id: str,
    frontend_image: str,
    backend_image: str,
    mongo_uri: str,
    jwt_secret: str
) -> dict:
    """Full deployment pipeline — returns live URLs."""

    logger.info(f"Starting ECS deployment for project {project_id}")

    # Get VPC and subnets
    vpc_id, subnet_ids = get_default_vpc_and_subnets()
    logger.info(f"Using VPC: {vpc_id}, Subnets: {subnet_ids}")

    # Create security group
    sg_id = create_security_group(project_id, vpc_id)
    logger.info(f"Security group created: {sg_id}")

    # Create ALB
    alb_arn, alb_dns, frontend_tg_arn, backend_tg_arn = create_alb(
        project_id, vpc_id, subnet_ids, sg_id
    )
    logger.info(f"ALB created: {alb_dns}")

    backend_url = f"http://{alb_dns}"
    frontend_url = f"http://{alb_dns}"

    # Register task definitions
    frontend_task = register_task_definition(
        project_id, "frontend", frontend_image, 80,
        {"REACT_APP_API_URL": backend_url}
    )

    backend_task = register_task_definition(
        project_id, "backend", backend_image, 5000,
        {
            "MONGO_URI": mongo_uri,
            "JWT_SECRET": jwt_secret,
            "PORT": "5000",
            "NODE_ENV": "production"
        }
    )

    # Create ECS services
    create_ecs_service(
        project_id, "frontend",
        frontend_task, subnet_ids, sg_id,
        frontend_tg_arn, 80
    )

    create_ecs_service(
        project_id, "backend",
        backend_task, subnet_ids, sg_id,
        backend_tg_arn, 5000
    )

    logger.info(f"Deployment complete — URL: {frontend_url}")

    return {
        "frontend_url": frontend_url,
        "backend_url": f"{backend_url}/api",
        "alb_dns": alb_dns,
        "project_id": project_id
    }