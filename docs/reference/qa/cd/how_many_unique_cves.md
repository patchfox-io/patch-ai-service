## Q: How many unique of CVEs are there?

### context 
This one is very similar to [Q: Do I have Log4Shell (or some other name brand vuln)?](./do_i_have_megaturtle.md) except that you are looking for a complete list of finding TYPES whereas with the aforementioned you are seeking specific findings by identifier. 


### how to answer 

1. gain agreement with user as to what vuln(s) they are talking about 

2. query the data-service db api to get a deduplicated list of CVEs. This is why we are using the `findingType` subEntity

```
https://{DATA_SERVICE_HOST}/api/v1/db/datasetMetrics/findingType/query?isCurrent=true,datasetName={DATASET_NAME}
```
