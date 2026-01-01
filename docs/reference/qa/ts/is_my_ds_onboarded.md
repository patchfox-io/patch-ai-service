# Q: Is my {repo/datasource} onboarded to Patchfox?

### context 
This is a simple check to the data-service core api to see if the Datasource is registered and if it is presently in an error state.

### how to answer

1. Call data-service core API to get list of Datasources 

```
https://{DATA_SERVICE_HOST}/api/v1/db/datasources?purl={DATASOURCE_NAME}
```

2. Look for {DATASOURCE_NAME} in the records and report findings to user. 

3. If the datasource is onboarded by in an error state see [Q: Why does PatchFox say {repo/datasource} is in ERROR state?](./datasource_error_why.md)

