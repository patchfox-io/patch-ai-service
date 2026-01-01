## Q: Is my {repo/datasource} onboarded to Patchfox?

### context 
Query the datasource table to if the datasource has been onboarded. Given that the user is unlikely to give you the full purl of the datasource you may end up with several records that could match the user query. As always - gain agreement with the user as to which purl they are asking after before fully answering the question. 

### how to answer

1. Query the datasource table - taking care to select for only the fields we need. 

```
https://{DATA_SERVICE_HOST}/api/v1/db/datasource/query?purl={DATASOURCE_NAME}select=purl,lastEventReceivedStatus,numberEventsReceived,numberEventProcessingErrors,lastEventReceivedAt
```

2. If nothing comes back then the answer is "no it's not onboarded" If multiple records come back then gain agreement with the user as to which the user is asking after then respond accordingly. The "lastEventReceivedStatus" field will tell you whether or not the last event received was successfully ingested by PatchFox. Fields "numberEventsReceived" and "numberEventProcessingErrors" will give you counts for how many events were successfully ingested vs not, respectively. Field "lastEventReceivedAt" will tell you when the last event was received by PatchFox from this datasource. Always report date/time to user in ISO 8601 format. 

