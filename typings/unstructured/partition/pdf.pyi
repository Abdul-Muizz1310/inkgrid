from unstructured.documents.elements import Element

def partition_pdf(
    *, filename: str, strategy: str, infer_table_structure: bool
) -> list[Element]: ...
