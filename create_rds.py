#!/usr/bin/env python3
# Simple boto3 script to create an AWS RDS DB instance and wait until available.
# Uses AWS credentials from environment, shared config, or instance profile.

import argparse
import getpass
import sys
import time

import boto3
import botocore


def parse_args():
    parser = argparse.ArgumentParser(description="Create an AWS RDS DB instance (boto3).")
    parser.add_argument("--db-instance-identifier", "-i", required=True, help="DB instance identifier")
    parser.add_argument("--db-instance-class", "-c", default="db.t3.micro", help="DB instance class")
    parser.add_argument("--engine", default="postgres", choices=["postgres", "mysql", "mariadb", "oracle-se2", "sqlserver-ex"], help="Database engine")
    parser.add_argument("--allocated-storage", type=int, default=20, help="Allocated storage (GB)")
    parser.add_argument("--db-name", default="mydb", help="Initial database name")
    parser.add_argument("--master-username", default="admin", help="Master username")
    parser.add_argument("--master-user-password", help="Master user password (will prompt if omitted)")
    parser.add_argument("--vpc-security-group-ids", nargs="*", help="Space-separated VPC security group IDs")
    parser.add_argument("--db-subnet-group-name", help="DB subnet group name (for VPC) if required")
    parser.add_argument("--publicly-accessible", action="store_true", help="Make the DB publicly accessible")
    parser.add_argument("--multi-az", action="store_true", help="Create a Multi-AZ DB instance")
    parser.add_argument("--backup-retention-period", type=int, default=7, help="Backup retention in days")
    parser.add_argument("--region", help="AWS region (overrides environment/profile)")
    return parser.parse_args()


def create_db_instance(rds, args):
    pw = args.master_user_password or getpass.getpass("Master user password: ")

    params = {
        "DBInstanceIdentifier": args.db_instance_identifier,
        "AllocatedStorage": args.allocated_storage,
        "DBInstanceClass": args.db_instance_class,
        "Engine": args.engine,
        "MasterUsername": args.master_username,
        "MasterUserPassword": pw,
        "DBName": args.db_name,
        "MultiAZ": args.multi_az,
        "PubliclyAccessible": args.publicly_accessible,
        "BackupRetentionPeriod": args.backup_retention_period,
        # default storage type; change if needed
        "StorageType": "gp2",
    }

    if args.vpc_security_group_ids:
        params["VpcSecurityGroupIds"] = args.vpc_security_group_ids
    if args.db_subnet_group_name:
        params["DBSubnetGroupName"] = args.db_subnet_group_name

    try:
        print("Creating DB instance", args.db_instance_identifier)
        resp = rds.create_db_instance(**params)
        print("Create call accepted, status:", resp.get("DBInstance", {}).get("DBInstanceStatus"))
        return True
    except botocore.exceptions.ClientError as e:
        print("Error creating DB instance:", e.response.get("Error", {}).get("Message"))
        return False


def wait_for_available(rds, identifier, timeout_minutes=30):
    waiter = rds.get_waiter("db_instance_available")
    timeout_seconds = timeout_minutes * 60
    start = time.time()
    try:
        print("Waiting for DB instance to become available (this may take several minutes)...")
        waiter.wait(DBInstanceIdentifier=identifier, WaiterConfig={"Delay": 30, "MaxAttempts": int(timeout_seconds / 30)})
        return True
    except botocore.exceptions.WaiterError as e:
        print("Timed out waiting for DB to become available:", str(e))
        return False
    except botocore.exceptions.ClientError as e:
        print("Error while waiting:", e.response.get("Error", {}).get("Message"))
        return False


def describe_endpoint(rds, identifier):
    try:
        resp = rds.describe_db_instances(DBInstanceIdentifier=identifier)
        inst = resp["DBInstances"][0]
        endpoint = inst.get("Endpoint", {})
        addr = endpoint.get("Address")
        port = endpoint.get("Port")
        print("DB instance available.")
        print("Endpoint:", addr)
        print("Port:", port)
        return addr, port
    except botocore.exceptions.ClientError as e:
        print("Error describing DB instance:", e.response.get("Error", {}).get("Message"))
        return None, None


def main():
    args = parse_args()

    session_kwargs = {}
    if args.region:
        session_kwargs["region_name"] = args.region

    session = boto3.Session(**session_kwargs)
    rds = session.client("rds")

    ok = create_db_instance(rds, args)
    if not ok:
        sys.exit(1)

    ok = wait_for_available(rds, args.db_instance_identifier)
    if not ok:
        sys.exit(2)

    describe_endpoint(rds, args.db_instance_identifier)


if __name__ == "__main__":
    main()
