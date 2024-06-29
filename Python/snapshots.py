#!/usr/bin/env python3

"""
Work with snapshots for Yandex Cloud Compute instances
"""

import argparse
import json
import os
import pathlib
import sys
from alive_progress import alive_bar
from argparser.main import args_parser
from prettytable import PrettyTable
from yandex_cloud_wrapper.yc_instance import YandexCloudInstance
from yandex_cloud_wrapper.yc_rest_api_helper import YandexCloudRestApiHelper


def main(namespace_args: argparse.Namespace) -> None:
    """
    Main
    """

    bar_max = len(namespace_args.vm_name)

    # 1 - Get Yandex Cloud Instances ID by Name
    all_instances = []
    yc_rest_api_helper = YandexCloudRestApiHelper(token=yc_token, folder_id=folder_id)
    with alive_bar(bar_max) as progress_bar:
        for vm_name in namespace_args.vm_name:
            instance: dict[str] = yc_rest_api_helper.get_instance_by_name(instance_name=vm_name)
            if namespace_args.action == "create" and instance is None:
                raise RuntimeError(f"Instance {vm_name} does not exist in YandexCloud! Instance must exist in order to create snapshot!")
            if instance is None:
                instance = load_instance_from_json(instance_name=vm_name)
            progress_bar.text("Getting instances from YandexCloud...")
            progress_bar()  # pylint: disable=E1102
            all_instances.append(instance)

    # 2 - Get Yandex Cloud Instance objects
    yc_instances = []
    for instance in all_instances:
        yc_instance = YandexCloudInstance(
            name=instance["name"],
            ip_address=instance["ip_address"],
            disk_id=instance["bootDisk"]["diskId"],
            instance_json=instance,
            yc_wrapper=yc_rest_api_helper,
        )
        yc_instances.append(yc_instance)

    # 3 - Create snapshots for all YC Instances

    if namespace_args.action == "create":
        run_action_with_alive_bar_on_hosts(
            action="create_snapshot",
            bar_text="Creating snapshots...",
            yc_instances=yc_instances,
        )
        run_action_with_alive_bar_on_hosts(
            action="wait_until_operation_is_done",
            bar_text="Wait until snapshots become READY...",
            yc_instances=yc_instances,
        )
        print_common_info_table(yc_instances=yc_instances)

    # 4 List: Show instances and there snapshots
    if namespace_args.action == "list":
        print_common_info_table(yc_instances=yc_instances)
        find_and_print_abandoned_snapshots(yc_instances=yc_instances)

    # 5 Delete snapshots
    if namespace_args.action == "delete":
        instances_with_snapshots = list(filter(lambda j: (j.snapshot_id is not None), yc_instances))
        if len(instances_with_snapshots) > 0:
            run_action_with_alive_bar_on_hosts(
                action="delete_snapshot",
                bar_text="Deleting snapshots...",
                yc_instances=instances_with_snapshots,
            )
            run_action_with_alive_bar_on_hosts(
                action="wait_until_operation_is_done",
                bar_text="Wait until snapshots become Deleted...",
                yc_instances=instances_with_snapshots,
            )
        instances_with_abandoned_snapshots = _find_instances_with_abandoned_snapshots(yc_instances=yc_instances)
        if len(instances_with_abandoned_snapshots) > 0:
            run_action_with_alive_bar_on_hosts(
                action="delete_abandoned_snapshot",
                bar_text="Deleting abandoned snapshots...",
                yc_instances=instances_with_abandoned_snapshots,
            )
            run_action_with_alive_bar_on_hosts(
                action="wait_until_operation_is_done",
                bar_text="Wait until snapshots become Deleted...",
                yc_instances=instances_with_abandoned_snapshots,
            )
        print_common_info_table(yc_instances=yc_instances)

    # 6 Restore to snapshot
    if namespace_args.action == "restore":
        check_that_instance_has_snapshot_to_restore(yc_instances=yc_instances)
        run_action_with_alive_bar_on_hosts(
            action="delete_instance",
            bar_text="Deleting current instances...",
            yc_instances=yc_instances,
        )
        run_action_with_alive_bar_on_hosts(
            action="wait_until_operation_is_done",
            bar_text="Wait until instances become Deleted...",
            yc_instances=yc_instances,
        )
        run_action_with_alive_bar_on_hosts(
            action="create_instance_from_snapshot",
            bar_text="Creating instances from snapshots...",
            yc_instances=yc_instances,
        )
        run_action_with_alive_bar_on_hosts(
            action="wait_until_operation_is_done",
            bar_text="Wait until instances become READY...",
            yc_instances=yc_instances,
        )
        print_common_info_table(yc_instances=yc_instances)


