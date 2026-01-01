from datetime import datetime

from pydantic import BaseModel
from typing import Optional


class Dataset(BaseModel):
    id: Optional[int] = None
    latest_job_id: Optional[str] = None
    latest_txid: Optional[str] = None
    name: Optional[str] = None
    status: Optional[str] = None
    updated_at: Optional[datetime] = None


class DatasetMetrics(BaseModel):
    id: Optional[int] = None
    commit_date_time: Optional[datetime] = None
    critical_findings: Optional[int] = None
    critical_findings_avoided_by_patching_past_year: Optional[int] = None
    critical_findings_in_backlog_between_sixty_and_ninety_days: Optional[str] = None
    critical_findings_in_backlog_between_thirty_and_sixty_days: Optional[str] = None
    critical_findings_in_backlog_over_ninety_days: Optional[str] = None
    datasource_count: Optional[int] = None
    datasource_event_count: Optional[int] = None
    different_patches: Optional[int] = None
    downlevel_packages: Optional[int] = None
    downlevel_packages_major: Optional[int] = None
    downlevel_packages_minor: Optional[int] = None
    downlevel_packages_patch: Optional[int] = None
    event_date_time: Optional[datetime] = None
    findings_avoided_by_patching_past_year: Optional[int] = None
    findings_in_backlog_between_sixty_and_ninety_days: Optional[str] = None
    findings_in_backlog_between_thirty_and_sixty_days: Optional[str] = None
    findings_in_backlog_over_ninety_days: Optional[str] = None
    forecast_maturity_date: Optional[datetime] = None
    high_findings: Optional[int] = None
    high_findings_avoided_by_patching_past_year: Optional[int] = None
    high_findings_in_backlog_between_sixty_and_ninety_days: Optional[str] = None
    high_findings_in_backlog_between_thirty_and_sixty_days: Optional[str] = None
    high_findings_in_backlog_over_ninety_days: Optional[str] = None
    is_current: Optional[bool] = None
    is_forecast_recommendations_taken: Optional[bool] = None
    is_forecast_same_course: Optional[bool] = None
    job_id: Optional[str] = None
    low_findings: Optional[int] = None
    low_findings_avoided_by_patching_past_year: Optional[int] = None
    low_findings_in_backlog_between_sixty_and_ninety_days: Optional[str] = None
    low_findings_in_backlog_between_thirty_and_sixty_days: Optional[str] = None
    low_findings_in_backlog_over_ninety_days: Optional[str] = None
    medium_findings: Optional[int] = None
    medium_findings_avoided_by_patching_past_year: Optional[int] = None
    medium_findings_in_backlog_between_sixty_and_ninety_days: Optional[str] = None
    medium_findings_in_backlog_between_thirty_and_sixty_days: Optional[str] = None
    medium_findings_in_backlog_over_ninety_days: Optional[str] = None
    package_indexes: Optional[list[int]] = None
    packages: Optional[int] = None
    packages_with_critical_findings: Optional[int] = None
    packages_with_findings: Optional[int] = None
    packages_with_high_findings: Optional[int] = None
    packages_with_low_findings: Optional[int] = None
    packages_with_medium_findings: Optional[int] = None
    patch_efficacy_score: Optional[str] = None
    patch_effort: Optional[str] = None
    patch_fox_patches: Optional[int] = None
    patch_impact: Optional[str] = None
    patches: Optional[int] = None
    recommendation_headline: Optional[str] = None
    recommendation_type: Optional[str] = None
    rps_score: Optional[str] = None
    same_patches: Optional[int] = None
    stale_packages: Optional[int] = None
    stale_packages_one_year: Optional[int] = None
    stale_packages_one_year_six_months: Optional[int] = None
    stale_packages_six_months: Optional[int] = None
    stale_packages_two_years: Optional[int] = None
    total_findings: Optional[int] = None
    txid: Optional[str] = None
    dataset_id: Optional[int] = None


