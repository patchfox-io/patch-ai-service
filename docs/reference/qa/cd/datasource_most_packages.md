## Q: Which repo has the most packages?

### context

This is a call to the datasourceMetricsCurrent table to figure out which datasources are larges by package count. Remember "repo" or "git repo" or "repository" means "datasource" to PatchFox. 

### how to answer

1. Call the data service as shown below. Note we use the size parameter in conjunction with the sort parameter to ensure what comes back is a top ten list. Also note that we're using the select parameter to ensure you're not getting more data back than you need in order to answer the question. 

```
https://{DATA_SERVICE_HOST}/api/v1/db/datasourceMetricsCurrent/query?size=10&select=purl,packages,sort=packages.desc
```
