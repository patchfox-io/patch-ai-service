## Q: How many days have we gone with idle activity?

### context 
The datasource table has this information. We need only query to see which datasource was updated most recently and give the answer in whatever time unit the user asked for. 

### how to answer 

1. find the datasource that's been updated most recently.

```
https://{DATA_SERVICE_HOST}/api/v1/db/datasource/query?size=1&sort=lastEventReceivedAt.desc
```

