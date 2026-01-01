# Q: I'm expecting this data to appear but I can't find it. Why?

### context
Depends on what kind of data. Gain agreement with the user before attempting to answer. If the user is asking after a Finding some other tool says is there but ours does not register, and, the findings are not apples to apples (ie - the other tool is reporting a finding from their internal database whereas we use only NVD findings) it's important to explain to the user the differences bewtween public and proprietary databases of Finding information. 

### how to answer 
1. If it is package data see [Q: Patchfox is failing to detect or pick up {dependency} in my repo. Help?](./pf_not_detecting_dependency.md) 

If it is a Datasource or DatasourceEvents then see [Q: Is my {repo/datasource} onboarded to Patchfox?](./is_my_ds_onboarded.md) and use the data provided by the specified endpoint to determine if the Datasource/DatasourceEvents are completely absent or if there has been some kind of error. 

If it is Finding data then first check with the user that the Finding in question is a CVE. At present PatchFox only supports CVE findings. If it is, then check [Q: Patchfox is failing to detect or pick up {dependency} in my repo. Help?](./pf_not_detecting_dependency.md) to see if the dependency is registered in the system and associated with the Dataset. From there use the following endpoint to pull all FindingTypes and validate that the expected Finding is or is not present. If it is not present but the Package is, check NVD to see if the finding is indeed associated with that Package.

```
https://{DATA_SERVICE_HOST}/api/v1/db/datasetMetrics/findingType/query
```
