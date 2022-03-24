# CSM Redfish Interface Emulator

The CSM Redfish Interface Emulator is based off DMTF's [Redfish Interface Emulator](https://github.com/DMTF/Redfish-Interface-Emulator) and can emulate a redfish interface with static and dynamic resources.

Although this project is based on DMTF's Redfish Interface Emulator project, it deviates a bit from DMTF's project's functionality. DMTF's project's dynamic resources are meant to be fully generated and generic. The CSM Redfish Interface Emulator project takes this an uses it to create dynamic resources that sit under a static mockup to emulate specific BMCs.

Static resources are emulated by simply copying a redfish mockup into the ./mockups/<BMC_type> directory and specifying the <BMC_type> in the MOCKUPFOLDERS field in the [emulator-config.json](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/emulator-config.json) file. The emulator will automatically make these resources answer to GET only. For more see the [Creating a Static Mockup](#creating-static-mockup) section.

Dynamic emulation is accomplished by creating custom python files for each dynamic resource. You can use the [Update Service API](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/update_service_api.py) as an example when creating a new dynamic resources.

New BMC types for emulation are created by loading a complete static mockup and overriding the resource URIs that you want to be dynamic. This is done by creating a <BMC_type>-loader.py file and adding the load() call to [resource_manager.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/resource_manager.py). For example [bard_peak_loader.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/bard_peak_loader.py). <BMC_type>-loader.py is where you will specify which resource URIs will be dynamic.

## Topics:

* [Running the emulator](#running-the-emulator)
    * [Docker](#docker)
    * [Locally](#locally)
* [Creating a new BMC type for emulation](#creating-new-emulator)
    * [Creating a static mockup](#creating-static-mockup)
    * [Creating dynamic resources](#creating-dynamic-resources)
        * [Behavior controls](behavior-controls)
        * [Templates for dynamic resources](#templates-for-dynamic-resources)
* [Existing static mockups](#existing-static-mockups)
* [Existing dynamic resources](#existing-dynamic-resources)
* [Existing emulators](#existing-emulators)
    * [Bard Peak](#bard-peak)

<a name="running-the-emulator"></a>

## Running the emulator

This emulator can be run locally or as a docker image.

<a name="docker"></a>

### Docker

You can either run a predefined emulator using their Dockerfile.<BMC_type> file or configure a custom docker image by editing the 'MOCKUPFOLDERS' field in [emulator-config.json](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/emulator-config.json) to specify which BMC mockup you want to use, delete the 'STATIC' field, and use the generic Dockerfile.
```
{
  "MODE": "Local",
  "HTTPS": "Enable",
  "TRAYS": [],
  "SPEC": "Redfish",
  "MOCKUPFOLDERS": ["<MyBMC>"]
}
```

**NOTE:** 'Dockerfile' assumes your custom static files are in place in the ./mockups/<MyBMC> directory.

**NOTE:** The 'MOCKUPFOLDERS' field is an array but only one is used.

**NOTE:** With 'emulator-config.json' as is, building with 'Dockerfile' will create a static only emulator using DMTF's generic static mockup.

Build the docker image.
```
docker build -t csm-redfish-interface-emulator:latest -f Dockerfile.<BMC_type> .
```

Set a local port for your BMC
```
BMC_PORT=5000
```

Run the docker image.
```
docker run -p ${BMC_PORT}:5000 --rm csm-redfish-interface-emulator:latest
```

<a name="locally"></a>

### Locally

Editing the 'MOCKUPFOLDERS' field in [emulator-config.json](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/emulator-config.json) to specify which BMC mockup you want to use and delete the 'STATIC' field.

```
{
  "MODE": "Local",
  "HTTPS": "Enable",
  "TRAYS": [],
  "SPEC": "Redfish",
  "MOCKUPFOLDERS": ["<MyBMC>"]
}
```

**NOTE:** The 'MOCKUPFOLDERS' field is an array but only one is used.

**NOTE:** With 'emulator-config.json' as is, running setup.sh will create a static only emulator using DMTF's generic static mockup.

Set a local port for your BMC
```
BMC_PORT=5000
```

Run the setup.sh script.
```
./setup.sh -p ${BMC_PORT} -w ../<WORK_DIR>
```

This will create a <WORK_DIR> directory outside of your csm-redfish-interface-emulator directory, pull in DMTF's Redfish Interface Emulator to the specified workspace directory, copy the local csm-redfish-interface-emulator files and directories into the specified workspace directory, and run the emulator. Any conflicting files will be replaced by the local csm-redfish-interface-emulator files. All static mockups in csm-redfish-interface-emulator/mockups will be copied into <WORK_DIR>/api_emulator/redfish/static.

The setup.sh script can also be run without starting the emulator to just prepare the emulator files.
```
./setup.sh -p ${BMC_PORT} -w ../<WORK_DIR> -n
```

**NOTE:** If <WORK_DIR> already exists before running the setup.sh script, it will first get deleted.

<a name="creating-new-emulator"></a>

## Creating a new BMC type for emulation

New BMC types can be added for emulation. This can be done by using a completely static mockup or a mix of static and dynamic resources. The following outlines the overall process.

<a name="creating-static-mockup"></a>

### Creating a static mockup

A static mockup is a directory tree that is an exact copy of the desired BMC type's redfish tree starting at the service base, /redfish/v1. Each directory has an index.json file that contains a copy of what is returned by a GET to that resource in the redfish tree. For example:
```
BardPeak:
- Systems
-- Node0
...
--- index.json
-- index.json
- index.json
```

DMTF has a tool that can be run against a real BMC to walk the entire redfish tree and create a mockup, the [Redfish Mockup Creator](https://github.com/DMTF/Redfish-Mockup-Creator).

**NOTE:** DMTF's Redfish Mockup Creator only follows "@odata.id", "Uri", or "Members@odata.nextLink" links to go deeper. Because of this "@Redfish.ActionInfo" URIs need to be manually copied to complete the static mockup if you expect these to be queried. For the Bard Peak mockup, the following URIs had to be manually copied:
- /redfish/v1/Systems/Node0/ResetActionInfo
- /redfish/v1/UpdateService/SimpleUpdateActionInfo

The static resource tree for a BMC type needs to be placed in csm-redfish-interface-emulator/mockups/<BMC_type> such that the index.json file in ./<BMC_type> is for the resource base, /redfish/v1.

<a name="creating-dynamic-resources"></a>

### Creating dynamic resources

To create an emulator with dynamic resources for a new BMC type you will need to create a <BMC_type>_loader.py file where the functions for setting up the dynamic resources will live. The [bard_peak_loader.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/bard_peak_loader.py) file is an example of this.

You will then need to add a call to the loader in [resource_manager.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/resource_manager.py). This is done for Bard Peak [here](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/resource_manager.py#L155)

You need to either use existing python functions or make new ones for any resource URI that you want to have answer to more than just GET or be modifiable by other URIs such as '/redfish/v1/Systems/<system_id>' and '/redfish/v1/Systems/<system_id>/Actions/ComputerSystem.Reset'. If the new dynamic resources are specific to the BMC type, create a <BMC_type>_<resource_name>_api.py file for them. Otherwise, existing functions can be used. The computer systems functions used in the Bard Peak emulator that are generic for any BMC type that has the '/redfish/v1/Systems/<system_id>/ResetActionInfo' URI to get power actions. This code exists in [computer_systems_api.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/computer_systems_api.py).

You can either use the [auto generator tool](https://github.com/DMTF/Redfish-Interface-Emulator/blob/master/README.md#auto-generate-the-api-file) that DMTF provides as part of their [Redfish Interface Emulator](https://github.com/DMTF/Redfish-Interface-Emulator) project to generate a template or use existing code as an example.

<a name="behavior-controls"></a>

#### Behavior controls

A few of the existing dynamic resources have 'hidden' config URIs used for configuring response behavior for the dynamic resource on the fly. The [update_service_api.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/update_service_api.py) file is an example of this. It provides a 'hidden' (not displayed in /redfish/v1/UpdateService/FirmwareInventory['Members']) URI. This URI is used to view (GET) currently configured behavior or set (PATCH) new behavior for the '/redfish/v1/UpdateService/SimpleUpdate' URI. For an emulated Bard Peak, this looks like:
```
{
  "Id": "UpdateServiceConfigInfo",
  "Name": "UpdateServiceConfig",
  "Description": "Use PATCH operations to set the below values to affect Update Service actions.",
  "Parameters": [
    {
      "DataType": "StringArray",
      "Name": "Fail",
      "Description": "List of targets that will fail update actions.",
      "AllowableValues": [
        "Node0.HPCNet3",
        "BMC",
        "Node0.HPCNet0",
        "FPGA2",
        "Node0.HPCNet1",
        "Node0.AccVBIOS",
        "Bootloader",
        "Node0.HPCNet2",
        "Node0.AccUC",
        "Recovery",
        "FPGA0",
        "Node0.BIOS",
        "FPGA1",
        "Node0.ManagementEthernet"
      ]
    },
    {
      "DataType": "Int",
      "Name": "Hang",
      "Description": "Amount of time in seconds to Hang."
    },
    {
      "DataType": "Int",
      "Name": "UpdateTime",
      "Description": "Amount of time in seconds to for updates to take."
    }
  ],
  "CurrentValues": {
    "UpdateTime": 10,
    "Fail": [
      "BMC"
    ],
    "Hang": 0
  }
}
```
You may wish to create a resource such as this for each of your dynamic resource to make testing more configurable.

<a name="templates-for-dynamic-resources"></a>

#### Templates for dynamic resources

Some dynamic resources such as the EventService generate responses (i.e. Redfish events) that are BMCType specific. Templates are used for these resources. The templates exist in the [src/api_emulator/redfish/templates/](https://github.com/Cray-HPE/csm-redfish-interface-emulator/tree/master/src/api_emulator/redfish/templates) directory. The BardPeak emulator uses [cray_events.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/templates/cray_events.py) and [cray_subscription.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/templates/cray_subscription.py) for generating subscriptions and redfish events for the EventService. Which templates to use are generally set by the <BMC_type>_loader.py when response format can vary between BMC type.

<a name="existing-static-mockups"></a>

## Existing static mockups:
- Bard Peak - [./mockups/BardPeak](https://github.com/Cray-HPE/csm-redfish-interface-emulator/tree/master/mockups/BardPeak)

<a name="existing-dynamic-resources"></a>

## Existing dynamic resources:
- Olympus Power Capping - [./src/api_emulator/redfish/olympus_power_api.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/olympus_power_api.py)
    GET/PATCH /redfish/v1/Chassis/<system_id>/Controls/<control_id>
    PATCH     /redfish/v1/Chassis/<system_id>/Controls.Deep
- Computer System Power Actions - [./src/api_emulator/redfish/computer_systems_api.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/computer_systems_api.py)
    GET /redfish/v1/Systems/<system_id>
    POST /redfish/v1/Systems/<system_id>/Actions/ComputerSystem.Reset
- Firmware Update - [./src/api_emulator/redfish/update_service_api.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/update_service_api.py)
    GET /redfish/v1/UpdateService/FirmwareInventory/<target_id>
    POST /redfish/v1/UpdateService/SimpleUpdate
    GET/PATCH /redfish/v1/UpdateService/FirmwareInventory/Config
- EventService - [./src/api_emulator/redfish/event_service_api.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/event_service_api.py), [./src/api_emulator/redfish/event_generator.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/event_service_api.py)
    GET/PATCH        /redfish/v1/EventService
    GET/POST         /redfish/v1/EventService/Subscriptions
    GET/PATCH/DELETE /redfish/v1/EventService/Subscriptions/<id>

<a name="existing-emulators"></a>

## Existing emulators

<a name="bard-peak"></a>

### Bard Peak:
- Loader - [./src/api_emulator/bard_peak_loader.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/bard_peak_loader.py)
- Static Mockup Files - [./mockups/BardPeak](https://github.com/Cray-HPE/csm-redfish-interface-emulator/tree/master/mockups/BardPeak)
- Dynamic Resources
    - Olympus Power Capping - [./src/api_emulator/redfish/olympus_power_api.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/olympus_power_api.py)
        GET/PATCH /redfish/v1/Chassis/<system_id>/Controls/<control_id>
    - Computer System Power Actions - [./src/api_emulator/redfish/computer_systems_api.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/computer_systems_api.py)
        GET /redfish/v1/Systems/<system_id>
        POST /redfish/v1/Systems/<system_id>/Actions/ComputerSystem.Reset
    - Firmware Update - [./src/api_emulator/redfish/update_service_api.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/update_service_api.py)
        GET /redfish/v1/UpdateService/FirmwareInventory/<target_id>
        POST /redfish/v1/UpdateService/SimpleUpdate
        GET/PATCH /redfish/v1/UpdateService/FirmwareInventory/Config
    - EventService - [./src/api_emulator/redfish/event_service_api.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/event_service_api.py), [./src/api_emulator/redfish/event_generator.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/event_service_api.py)
        GET/PATCH        /redfish/v1/EventService
        GET/POST         /redfish/v1/EventService/Subscriptions
        GET/PATCH/DELETE /redfish/v1/EventService/Subscriptions/<id>
    - EventService Templates - [./src/api_emulator/redfish/templates/cray_events.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/templates/cray_events.py), [./src/api_emulator/redfish/templates/cray_subscription.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/templates/cray_subscription.py)

