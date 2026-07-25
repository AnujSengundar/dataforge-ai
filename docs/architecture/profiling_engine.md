# Dataset Profiling Engine

The Dataset Profiling Engine computes deterministic, non-LLM metadata for each physical dataset version. Profiles belong to `dataset_version_id`, not directly to a logical dataset.

## Architecture

Profiling runs as part of dataset-version ingestion. The ingestion flow reads the uploaded tabular file once with Polars, computes dataset-level metrics, computes enhanced column metrics, and persists one current profile plus one column metadata row per column.

The current design uses Pattern A: one current profile per dataset version. Re-profiling replaces the existing profile and column metadata only after successful computation. Failed writes roll back partial profile/column changes and retain the dataset-version record for auditability.

## Dataset-Level Metrics

| Metric | Definition |
|---|---|
| `row_count` | Number of rows in the dataset version. |
| `column_count` | Number of columns in the dataset version. |
| `duplicate_row_count` | Duplicate occurrences after the first occurrence in each duplicate group. |
| `duplicate_row_percentage` | `duplicate_row_count / row_count * 100`; `0.0` when row count is zero. |
| `fully_null_row_count` | Rows where all columns are null. |
| `fully_null_row_percentage` | `fully_null_row_count / row_count * 100`; `0.0` when row count is zero. |
| `estimated_memory_bytes` | Polars estimated in-memory dataframe size. |
| `source_file_size_bytes` | Uploaded source file size in bytes. |
| `profiling_duration_ms` | Wall-clock profiling duration in milliseconds. |
| `profiled_at` | Time when the profile was generated. |

## Column Metrics

Column metadata includes physical dtype, normalized logical type, null counts, null percentage, non-null count, distinct count excluding nulls, unique percentage, bounded sample values, safe min/max, numeric mean, numeric median, numeric standard deviation, string length metrics, date ranges, top values, and deterministic detection flags.

`unique_percentage = distinct_non_null_count / non_null_count * 100`. If non-null count is zero, `unique_percentage = 0.0`.

## Logical Types

Logical type inference is normalized to:

- `integer`
- `decimal`
- `boolean`
- `string`
- `date`
- `datetime`
- `unknown`

Physical source dtype is preserved separately as `physical_type`.

## Detection Heuristics

All thresholds are configured through settings and expressed as percentage units where applicable.

| Detection | Rule |
|---|---|
| Fully null | `non_null_count == 0`. |
| Constant | `distinct_non_null_count == 1`; fully null columns are not constant. |
| High null | `null_percentage >= PROFILE_HIGH_NULL_THRESHOLD`. |
| Candidate identifier | Non-null count is positive, unique percentage meets threshold, null percentage is below threshold, and decimal measurement columns are avoided unless name hints suggest identifier semantics. |
| Candidate categorical | Non-null count is positive, distinct count is greater than one, unique percentage is below threshold, distinct count is under the maximum, logical type is string/integer/boolean, and the column is not an identifier. |
| Numeric as text | A bounded sample of string/unknown values meets `PROFILE_NUMERIC_TEXT_MATCH_THRESHOLD`. |
| Datetime as text | A bounded sample of string/unknown values matches controlled date/datetime formats and is not better explained as numeric text. |

## Configuration

```text
PROFILE_HIGH_NULL_THRESHOLD=40.0
PROFILE_IDENTIFIER_UNIQUE_THRESHOLD=98.0
PROFILE_IDENTIFIER_MAX_NULL_PERCENTAGE=1.0
PROFILE_CATEGORICAL_UNIQUE_THRESHOLD=5.0
PROFILE_CATEGORICAL_MAX_DISTINCT=100
PROFILE_TYPE_COERCION_SAMPLE_SIZE=1000
PROFILE_NUMERIC_TEXT_MATCH_THRESHOLD=95.0
PROFILE_DATETIME_TEXT_MATCH_THRESHOLD=95.0
PROFILE_SAMPLE_VALUES=5
PROFILE_SAMPLE_MAX_CHARS=200
```

Percentage values must be between `0` and `100`. Sample sizes and max string lengths must be positive.

## API Examples

Get a dataset-version profile:

```http
GET /api/datasets/{dataset_id}/versions/{version_id}/profile
```

Get columns ordered by ordinal position:

```http
GET /api/datasets/{dataset_id}/versions/{version_id}/columns
```

Get one column:

```http
GET /api/datasets/{dataset_id}/versions/{version_id}/columns/{column_name}
```

## Performance Characteristics

The profiler uses Polars vectorized operations, bounded sample checks, bounded sample storage, and single-read ingestion where possible. It avoids Spark, distributed processing, row-by-row statistics loops, and LLM calls.

## Known Limitations

- No immutable profile-run history yet.
- Manual re-profiling API is not exposed yet.
- Datetime-as-text detection intentionally uses controlled formats instead of locale-dependent parsing.
- Complex nested column types are classified as `unknown`.
