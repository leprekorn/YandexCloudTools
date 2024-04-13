"""
Yandex Cloud Instance object
"""

from typing import Optional

from tenacity import retry, retry_if_result, stop_after_attempt, wait_fixed

from .yc_rest_api_helper import YandexCloudRestApiHelper


# pylint: disable=R0902, R0913
class YandexCloudInstance:
    """
    Yandex Cloud Instance
    """

    def __init__(
        self,
        name: str,
        ip_address: str,
        disk_id: str,
        instance_json: dict[str],
        yc_wrapper: YandexCloudRestApiHelper,
    ):
        self.yc_wrapper = yc_wrapper
        self.name = name
        self.ip_address = ip_address
        self.disk_id = disk_id
        self.instance_json = instance_json
        self.disk_info: dict[str] = instance_json.get("disk_info")
        self.disk_source_snapshot_id: str = self.disk_info.get("sourceSnapshotId")
        self.snapshot_name: str = self.name + "-snapshot"
        self.snapshot_description: str = "Created by bundle_dev_tools"
        self.operation_id = None

    @property
    def snapshot_json(self) -> Optional[dict[str]]:
        """
        Return snapshot json
        """
        return self.get_snapshot()

    @property
    def snapshot_id(self) -> str:
        """
        Return snapshot id
        """
        return self.snapshot_json.get("id")

    @property
    def snapshot_created_at(self) -> str:
        """
        Return snapshot createdAt
        """
        return self.snapshot_json.get("createdAt")

    @property
    def snapshot_status(self) -> str:
        """
        Return snapshot status
        """
        return self.snapshot_json.get("status")

    @property
    def abandoned_snapshot(self) -> Optional[dict[str]]:
        """
        Return abandoned snapshot (snapshot with name of this VM, but not linked with instance's disk)
        """
        snapshot = self.yc_wrapper.get_snapshot_by_name(
            snapshot_name=self.snapshot_name
        )
        if (
            snapshot is not None
            and snapshot["description"] == self.snapshot_description
            and not self.yc_wrapper.compare_snapshot_and_disk(
                snapshot=snapshot, disk_info=self.disk_info
            )
        ):
            return snapshot
        return None

    @retry(
        stop=stop_after_attempt(10),
        wait=wait_fixed(20),
        retry=retry_if_result(lambda result: result is False),
    )
    def wait_until_operation_is_done(self) -> bool:
        """
        Check that operation is done
        """
        if self.operation_id is not None:
            return self.yc_wrapper.get_operation_status(operation_id=self.operation_id)
        return False

    def get_snapshot(self) -> dict[str]:
        """
        Get snapshot if exist for this instance with it's disk_id
        """
        return (
            self.yc_wrapper.find_snapshot_for_disk(
                disk_info=self.disk_info, snapshot_name=self.snapshot_name
            )
            or {}
        )

    def create_snapshot(self) -> None:
        """
        Create snapshot for boot disk
        """
        if self.snapshot_id is not None:
            raise RuntimeError(
                f"Snapshot: {self.snapshot_json['name']} already exist for VM: {self.name} with disk id: {self.disk_id}"
            )

        if self.abandoned_snapshot is not None:
            raise RuntimeError(
                f"Can't create snapshot, abandoned snapshot for this VM already exist. Please delete snapshot {self.snapshot_name} first!"
            )
        self.operation_id = self.yc_wrapper.create_snapshot_for_disk(
            source_disk_id=self.disk_id,
            snapshot_name=self.snapshot_name,
            snapshot_description=self.snapshot_description,
        )

    def delete_snapshot(self) -> None:
        """
        Delete snapshot
        """
        if self.snapshot_id is not None:
            self.__delete_snapshot(snapshot_id=self.snapshot_id)

    def delete_abandoned_snapshot(self) -> None:
        """
        Delete abandoned snapshot
        """
        if (
            self.abandoned_snapshot is not None
            and self.abandoned_snapshot.get("id") is not None
        ):
            self.__delete_snapshot(snapshot_id=self.abandoned_snapshot["id"])

    def __delete_snapshot(self, snapshot_id: str) -> None:
        """
        Delete snapshot by id
        """
        self.operation_id = self.yc_wrapper.delete_snapshot_for_disk(
            snapshot_id=snapshot_id
        )

    def delete_instance(self) -> None:
        """
        Delete this instance
        """
        if self.snapshot_id is None:
            raise RuntimeError(
                "You don't have snapshot for this instance, are you sure want to delete it?"
            )
        self.operation_id = self.yc_wrapper.delete_compute_instance(
            instance_id=self.instance_json.get("id")
        )

    def create_instance_from_snapshot(self) -> None:
        """
        Create new instance from snapshot
        """
        if self.snapshot_id is None:
            raise RuntimeError(
                "Do not have valid snapshot for this instance, can't restore to snapshot"
            )
        self.operation_id = self.yc_wrapper.create_compute_instance_from_snapshot(
            instance_json=self.instance_json, snapshot_id=self.snapshot_id
        )