class Datasource(BaseModel):
    id: Optional[int] = None
    commit_branch: Optional[str] = None
    domain: Optional[str] = None
    first_event_received_at: Optional[datetime] = None
    last_event_received_at: Optional[datetime] = None
    last_event_received_status: Optional[str] = None
    latest_job_id: Optional[str] = None
    latest_txid: Optional[str] = None
    name: Optional[str] = None
    number_event_processing_errors: Optional[str] = None
    number_events_received: Optional[str] = None
    package_indexes: Optional[list[int]] = None
    purl: Optional[str] = None
    status: Optional[str] = None
    type: Optional[str] = None


class DatasourceEvent(BaseModel):
    id: Optional[int] = None
    analyzed: Optional[bool] = None
    commit_branch: Optional[str] = None
    commit_date_time: Optional[datetime] = None
    commit_hash: Optional[str] = None
    event_date_time: Optional[datetime] = None
    forecasted: Optional[bool] = None
    job_id: Optional[str] = None
    oss_enriched: Optional[bool] = None
    package_index_enriched: Optional[bool] = None
    # payload: Optional[bytes] = None
    processing_error: Optional[str] = None
    purl: Optional[str] = None
    recommended: Optional[bool] = None
    status: Optional[str] = None
    txid: Optional[str] = None
    datasource_id: Optional[int] = None


class Edit(BaseModel):
    id: Optional[int] = None
    after: Optional[str] = None
    avoids_vulnerabilities_rank: Optional[int] = None
    before: Optional[str] = None
    commit_date_time: Optional[datetime] = None
    critical_findings: Optional[int] = None
    decrease_backlog_rank: Optional[int] = None
    decrease_vulnerability_count_rank: Optional[int] = None
    edit_type: Optional[str] = None
    event_date_time: Optional[datetime] = None
    grow_patch_efficacy_index: Optional[int] = None
    high_findings: Optional[int] = None
    increase_impact_rank: Optional[int] = None
    is_pf_recommended_edit: Optional[bool] = None
    is_same_edit: Optional[bool] = None
    is_user_edit: Optional[bool] = None
    low_findings: Optional[int] = None
    medium_findings: Optional[int] = None
    reduce_cve_backlog_growth_index: Optional[int] = None
    reduce_cve_backlog_index: Optional[int] = None
    reduce_cve_growth_index: Optional[int] = None
    reduce_cves_index: Optional[int] = None
    reduce_downlevel_packages_growth_index: Optional[int] = None
    reduce_downlevel_packages_index: Optional[int] = None
    reduce_stale_packages_growth_index: Optional[int] = None
    reduce_stale_packages_index: Optional[int] = None
    remove_redundant_packages_index: Optional[int] = None
    same_edit_count: Optional[int] = None
    dataset_metrics_id: Optional[int] = None
    datasource_id: Optional[int] = None


class Finding(BaseModel):
    id: Optional[int] = None
    identifier: Optional[str] = None


class FindingData(BaseModel):
    id: Optional[int] = None
    cpes: Optional[list[str]] = None
    description: Optional[str] = None
    identifier: Optional[str] = None
    patched_in: Optional[list[str]] = None
    published_at: Optional[datetime] = None
    reported_at: Optional[datetime] = None
    severity: Optional[str] = None
    finding_id: Optional[int] = None


class FindingReporter(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None


class Package(BaseModel):
    id: Optional[int] = None
    most_recent_version: Optional[str] = None
    most_recent_version_published_at: Optional[datetime] = None
    name: Optional[str] = None
    namespace: Optional[str] = None
    number_major_versions_behind_head: Optional[int] = None
    number_minor_versions_behind_head: Optional[int] = None
    number_patch_versions_behind_head: Optional[int] = None
    number_versions_behind_head: Optional[int] = None
    purl: Optional[str] = None
    this_version_published_at: Optional[str] = None
    type: Optional[str] = None
    updated_at: Optional[datetime] = None
    version: Optional[str] = None


class PackageFamily(BaseModel):
    dataset_metrics_id: Optional[int] = None
    package_family: Optional[str] = None


class PackageFinding(BaseModel):
    package_id: Optional[int] = None
    finding_id: Optional[int] = None