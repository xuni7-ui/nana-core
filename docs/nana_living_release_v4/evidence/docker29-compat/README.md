# Docker 29 image identity compatibility — independent archive inspection

The original V4.0.3 ZIP remains unchanged. The associated audit streams the
archive and verifies the OCI manifest and config blob SHA256/size, all layer
blob digests/sizes, and the ordered config rootfs diff_ids. The result confirms
the reported config/manifest distinction in the original bytes.

The host T2–T4 READY_FOR_SWITCH is user-reported, not independently observed in
this workspace. The host patch and WORKCOPY_SEAL were not accessible here at the
time of this inspection. No modified deployment tool, Docker 29 qualification,
production change, or T5 authorization is claimed by this evidence alone.
