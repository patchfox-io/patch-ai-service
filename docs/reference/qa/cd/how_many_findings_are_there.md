## Q: How many findings are there?

### context
here you need only the most current [datasetMetrics](../../../reference/entities/entities.md#datasetmetrics) record. It will contain the current counts. 

### how to answer

1. query the data-service.

```
https://{DATA_SERVICE_HOST}/api/v1/db/datasetMetrics/query?isCurrent=true,datasetName={DATASET_NAME}&size=1&sort=commitDateTime.desc&select=totalFindings,criticalFindings,highFindings,lowFindings,packages,packagesWithCriticalFindings,packagesWithHighFindings,packagesWithMediumFindings,packagesWithLowFindings
```