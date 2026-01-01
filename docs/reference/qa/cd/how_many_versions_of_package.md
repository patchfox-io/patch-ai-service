## Q: How many different versions of {PACKAGE_NAME} are there?

### context 
This question is about how many versions are there in the dataset RIGHT NOW. It's important you use the endpoint shown below 
to answer the question because it will do that for you. DO NOT GO TO THE PACKAGE TABLE. That will show you how many versions of
{PACKAGE_NAME} have EVER been in the dataset - which is a different question. 



### how to answer
1. Query the datasetMetrics table for the Package record(s) for the Dataset(s) scoped to the user's request. Note that we are using the packageType subquery and not the package subquery to get a deduplicated list of packages associated with the dataset. Note how we set the size parameter (how many entries per page) higher than the default 20 to avoid making too many network calls. Lastly note that when making this kind of call the defaultbehavior will be to return information gername to the most recent, but commitDateTime, datasetMetrics record.

```
https://{DATA_SERVICE_HOST}/api/v1/db/datasetMetrics/packageType/query?size=100datasetName={DATASET_NAME}&isCurrent=true&purl={PACKAGE_NAME}
```

2. If there is more than one package type (a package purl sans the version) that matches {PACKAGE_NAME} gain agreement with the user as to which package type they are asking after. 

3. The packageType subquery will return a deduplicated list of all packages associated with the dataset. PatchFox considers package unique if it has a unique combination of namespace, name, and version. Therefore, the count of purls in the return dataset that matches what you and the user agree matches {PACKAGE_NAME} is the answer to the question "how many different versions of {PACKAGE_TYPE} are there? 
 
