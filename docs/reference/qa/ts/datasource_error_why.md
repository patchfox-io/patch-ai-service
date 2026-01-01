# Q: Why does PatchFox say {repo/datasource} is in ERROR state?

### context 
"ERROR state" can mean two different things in the context of a datasource. It can mean either there was a failure to ingest a datasourceEvent from that datasource or it can mean there was a pipeline processing issue for that datasource during the last job. 

### how to answer 

1. see aforementioned context. 

2. if the issue is ingesting the last datasourceEvent, tell the user you see the error flag and if it's a 4xx error report it as such and provide the likely reason for it given the meaning of the code. If it is a 5xx code tell the user you see the trouble flag but are not sure why it occurred and that you have sent a message to the PatchFox engineers for support. 

3. if the issue is a pipeline processing error tell the user you see the trouble flag but are not sure why it occurred and that you have sent a message to the PatchFox engineers for support. 