def run_action_with_alive_bar_on_hosts(action: str, bar_text: str, yc_instances: list[YandexCloudInstance]):
    """
    Create alive bar
    For each instance run action with progress bar
    """
    with alive_bar(len(yc_instances)) as progress_bar:
        progress_bar.text(bar_text)
        for yc_instance in yc_instances:
            if "wait_until_operation_is_done" in action:
                yc_instance.wait_until_operation_is_done()
            elif "create_snapshot" in action:
                yc_instance.create_snapshot()
            elif "delete_snapshot" in action:
                yc_instance.delete_snapshot()
            elif "delete_abandoned_snapshot" in action:
                yc_instance.delete_abandoned_snapshot()
            elif "delete_instance" in action:
                if yc_instance.instance_exist:
                    yc_instance.delete_instance()
            elif "create_instance_from_snapshot" in action:
                yc_instance.create_instance_from_snapshot()
            else:
                raise RuntimeError(f"Invalid action {action}")
            progress_bar()  # pylint: disable=E1102


def _create_common_info_table() -> PrettyTable:
    """Create pretty table"""
    table = PrettyTable()
    table.field_names = [
        "Host",
        "ip address",
        "DiskId",
        "Disk source snapshotId",
        "SnapshotId",
        "Snapshot created at",
        "Snapshot status",
    ]
    return table


def _create_abandoned_snapshots_table() -> PrettyTable:
    """Create pretty table"""
    table = PrettyTable()
    table.field_names = [
        "Id",
        "Name",
        "description",
        "createdAt",
        "status",
    ]
    return table


def print_abandoned_snapshots_table(yc_instances: list[YandexCloudInstance]):
    """
    Print pretty
    """
    table = _create_abandoned_snapshots_table()
    for instance in yc_instances:
        table.add_row(
            [
                instance.abandoned_snapshot["id"],
                instance.abandoned_snapshot["name"],
                instance.abandoned_snapshot["description"],
                instance.abandoned_snapshot["createdAt"],
                instance.abandoned_snapshot["status"],
            ]
        )
    print(table)


def print_common_info_table(yc_instances: list[YandexCloudInstance]):
    """
    Print pretty
    """
    table = _create_common_info_table()
    with alive_bar(len(yc_instances)) as progress_bar:
        progress_bar.text("Getting instances snapshots...")
        for instance in yc_instances:
            table.add_row(
                [
                    instance.name,
                    instance.ip_address,
                    instance.disk_id,
                    instance.disk_source_snapshot_id,
                    instance.snapshot_id,
                    instance.snapshot_created_at,
                    instance.snapshot_status,
                ]
            )
            progress_bar()  # pylint: disable=E1102
    print(table)


def find_and_print_abandoned_snapshots(yc_instances: list[YandexCloudInstance]):
    """
    Find abandoned snapshots for instance
    If found, print table with abandoned snapshots
    """
    instances_with_abandoned_snapshots = _find_instances_with_abandoned_snapshots(yc_instances=yc_instances)
    if len(instances_with_abandoned_snapshots) > 0:
        print("Found abandoned snapshots:")
        print_abandoned_snapshots_table(yc_instances=instances_with_abandoned_snapshots)


def _find_instances_with_abandoned_snapshots(
    yc_instances: list[YandexCloudInstance],
) -> list[YandexCloudInstance]:
    """
    Find abandoned snapshots for instance
    """
    return list(filter(lambda j: (j.abandoned_snapshot is not None), yc_instances))


def check_that_instance_has_snapshot_to_restore(
    yc_instances: list[YandexCloudInstance],
):
    """
    Check that instance has snapshot
    """
    instance_without_snapshot = next(
        filter(
            lambda j: (j.snapshot_id is None or j.snapshot_status != "READY"),
            yc_instances,
        ),
        None,
    )
    if instance_without_snapshot is not None:
        raise RuntimeError("Some instances do not have ready snapshot to restore, please check snapshot list!")


def load_instance_from_json(instance_name: str) -> dict[str, any]:
    """
    Try to load json from disk if exist
    """
    json_data_folder = "yandex_cloud_wrapper/json_data"
    json_files_folder = pathlib.Path(__file__).parent.resolve() / json_data_folder
    instance_json = pathlib.Path(json_files_folder / f"{instance_name}.json")
    if not (json_files_folder.is_dir() and instance_json.is_file()):
        raise ValueError(f"Could not get instance {instance_name} from json file on disk, or from YandexCloud REST API")
    with open(instance_json, "r", encoding="utf-8") as instance_file:
        instance = json.load(instance_file)
        return instance


if __name__ == "__main__":
    args_parser = args_parser()
    args_parser.add_argument(
        "-v",
        "--vm_name",
        help="Provide VMs name(from Yandex Cloud). You can pass many VMs at onces",
        dest="vm_name",
        action="append",
    )
    args_parser.add_argument("action", choices=["create", "list", "delete", "restore"])
    namespace = args_parser.parse_args(sys.argv[1:])
    if namespace.action not in ["create", "list", "delete", "restore"]:
        raise ValueError("Please provide correct action!")
    yc_token: str = os.environ.get("YC_TOKEN")
    folder_id: str = os.environ.get("YC_FOLDER_ID")
    if None in (yc_token, folder_id):
        raise ValueError("Please provide YC_TOKEN and FOLDER_ID environment variables!")
    if len(namespace.vm_name) == 0:
        raise ValueError("Please provide Yandex Cloud VM Names!")
    main(namespace_args=namespace)
