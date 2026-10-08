"""The file a ParseBench example's saved Markdown lives in: shared by the run and its driver.

Dependency-free, so the driver can import it inside parse-bench's own environment.
"""


def saved_name(example_id: str) -> str:
    """`table/<stem>` is saved as `table__<stem>.md`."""
    return example_id.replace("/", "__") + ".md"
