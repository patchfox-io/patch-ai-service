## Q: How Much of the Dataset is Different Versions of the Same Thing? 

### context
The Redundant Package Score measure, stored in the DatasetMetrics table, is the answer to this question. It is a measure indicating the percentage of the Packages in the Dataset at that time are different versions of the same thing. See [Custom Metrics](../../custom_metrics.md) for more information. 

### how to answer 
1. Query the for the current DatasetMetrics record(s) for the Dataset(s) scoped to the user's request. We use the size parameter to ensure the first page contains only the record you need. No need to look through the other pages. 

```
https://{DATA_SERVICE_HOST}/api/v1/db/datasetMetrics/query?sort=commitDateTime.desc&size=1&datasetName={DATASET_NAME}&isCurrent=true&select=rpsScore
```

2. Extract the RPS score from the record and report it to user as a percentage. 
