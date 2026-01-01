## Q: How many packages do we have for which patches are available? 

### context
Our ability to answer this question is predicated on the scope of coverage from the package-index service. Look to the system prompt to tell you what we currently support. Make sure the user understands this.

### how to answer

1. Query the for the Package record(s) for the Dataset(s) scoped to the user's request. Note that we are getting the full list (with duplicates) by way of the package subquery and not the packageType subquery. Also note the use of Package field numberVersionsBehindHead. The database will create a default value of -1 for that field unless the package-index encrichment service has updated that record in which case it will be >= 0. THIS WILL GIVE YOU THE NUMBER OF PACKAGE TYPES THAT HAVE AN UPDATE AVAILABLE. Note also that for this type of query - the API will - by default - give information for the most recent commit. Note also that we use the size parameter to prevent the need to make to many requests. 

```
https://{DATA_SERVICE_HOST}/api/v1/db/datasetMetrics/package/query?size=100&isCurrent=true&datasetName={DATASET_NAME}&numberVersionsBehindHead=gte.1
```

