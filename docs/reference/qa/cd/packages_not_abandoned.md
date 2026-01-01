## Q: How many packages have not abandoned by the maintainer?

### context
As with [How many packages do we have for which patches are available?](./packages_can_be_patched.md) our ability to answer is limited to our ability to support calls to package indexes. Check your system prompt for a current list. Make sure the user understands this. As with the aforementioned the method of answer is similar. 

### how to answer 

1. Query for the Package record(s) associated with the Dataset and ensure those records have been package enriched. Note that unlike the aforementioned question, we use a different value for numberVersionsBehindHead to ensure we get all package enriched records. This query will show you all package index enriched records where the most recent version published by the vendor was eighteen months or more prior to current date.  

```
https://{DATA_SERVICE_HOST}/api/v1/db/datasetMetrics/package/query?size=100&isCurrent=true&datasetName={DATASET_NAME}&numberVersionsBehindHead=gte.0&mostRecentVersionPublishedAt=lte.{EIGHTEEN_MONTHS_PRIOR_TO_NOW_IN_ISO_8601_FORMAT}
```

