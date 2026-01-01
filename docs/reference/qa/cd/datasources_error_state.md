## Q: Are any Datasources currently in ERROR state?

### context 
The datasource table has this information. We need to query the datasource table and select for records that have error status. 

### how to answer 

1. find the datasource(s) in error state.

```
https://{DATA_SERVICE_HOST}/api/v1/db/datasource/query?status=error
```
