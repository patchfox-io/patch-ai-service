# How PatchFox creates recommendations
PatchFox has a set of business goals it will always process recommendations against. They are: 

* REDUCE CVES
* REDUCE CVE GROWTH 
* REDUCE CVE BACKLOG
* REDUCE CVE BACKLOG GROWTH
* REDUCE STALE PACKAGES
* REDUCE STALE PACKAGES GROWTH
* REDUCE DOWNLEVEL PACKAGES
* REDUCE DOWNLEVEL PACKAGES GROWTH
* GROW PATCH EFFICACY
* REMOVE REDUNDANT PACKAGES

Each one of those is tied to a set of metrics tracked at the Dataset level on a per-commit basis. PatchFox knows what the actual state of the Dataset is, and by way of the ML forecast, it knows where the metrics are likely to land in future. PatchFox uses these two pieces of information to, for every business goal in the aforementioned list, create an ordered list of Patch recommendations that represent the fastest way to improve the metrics associated with the business goal. 
