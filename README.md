# Setup:
- Add to config.yaml your parameters
- run ./install.sh in order to create VENV and install requirements

## Addition installation for using snapshots:
- Install [YC CLI](https://yandex.cloud/ru/docs/cli/quickstart)
- Configure YC CLI: set your oAuth, cloud-id, folder-id, compute-default-zone
```
yc config profile create <your email>
yc init
```
Put in ~/.bashrc vars:
```
export YC_TOKEN=$(yc iam create-token)
export YC_FOLDER_ID=$(yc config get folder-id)
```

## Scripts overview:
- snapshots.sh: Work with snapshots in Yandex Cloud.


## Run scripts:
### install.sh  - install environment

### snapshots.sh - Operate with snapshots for you Yandex Cloud Compute instances
#### Requirements:
- YC CLI must be configured and installed
- You must have 2 environments variables in your system:
- environment variables YC_TOKEN and YC_FOLDER_ID must present at your profile

#### Limitations:
- Only one snapshot can be created to each VM
- You can restore to snapshot many times for each VM
- If you  delete VM, that snapshot becomes abandoned
- Cannot create snapshots for VM's which have abandoned snapshots, delete abandoned snapshot firstly
- Delete deletes all VM snapshots including abandoned


```
Usage:
usage: snapshots.py [-h] [-v VM_NAME] {create,list,delete,restore}

positional arguments:
  {create,list,delete,restore}

options:
  -h, --help            show this help message and exit
  -v VM_NAME, --vm_name VM_NAME
                        Provide VMs name(from Yandex Cloud). You can pass many VMs at onces
Elapsed Time: 0 minutes and 0 seconds
```

```
Examples:

./snapshots.sh -v test-vm-1 -v test-vm-2 list
|████████████████████████████████████████| 2/2 [100%] in 0.6s (3.19/s) 
|████████████████████████████████████████| 2/2 [100%] in 1.1s (1.50/s) 
+-----------+--------------+----------------------+------------------------+------------+---------------------+-----------------+
|    Host   |  ip address  |        DiskId        | Disk source snapshotId | SnapshotId | Snapshot created at | Snapshot status |
+-----------+--------------+----------------------+------------------------+------------+---------------------+-----------------+
| test-vm-1 | 10.92.42.138 | epdr80s8f359atai9g61 |          None          |    None    |         None        |       None      |
| test-vm-2 | 10.92.42.236 | epd6ogc8n9aqhhcfasnk |          None          |    None    |         None        |       None      |
+-----------+--------------+----------------------+------------------------+------------+---------------------+-----------------+
Elapsed Time: 0 minutes and 2 seconds

./snapshots.sh -v test-vm-1 -v test-vm-2 create
|████████████████████████████████████████| 2/2 [100%] in 0.7s (2.47/s) 
|████████████████████████████████████████| 2/2 [100%] in 1.7s (0.95/s) 
|████████████████████████████████████████| 2/2 [100%] in 20.8s (0.06/s) 
|████████████████████████████████████████| 2/2 [100%] in 0.8s (2.12/s) 
+-----------+--------------+----------------------+------------------------+----------------------+----------------------+-----------------+
|    Host   |  ip address  |        DiskId        | Disk source snapshotId |      SnapshotId      | Snapshot created at  | Snapshot status |
+-----------+--------------+----------------------+------------------------+----------------------+----------------------+-----------------+
| test-vm-1 | 10.92.42.138 | epdr80s8f359atai9g61 |          None          | fd8epbb8gouck7e594vp | 2024-04-13T17:08:05Z |      READY      |
| test-vm-2 | 10.92.42.236 | epd6ogc8n9aqhhcfasnk |          None          | fd8s3dqn8liphh7577ul | 2024-04-13T17:08:06Z |      READY      |
+-----------+--------------+----------------------+------------------------+----------------------+----------------------+-----------------+
Elapsed Time: 0 minutes and 25 seconds


./snapshots.sh -v test-vm-1 -v test-vm-2 restore
|████████████████████████████████████████| 2/2 [100%] in 0.7s (2.46/s) 
|████████████████████████████████████████| 2/2 [100%] in 1.1s (1.51/s) 
|████████████████████████████████████████| 2/2 [100%] in 1:00.6 (0.03/s) 
|████████████████████████████████████████| 2/2 [100%] in 1.7s (0.95/s) 
|████████████████████████████████████████| 2/2 [100%] in 1:00.8 (0.02/s) 
|████████████████████████████████████████| 2/2 [100%] in 0.7s (2.44/s) 
+-----------+--------------+----------------------+------------------------+----------------------+----------------------+-----------------+
|    Host   |  ip address  |        DiskId        | Disk source snapshotId |      SnapshotId      | Snapshot created at  | Snapshot status |
+-----------+--------------+----------------------+------------------------+----------------------+----------------------+-----------------+
| test-vm-1 | 10.92.42.138 | epdr80s8f359atai9g61 |          None          | fd8epbb8gouck7e594vp | 2024-04-13T17:08:05Z |      READY      |
| test-vm-2 | 10.92.42.236 | epd6ogc8n9aqhhcfasnk |          None          | fd8s3dqn8liphh7577ul | 2024-04-13T17:08:06Z |      READY      |
+-----------+--------------+----------------------+------------------------+----------------------+----------------------+-----------------+
Elapsed Time: 2 minutes and 6 seconds

./snapshots.sh -v test-vm-1 list
|████████████████████████████████████████| 1/1 [100%] in 0.4s (2.47/s) 
|████████████████████████████████████████| 1/1 [100%] in 0.5s (1.95/s) 
+-----------+--------------+----------------------+------------------------+------------+---------------------+-----------------+
|    Host   |  ip address  |        DiskId        | Disk source snapshotId | SnapshotId | Snapshot created at | Snapshot status |
+-----------+--------------+----------------------+------------------------+------------+---------------------+-----------------+
| test-vm-1 | 10.92.42.138 | epd2utaed98n0qukr05h |  fd8epbb8gouck7e594vp  |    None    |         None        |       None      |
+-----------+--------------+----------------------+------------------------+------------+---------------------+-----------------+
Elapsed Time: 0 minutes and 1 seconds

```
