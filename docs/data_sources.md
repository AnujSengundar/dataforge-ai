# Data Sources

The first version of DataForge AI will focus on job postings and skill trends. The project should begin with simple, controlled data before adding more complex real-world sources.

## Recommended Starting Point

Start with synthetic or sample CSV data first.

This approach keeps Day 2 and the early schema-design phase clean and predictable. It allows the project to define core entities such as jobs, companies, skills, locations, salaries, and posting dates before dealing with API limits, inconsistent formats, or website restrictions.

Example starter CSV files could include:

- `jobs.csv`
- `companies.csv`
- `skills.csv`
- `job_skills.csv`
- `locations.csv`

## Possible Data Source Categories

### Public APIs

Potential APIs or API-style sources for job and labor-market data include:

- USAJOBS API for United States federal job postings.
- Adzuna API for job listings and labor-market data.
- Arbeitnow API for job postings.
- Remotive API for remote job postings.
- Remote OK API for remote job data, subject to its usage terms.
- GitHub Jobs-style datasets or archived job data, where legally available.

APIs are useful because they usually provide structured data and clearer usage rules than scraping web pages.

### Public Datasets

Possible public dataset sources include:

- Kaggle job posting datasets.
- Google Dataset Search results for job postings, salaries, and skill trends.
- Government labor datasets such as O*NET, Bureau of Labor Statistics data, and other open labor-market sources.
- Public salary or employment datasets released for research or education.
- Open data portals from cities, states, or countries.

Public datasets are useful for historical analysis, skill mapping, and warehouse modeling.

### CSV Files

CSV files are the best initial source for this project.

Possible CSV-based inputs include:

- Manually created sample job postings.
- Synthetic job postings generated for testing.
- Downloaded public datasets that allow reuse.
- Curated skill-taxonomy files.
- Manually maintained lists of companies, job roles, locations, and technologies.

CSV files make it easier to build and test the first ingestion pipeline, OLTP schema, warehouse schema, and Power BI dashboards.

### Manual Sample Data

Manual sample data can be used during the earliest stage of the project.

This data should include realistic examples for:

- Job title
- Company name
- Location
- Remote or onsite status
- Salary range
- Experience level
- Employment type
- Required skills
- Job description
- Posting date

Manual data is not meant to be the final data source. It is a practical way to develop the project structure before connecting real data.

## Scraping Considerations

Web scraping should not be implemented yet.

If scraping is added later, it must respect:

- Website terms of service.
- `robots.txt` rules.
- Rate limits and responsible request behavior.
- Legal and ethical data-use expectations.
- Privacy and personal-data concerns.

The preferred path is to start with synthetic or sample CSV data, then use APIs and public datasets before considering any scraping.

## Initial Data Strategy

The initial data strategy is:

1. Create sample CSV data for job market entities.
2. Design OLTP tables around job postings, companies, locations, and skills.
3. Design warehouse tables for analytics and reporting.
4. Build ingestion from CSV into PostgreSQL.
5. Add public APIs or public datasets after the base schema is stable.
