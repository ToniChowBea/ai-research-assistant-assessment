from research_assistant.data_api import analysis, introspection, lookups


async def list_projects(status: str | None = None) -> list[dict]:
    """List research projects on the platform
    Args:
        status: Optional filter - 'Active' or 'Completed. Omit for all projects
    """
    return await lookups.list_projects(status)


async def get_project(project_id: str) -> dict:
    """Get one project's details plus the datasets linked to it.
    Returns found=False with error message if not found.
    Args:
        project_id: The unique identifier of the project to retrieve.
    """
    return await lookups.get_project(project_id)


async def search_projects(query: str) -> list[dict]:
    """Search research projects by keyword in their title or organisation
    (the organisation is the clinical discipline/theme, e.g. 'Public Health',
    'Digital Health', 'Cardiology'). Use for topic and theme questions about
    research, e.g. 'asthma', 'public health', 'digital health'. Pair with
    search_datasets when a question spans both.
    Args:
        query: A topic or discipline keyword, e.g. 'asthma' or 'public health'.
    """
    return await lookups.search_projects(query)


async def search_datasets(query: str) -> list[dict]:
    """Search datasets by keyword across name, description and field names.
    Args:
        query: A topic keyword, e.g. 'diabetes', 'heart failure', 'hba1c'.
    """
    return await lookups.search_datasets(query)


async def list_datasets() -> list[dict]:
    """List every dataset with its id, name, record count and restricted flag.
    Use this for questions spanning all datasets, restricted datasets, or
    datasets filtered by record count — one call instead of many. Use
    get_dataset_metadata when you need a single dataset's fields and full
    description.
    """
    return await lookups.list_datasets()


async def get_dataset_metadata(dataset_id: str) -> dict:
    """Get a dataset's full metadata: description, record count, restricted flag,
    and its list of fields.
    Returns found=False with an error message if the id does not exist.
    Args:
        dataset_id: Dataset id, e.g. 'DS001'. Case-insensitive.
    """
    return await lookups.get_dataset_metadata(dataset_id)


async def list_researchers(username: str | None = None) -> list[dict]:
    """List researchers with their role and the project ids they can access.
    A projects value of '*' means access to all projects (administrator).
    Args:
        username: Optional — return only this researcher, e.g. 'alice'.
    """
    return await lookups.list_researchers(username)


async def describe_schema(dataset_id: str) -> dict:
    """Get the SQL table name and typed columns for a dataset's analytical data.
    Call this before writing any analytical query for a dataset.
    Args:
        dataset_id: Dataset id, e.g. 'DS001'. Case-insensitive.
    """
    return await introspection.describe_schema(dataset_id)


async def sample_rows(dataset_id: str, n: int = 3) -> dict:
    """See a few real rows from a dataset, to learn actual value formats
    (e.g. sex is 'F'/'M', smoking_status is 'ex-smoker').
    Args:
        dataset_id: Dataset id, e.g. 'DS001'.
        n: Number of rows, 1-5.
    """
    return await introspection.sample_rows(dataset_id, n)


async def list_distinct_values(dataset_id: str, column: str) -> dict:
    """List the exact distinct values of one column. Use before filtering on a
    categorical column so the filter value matches exactly.
    Args:
        dataset_id: Dataset id, e.g. 'DS003'.
        column: Column name as returned by describe_schema.
    """
    return await introspection.list_distinct_values(dataset_id, column)


async def run_analysis(
    dataset_id: str,
    metric: str,
    column: str | None = None,
    group_by: str | None = None,
    filters: list[dict] | None = None,
) -> dict:
    """Run a governed analysis on a dataset.
    Args:
        dataset_id: e.g 'DS001'
        metric: one of count, avg, sum, min, max
        column: required for avg/sum/min/max
        group_by: optional column to group results by
        filters: optional list
    """
    return await analysis.run_analysis(dataset_id, metric, column, group_by, filters)
