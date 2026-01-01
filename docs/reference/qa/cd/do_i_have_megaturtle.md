## Q: Do I have Log4Shell (or some other name brand vuln)?

### context 
This question revolves around your ability to translate {SOME_VULN_NAME} to {SOME_CVE}. Once you do that it's a simple matter of looking at the current findings for {DATASET_NAME}

### how to answer 

1. gain agreement with user as to what vuln(s) they are talking about 

2. map the name of the vuln to the identifier

3. query the data-service db api to get see whether or not the finding exists. 

```
https://{DATA_SERVICE_HOST}/api/v1/db/datasetMetrics/findingType/query?identifier={COMMA DELIMITED LIST OF CVE OR OTHER FINDING IDENTIFIERS},isCurrent=true,datasetName={DATASET_NAME}
```
