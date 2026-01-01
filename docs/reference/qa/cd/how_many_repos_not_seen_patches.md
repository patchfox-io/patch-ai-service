## Q: How many repos have not seen patch updates in more than {TIME_DURATION}?

### context 

User is actually asking after datasources. Query the datasource table for records that have a lastEventReceivedAt prior to {PRESENT_TIME} - {TIME_DURATION}. Remember that all time designations to PatchFox must be made in ISO-8601 format. 

### how to answer 

1. Call data-service to get the datasource records the user is asking after. 

Note: 

* we're using the "select" argument to ensure you only get the data you need to answer the question.

* we are using the the search criteria "lte" to retrive only records with latestEventReceivedAt values prior to or equal to {PRESENT_TIME} - {DURATION}.

* we're requesting the status field so you can report any datasources that had an issue ingesting the last datasourceEvent sent to it. 

```
https://{DATA_SERVICE_HOST}/api/v1/db/dataSource/query?select=purl,lastEventReceivedAt,status&latestEventReceivedAt=lte.{TIME}
```

2. report the datasources to the user - ensuring to call out any with a status that indicates an issue. 
