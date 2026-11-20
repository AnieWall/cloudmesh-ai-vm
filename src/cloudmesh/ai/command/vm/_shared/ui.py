from rich.console import Console
from rich.table import Table

console = Console()


def render_table(
    title: str,
    columns: list[str],
    rows: list[list],
    alignments: list[str] | None = None,
    no_wrap: list[str] | None = None,
):
    """Render a Rich table for CLI output.

    This helper mirrors the implementation in ``cloudmesh.ai.command._shared.ui``
    but historically lived as a duplicated copy. The original version lacked a
    ``no_wrap`` parameter, which caused long column values – most notably VM names –
    to be truncated when the terminal width was limited. Adding this argument
    restores parity and allows callers to request that specific columns never be
    wrapped or shortened.

    Args:
        title: Table title.
        columns: List of column headers.
        rows: List of rows (each row is a list of items).
        alignments: Optional list of alignments ("left", "center", "right") for
            each column.
        no_wrap: Optional list of column headers whose cell contents should be
            displayed without wrapping or truncation.
    """
    table = Table(title=title, show_header=True, header_style="bold magenta")

    for i, col in enumerate(columns):
        # Default alignment is "left" unless specified otherwise
        align = "left"
        if alignments and i < len(alignments):
            align = alignments[i]

        # ``no_wrap`` behaves like the counterpart in the shared UI module –
        # columns listed here will be rendered in full regardless of terminal
        # width.
        table.add_column(col, justify=align, no_wrap=bool(no_wrap and col in no_wrap))

    for row in rows:
        table.add_row(*[str(item) for item in row])

    console.print(table)
