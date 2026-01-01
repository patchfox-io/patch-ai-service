## Q: Which product line has the most vulnerabilities right now?

### context 
First and foremost - you don't have a sense of how "datasource" maps to "product line" so they are really asking one of two questions. They are either asking "which git repos (datasources) have the most findings or they are asking about collections of datasources (dit repos) that to them map to a particular product. 

Your first task is to gain agreement with the user as to which they are talking about. Then make the appropriate calls to the data service and report answer to the user. 

### how to answer

1. If what the user wants is to know which datasources have the most findings, make the following call. This wil give you the top ten datasources by current finding count. 

```
https://{DATA_SERVICE_HOST}/api/v1/db/datasourceMetricsCurrent/query?sort=totalFindings.desc&size=10
```

2. If the user is asking about specific product lines (ie - groups of data sources) you're going to need to know the names of the datasources that constitute the products they are looking for. Once you have them make the appropriate API call(s) and aggregate the finding metrics by datasource name grouping. 

For example, if product "foo" consists of datasources "d1" and "d2" and product "bar" consists of datasources "dx" and "dy" and "dz" then make the following call

```
https://{DATA_SERVICE_HOST}/api/v1/db/datasourceMetricsCurrent/query?sort=totalFindings.desc&purl=d1,d2,dx,dy,dz
```

Combine the numbers for {d1, d1} and {dx, dy, dz} so that you can present a comparrison to the user as to which product line has the most findings. 
