# MVP Requirements

## Functional Requirements

- Users can upload a CSV file.
- The system validates file type, size, and basic readability.
- The system stores file-level metadata such as filename, upload time, row count, column count, and detected columns.
- Users can preview a sample of uploaded rows.
- The system infers column names, likely data types, null counts, uniqueness, and basic statistics.
- The system generates a data profile for numeric, categorical, date, and text columns.
- Raw uploaded data is loaded into a PostgreSQL staging table.
- The system stores profiling output and schema inference results in a PostgreSQL metadata database.
- The system generates basic summary insights, such as missing-value warnings, top categories, numeric ranges, and possible date coverage.
- Users can view dataset metadata, profile results, and basic insights through the application interface.

## Non-Functional Requirements

- The MVP should run locally with Docker Compose.
- The backend should expose clear API boundaries through FastAPI.
- Data storage should use PostgreSQL first for both metadata and warehouse/staging workloads.
- The architecture should support future separation of metadata storage and warehouse storage.
- File processing should be repeatable and traceable through stored metadata.
- The system should handle invalid files gracefully with clear error messages.
- Profiling should be deterministic for the same uploaded file.
- The codebase should remain modular enough to add AI, ML, and MCP capabilities later.
- The first version should avoid paid external services.

## Acceptance Criteria

- A valid CSV can be uploaded successfully.
- The uploaded dataset can be previewed.
- Dataset metadata is stored in PostgreSQL.
- A data profile is generated and persisted.
- Raw data is loaded into a PostgreSQL staging table.
- The system infers likely column types.
- The system returns basic summary insights for the dataset.
- Invalid or unreadable files are rejected with a clear failure reason.
- The full MVP workflow can run locally from a clean Docker Compose setup.

## Success Metrics

- Time from CSV upload to basic insights is under one minute for small sample datasets.
- At least 95% of valid sample CSV files complete the MVP workflow successfully.
- Metadata is captured for every successfully uploaded dataset.
- Raw row counts in PostgreSQL match the uploaded file row counts.
- Profile output includes coverage for numeric, categorical, date, and text-like columns.
- The MVP architecture can support the planned AI, ML, and reporting layers without major redesign.
