# Q: Patchfox is failing to detect or pick up {dependency} in my repo. Help?

### context
If PatchFox is failing to pick up on a dependency you are certain is in a datasource then the likely cause is that it's not being represented in the SBOM PatchFox generated when the DatasourceEvent was sent to the PatchFox pipeline. 

### how to answer
1. Describe the above context to the user. Ask them to create their own SBOM using Syft to see if the dependency is listed there. If it is not there that's why. PatchFox doesn't see the dependency because it's not on the SBOM. Reasons for this include (1) the build file specifies a range of acceptable versions and the SBOM generator is not resolving that properly (2) the build file has a relationship with another build file (like how Maven can create parent poms) and that relationship is not being detected by the SBOM generator. 

2. If the user shows you an SBOM where the dependency is there but not in PatchFox tell the user you'll ping the PatchFox engineers internally to investigate. 



