"""
Interact with YC Cloud via REST API
"""

from typing import Optional

import requests


class YandexCloudRestApiHelper:
    """
    Yandex Cloud REST API Helper
    """

    YANDEX_CLOUD_COMPUTE_API_URL = "https://compute.api.cloud.yandex.net"
    YANDEX_CLOUD_INSTANCES_ENDPOINT = (
        f"{YANDEX_CLOUD_COMPUTE_API_URL}/compute/v1/instances"
    )
    YANDEX_CLOUD_DISKS_ENDPOINT = f"{YANDEX_CLOUD_COMPUTE_API_URL}/compute/v1/disks"
    YANDEX_CLOUD_SNAPSHOTS_ENDPOINT = (
        f"{YANDEX_CLOUD_COMPUTE_API_URL}/compute/v1/snapshots"
    )
    YANDEX_CLOUD_OPERATIONS_ENDPOINT = (
        "https://operation.api.cloud.yandex.net/operations"
    )

    def __init__(self, token: str, folder_id: str):
        self.token = token
        self.folder_id = folder_id
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }
        self.session = requests.Session()

    def get_instance_by_name(self, instance_name: str) -> dict[str]:
        """
        Get instances list from YC REST API
        Filter instances by name
        Return instance json
        """
        params = {"folderId": self.folder_id, "filter": f'name="{instance_name}"'}
        response: dict = self.__get_response(
            url=self.YANDEX_CLOUD_INSTANCES_ENDPOINT, params=params
        )
        check_response = response.get("instances")
        if check_response is None:
            raise KeyError(f"There is no compute instance with name {instance_name}!")
        instance = response["instances"][0]
        instance_disk_id = instance["bootDisk"]["diskId"]
        instance_disk = self.get_instance_disk(disk_id=instance_disk_id)
        instance.update({"disk_info": instance_disk})
        instance_ip_address = instance["networkInterfaces"][0]["primaryV4Address"][
            "address"
        ]
        instance_subnet_id = instance["networkInterfaces"][0]["subnetId"]
        instance.update({"subnetId": instance_subnet_id})
        instance.update({"ip_address": instance_ip_address})
        return instance

    def get_instance_disk(self, disk_id: str) -> dict[str]:
        """
        Get info about instance's disk
        """
        url = f"{self.YANDEX_CLOUD_DISKS_ENDPOINT}/{disk_id}"
        response: dict = self.__get_response(url=url, params={})
        return response

    def get_snapshot_by_name(self, snapshot_name: str = None) -> Optional[dict[str]]:
        """
        Get snapshot by name
        """
        params = {"folderId": self.folder_id, "filter": f'name="{snapshot_name}"'}
        response: dict = self.__get_response(
            url=self.YANDEX_CLOUD_SNAPSHOTS_ENDPOINT, params=params
        )
        if response.get("snapshots") is not None:
            return response["snapshots"][0]
        return None

    def get_all_snapshots(self) -> list[dict[str]]:
        """
        Get all snapshots
        """
        params = {"folderId": self.folder_id}
        response: dict = self.__get_response(
            url=self.YANDEX_CLOUD_SNAPSHOTS_ENDPOINT, params=params
        )
        return response.get("snapshots")

    def find_snapshot_for_disk(
        self, disk_info: dict[str], snapshot_name: str = None
    ) -> Optional[dict[str]]:
        """
        Find snapshot for disk
        """
        snapshot_by_name = self.get_snapshot_by_name(snapshot_name=snapshot_name)
        if snapshot_by_name is not None:
            if self.compare_snapshot_and_disk(
                snapshot=snapshot_by_name, disk_info=disk_info
            ):
                return snapshot_by_name

        all_snapshots = self.get_all_snapshots()
        for snapshot in all_snapshots:
            if self.compare_snapshot_and_disk(snapshot=snapshot, disk_info=disk_info):
                return snapshot
        return None

    def create_snapshot_for_disk(
        self, source_disk_id: str, snapshot_name: str, snapshot_description: str
    ) -> str:
        """
        Create snapshot for disk
        """
        body = {
            "folderId": self.folder_id,
            "diskId": source_disk_id,
            "name": snapshot_name,
            "description": snapshot_description,
        }
        create_snapshot_response = self.__post_response(
            url=self.YANDEX_CLOUD_SNAPSHOTS_ENDPOINT, json_body=body
        )
        return create_snapshot_response

    def create_compute_instance_from_snapshot(
        self, instance_json: dict[str], snapshot_id: str
    ) -> str:
        """
        Create compute instance with params from instance json.
        Use snapshotId to create boot disk
        """
        body = {
            "folderId": self.folder_id,
            "name": instance_json["name"],
            "description": "Created by bundle-dev-tools",
            "labels": instance_json["labels"],
            "zoneId": instance_json["zoneId"],
            "platformId": instance_json["platformId"],
            "resourcesSpec": {
                "memory": instance_json["resources"]["memory"],
                "cores": instance_json["resources"]["cores"],
                "coreFraction": instance_json["resources"]["coreFraction"],
            },
            "bootDiskSpec": {
                "mode": instance_json["bootDisk"]["mode"],
                "deviceName": instance_json["bootDisk"]["deviceName"],
                "autoDelete": instance_json["bootDisk"]["autoDelete"],
                "diskSpec": {
                    "name": instance_json["name"] + "-disk",
                    "description": "Created by bundle-dev-tools",
                    "typeId": instance_json["disk_info"]["typeId"],
                    "size": instance_json["disk_info"]["size"],
                    "blockSize": instance_json["disk_info"]["blockSize"],
                    "snapshotId": snapshot_id,
                },
            },
            "networkInterfaceSpecs": [
                {
                    "subnetId": instance_json["subnetId"],
                    "primaryV4AddressSpec": {
                        "address": instance_json["ip_address"],
                    },
                }
            ],
            "hostname": instance_json["fqdn"].split(".")[0],
            "schedulingPolicy": {
                "preemptible": instance_json["schedulingPolicy"]["preemptible"]
            },
        }
        create_instance_response = self.__post_response(
            url=self.YANDEX_CLOUD_INSTANCES_ENDPOINT, json_body=body
        )
        return create_instance_response

    def delete_snapshot_for_disk(self, snapshot_id: str) -> str:
        """
        Delete snapshot for disk
        """
        return self.__delete_entity(
            entity_id=snapshot_id, url=self.YANDEX_CLOUD_SNAPSHOTS_ENDPOINT
        )

    def delete_compute_instance(self, instance_id: str) -> str:
        """
        Delete compute instance by id
        """
        return self.__delete_entity(
            entity_id=instance_id, url=self.YANDEX_CLOUD_INSTANCES_ENDPOINT
        )

    def __delete_entity(
        self,
        url: str,
        entity_id: str,
    ) -> Optional[str]:
        """
        Delete entity by ID
        """
        delete_response = self.__delete_response(url=url, entity_id=entity_id)
        return delete_response

    def __get_response(self, url: str, params: dict[str]) -> dict[str]:
        """
        Create Session and return json response
        """
        self.session.headers.update(self.headers)
        response = self.session.get(url=url, params=params)
        response.raise_for_status()
        return response.json()

    def __post_response(self, url: str, json_body: dict[str]) -> str:
        """
        Create Session and post json request
        Return operation id (action is async)
        """
        self.session.headers.update(self.headers)
        response = self.session.post(url=url, json=json_body)
        response.raise_for_status()
        operation_id = response.json().get("id")
        return operation_id

    def __delete_response(self, url: str, entity_id: str) -> Optional[str]:
        """
        Create Session and delete entity
        Return json response
        """
        self.session.headers.update(self.headers)
        url = url + "/" + entity_id
        response = self.session.delete(url=url)
        response.raise_for_status()
        operation_id = response.json().get("id")
        return operation_id

    def get_operation_status(self, operation_id: str) -> bool:
        """
        Wait until REST API operation ends with success
        """
        url = f"{self.YANDEX_CLOUD_OPERATIONS_ENDPOINT}/{operation_id}"
        operation_result = self.__get_response(url=url, params={})
        done = operation_result["done"]
        return done

    def compare_snapshot_and_disk(
        self, snapshot: dict[str], disk_info: dict[str]
    ) -> bool:
        """
        Compare snapshot and disk by sourceDiskId and sourceSnapshotId
        """
        return (
            snapshot["sourceDiskId"] == disk_info["id"]
            or disk_info.get("sourceSnapshotId") == snapshot["id"]
        )
