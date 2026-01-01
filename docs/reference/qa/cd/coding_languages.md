## Q: Show me the coding languages represented in our company and rank them by greatest to least amount of code

### context

We can't answer questions about how much quantity of code. What we can do is use two other pieces of information to answer the question.

* number of datasources by code ecosystem 
* number of packages by datasource 

When answering this question make sure the user understands this. 

### how to answer

1. To answer this question pull from the datasourceMetricsCurrent table. There will be one record per datasource and it will have information including the type of datasource (contained within the purl - see [How we reference information and sources therein](../../pf_core_concepts/pf_data_nomenclature.md) for more information on how to parse a datasource purl). Parse the number of packages, and the count of datasources by type (pypi, maven, npm, etc) and report that to the user. Note how we are using the page size parameter to reduce the number of network calls as well as the select parameter to ensure you're only working with the subset of data you need to do the job. Lastly we're sorting by packages (desc) to make it easier to figure out which datasources are largest by that measure. 

```
https://{DATA_SERVICE_HOST}/api/v1/db/datasourceMetricsCurrent/query?size=500&select=purl,packages,sort=packages.desc
```

2. Double check your answer by quering the datasetMetrics table for the `packages` column which indicates the total number of packages in the dataset. If you end up with a tally that's larger than the total number of packages in the dataset you've done something wrong! Note that we're using the size and sort parameters to ensure we're getting the most current record by commitDateTime. 

```
https://{DATA_SERVICE_HOST}/api/v1/db/datasetMetrics/query?select=packages&isCurrent=true&datasetName={DATASET_NAME}&size=1&sort=commitDateTime.desc
```